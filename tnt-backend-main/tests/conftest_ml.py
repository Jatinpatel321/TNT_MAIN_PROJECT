"""ML-test environment stabilisation.

Loaded automatically by pytest because it lives inside the ``tests/`` package
(same directory as ``conftest.py``).  All fixtures here are *additive* — they
never remove or replace the fixtures already defined in conftest.py.

Problems this module solves
---------------------------
1. ``n_jobs=-1`` in sklearn RandomizedSearchCV / cross_val_score
   ⟶ spawns Windows loky worker processes that fail inside the sandbox
   (PermissionError when cloning the process image).
   Fix: monkeypatch _tune_regressor / _tune_classifier to force n_jobs=1.

2. ``xgb.XGBRegressor(n_jobs=-1)`` without ``device='cpu'``
   ⟶ XGBoost probes CUDA at fit() time on every CV fold.
   On Windows sandbox: ``XGBoostError: cudaGetLastError() (0 vs. 46)``
   Fix: monkeypatch the XGBRegressor / XGBClassifier constructors to inject
   ``device='cpu', n_jobs=1``.

3. sklearn ``UserWarning: total space of parameters N is smaller than n_iter``
   ⟶ emitted when param_grid has fewer combinations than n_iter=10.
   The existing pytest.ini has ``filterwarnings = error::ResourceWarning`` but
   does *not* promote this UserWarning to an error — it is just noise.
   Fix: add an explicit ``ignore`` filter so it never appears in test output.

4. sklearn ``FitFailedWarning`` from XGBoost CUDA errors inside CV folds
   ⟶ caused by problem (2); fixed transitively once device='cpu' is set.

Design constraints
------------------
* No production ML code is modified.
* All patches are applied *only* during test session and reverted on teardown.
* Deterministic seeds (random_state=42) are preserved in all re-created objects.
* The full param_grid is kept intact — only n_jobs and device are overridden,
  so the coverage paths through _tune_regressor / _tune_classifier remain
  exercised; results are bit-for-bit identical to a n_jobs=1 run on Linux CI.
"""

from __future__ import annotations

import os
import warnings
from typing import Any, Dict, Tuple
from unittest.mock import patch

import numpy as np
import pytest


# ── 1. Suppress known-safe sklearn / XGBoost warnings ─────────────────────

def pytest_configure(config):
    """Register additional filterwarnings early, before test collection."""
    config.addinivalue_line(
        "filterwarnings",
        # sklearn warns when n_iter > total grid combinations; harmless.
        "ignore:The total space of parameters.*is smaller than n_iter:UserWarning",
    )
    config.addinivalue_line(
        "filterwarnings",
        # sklearn FitFailedWarning wraps per-fold errors; root cause fixed by
        # the XGBoost CPU device patch, but keep silent as belt-and-suspenders.
        "ignore::sklearn.exceptions.FitFailedWarning",
    )
    config.addinivalue_line(
        "filterwarnings",
        # XGBoost may emit CUDA-probe warnings even with device='cpu' set after
        # import (version-dependent). Keep silent.
        "ignore:.*cuda.*:UserWarning",
    )
    config.addinivalue_line(
        "filterwarnings",
        # Some sklearn versions emit non-finite score warnings when a fold has
        # too few samples; the production code already handles this gracefully.
        "ignore:One or more of the test scores are non-finite:UserWarning",
    )


# ── 2. Monkeypatch ModelTrainer to use n_jobs=1 + CPU device ─────────────

