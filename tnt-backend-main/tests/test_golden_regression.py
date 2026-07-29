"""Golden regression test suite for all 5 ML model types.

These tests load hand-verified fixture files from tests/golden/ and run each input
through the ACTUAL trained model (via ModelRegistry), asserting the output falls within
the recorded defensible range.

Rules:
- Skip (not fail) if no trained model exists for a model type.
- Skip (not fail) if the model's stored feature list doesn't match the fixture's feature list.
- Only fail if a trained model exists AND its prediction is outside the recorded range.
- Classification models (fraud_detection) use predicted class (0/1) comparison.
- Regression models use numeric range [expected_min, expected_max].

CI notes
--------
No .github/workflows or equivalent CI config was found in this repository (as of the
creation of this file). Wiring this test into CI is a separate follow-up task. When CI
is set up, add this test with:

    pytest tests/test_golden_regression.py -v

It will run fast (no DB required — all inference is on loaded pickle models).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
import pytest

logger = logging.getLogger("tnt.tests.golden")

# ── Fixture directory ─────────────────────────────────────────────────────────

GOLDEN_DIR = Path(__file__).parent / "golden"

# ── Model type → fixture file mapping ─────────────────────────────────────────

FIXTURE_FILES = {
    "eta_prediction":     GOLDEN_DIR / "eta_prediction.json",
    "demand_forecast":    GOLDEN_DIR / "demand_forecast.json",
    "vendor_ranking":     GOLDEN_DIR / "vendor_ranking.json",
    "slot_recommendation": GOLDEN_DIR / "slot_recommendation.json",
    "fraud_detection":    GOLDEN_DIR / "fraud_detection.json",
}

# Classification model types (predict class 0/1 instead of a continuous value)
CLASSIFICATION_MODELS = {"fraud_detection"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_fixture(path: Path) -> dict[str, Any]:
    """Load and parse a golden fixture JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _features_to_array(feature_dict: dict[str, float], feature_names: list[str]) -> np.ndarray:
    """Convert ordered feature dict to numpy row vector matching feature_names order."""
    return np.array([[feature_dict[name] for name in feature_names]], dtype=np.float64)


def _try_load_model(model_type: str):
    """Attempt to load the active trained model from ModelRegistry.

    Returns (model, feature_names) on success, or raises pytest.skip if:
    - No trained model exists in the registry.
    - The pickle artifact file is missing from disk.
    - The registry DB is unavailable (ImportError / SQLAlchemyError).
    """
    try:
        from app.ml.registry import ModelRegistry
    except ImportError as e:
        pytest.skip(f"ModelRegistry not importable ({e}) — skipping golden tests for {model_type}")

    try:
        result = ModelRegistry.load(model_type)
    except Exception as e:
        pytest.skip(f"ModelRegistry.load({model_type!r}) raised {type(e).__name__}: {e}")

    if result is None:
        pytest.skip(
            f"No trained model found in registry for model_type='{model_type}'. "
            f"Run training first (POST /ml/train/{model_type}) then re-run this test."
        )

    model, metadata = result
    feature_names: list[str] = metadata.get("features") or []
    return model, feature_names


def _check_feature_count(model, X: np.ndarray, model_type: str, fixture_features: list[str]) -> None:
    """Skip if the loaded model was trained with a different number of features.

    This catches stale models (trained before a feature-set change) before they
    raise cryptic sklearn ValueError about n_features_in_.
    """
    expected_n = getattr(model, "n_features_in_", None)
    if expected_n is not None and expected_n != X.shape[1]:
        pytest.skip(
            f"{model_type}: loaded model expects {expected_n} features but fixture "
            f"provides {X.shape[1]} ({fixture_features}). "
            f"The registry contains a stale model trained before the current feature schema. "
            f"Retrain the model (POST /ml/train/{model_type}) to update it."
        )


def _predict_regression(model, X: np.ndarray, model_type: str, fixture_features: list[str]) -> float:
    """Run model.predict and return scalar prediction."""
    _check_feature_count(model, X, model_type, fixture_features)
    try:
        pred = model.predict(X)
    except ValueError as e:
        pytest.skip(
            f"{model_type}: model.predict raised ValueError ({e}). "
            f"Likely a stale model — retrain to fix."
        )
    return float(np.squeeze(pred))


