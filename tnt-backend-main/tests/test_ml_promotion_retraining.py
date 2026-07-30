"""
Unit tests for:
  - app/ml/promotion.py   (promote_if_better, check_and_rollback_degraded_models)
  - app/ml/retraining.py  (run_single_model_retraining, run_scheduled_retraining)

All deferred imports (train_*, promote_if_better, backtest_*, SessionLocal, RetrainingLog)
live inside function bodies, so they are patched at their ORIGIN modules:
  - app.ml.training_pipeline.train_eta  (not app.ml.retraining.train_eta)
  - app.ml.promotion.promote_if_better  (not app.ml.retraining.promote_if_better)
  - app.ml.backtest.backtest_eta        (not app.ml.promotion.backtest_eta)
  - app.database.session.SessionLocal   (not app.ml.retraining.SessionLocal)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, call

import pytest
from sqlalchemy.orm import Session

from app.ml.promotion import (
    _extract_primary_metric,
    check_and_rollback_degraded_models,
    promote_if_better,
)
from app.ml.retraining import run_scheduled_retraining, run_single_model_retraining
from app.ml.retraining_log_model import RetrainingLog


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_version(
    version_id: str,
    model_type: str,
    status: str = "active",
    metrics: dict | None = None,
    trained_at: datetime | None = None,
) -> dict:
    if trained_at is None:
        trained_at = datetime.now(timezone.utc)
    return {
        "version_id": version_id,
        "model_type": model_type,
        "status": status,
        "metrics": metrics or {},
        "accuracy": None,
        "file_path": f"/tmp/{version_id}.pkl",
        "trained_at": trained_at.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Section 1 — _extract_primary_metric
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractPrimaryMetric:
    """Unit tests for the _extract_primary_metric helper."""

    # --- Classification (fraud_detection) ------------------------------------

    def test_classification_cv_f1(self):
        name, val = _extract_primary_metric("fraud_detection", {"cv_f1": 0.88, "f1": 0.80})
        assert name == "cv_f1"
        assert val == pytest.approx(0.88)

    def test_classification_f1_fallback(self):
        name, val = _extract_primary_metric("fraud_detection", {"f1": 0.80, "accuracy": 0.85})
        assert name == "f1"
        assert val == pytest.approx(0.80)

    def test_classification_accuracy_fallback(self):
        name, val = _extract_primary_metric("fraud_detection", {"accuracy": 0.91})
        assert name == "accuracy"
        assert val == pytest.approx(0.91)

    def test_classification_no_metric_returns_zero(self):
        name, val = _extract_primary_metric("fraud_detection", {})
        assert name == "f1"
        assert val == 0.0

    def test_classification_non_dict_metrics(self):
        name, val = _extract_primary_metric("fraud_detection", None)
        assert name == "f1"
        assert val == 0.0

    # --- Regression (eta_prediction etc.) ------------------------------------

    def test_regression_cv_rmse(self):
        name, val = _extract_primary_metric("eta_prediction", {"cv_rmse": 2.5, "rmse": 4.0})
        assert name == "cv_rmse"
        assert val == pytest.approx(2.5)

    def test_regression_rmse_fallback(self):
        name, val = _extract_primary_metric("eta_prediction", {"rmse": 3.2, "mae": 2.1})
        assert name == "rmse"
        assert val == pytest.approx(3.2)

    def test_regression_mae_fallback(self):
        name, val = _extract_primary_metric("eta_prediction", {"mae": 1.8})
        assert name == "mae"
        assert val == pytest.approx(1.8)

    def test_regression_r2_inverted(self):
        name, val = _extract_primary_metric("slot_recommendation", {"r2": 0.75})
        assert name == "r2_inverted"
        assert val == pytest.approx(1.0 - 0.75)

    def test_regression_no_metric_returns_inf(self):
        name, val = _extract_primary_metric("eta_prediction", {})
        assert name == "rmse"
        assert val == float("inf")

    def test_regression_non_dict_metrics(self):
        name, val = _extract_primary_metric("vendor_ranking", "bad_input")
        assert name == "rmse"
        assert val == float("inf")


# ─────────────────────────────────────────────────────────────────────────────
# Section 2 — promote_if_better
# ─────────────────────────────────────────────────────────────────────────────

class TestPromoteIfBetter:
    """Unit tests for promote_if_better using ModelRegistry monkeypatching."""

    def test_candidate_not_found_returns_false(self):
        with patch("app.ml.promotion.ModelRegistry.get_version", return_value=None):
            assert promote_if_better("eta_prediction", "v1") is False

    def test_first_version_auto_promoted(self):
        cand = _make_version("eta_v1", "eta_prediction", status="inactive")
        with (
            patch("app.ml.promotion.ModelRegistry.get_version", return_value=cand),
            patch("app.ml.promotion.ModelRegistry.list_versions", return_value=[cand]),
            patch("app.ml.promotion.ModelRegistry.set_active_version", return_value=True) as mock_set,
        ):
            result = promote_if_better("eta_prediction", "eta_v1")
        assert result is True
        mock_set.assert_called_once_with("eta_prediction", "eta_v1")

    # --- Regression metric comparison ----------------------------------------

    def test_regression_candidate_better_promoted(self):
        champ = _make_version("eta_v1", "eta_prediction", status="active", metrics={"rmse": 5.0})
        cand  = _make_version("eta_v2", "eta_prediction", status="inactive", metrics={"rmse": 3.0})
        with (
            patch("app.ml.promotion.ModelRegistry.get_version", return_value=cand),
            patch("app.ml.promotion.ModelRegistry.list_versions", return_value=[champ, cand]),
            patch("app.ml.promotion.ModelRegistry.set_active_version", return_value=True) as mock_set,
        ):
            result = promote_if_better("eta_prediction", "eta_v2")
        assert result is True
        mock_set.assert_called_once_with("eta_prediction", "eta_v2")

    def test_regression_candidate_worse_rejected(self):
        champ = _make_version("eta_v1", "eta_prediction", status="active", metrics={"rmse": 2.0})
        cand  = _make_version("eta_v2", "eta_prediction", status="inactive", metrics={"rmse": 6.0})
        with (
            patch("app.ml.promotion.ModelRegistry.get_version", return_value=cand),
            patch("app.ml.promotion.ModelRegistry.list_versions", return_value=[champ, cand]),
            patch("app.ml.promotion.ModelRegistry.set_active_version", return_value=True) as mock_set,
        ):
            result = promote_if_better("eta_prediction", "eta_v2")
        assert result is False
        mock_set.assert_called_once_with("eta_prediction", "eta_v1")

    def test_regression_equal_metric_tie_promotes_candidate(self):
        champ = _make_version("eta_v1", "eta_prediction", status="active", metrics={"rmse": 3.0})
        cand  = _make_version("eta_v2", "eta_prediction", status="inactive", metrics={"rmse": 3.0})
        with (
            patch("app.ml.promotion.ModelRegistry.get_version", return_value=cand),
            patch("app.ml.promotion.ModelRegistry.list_versions", return_value=[champ, cand]),
            patch("app.ml.promotion.ModelRegistry.set_active_version", return_value=True) as mock_set,
        ):
            result = promote_if_better("eta_prediction", "eta_v2")
        assert result is True
        mock_set.assert_called_once_with("eta_prediction", "eta_v2")

    def test_regression_missing_metrics_uses_inf(self):
        """Missing metrics on candidate → inf; any finite champion wins."""
        champ = _make_version("eta_v1", "eta_prediction", status="active", metrics={"rmse": 4.0})
        cand  = _make_version("eta_v2", "eta_prediction", status="inactive", metrics={})
        with (
            patch("app.ml.promotion.ModelRegistry.get_version", return_value=cand),
            patch("app.ml.promotion.ModelRegistry.list_versions", return_value=[champ, cand]),
            patch("app.ml.promotion.ModelRegistry.set_active_version", return_value=True) as mock_set,
        ):
            result = promote_if_better("eta_prediction", "eta_v2")
        # inf > 4.0 → worse → not promoted
        assert result is False
        mock_set.assert_called_once_with("eta_prediction", "eta_v1")

    # --- Classification metric comparison ------------------------------------

    def test_classification_candidate_better_promoted(self):
        champ = _make_version("fraud_v1", "fraud_detection", status="active", metrics={"f1": 0.70})
        cand  = _make_version("fraud_v2", "fraud_detection", status="inactive", metrics={"f1": 0.85})
        with (
            patch("app.ml.promotion.ModelRegistry.get_version", return_value=cand),
            patch("app.ml.promotion.ModelRegistry.list_versions", return_value=[champ, cand]),
            patch("app.ml.promotion.ModelRegistry.set_active_version", return_value=True) as mock_set,
        ):
            result = promote_if_better("fraud_detection", "fraud_v2")
        assert result is True
        mock_set.assert_called_once_with("fraud_detection", "fraud_v2")

    def test_classification_candidate_worse_rejected(self):
        champ = _make_version("fraud_v1", "fraud_detection", status="active", metrics={"f1": 0.90})
        cand  = _make_version("fraud_v2", "fraud_detection", status="inactive", metrics={"f1": 0.60})
        with (
            patch("app.ml.promotion.ModelRegistry.get_version", return_value=cand),
            patch("app.ml.promotion.ModelRegistry.list_versions", return_value=[champ, cand]),
            patch("app.ml.promotion.ModelRegistry.set_active_version", return_value=True) as mock_set,
        ):
            result = promote_if_better("fraud_detection", "fraud_v2")
        assert result is False
        mock_set.assert_called_once_with("fraud_detection", "fraud_v1")

    def test_classification_equal_tie_promotes_candidate(self):
        champ = _make_version("fraud_v1", "fraud_detection", status="active", metrics={"cv_f1": 0.80})
        cand  = _make_version("fraud_v2", "fraud_detection", status="inactive", metrics={"cv_f1": 0.80})
        with (
            patch("app.ml.promotion.ModelRegistry.get_version", return_value=cand),
            patch("app.ml.promotion.ModelRegistry.list_versions", return_value=[champ, cand]),
            patch("app.ml.promotion.ModelRegistry.set_active_version", return_value=True) as mock_set,
        ):
            result = promote_if_better("fraud_detection", "fraud_v2")
        assert result is True
        mock_set.assert_called_once_with("fraud_detection", "fraud_v2")


# ─────────────────────────────────────────────────────────────────────────────
# Section 3 — check_and_rollback_degraded_models
# ─────────────────────────────────────────────────────────────────────────────

# Deferred imports in check_and_rollback_degraded_models:
#   from app.ml.backtest import backtest_eta, backtest_vendor_ranking  → patch at app.ml.backtest.*
#   from app.ml.retraining_log_model import RetrainingLog              → patch at app.ml.retraining_log_model.RetrainingLog
#   from app.database.session import SessionLocal                       → patch at app.database.session.SessionLocal

_ROLLBACK_PATCH_BASE = {
    "list":  "app.ml.promotion.ModelRegistry.list_versions",
    "active": "app.ml.promotion.ModelRegistry.get_active_version",
    "set":   "app.ml.promotion.ModelRegistry.set_active_version",
    "eta_bt": "app.ml.backtest.backtest_eta",
    "vr_bt":  "app.ml.backtest.backtest_vendor_ranking",
}


class TestCheckAndRollbackDegradedModels:
    """Tests for automatic rollback logic with various degradation conditions."""

    def _run(
        self,
        db: Session,
        list_versions_map: dict,
        active_version_map: dict,
        backtest_eta_result: dict | None = None,
        backtest_vendor_result: dict | None = None,
    ) -> dict:
        backtest_eta_result    = backtest_eta_result    or {"status": "no_data"}
        backtest_vendor_result = backtest_vendor_result or {"status": "no_data"}

        with (
            patch(_ROLLBACK_PATCH_BASE["list"],   side_effect=lambda mt: list_versions_map.get(mt, [])),
            patch(_ROLLBACK_PATCH_BASE["active"],  side_effect=lambda mt: active_version_map.get(mt)),
            patch(_ROLLBACK_PATCH_BASE["set"],     return_value=True),
            patch(_ROLLBACK_PATCH_BASE["eta_bt"],  return_value=backtest_eta_result),
            patch(_ROLLBACK_PATCH_BASE["vr_bt"],   return_value=backtest_vendor_result),
        ):
            return check_and_rollback_degraded_models(db=db)

    # --- Skip branches -------------------------------------------------------

    def test_no_versions_skipped(self, db_session: Session):
        results = self._run(db_session, {}, {})
        assert results == {}

    def test_no_active_version_skipped(self, db_session: Session):
        v1 = _make_version("eta_v1", "eta_prediction", status="inactive")
        results = self._run(
            db_session,
            {"eta_prediction": [v1]},
            {"eta_prediction": None},
        )
        assert results == {}

    def test_no_trained_at_skipped(self, db_session: Session):
        v1 = _make_version("eta_v1", "eta_prediction")
        v1["trained_at"] = None
        results = self._run(
            db_session,
            {"eta_prediction": [v1]},
            {"eta_prediction": v1},
        )
        assert results == {}

    def test_model_outside_7_day_window_skipped(self, db_session: Session):
        old_time = datetime.now(timezone.utc) - timedelta(days=10)
        v1 = _make_version("eta_v1", "eta_prediction", trained_at=old_time)
        results = self._run(
            db_session,
            {"eta_prediction": [v1]},
            {"eta_prediction": v1},
        )
        assert results == {}

    def test_no_previous_version_skipped(self, db_session: Session):
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        v1 = _make_version("eta_v1", "eta_prediction", trained_at=recent)
        results = self._run(
            db_session,
            {"eta_prediction": [v1]},
            {"eta_prediction": v1},
        )
        assert results == {}

    # --- ETA backtest --------------------------------------------------------

    def test_eta_backtest_degraded_triggers_rollback(self, db_session: Session):
        recent = datetime.now(timezone.utc) - timedelta(days=2)
        prev   = _make_version("eta_v1", "eta_prediction", status="inactive",
                               metrics={"rmse": 3.0}, trained_at=recent - timedelta(days=5))
        active = _make_version("eta_v2", "eta_prediction", status="active",
                               metrics={"rmse": 5.0}, trained_at=recent)
        # live MAE=5.0, baseline rmse=3.0 → (5-3)/3*100 = 66.7% > 20%
        results = self._run(
            db_session,
            {"eta_prediction": [active, prev]},
            {"eta_prediction": active},
            backtest_eta_result={"status": "success", "mae_minutes": 5.0},
        )
        r = results.get("eta_prediction", {})
        assert r.get("rolled_back") is True
        assert r["previous_version"] == "eta_v1"
        assert r["degraded_version"] == "eta_v2"

    def test_eta_backtest_no_degradation_not_rolled_back(self, db_session: Session):
        recent = datetime.now(timezone.utc) - timedelta(days=2)
        prev   = _make_version("eta_v1", "eta_prediction", status="inactive",
                               metrics={"rmse": 5.0}, trained_at=recent - timedelta(days=5))
        active = _make_version("eta_v2", "eta_prediction", status="active",
                               metrics={"rmse": 3.0}, trained_at=recent)
        results = self._run(
            db_session,
            {"eta_prediction": [active, prev]},
            {"eta_prediction": active},
            backtest_eta_result={"status": "success", "mae_minutes": 3.0},
        )
        assert results.get("eta_prediction", {}).get("rolled_back") is False

    def test_eta_backtest_failed_status_no_rollback(self, db_session: Session):
        recent = datetime.now(timezone.utc) - timedelta(days=2)
        prev   = _make_version("eta_v1", "eta_prediction", status="inactive",
                               metrics={"rmse": 3.0}, trained_at=recent - timedelta(days=5))
        active = _make_version("eta_v2", "eta_prediction", status="active",
                               metrics={"rmse": 10.0}, trained_at=recent)
        results = self._run(
            db_session,
            {"eta_prediction": [active, prev]},
            {"eta_prediction": active},
            backtest_eta_result={"status": "failed"},
        )
        assert results.get("eta_prediction", {}).get("rolled_back") is False

    # --- Vendor ranking backtest ---------------------------------------------

    def test_vendor_ranking_backtest_degraded_triggers_rollback(self, db_session: Session):
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        prev   = _make_version("vr_v1", "vendor_ranking", status="inactive",
                               metrics={"rmse": 2.0}, trained_at=recent - timedelta(days=5))
        active = _make_version("vr_v2", "vendor_ranking", status="active",
                               metrics={"rmse": 3.0}, trained_at=recent)
        # baseline=2.0, live top_1=1.0 → (2-1)/2*100=50% > 20%
        results = self._run(
            db_session,
            {"vendor_ranking": [active, prev]},
            {"vendor_ranking": active},
            backtest_vendor_result={"status": "success", "top_1_hit_rate": 1.0},
        )
        assert results.get("vendor_ranking", {}).get("rolled_back") is True

    def test_vendor_ranking_backtest_no_degradation(self, db_session: Session):
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        prev   = _make_version("vr_v1", "vendor_ranking", status="inactive",
                               metrics={"rmse": 2.0}, trained_at=recent - timedelta(days=5))
        active = _make_version("vr_v2", "vendor_ranking", status="active",
                               metrics={"rmse": 1.5}, trained_at=recent)
        # live=2.5 > baseline=2.0 → no degradation
        results = self._run(
            db_session,
            {"vendor_ranking": [active, prev]},
            {"vendor_ranking": active},
            backtest_vendor_result={"status": "success", "top_1_hit_rate": 2.5},
        )
        assert results.get("vendor_ranking", {}).get("rolled_back") is False

    # --- Fraud detection (classification) ------------------------------------

    def test_fraud_detection_degraded_triggers_rollback(self, db_session: Session):
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        prev   = _make_version("fraud_v1", "fraud_detection", status="inactive",
                               metrics={"f1": 0.90}, trained_at=recent - timedelta(days=5))
        active = _make_version("fraud_v2", "fraud_detection", status="active",
                               metrics={"f1": 0.50}, trained_at=recent)
        results = self._run(
            db_session,
            {"fraud_detection": [active, prev]},
            {"fraud_detection": active},
        )
        assert results.get("fraud_detection", {}).get("rolled_back") is True

    def test_fraud_detection_no_degradation(self, db_session: Session):
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        prev   = _make_version("fraud_v1", "fraud_detection", status="inactive",
                               metrics={"f1": 0.70}, trained_at=recent - timedelta(days=5))
        active = _make_version("fraud_v2", "fraud_detection", status="active",
                               metrics={"f1": 0.80}, trained_at=recent)
        results = self._run(
            db_session,
            {"fraud_detection": [active, prev]},
            {"fraud_detection": active},
        )
        assert results.get("fraud_detection", {}).get("rolled_back") is False

    # --- General regression (demand_forecast, slot_recommendation) -----------

    def test_demand_forecast_degraded_triggers_rollback(self, db_session: Session):
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        prev   = _make_version("dem_v1", "demand_forecast", status="inactive",
                               metrics={"rmse": 2.0}, trained_at=recent - timedelta(days=5))
        active = _make_version("dem_v2", "demand_forecast", status="active",
                               metrics={"rmse": 5.0}, trained_at=recent)
        results = self._run(
            db_session,
            {"demand_forecast": [active, prev]},
            {"demand_forecast": active},
        )
        assert results.get("demand_forecast", {}).get("rolled_back") is True

    def test_demand_forecast_baseline_inf_skips_degradation(self, db_session: Session):
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        prev   = _make_version("dem_v1", "demand_forecast", status="inactive",
                               metrics={}, trained_at=recent - timedelta(days=5))
        active = _make_version("dem_v2", "demand_forecast", status="active",
                               metrics={"rmse": 5.0}, trained_at=recent)
        results = self._run(
            db_session,
            {"demand_forecast": [active, prev]},
            {"demand_forecast": active},
        )
        assert results.get("demand_forecast", {}).get("rolled_back") is False

    # --- Edge cases ----------------------------------------------------------

    def test_invalid_trained_at_string_uses_now(self, db_session: Session):
        """Malformed trained_at falls back to now() → age≈0 → inside window."""
        prev   = _make_version("eta_v1", "eta_prediction", status="inactive",
                               metrics={"rmse": 3.0})
        active = _make_version("eta_v2", "eta_prediction", status="active",
                               metrics={"rmse": 10.0})
        active["trained_at"] = "not-a-valid-date"
        results = self._run(
            db_session,
            {"eta_prediction": [active, prev]},
            {"eta_prediction": active},
            backtest_eta_result={"status": "no_data"},
        )
        assert results.get("eta_prediction", {}).get("rolled_back") is False

    def test_naive_datetime_string_gets_utc_tzinfo(self, db_session: Session):
        """A naive ISO datetime string (no Z / +00:00) parses but has tzinfo=None.
        Line 144 of promotion.py adds UTC tzinfo so age calculation can proceed."""
        recent = datetime.now(timezone.utc) - timedelta(days=2)
        # Strip timezone from the ISO string so fromisoformat gives a naive datetime
        naive_str = recent.strftime("%Y-%m-%dT%H:%M:%S")  # no '+00:00', no 'Z'
        prev   = _make_version("eta_v1", "eta_prediction", status="inactive",
                               metrics={"rmse": 3.0}, trained_at=recent - timedelta(days=5))
        active = _make_version("eta_v2", "eta_prediction", status="active",
                               metrics={"rmse": 10.0})
        active["trained_at"] = naive_str  # naive -> triggers line 144
        results = self._run(
            db_session,
            {"eta_prediction": [active, prev]},
            {"eta_prediction": active},
            backtest_eta_result={"status": "no_data"},
        )
        # Inside 7-day window (age~2 days) but no live metric -> not degraded
        assert results.get("eta_prediction", {}).get("rolled_back") is False

    def test_rollback_db_log_failure_handled(self, db_session: Session):
        """DB commit error during rollback log must not crash the function."""
        recent = datetime.now(timezone.utc) - timedelta(days=2)
        prev   = _make_version("eta_v1", "eta_prediction", status="inactive",
                               metrics={"rmse": 3.0}, trained_at=recent - timedelta(days=5))
        active = _make_version("eta_v2", "eta_prediction", status="active",
                               metrics={"rmse": 10.0}, trained_at=recent)

        with (
            patch(_ROLLBACK_PATCH_BASE["list"],
                  side_effect=lambda mt: [active, prev] if mt == "eta_prediction" else []),
            patch(_ROLLBACK_PATCH_BASE["active"],
                  side_effect=lambda mt: active if mt == "eta_prediction" else None),
            patch(_ROLLBACK_PATCH_BASE["set"],   return_value=True),
            patch(_ROLLBACK_PATCH_BASE["eta_bt"], return_value={"status": "success", "mae_minutes": 50.0}),
            patch(_ROLLBACK_PATCH_BASE["vr_bt"],  return_value={"status": "no_data"}),
            patch.object(db_session, "commit", side_effect=Exception("DB commit boom")),
        ):
            results = check_and_rollback_degraded_models(db=db_session)

        assert results.get("eta_prediction", {}).get("rolled_back") is True

    def test_uses_session_local_when_db_is_none(self, db_session: Session):
        """When db=None, SessionLocal() is called and closed at end."""
        with (
            patch("app.database.session.SessionLocal", return_value=db_session),
            patch.object(db_session, "close", return_value=None) as mock_close,
            patch(_ROLLBACK_PATCH_BASE["list"],   return_value=[]),
            patch(_ROLLBACK_PATCH_BASE["active"],  return_value=None),
        ):
            results = check_and_rollback_degraded_models(db=None)

        mock_close.assert_called_once()
        assert results == {}


# ─────────────────────────────────────────────────────────────────────────────
# Section 4 — run_single_model_retraining
# ─────────────────────────────────────────────────────────────────────────────

# Deferred imports in run_single_model_retraining:
#   from app.ml.training_pipeline import train_eta, ...  → patch at app.ml.training_pipeline.*
#   from app.ml.promotion import promote_if_better       → patch at app.ml.promotion.promote_if_better

_TRAIN_TARGETS = {
    "eta_prediction":      "app.ml.training_pipeline.train_eta",
    "demand_forecast":     "app.ml.training_pipeline.train_demand",
    "slot_recommendation": "app.ml.training_pipeline.train_slot_recommendation",
    "vendor_ranking":      "app.ml.training_pipeline.train_vendor_ranking",
    "fraud_detection":     "app.ml.training_pipeline.train_fraud_detection",
}
_PROMOTE = "app.ml.promotion.promote_if_better"


class TestRunSingleModelRetraining:
    """Tests for run_single_model_retraining covering all branches."""

    def _run(
        self,
        model_type: str,
        db: Session,
        train_result: dict,
        promoted: bool = True,
    ) -> dict:
        target = _TRAIN_TARGETS[model_type]
        with (
            patch(target, return_value=train_result),
            patch(_PROMOTE, return_value=promoted),
        ):
            return run_single_model_retraining(model_type, db)

    # --- All supported model types, "success" + "trained" + promoted ---------

    @pytest.mark.parametrize("model_type", list(_TRAIN_TARGETS.keys()))
    def test_all_model_types_success_promoted(self, db_session: Session, model_type: str):
        # result dict is returned as-is from train_*; only "promoted" key is injected.
        # The DB log gets status="promoted".
        result = self._run(
            model_type, db_session,
            {"status": "success", "version_id": f"{model_type}_v1"},
            promoted=True,
        )
        assert result["status"] == "success"   # original train status
        assert result["promoted"] is True
        log = db_session.query(RetrainingLog).filter_by(
            model_type=model_type, status="promoted"
        ).first()
        assert log is not None

    @pytest.mark.parametrize("model_type", list(_TRAIN_TARGETS.keys()))
    def test_all_model_types_success_not_promoted(self, db_session: Session, model_type: str):
        result = self._run(
            model_type, db_session,
            {"status": "success", "version_id": f"{model_type}_v1"},
            promoted=False,
        )
        assert result["status"] == "success"   # original train status unchanged
        assert result["promoted"] is False
        log = db_session.query(RetrainingLog).filter_by(
            model_type=model_type, status="not_promoted"
        ).first()
        assert log is not None

    def test_trained_status_treated_as_success(self, db_session: Session):
        # "trained" is also treated as success → promote_if_better is called
        result = self._run(
            "eta_prediction", db_session,
            {"status": "trained", "version_id": "eta_v2"},
            promoted=True,
        )
        assert result["status"] == "trained"   # raw status from train_eta
        assert result["promoted"] is True

    # --- success with no version_id (status="success") -----------------------

    def test_success_status_no_version_id(self, db_session: Session):
        with patch(_TRAIN_TARGETS["eta_prediction"], return_value={"status": "success"}):
            result = run_single_model_retraining("eta_prediction", db_session)
        assert result["status"] == "success"

    # --- insufficient_data ---------------------------------------------------

    def test_insufficient_data_logged(self, db_session: Session):
        train_result = {"status": "insufficient_data", "reason": "only 5 rows available"}
        with patch(_TRAIN_TARGETS["eta_prediction"], return_value=train_result):
            result = run_single_model_retraining("eta_prediction", db_session)

        assert result["status"] == "insufficient_data"
        log = db_session.query(RetrainingLog).filter_by(
            model_type="eta_prediction", status="insufficient_data"
        ).first()
        assert log is not None
        assert "5 rows" in log.error_message

    # --- failed status -------------------------------------------------------

    def test_failed_status_logged(self, db_session: Session):
        train_result = {"status": "failed", "error": "model training exploded"}
        with patch(_TRAIN_TARGETS["eta_prediction"], return_value=train_result):
            result = run_single_model_retraining("eta_prediction", db_session)

        assert result["status"] == "failed"
        log = db_session.query(RetrainingLog).filter_by(
            model_type="eta_prediction", status="failed"
        ).first()
        assert log is not None

    # --- unknown status with version_id (else branch) -----------------------

    def test_unknown_status_with_version_id_promoted(self, db_session: Session):
        # Unknown status but version_id present → promote_if_better called;
        # result dict gets "promoted" injected; DB log gets status="promoted".
        train_result = {"status": "partial", "version_id": "eta_v3"}
        with (
            patch(_TRAIN_TARGETS["eta_prediction"], return_value=train_result),
            patch(_PROMOTE, return_value=True),
        ):
            result = run_single_model_retraining("eta_prediction", db_session)
        assert result["status"] == "partial"   # raw status unchanged
        assert result["promoted"] is True
        log = db_session.query(RetrainingLog).filter_by(
            model_type="eta_prediction", status="promoted"
        ).first()
        assert log is not None

    def test_unknown_status_with_version_id_not_promoted(self, db_session: Session):
        train_result = {"status": "partial", "version_id": "eta_v3"}
        with (
            patch(_TRAIN_TARGETS["eta_prediction"], return_value=train_result),
            patch(_PROMOTE, return_value=False),
        ):
            result = run_single_model_retraining("eta_prediction", db_session)
        assert result["status"] == "partial"   # raw status unchanged
        assert result["promoted"] is False

    # --- unknown status without version_id ("completed" in DB log) -----------

    def test_unknown_status_no_version_id(self, db_session: Session):
        # No version_id → status="completed" in DB log; result dict returned as-is.
        with patch(_TRAIN_TARGETS["eta_prediction"], return_value={"status": "partial"}):
            result = run_single_model_retraining("eta_prediction", db_session)
        assert result["status"] == "partial"    # raw status unchanged
        assert "promoted" not in result
        log = db_session.query(RetrainingLog).filter_by(
            model_type="eta_prediction", status="completed"
        ).first()
        assert log is not None

    # --- non-dict result (status=success branch) -----------------------------

    def test_non_dict_result_treated_as_success(self, db_session: Session):
        with patch(_TRAIN_TARGETS["eta_prediction"], return_value="not_a_dict"):
            result = run_single_model_retraining("eta_prediction", db_session)
        assert result == "not_a_dict"

    # --- unknown model type --------------------------------------------------

    def test_unknown_model_type_exception_logged(self, db_session: Session):
        result = run_single_model_retraining("unknown_model_xyz", db_session)
        assert result["status"] == "failed"
        assert "Unknown model_type" in result["error"]
        log = db_session.query(RetrainingLog).filter_by(
            model_type="unknown_model_xyz", status="failed"
        ).first()
        assert log is not None

    # --- DB log failure handled gracefully -----------------------------------

    def test_db_log_failure_handled(self, db_session: Session):
        train_result = {"status": "success", "version_id": "eta_v1"}
        with (
            patch(_TRAIN_TARGETS["eta_prediction"], return_value=train_result),
            patch(_PROMOTE, return_value=True),
            patch.object(db_session, "commit", side_effect=Exception("DB commit failed")),
        ):
            result = run_single_model_retraining("eta_prediction", db_session)
        assert result.get("promoted") is True


# ─────────────────────────────────────────────────────────────────────────────
# Section 5 — run_scheduled_retraining
# ─────────────────────────────────────────────────────────────────────────────

# Deferred imports in run_scheduled_retraining:
#   from app.database.session import SessionLocal → patch at app.database.session.SessionLocal

_SINGLE_RETRAIN = "app.ml.retraining.run_single_model_retraining"


class TestRunScheduledRetraining:

    def test_all_defaults_run(self, db_session: Session):
        expected = {mt: {"status": "promoted"} for mt in [
            "eta_prediction", "demand_forecast", "slot_recommendation",
            "vendor_ranking", "fraud_detection",
        ]}
        with patch(_SINGLE_RETRAIN, side_effect=lambda mt, db: expected[mt]):
            results = run_scheduled_retraining(db=db_session)
        assert set(results.keys()) == set(expected.keys())

    def test_custom_model_types_only(self, db_session: Session):
        with patch(_SINGLE_RETRAIN, return_value={"status": "promoted"}):
            results = run_scheduled_retraining(
                model_types=["eta_prediction", "fraud_detection"],
                db=db_session,
            )
        assert set(results.keys()) == {"eta_prediction", "fraud_detection"}

    def test_one_model_failure_does_not_stop_others(self, db_session: Session):
        """Outer exception handler catches raised exceptions from run_single_model_retraining."""
        call_count = {"n": 0}

        def _side(mt, db):
            call_count["n"] += 1
            if mt == "demand_forecast":
                raise RuntimeError("Unhandled boom")
            return {"status": "promoted"}

        with patch(_SINGLE_RETRAIN, side_effect=_side):
            results = run_scheduled_retraining(
                model_types=["eta_prediction", "demand_forecast", "fraud_detection"],
                db=db_session,
            )

        assert call_count["n"] == 3
        assert results["demand_forecast"]["status"] == "failed"
        assert "Unhandled boom" in results["demand_forecast"]["error"]
        assert results["eta_prediction"]["status"] == "promoted"
        assert results["fraud_detection"]["status"] == "promoted"

    def test_uses_session_local_when_db_is_none(self, db_session: Session):
        """When db=None, SessionLocal() is called and closed at end."""
        with (
            patch("app.database.session.SessionLocal", return_value=db_session),
            patch.object(db_session, "close", return_value=None) as mock_close,
            patch(_SINGLE_RETRAIN, return_value={"status": "promoted"}),
        ):
            results = run_scheduled_retraining(model_types=["eta_prediction"], db=None)

        mock_close.assert_called_once()
        assert "eta_prediction" in results