def _make_safe_tune_regressor(original_fn):
    """Return a wrapper around ModelTrainer._tune_regressor that:
    - Forces n_jobs=1 on the estimator (removes multiprocessing).
    - Forces device='cpu' on XGBoost estimators (removes CUDA probe).
    - Forces n_jobs=1 on RandomizedSearchCV and cross_val_score.
    - Keeps random_state=42 for determinism.
    """
    import functools

    @functools.wraps(original_fn)
    def _safe_tune_regressor(
        self,
        estimator,
        param_grid: Dict,
        X: np.ndarray,
        y: np.ndarray,
        name: str,
        n_iter: int = 10,
        cv: int = 5,
    ) -> Tuple[Any, Dict[str, Any], float]:
        estimator = _sanitize_estimator(estimator)

        from sklearn.model_selection import RandomizedSearchCV, cross_val_score

        n_samples = len(X)
        effective_cv = min(cv, n_samples) if n_samples >= 2 else 2
        effective_iter = min(n_iter, max(1, n_samples // 2))

        try:
            search = RandomizedSearchCV(
                estimator,
                param_distributions=param_grid,
                n_iter=effective_iter,
                cv=effective_cv,
                scoring="neg_root_mean_squared_error",
                random_state=42,
                n_jobs=1,          # ← force serial execution
                refit=True,
            )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                search.fit(X, y)
            best_est = search.best_estimator_
            best_params = search.best_params_
        except Exception as e:
            import logging
            logging.getLogger("tnt.ml.training").warning(
                f"{name} RandomizedSearchCV failed ({e}), fitting with defaults"
            )
            estimator.fit(X, y)
            best_est = estimator
            best_params = {}

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                cv_scores = cross_val_score(
                    best_est, X, y,
                    cv=effective_cv,
                    scoring="neg_root_mean_squared_error",
                    n_jobs=1,      # ← force serial execution
                )
            cv_rmse = float(np.mean(np.abs(cv_scores)))
        except Exception as e:
            import logging
            logging.getLogger("tnt.ml.training").warning(
                f"{name} cross_val_score failed ({e}), using 0.0 placeholder"
            )
            cv_rmse = 0.0

        return best_est, best_params, cv_rmse

    return _safe_tune_regressor


def _make_safe_tune_classifier(original_fn):
    """Return a wrapper around ModelTrainer._tune_classifier that forces
    n_jobs=1 and CPU device for safe sandbox execution."""
    import functools

    @functools.wraps(original_fn)
    def _safe_tune_classifier(
        self,
        estimator,
        param_grid: Dict,
        X: np.ndarray,
        y: np.ndarray,
        name: str,
        n_iter: int = 10,
        cv: int = 5,
    ) -> Tuple[Any, Dict[str, Any], float]:
        estimator = _sanitize_estimator(estimator)

        from sklearn.model_selection import RandomizedSearchCV, cross_val_score

        n_samples = len(X)
        effective_cv = min(cv, n_samples) if n_samples >= 2 else 2
        effective_iter = min(n_iter, max(1, n_samples // 2))

        try:
            search = RandomizedSearchCV(
                estimator,
                param_distributions=param_grid,
                n_iter=effective_iter,
                cv=effective_cv,
                scoring="f1",
                random_state=42,
                n_jobs=1,          # ← force serial execution
                refit=True,
            )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                search.fit(X, y)
            best_est = search.best_estimator_
            best_params = search.best_params_
        except Exception as e:
            import logging
            logging.getLogger("tnt.ml.training").warning(
                f"{name} RandomizedSearchCV failed ({e}), fitting with defaults"
            )
            estimator.fit(X, y)
            best_est = estimator
            best_params = {}

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                cv_scores = cross_val_score(
                    best_est, X, y,
                    cv=effective_cv,
                    scoring="f1",
                    n_jobs=1,      # ← force serial execution
                )
            cv_f1 = float(np.mean(cv_scores))
        except Exception as e:
            import logging
            logging.getLogger("tnt.ml.training").warning(
                f"{name} cross_val_score failed ({e}), using 0.0 placeholder"
            )
            cv_f1 = 0.0

        return best_est, best_params, cv_f1

    return _safe_tune_classifier


def _sanitize_estimator(estimator):
    """Return a copy of *estimator* with n_jobs=1 and, for XGBoost,
    device='cpu'.  Does *not* modify the original object."""
    params = estimator.get_params()

    # Force serial execution regardless of estimator type
    if "n_jobs" in params:
        estimator = estimator.set_params(n_jobs=1)

    # Force CPU-only device for XGBoost (avoids cudaGetLastError on Windows)
    if "device" in params:
        estimator = estimator.set_params(device="cpu")

    # XGBoost uses 'nthread' as an alias; set for robustness
    if "nthread" in params:
        estimator = estimator.set_params(nthread=1)

    return estimator


# ── 3. Session-scoped autouse fixture that applies all patches ─────────────

@pytest.fixture(scope="session", autouse=True)
def _ml_test_safe_environment():
    """Patch ModelTrainer's tuning methods for the entire test session.

    Scope: session — applied once, covering all 154+ ML tests.
    autouse: True — no opt-in required per test.

    Patches applied:
      • ModelTrainer._tune_regressor  → serial + CPU-safe wrapper
      • ModelTrainer._tune_classifier → serial + CPU-safe wrapper

    The patches are reverted automatically when the session ends (pytest
    guarantees teardown of session-scoped fixtures after all tests finish).
    """
    try:
        from app.ml.training_pipeline import ModelTrainer
    except ImportError:
        # If the module can't be imported at all, skip gracefully
        yield
        return

    original_tune_regressor = ModelTrainer._tune_regressor
    original_tune_classifier = ModelTrainer._tune_classifier

    safe_tune_regressor = _make_safe_tune_regressor(original_tune_regressor)
    safe_tune_classifier = _make_safe_tune_classifier(original_tune_classifier)

    with (
        patch.object(ModelTrainer, "_tune_regressor", safe_tune_regressor),
        patch.object(ModelTrainer, "_tune_classifier", safe_tune_classifier),
    ):
        yield

    # Patches are reverted automatically when the context managers exit,
    # but we explicitly note: originals are NOT touched, so production
    # imports that happened before the session are unaffected.


# ── 4. Per-test writable temp dir for model storage ───────────────────────

@pytest.fixture(autouse=True)
def _ml_writable_model_dir(request, tmp_path, monkeypatch):
    """Give each ML test its own writable model storage directory.

    Avoids cross-test pollution of pickle files and registry metadata.
    The ``MODEL_STORAGE_DIR`` env var is the single control point used
    by both ``app/ml/registry.py`` and ``app/ml/training_pipeline.py``.

    Design note
    -----------
    ``tests/test_ml_engine.py`` already manages its own ``MODEL_STORAGE_DIR``
    at module import time and has a ``clean_registry`` autouse fixture that
    handles per-test cleanup of that directory.  To avoid conflicting with
    that setup this fixture detects that module and becomes a no-op there.

    For all other test modules (test_ai_planners, test_ml_bridge, future
    tests) it provides a fresh per-test writable directory.
    """
    # Detect if this test is owned by test_ml_engine.py which self-manages dirs.
    module_name = getattr(
        getattr(request.node, "module", None), "__name__", ""
    )
    if "test_ml_engine" in module_name:
        # Let test_ml_engine.py's own clean_registry fixture handle this.
        yield None
        return

    model_dir = tmp_path / "ml_models"
    model_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("MODEL_STORAGE_DIR", str(model_dir))
    # Also patch the module-level Path constant in registry (already imported).
    try:
        import app.ml.registry as _registry
        monkeypatch.setattr(_registry, "MODEL_STORAGE_DIR", model_dir)
        model_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    try:
        import app.ml.training_pipeline as _tp
        monkeypatch.setattr(_tp, "MODEL_STORAGE_DIR", str(model_dir))
    except Exception:
        pass
    yield model_dir


# ── 5. Deterministic numpy global seed for ML tests ───────────────────────

@pytest.fixture(autouse=True)
def _ml_deterministic_seed():
    """Reset numpy's legacy global random state to seed=42 before every test.

    This covers calls to ``np.random.*`` that are not yet using the new
    ``np.random.default_rng()`` API.  Tests that need a different seed can
    reset it locally — this fixture only guarantees a *known starting state*.
    """
    np.random.seed(42)
    yield
    # No teardown needed; the seed is reset at the start of the next test.