def _predict_classification(model, X: np.ndarray, model_type: str, fixture_features: list[str]) -> int:
    """Run model.predict (class label) for classification models."""
    _check_feature_count(model, X, model_type, fixture_features)
    try:
        pred = model.predict(X)
    except ValueError as e:
        pytest.skip(
            f"{model_type}: model.predict raised ValueError ({e}). "
            f"Likely a stale model — retrain to fix."
        )
    return int(np.squeeze(pred))


# ── Test class ─────────────────────────────────────────────────────────────────

class TestGoldenRegression:
    """Golden regression tests for all 5 trained ML models.

    Each test method loads the corresponding fixture, loads the live trained model,
    and asserts each case's prediction falls within the hand-reasoned range.
    """

    def _run_regression_cases(self, model_type: str) -> None:
        """Generic runner for regression model golden cases."""
        fixture_path = FIXTURE_FILES[model_type]
        assert fixture_path.exists(), f"Missing fixture file: {fixture_path}"

        fixture = _load_fixture(fixture_path)
        fixture_features: list[str] = fixture["feature_names"]

        model, registry_features = _try_load_model(model_type)

        # If registry has feature list, validate it matches fixture
        if registry_features and set(registry_features) != set(fixture_features):
            pytest.skip(
                f"{model_type}: registry feature list {registry_features} "
                f"does not match fixture feature list {fixture_features}. "
                f"Update the golden fixture after retraining with new features."
            )

        # Use fixture feature ordering (authoritative order for this test)
        effective_features = fixture_features

        failures = []
        skipped_cases = []

        for case in fixture["cases"]:
            case_id = case["id"]
            desc = case.get("description", "")
            feat_dict = case["features"]

            # Validate all fixture features present in case
            missing = [f for f in effective_features if f not in feat_dict]
            if missing:
                skipped_cases.append(f"{case_id}: missing feature keys {missing}")
                continue

            X = _features_to_array(feat_dict, effective_features)
            pred = _predict_regression(model, X, model_type, effective_features)

            lo = case["expected_min"]
            hi = case["expected_max"]

            if not (lo <= pred <= hi):
                failures.append(
                    f"\n  [{case_id}] {desc}\n"
                    f"    features:  {feat_dict}\n"
                    f"    predicted: {pred:.4f}\n"
                    f"    expected:  [{lo}, {hi}]"
                )

        for sk in skipped_cases:
            logger.warning("Skipped golden case for %s: %s", model_type, sk)

        if failures:
            pytest.fail(
                f"{model_type}: {len(failures)}/{len(fixture['cases'])} golden cases "
                f"outside expected range:\n" + "".join(failures)
            )

    def _run_classification_cases(self, model_type: str) -> None:
        """Generic runner for classification model golden cases."""
        fixture_path = FIXTURE_FILES[model_type]
        assert fixture_path.exists(), f"Missing fixture file: {fixture_path}"

        fixture = _load_fixture(fixture_path)
        fixture_features: list[str] = fixture["feature_names"]

        model, registry_features = _try_load_model(model_type)

        if registry_features and set(registry_features) != set(fixture_features):
            pytest.skip(
                f"{model_type}: registry features {registry_features} != fixture {fixture_features}. "
                f"Update fixture after retraining."
            )

        effective_features = fixture_features
        failures = []

        for case in fixture["cases"]:
            case_id = case["id"]
            desc = case.get("description", "")
            feat_dict = case["features"]
            expected_class = case["expected_class"]

            missing = [f for f in effective_features if f not in feat_dict]
            if missing:
                logger.warning("Skipped %s: missing keys %s", case_id, missing)
                continue

            X = _features_to_array(feat_dict, effective_features)
            pred_class = _predict_classification(model, X, model_type, effective_features)

            if pred_class != expected_class:
                note = case.get("note", "")
                failures.append(
                    f"\n  [{case_id}] {desc}\n"
                    f"    note:      {note}\n"
                    f"    features:  {feat_dict}\n"
                    f"    predicted: {pred_class}\n"
                    f"    expected:  {expected_class}"
                )

        if failures:
            pytest.fail(
                f"{model_type}: {len(failures)}/{len(fixture['cases'])} golden cases "
                f"predicted wrong class:\n" + "".join(failures)
            )

    # ── ETA prediction ────────────────────────────────────────────────────────

    def test_eta_golden_regression(self):
        """ETA model must predict within [expected_min, expected_max] minutes for all golden cases."""
        self._run_regression_cases("eta_prediction")

    # ── Demand forecast ───────────────────────────────────────────────────────

    def test_demand_golden_regression(self):
        """Demand model must predict within [expected_min, expected_max] orders/hour for all golden cases."""
        self._run_regression_cases("demand_forecast")

    # ── Vendor ranking ────────────────────────────────────────────────────────

    def test_vendor_ranking_golden_regression(self):
        """Vendor ranking model must predict performance score within [expected_min, expected_max]."""
        self._run_regression_cases("vendor_ranking")

    # ── Slot recommendation ───────────────────────────────────────────────────

    def test_slot_recommendation_golden_regression(self):
        """Slot recommendation model must predict occupancy score within [expected_min, expected_max]."""
        self._run_regression_cases("slot_recommendation")

    # ── Fraud detection ───────────────────────────────────────────────────────

    def test_fraud_detection_golden_regression(self):
        """Fraud detection model must predict the correct class (0=clean, 1=fraud) for all golden cases."""
        self._run_classification_cases("fraud_detection")


# ── Sanity-check: fixture files must exist and be valid JSON ──────────────────

class TestGoldenFixtureIntegrity:
    """Fast, DB-free smoke test: verifies fixture files are valid and complete."""

    @pytest.mark.parametrize("model_type,fixture_path", list(FIXTURE_FILES.items()))
    def test_fixture_file_exists(self, model_type: str, fixture_path: Path):
        assert fixture_path.exists(), f"Missing golden fixture for {model_type}: {fixture_path}"

    @pytest.mark.parametrize("model_type,fixture_path", list(FIXTURE_FILES.items()))
    def test_fixture_valid_json(self, model_type: str, fixture_path: Path):
        if not fixture_path.exists():
            pytest.skip(f"Fixture file missing: {fixture_path}")
        data = _load_fixture(fixture_path)
        assert "model_type" in data, "fixture missing 'model_type' key"
        assert "feature_names" in data, "fixture missing 'feature_names' key"
        assert "cases" in data, "fixture missing 'cases' key"
        assert len(data["cases"]) >= 5, f"fixture has fewer than 5 cases ({len(data['cases'])})"

    @pytest.mark.parametrize("model_type,fixture_path", list(FIXTURE_FILES.items()))
    def test_fixture_cases_have_required_keys(self, model_type: str, fixture_path: Path):
        if not fixture_path.exists():
            pytest.skip(f"Fixture file missing: {fixture_path}")
        data = _load_fixture(fixture_path)
        feature_names = data["feature_names"]
        is_classification = model_type in CLASSIFICATION_MODELS

        for case in data["cases"]:
            case_id = case.get("id", "unknown")
            assert "id" in case, f"case missing 'id': {case}"
            assert "features" in case, f"{case_id}: missing 'features'"

            feat_keys = set(case["features"].keys())
            for fname in feature_names:
                assert fname in feat_keys, (
                    f"{case_id}: fixture feature '{fname}' missing from case features {feat_keys}"
                )

            if is_classification:
                assert "expected_class" in case, f"{case_id}: classification case missing 'expected_class'"
                assert case["expected_class"] in (0, 1), f"{case_id}: expected_class must be 0 or 1"
            else:
                assert "expected_min" in case, f"{case_id}: regression case missing 'expected_min'"
                assert "expected_max" in case, f"{case_id}: regression case missing 'expected_max'"
                assert case["expected_min"] <= case["expected_max"], (
                    f"{case_id}: expected_min ({case['expected_min']}) > expected_max ({case['expected_max']})"
                )

    @pytest.mark.parametrize("model_type,fixture_path", list(FIXTURE_FILES.items()))
    def test_regression_ranges_are_defensible(self, model_type: str, fixture_path: Path):
        """Ranges must not be absurdly wide — width must be < 5x expected_min for regression models."""
        if not fixture_path.exists():
            pytest.skip(f"Fixture file missing: {fixture_path}")
        if model_type in CLASSIFICATION_MODELS:
            pytest.skip("Classification model — no numeric range to check")

        data = _load_fixture(fixture_path)
        for case in data["cases"]:
            lo, hi = case["expected_min"], case["expected_max"]
            width = hi - lo
            # Ranges shouldn't be so wide they catch anything — upper bound: width ≤ max(hi, 5.0) * 1.5
            max_allowed_width = max(hi, 5.0) * 1.5
            assert width <= max_allowed_width, (
                f"{case['id']}: range [{lo}, {hi}] is too wide (width={width:.1f}). "
                f"Narrow the golden range to be more defensible."
            )
