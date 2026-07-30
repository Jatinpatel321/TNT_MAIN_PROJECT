"""Comprehensive unit tests for app/ml/training_pipeline.py targeting ≥ 95% coverage.

Uses fast synthetic datasets and targeted monkeypatching of DatasetBuilder /
ModelRegistry to test all branches (availability flags, error handling,
model selection by CV metrics, temporal vs random splits, SVD vs popularity
fallbacks, and RetrainingService) cleanly without needing a live DB.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.ml.training_pipeline import (
    ModelTrainer,
    RetrainingService,
    _log_ml_dependency_warnings,
    run_full_training_pipeline,
    time_based_split,
    train_demand,
    train_demand_forecast,
    train_eta,
    train_eta_models,
    train_fraud_detection,
    train_slot_recommendation,
    train_vendor_ranking,
)


# ── Synthetic Dataset Generators ────────────────────────────────────────────

def _make_regression_data(n: int = 30, n_features: int = 4):
    """Return synthetic regression X, y, feature_cols, and timestamps."""
    rng = np.random.default_rng(42)
    X = rng.standard_normal((n, n_features))
    y = X[:, 0] * 2.5 + rng.standard_normal(n) * 0.1
    feature_cols = [f"feat_{i}" for i in range(n_features)]
    base_time = datetime(2026, 1, 1, 10, 0, 0)
    timestamps = np.array([base_time + timedelta(hours=i) for i in range(n)], dtype=object)
    return X, y, feature_cols, timestamps


def _make_binary_clf_data(n: int = 30, n_features: int = 4):
    """Return synthetic binary classification X, y with both 0 and 1 classes."""
    rng = np.random.default_rng(123)
    X = rng.standard_normal((n, n_features))
    y = (X[:, 0] > 0).astype(float)
    y[0] = 0.0
    y[1] = 1.0
    feature_cols = [f"feat_{i}" for i in range(n_features)]
    return X, y, feature_cols


# ══════════════════════════════════════════════════════════════════════════
# 1. Dependency Warning Logging
# ══════════════════════════════════════════════════════════════════════════

class TestDependencyWarnings:
    """Test _log_ml_dependency_warnings under missing library flags."""

    def test_log_warnings_when_all_missing(self, monkeypatch):
        """When availability flags are False, warning messages are emitted."""
        monkeypatch.setattr("app.ml.training_pipeline._RF_AVAILABLE", False)
        monkeypatch.setattr("app.ml.training_pipeline._XGB_AVAILABLE", False)
        monkeypatch.setattr("app.ml.training_pipeline._LGBM_AVAILABLE", False)

        with patch("app.ml.training_pipeline.logger.warning") as mock_warn:
            _log_ml_dependency_warnings()
        assert mock_warn.call_count == 3
        messages = [call.args[0] for call in mock_warn.call_args_list]
        assert any("scikit-learn is NOT available" in m for m in messages)
        assert any("XGBoost is NOT available" in m for m in messages)
        assert any("LightGBM is NOT available" in m for m in messages)


# ══════════════════════════════════════════════════════════════════════════
# 2. Time-Based Split Edge Cases
# ══════════════════════════════════════════════════════════════════════════

class TestTimeBasedSplit:
    """Test time_based_split edge cases."""

    def test_empty_input_returns_empty_arrays(self):
        """Empty X returns empty arrays without error."""
        X = np.empty((0, 3))
        y = np.array([])
        ts = np.array([], dtype=object)
        X_tr, X_te, y_tr, y_te, ts_tr, ts_te = time_based_split(X, y, ts)
        assert len(X_tr) == 0
        assert len(X_te) == 0
        assert len(ts_tr) == 0


# ══════════════════════════════════════════════════════════════════════════
# 3. Model Tuning Exception Fallbacks
# ══════════════════════════════════════════════════════════════════════════

class TestTuningExceptionFallbacks:
    """Test fallback paths in _tune_regressor and _tune_classifier."""

    def test_tune_regressor_search_exception_fallback(self, db_session):
        """When RandomizedSearchCV raises an exception, fit estimator directly."""
        from sklearn.ensemble import RandomForestRegressor
        trainer = ModelTrainer(db_session)
        X, y, _, _ = _make_regression_data(10)
        rf = RandomForestRegressor(random_state=42)

        with patch("sklearn.model_selection.RandomizedSearchCV", side_effect=RuntimeError("Search error")):
            best_est, best_params, cv_rmse = trainer._tune_regressor(
                rf, trainer._RF_PARAM_GRID, X, y, "Test-RF"
            )

        assert best_est is rf
        assert best_params == {}
        assert isinstance(cv_rmse, float)

    def test_tune_regressor_cross_val_score_exception(self, db_session):
        """When cross_val_score raises an exception, cv_rmse defaults to 0.0."""
        from sklearn.ensemble import RandomForestRegressor
        trainer = ModelTrainer(db_session)
        X, y, _, _ = _make_regression_data(10)
        rf = RandomForestRegressor(random_state=42)

        with patch("sklearn.model_selection.cross_val_score", side_effect=RuntimeError("CV error")):
            _, _, cv_rmse = trainer._tune_regressor(
                rf, {"n_estimators": [5]}, X, y, "Test-RF"
            )

        assert cv_rmse == 0.0

    def test_tune_classifier_search_exception_fallback(self, db_session):
        """When RandomizedSearchCV raises an exception, fit classifier directly."""
        from sklearn.ensemble import RandomForestClassifier
        trainer = ModelTrainer(db_session)
        X, y, _ = _make_binary_clf_data(10)
        clf = RandomForestClassifier(random_state=42)

        with patch("sklearn.model_selection.RandomizedSearchCV", side_effect=RuntimeError("Search error")):
            best_est, best_params, cv_f1 = trainer._tune_classifier(
                clf, {"n_estimators": [5]}, X, y, "Test-CLF"
            )

        assert best_est is clf
        assert best_params == {}
        assert isinstance(cv_f1, float)

    def test_tune_classifier_cross_val_score_exception(self, db_session):
        """When cross_val_score fails in classifier tuning, cv_f1 defaults to 0.0."""
        from sklearn.ensemble import RandomForestClassifier
        trainer = ModelTrainer(db_session)
        X, y, _ = _make_binary_clf_data(10)
        clf = RandomForestClassifier(random_state=42)

        with patch("sklearn.model_selection.cross_val_score", side_effect=RuntimeError("CV error")):
            _, _, cv_f1 = trainer._tune_classifier(
                clf, {"n_estimators": [5]}, X, y, "Test-CLF"
            )

        assert cv_f1 == 0.0


# ══════════════════════════════════════════════════════════════════════════
# 4. Phase 3: train_eta Tests
# ══════════════════════════════════════════════════════════════════════════

class TestTrainEta:
    """Test train_eta error paths, split logic, and model selection."""

    def test_train_eta_extraction_exception(self, db_session):
        """When feature extraction raises an exception, return status=failed."""
        trainer = ModelTrainer(db_session)
        with patch("app.ml.features.extract_eta_training_data", side_effect=RuntimeError("DB query failed")):
            res = trainer.train_eta()
        assert res["status"] == "failed"
        assert "DB query failed" in res["error"]

    def test_train_eta_empty_dataset(self, db_session):
        """When extract_eta_training_data returns empty arrays, return status=failed."""
        trainer = ModelTrainer(db_session)
        empty_x = np.empty((0, 4))
        empty_y = np.array([])
        with patch("app.ml.features.extract_eta_training_data", return_value=(empty_x, empty_y, ["f1"])):
            res = trainer.train_eta()
        assert res["status"] == "failed"
        assert "Empty ETA dataset" in res["error"]

    def test_train_eta_timestamp_query_exception_fallback(self, db_session):
        """When timestamp query fails, fall back to random_fallback split."""
        trainer = ModelTrainer(db_session)
        X, y, feature_cols, _ = _make_regression_data(25)

        with (
            patch("app.ml.features.extract_eta_training_data", return_value=(X, y, feature_cols)),
            patch.object(db_session, "query", side_effect=RuntimeError("Timestamp query fail")),
            patch("app.ml.registry.ModelRegistry.save", return_value="eta_v1"),
        ):
            res = trainer.train_eta()

        assert res["status"] == "success"
        assert res["split_method"] == "random_fallback"

    def test_train_eta_mismatched_timestamps_fallback(self, db_session):
        """When timestamp count != X row count, fall back to random_fallback split."""
        trainer = ModelTrainer(db_session)
        X, y, feature_cols, _ = _make_regression_data(25)

        # Mock query to return 10 timestamps (mismatched with 25 rows)
        mock_query = MagicMock()
        mock_row = MagicMock()
        mock_row.created_at = datetime(2026, 1, 1)
        mock_query.join.return_value.filter.return_value.all.return_value = [mock_row] * 10

        with (
            patch("app.ml.features.extract_eta_training_data", return_value=(X, y, feature_cols)),
            patch.object(db_session, "query", return_value=mock_query),
            patch("app.ml.registry.ModelRegistry.save", return_value="eta_v1"),
        ):
            res = trainer.train_eta()

        assert res["status"] == "success"
        assert res["split_method"] == "random_fallback"

    def test_train_eta_temporal_split_success(self, db_session):
        """When timestamp count matches X row count, split_method is temporal."""
        trainer = ModelTrainer(db_session)
        X, y, feature_cols, timestamps = _make_regression_data(25)

        ts_rows = [MagicMock(created_at=t) for t in timestamps]
        mock_query = MagicMock()
        mock_query.join.return_value.filter.return_value.all.return_value = ts_rows

        with (
            patch("app.ml.features.extract_eta_training_data", return_value=(X, y, feature_cols)),
            patch.object(db_session, "query", return_value=mock_query),
            patch("app.ml.registry.ModelRegistry.save", return_value="eta_v1"),
        ):
            res = trainer.train_eta()

        assert res["status"] == "success"
        assert res["split_method"] == "temporal"

    def test_train_eta_rf_exception_and_xgb_exception_and_lgb_exception(self, db_session):
        """When all model training blocks fail, return status=failed with 'No model trained'."""
        trainer = ModelTrainer(db_session)
        X, y, feature_cols, _ = _make_regression_data(20)

        with (
            patch("app.ml.features.extract_eta_training_data", return_value=(X, y, feature_cols)),
            patch.object(trainer, "_tune_regressor", side_effect=RuntimeError("Fit failed")),
        ):
            res = trainer.train_eta()

        assert res["status"] == "failed"
        assert "No model trained" in res["error"]

    def test_train_eta_selects_best_cv_rmse_model(self, db_session):
        """Best model selection is based strictly on lowest cv_rmse across evaluated models."""
        trainer = ModelTrainer(db_session)
        X, y, feature_cols, _ = _make_regression_data(25)

        # Tune responses: (est, params, cv_rmse)
        # RF cv_rmse = 3.5, XGB cv_rmse = 1.2 (winner), LGBM cv_rmse = 2.1
        rf_est = MagicMock(predict=MagicMock(return_value=y[:5]))
        xgb_est = MagicMock(predict=MagicMock(return_value=y[:5]))
        lgb_est = MagicMock(predict=MagicMock(return_value=y[:5]))

        def fake_tune(est, grid, X, y, name, **kwargs):
            if "RF" in name:
                return rf_est, {"n_estimators": 50}, 3.5
            elif "XGB" in name:
                return xgb_est, {"n_estimators": 80}, 1.2
            else:
                return lgb_est, {"n_estimators": 60}, 2.1

        with (
            patch("app.ml.features.extract_eta_training_data", return_value=(X, y, feature_cols)),
            patch.object(trainer, "_tune_regressor", side_effect=fake_tune),
            patch("app.ml.registry.ModelRegistry.save", return_value="eta_best_v1") as mock_save,
        ):
            res = trainer.train_eta()

        assert res["status"] == "success"
        assert res["best_model"] == "XGBoost"
        assert res["best_cv_rmse"] == 1.2
        # Check metadata passed to registry
        saved_kwargs = mock_save.call_args.kwargs
        assert saved_kwargs["metrics"]["cv_rmse"] == 1.2
        assert saved_kwargs["hyperparams"]["model"] == "XGBoost"


# ══════════════════════════════════════════════════════════════════════════
# 5. Phase 4: train_demand Tests
# ══════════════════════════════════════════════════════════════════════════

class TestTrainDemand:
    """Test train_demand per-vendor extraction, temporal split, and fallbacks."""

    def test_train_demand_vendor_extraction_exception(self, db_session):
        """Vendor extraction exception is logged and gracefully skipped."""
        trainer = ModelTrainer(db_session)
        mock_vendor = MagicMock(id=10, role="vendor", is_approved=True)

        with (
            patch.object(db_session, "query", return_value=MagicMock(filter=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_vendor]))))),
            patch("app.ml.features.extract_demand_features", side_effect=RuntimeError("Demand query fail")),
        ):
            res = trainer.train_demand()

        assert res["status"] == "failed"
        assert "Empty demand dataset" in res["error"]

    def test_train_demand_vendor_timestamp_mismatch(self, db_session):
        """When ts_all count != X rows (line 539 check), random_fallback split is used (lines 544-551)."""
        import sys
        trainer = ModelTrainer(db_session)
        mock_vendor = MagicMock(id=1, role="vendor", is_approved=True)
        X_v, y_v, cols, timestamps = _make_regression_data(10)
        X_v, y_v = np.abs(X_v), np.abs(y_v)

        class MismatchedLenArray(np.ndarray):
            def __len__(self):
                try:
                    frame = sys._getframe(1)
                    if frame.f_code.co_name == "train_demand" and frame.f_lineno == 539:
                        return super().__len__() + 1
                except Exception:
                    pass
                return super().__len__()

        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = [mock_vendor]
        ts_rows = [MagicMock(hour_bucket=t.isoformat()) for t in timestamps]
        mock_query.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = ts_rows

        rf_est = MagicMock(predict=MagicMock(side_effect=lambda x: np.zeros(len(x))))

        orig_vstack = np.vstack
        def fake_vstack(mats, **kwargs):
            res = orig_vstack(mats, **kwargs)
            return res.view(MismatchedLenArray)

        with (
            patch.object(db_session, "query", return_value=mock_query),
            patch("app.ml.features.extract_demand_features", return_value=(X_v, y_v, cols)),
            patch("numpy.vstack", side_effect=fake_vstack),
            patch.object(trainer, "_tune_regressor", return_value=(rf_est, {}, 1.0)),
            patch("app.ml.registry.ModelRegistry.save", return_value="demand_v1"),
        ):
            res = trainer.train_demand()

        assert res["status"] == "success"
        assert res["split_method"] == "random_fallback"









    def test_train_eta_lgbm_failure(self, db_session):
        """LightGBM failure in train_eta is caught and logged (lines 410-413)."""
        trainer = ModelTrainer(db_session)
        X, y, feature_cols, _ = _make_regression_data(20)

        def fake_tune(est, grid, X, y, name, **kwargs):
            if "LGBM" in name:
                raise RuntimeError("LGBM error")
            m = MagicMock()
            m.predict.return_value = y[:4]
            return m, {}, 1.0

        with (
            patch("app.ml.features.extract_eta_training_data", return_value=(X, y, feature_cols)),
            patch.object(trainer, "_tune_regressor", side_effect=fake_tune),
            patch("app.ml.registry.ModelRegistry.save", return_value="eta_v1"),
        ):
            res = trainer.train_eta()

        assert res["status"] == "success"
        assert res["best_model"] in ("RandomForest", "XGBoost")

    def test_train_vendor_ranking_xgb_failure(self, db_session):
        """XGBoost failure in train_vendor_ranking is caught and logged (lines 922-925)."""
        trainer = ModelTrainer(db_session)
        X, y, cols, _ = _make_regression_data(20)

        def fake_tune(est, grid, X, y, name, **kwargs):
            if "XGB" in name:
                raise RuntimeError("XGB vendor error")
            m = MagicMock()
            m.predict.return_value = y[:4]
            return m, {}, 1.0

        with (
            patch("app.ml.features.extract_vendor_ranking_features", return_value=(X, y, cols)),
            patch.object(trainer, "_tune_regressor", side_effect=fake_tune),
            patch("app.ml.registry.ModelRegistry.save", return_value="vendor_v1"),
        ):
            res = trainer.train_vendor_ranking()

        assert res["status"] == "success"
        assert res["best_model"] == "RandomForest"


    def test_train_demand_temporal_split_success(self, db_session):
        """When vendor timestamps match feature count (including ISO string parsing), split_method is temporal."""
        trainer = ModelTrainer(db_session)
        mock_vendor = MagicMock(id=1, role="vendor", is_approved=True)
        X_v, y_v, cols, timestamps = _make_regression_data(15)
        X_v = np.abs(X_v)
        y_v = np.abs(y_v)

        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = [mock_vendor]
        # Test ISO string hour_bucket parsing (lines 515-517)
        ts_rows = [MagicMock(hour_bucket=t.isoformat()) for t in timestamps]
        mock_query.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = ts_rows

        with (
            patch.object(db_session, "query", return_value=mock_query),
            patch("app.ml.features.extract_demand_features", return_value=(X_v, y_v, cols)),
            patch("app.ml.registry.ModelRegistry.save", return_value="demand_v1"),
        ):
            res = trainer.train_demand()

        assert res["status"] == "success"
        assert res["split_method"] == "temporal"

    def test_train_demand_all_models_fail(self, db_session):
        """When all demand model fits fail, return status=failed."""
        trainer = ModelTrainer(db_session)
        mock_vendor = MagicMock(id=1, role="vendor", is_approved=True)
        X_v, y_v, cols, timestamps = _make_regression_data(10)

        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = [mock_vendor]
        ts_rows = [MagicMock(hour_bucket=t.isoformat()) for t in timestamps]
        mock_query.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = ts_rows

        with (
            patch.object(db_session, "query", return_value=mock_query),
            patch("app.ml.features.extract_demand_features", return_value=(X_v, y_v, cols)),
            patch("app.ml.training_pipeline._XGB_AVAILABLE", False),
            patch("app.ml.training_pipeline._RF_AVAILABLE", False),
        ):
            res = trainer.train_demand()

        assert res["status"] == "failed"
        assert "No model trained" in res["error"]

    def test_train_demand_xgb_fail_rf_success(self, db_session):
        """XGBoost failure logged and fallback to RandomForest."""
        trainer = ModelTrainer(db_session)
        mock_vendor = MagicMock(id=1, role="vendor", is_approved=True)
        X_v, y_v, cols, timestamps = _make_regression_data(10)

        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = [mock_vendor]
        ts_rows = [MagicMock(hour_bucket=t.isoformat()) for t in timestamps]
        mock_query.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = ts_rows

        def fake_tune(est, grid, X, y, name, **kwargs):
            if "XGB" in name:
                raise RuntimeError("XGB tune fail")
            from sklearn.ensemble import RandomForestRegressor
            rf = RandomForestRegressor(random_state=42, n_jobs=1)
            rf.fit(X, y)
            return rf, {}, 1.0

        with (
            patch.object(db_session, "query", return_value=mock_query),
            patch("app.ml.features.extract_demand_features", return_value=(X_v, y_v, cols)),
            patch.object(trainer, "_tune_regressor", side_effect=fake_tune),
            patch("app.ml.registry.ModelRegistry.save", return_value="demand_v2"),
        ):
            res = trainer.train_demand()

        assert res["status"] == "success"
        assert res["best_model"] == "RandomForest"

    def test_train_demand_rf_fail_xgb_success(self, db_session):
        """RandomForest failure logged (lines 594-595) and XGBoost used as best_model."""
        trainer = ModelTrainer(db_session)
        mock_vendor = MagicMock(id=1, role="vendor", is_approved=True)
        X_v, y_v, cols, timestamps = _make_regression_data(10)

        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = [mock_vendor]
        ts_rows = [MagicMock(hour_bucket=t.isoformat()) for t in timestamps]
        mock_query.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = ts_rows

        def fake_tune(est, grid, X, y, name, **kwargs):
            if "RF" in name:
                raise RuntimeError("RF tune fail")
            import xgboost as xgb
            xgb_model = xgb.XGBRegressor(random_state=42, n_jobs=1)
            xgb_model.fit(X, y)
            return xgb_model, {}, 1.0

        with (
            patch.object(db_session, "query", return_value=mock_query),
            patch("app.ml.features.extract_demand_features", return_value=(X_v, y_v, cols)),
            patch.object(trainer, "_tune_regressor", side_effect=fake_tune),
            patch("app.ml.registry.ModelRegistry.save", return_value="demand_v3"),
        ):
            res = trainer.train_demand()

        assert res["status"] == "success"
        assert res["best_model"] == "XGBoost"





# ══════════════════════════════════════════════════════════════════════════
# 6. Phase 5: train_slot_recommendation Tests
# ══════════════════════════════════════════════════════════════════════════

class TestTrainSlotRecommendation:
    """Test train_slot_recommendation error and success paths."""

    def test_train_slot_extraction_exception(self, db_session):
        """Extraction exception returns status=failed."""
        trainer = ModelTrainer(db_session)
        with patch("app.ml.features.extract_slot_features", side_effect=RuntimeError("Slot extract fail")):
            res = trainer.train_slot_recommendation()
        assert res["status"] == "failed"
        assert "Slot extract fail" in res["error"]

    def test_train_slot_empty_dataset(self, db_session):
        """Empty slot dataset returns status=failed."""
        trainer = ModelTrainer(db_session)
        with patch("app.ml.features.extract_slot_features", return_value=(np.empty((0, 3)), np.array([]), ["f1"])):
            res = trainer.train_slot_recommendation()
        assert res["status"] == "failed"
        assert "Empty slot dataset" in res["error"]

    def test_train_slot_model_fit_failure(self, db_session):
        """Model fit exception returns status=failed."""
        trainer = ModelTrainer(db_session)
        X, y, cols, _ = _make_regression_data(15)
        with (
            patch("app.ml.features.extract_slot_features", return_value=(X, y, cols)),
            patch.object(trainer, "_tune_regressor", side_effect=RuntimeError("RF fit fail")),
        ):
            res = trainer.train_slot_recommendation()
        assert res["status"] == "failed"
        assert "No model trained" in res["error"]

    def test_train_slot_success(self, db_session):
        """Successful slot recommendation model training."""
        trainer = ModelTrainer(db_session)
        X, y, cols, _ = _make_regression_data(20)
        y = np.clip(y * 10, 0, 100)

        with (
            patch("app.ml.features.extract_slot_features", return_value=(X, y, cols)),
            patch("app.ml.registry.ModelRegistry.save", return_value="slot_v1"),
        ):
            res = trainer.train_slot_recommendation()

        assert res["status"] == "success"
        assert res["model_type"] == "slot_recommendation"
        assert res["best_model"] == "RandomForest"
        assert "best_cv_rmse" in res


# ══════════════════════════════════════════════════════════════════════════
# 7. Phase 6: train_recommendation Tests
# ══════════════════════════════════════════════════════════════════════════

class TestTrainRecommendation:
    """Test train_recommendation SVD collaborative filtering & popularity fallback."""

    def test_train_recommendation_empty_df(self, db_session):
        """Empty recommendation dataset returns status=failed."""
        trainer = ModelTrainer(db_session)
        with patch.object(trainer.builder, "build_recommendation_dataset", return_value=pd.DataFrame()):
            res = trainer.train_recommendation()
        assert res["status"] == "failed"
        assert "Empty recommendation dataset" in res["error"]

    def test_train_recommendation_no_valid_interactions(self, db_session):
        """Dataset with non-matching row iterations returns no valid interactions failure."""
        trainer = ModelTrainer(db_session)
        # DataFrame has row with user_id=1, item_id=10
        df = pd.DataFrame([{"user_id": 1, "item_id": 10, "interaction_strength": 5.0, "order_count": 1}])
        with patch.object(trainer.builder, "build_recommendation_dataset", return_value=df):
            # Patch user_encoder to exclude 1 so iteration loop yields empty data_vals
            with patch("pandas.DataFrame.iterrows", return_value=iter([(0, {"user_id": 99, "item_id": 999})])):
                res = trainer.train_recommendation()
        assert res["status"] == "failed"
        assert "No valid interactions" in res["error"]

    def test_train_recommendation_svd_low_dimensions_popularity_fallback(self, db_session):
        """When matrix dimensions < 3, SVD cannot run (n_components < 2) → popularity fallback."""
        trainer = ModelTrainer(db_session)
        # 1 user and 1 item → matrix shape (1, 1) -> n_components = min(50, 0) = 0 < 2
        df = pd.DataFrame([
            {"user_id": 1, "item_id": 100, "interaction_strength": 5.0, "order_count": 3,
             "item_name": "Burger", "vendor_id": 2, "vendor_name": "Cafe", "price_paise": 500, "category": "Food"}
        ])

        with (
            patch.object(trainer.builder, "build_recommendation_dataset", return_value=df),
            patch("app.ml.registry.ModelRegistry.save", return_value="pop_v1") as mock_save,
        ):
            res = trainer.train_recommendation()

        assert res["status"] == "success"
        assert res["algorithm"] == "popularity_based"
        saved_kwargs = mock_save.call_args.kwargs
        assert saved_kwargs["hyperparams"]["algorithm"] == "popularity_based"

    def test_train_recommendation_svd_success(self, db_session):
        """SVD collaborative filtering succeeds when matrix has sufficient dimensions."""
        trainer = ModelTrainer(db_session)
        # 5 users x 5 items dataset
        records = []
        for u in range(1, 6):
            for i in range(101, 106):
                records.append({"user_id": u, "item_id": i, "interaction_strength": float(u + i % 3), "order_count": 1})
        df = pd.DataFrame(records)

        with (
            patch.object(trainer.builder, "build_recommendation_dataset", return_value=df),
            patch("app.ml.registry.ModelRegistry.save", return_value="svd_v1") as mock_save,
        ):
            res = trainer.train_recommendation()

        assert res["status"] == "success"
        assert res["algorithm"] == "TruncatedSVD"
        assert "explained_variance" in res
        saved_kwargs = mock_save.call_args.kwargs
        assert saved_kwargs["model_type"] == "recommendation_engine"


# ══════════════════════════════════════════════════════════════════════════
# 8. Phase 7: train_vendor_ranking Tests
# ══════════════════════════════════════════════════════════════════════════

class TestTrainVendorRanking:
    """Test train_vendor_ranking extraction, failures, and success."""

    def test_train_vendor_ranking_extraction_exception(self, db_session):
        """Extraction exception returns status=failed."""
        trainer = ModelTrainer(db_session)
        with patch("app.ml.features.extract_vendor_ranking_features", side_effect=RuntimeError("Vendor extract fail")):
            res = trainer.train_vendor_ranking()
        assert res["status"] == "failed"
        assert "Vendor extract fail" in res["error"]

    def test_train_vendor_ranking_empty_dataset(self, db_session):
        """Empty vendor dataset returns status=failed."""
        trainer = ModelTrainer(db_session)
        with patch("app.ml.features.extract_vendor_ranking_features", return_value=(np.empty((0, 4)), np.array([]), ["f1"])):
            res = trainer.train_vendor_ranking()
        assert res["status"] == "failed"
        assert "Empty vendor dataset" in res["error"]

    def test_train_vendor_ranking_all_fits_fail(self, db_session):
        """When RF and XGB fits fail, return status=failed."""
        trainer = ModelTrainer(db_session)
        X, y, cols, _ = _make_regression_data(15)
        with (
            patch("app.ml.features.extract_vendor_ranking_features", return_value=(X, y, cols)),
            patch.object(trainer, "_tune_regressor", side_effect=RuntimeError("Fit fail")),
        ):
            res = trainer.train_vendor_ranking()
        assert res["status"] == "failed"
        assert "No model trained" in res["error"]

    def test_train_vendor_ranking_success(self, db_session):
        """Successful vendor ranking model training."""
        trainer = ModelTrainer(db_session)
        X, y, cols, _ = _make_regression_data(20)
        y = np.clip(y * 10, 0, 100)

        with (
            patch("app.ml.features.extract_vendor_ranking_features", return_value=(X, y, cols)),
            patch("app.ml.registry.ModelRegistry.save", return_value="vendor_v1"),
        ):
            res = trainer.train_vendor_ranking()

        assert res["status"] == "success"
        assert res["model_type"] == "vendor_ranking"
        assert res["best_model"] in ("RandomForest", "XGBoost")


# ══════════════════════════════════════════════════════════════════════════
# 9. Fraud Detection Tests
# ══════════════════════════════════════════════════════════════════════════

class TestTrainFraudDetection:
    """Test train_fraud_detection standalone function branches."""

    def test_train_fraud_extraction_exception(self, db_session):
        """Extraction exception returns status=failed."""
        with patch("app.ml.features.extract_fraud_features", side_effect=RuntimeError("Fraud extract error")):
            res = train_fraud_detection(db_session)
        assert res["status"] == "failed"
        assert "Fraud extract error" in res["error"]

    def test_train_fraud_empty_dataset(self, db_session):
        """Empty fraud dataset returns status=failed."""
        with patch("app.ml.features.extract_fraud_features", return_value=(np.empty((0, 4)), np.array([]), ["f1"])):
            res = train_fraud_detection(db_session)
        assert res["status"] == "failed"
        assert "Empty dataset" in res["error"]

    def test_train_fraud_single_class_auto_fix(self, db_session):
        """When y contains only 1 unique class (e.g. all 0s), auto-fix y[0]=1.0."""
        X, _, cols = _make_binary_clf_data(20)
        y_single = np.zeros(20)  # all 0s

        with (
            patch("app.ml.features.extract_fraud_features", return_value=(X, y_single, cols)),
            patch("app.ml.registry.ModelRegistry.save", return_value="fraud_v1"),
        ):
            res = train_fraud_detection(db_session)

        assert res["status"] == "success"
        assert res["model_type"] == "fraud_detection"

    def test_train_fraud_randomized_search_fallback(self, db_session):
        """When RandomizedSearchCV raises an exception, fit default classifier directly."""
        X, y, cols = _make_binary_clf_data(20)

        with (
            patch("app.ml.features.extract_fraud_features", return_value=(X, y, cols)),
            patch("sklearn.model_selection.RandomizedSearchCV", side_effect=RuntimeError("Search fail")),
            patch("app.ml.registry.ModelRegistry.save", return_value="fraud_v1"),
        ):
            res = train_fraud_detection(db_session)

        assert res["status"] == "success"
        assert res["tuned_params"] == {}

    def test_train_fraud_cross_val_score_failure(self, db_session):
        """When cross_val_score raises an exception, cv_f1 defaults to 0.0."""
        X, y, cols = _make_binary_clf_data(20)

        with (
            patch("app.ml.features.extract_fraud_features", return_value=(X, y, cols)),
            patch("sklearn.model_selection.cross_val_score", side_effect=RuntimeError("CV fail")),
            patch("app.ml.registry.ModelRegistry.save", return_value="fraud_v1"),
        ):
            res = train_fraud_detection(db_session)

        assert res["status"] == "success"
        assert res["cv_f1"] == 0.0

    def test_train_fraud_outer_exception_returns_failed(self, db_session):
        """Unhandled outer exception returns status=failed."""
        X, y, cols = _make_binary_clf_data(20)

        with (
            patch("app.ml.features.extract_fraud_features", return_value=(X, y, cols)),
            patch("sklearn.ensemble.RandomForestClassifier.fit", side_effect=RuntimeError("Outer fit fail")),
            patch("sklearn.model_selection.RandomizedSearchCV.fit", side_effect=RuntimeError("Outer search fail")),
        ):
            res = train_fraud_detection(db_session)

        assert res["status"] == "failed"
        assert "Outer" in res["error"]


# ══════════════════════════════════════════════════════════════════════════
# 11. Direct Tuning Methods Execution
# ══════════════════════════════════════════════════════════════════════════

class TestDirectTuningMethods:
    """Test actual implementation lines 181-221 and 237-277 of _tune_regressor and _tune_classifier."""

    def test_tune_regressor_actual_execution(self, db_session):
        """Call unwrapped _tune_regressor implementation lines 181-221."""
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import RandomizedSearchCV, cross_val_score
        from app.ml.training_pipeline import ModelTrainer

        trainer = ModelTrainer(db_session)
        X, y, _, _ = _make_regression_data(15)
        rf = RandomForestRegressor(random_state=42, n_jobs=1)
        grid = {"n_estimators": [5, 10], "max_depth": [3, 5]}

        fn = getattr(ModelTrainer._tune_regressor, "__wrapped__", ModelTrainer._tune_regressor)

        orig_search_init = RandomizedSearchCV.__init__
        def safe_search_init(self, *args, **kwargs):
            kwargs["n_jobs"] = 1
            orig_search_init(self, *args, **kwargs)

        orig_cv_score = cross_val_score
        def safe_cv_score(*args, **kwargs):
            kwargs["n_jobs"] = 1
            return orig_cv_score(*args, **kwargs)

        with patch.object(RandomizedSearchCV, "__init__", safe_search_init), \
             patch("sklearn.model_selection.cross_val_score", side_effect=safe_cv_score):
            best_est, best_params, cv_rmse = fn(trainer, rf, grid, X, y, "Test-Reg", n_iter=2, cv=2)

        assert best_est is not None
        assert isinstance(best_params, dict)
        assert isinstance(cv_rmse, float)

    def test_tune_classifier_actual_execution(self, db_session):
        """Call unwrapped _tune_classifier implementation lines 237-277."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import RandomizedSearchCV, cross_val_score
        from app.ml.training_pipeline import ModelTrainer

        trainer = ModelTrainer(db_session)
        X, y, _ = _make_binary_clf_data(15)
        clf = RandomForestClassifier(random_state=42, n_jobs=1)
        grid = {"n_estimators": [5, 10], "max_depth": [3, 5]}

        fn = getattr(ModelTrainer._tune_classifier, "__wrapped__", ModelTrainer._tune_classifier)

        orig_search_init = RandomizedSearchCV.__init__
        def safe_search_init(self, *args, **kwargs):
            kwargs["n_jobs"] = 1
            orig_search_init(self, *args, **kwargs)

        orig_cv_score = cross_val_score
        def safe_cv_score(*args, **kwargs):
            kwargs["n_jobs"] = 1
            return orig_cv_score(*args, **kwargs)

        with patch.object(RandomizedSearchCV, "__init__", safe_search_init), \
             patch("sklearn.model_selection.cross_val_score", side_effect=safe_cv_score):
            best_est, best_params, cv_f1 = fn(trainer, clf, grid, X, y, "Test-Clf", n_iter=2, cv=2)

        assert best_est is not None
        assert isinstance(best_params, dict)
        assert isinstance(cv_f1, float)



    def test_train_fraud_no_classifier_available(self, db_session, monkeypatch):
        """When _RF_AVAILABLE is False, return status=failed 'No classifier available'."""
        monkeypatch.setattr("app.ml.training_pipeline._RF_AVAILABLE", False)
        X, y, cols = _make_binary_clf_data(20)

        with patch("app.ml.features.extract_fraud_features", return_value=(X, y, cols)):
            res = train_fraud_detection(db_session)

        assert res["status"] == "failed"
        assert "No classifier available" in res["error"]


# ══════════════════════════════════════════════════════════════════════════
# 10. Full Pipeline & Retraining Service Tests
# ══════════════════════════════════════════════════════════════════════════

class TestFullPipelineAndRetrainingService:
    """Test ModelTrainer.train_all, RetrainingService, and standalone function wrappers."""

    def test_train_all_full_pipeline(self, db_session):
        """train_all invokes all model training phases and summarizes results."""
        trainer = ModelTrainer(db_session)
        dummy_inventory = {"orders": 100}
        dummy_summary = {"eta_prediction": {"total_versions": 1}}

        fake_eta = {"status": "success", "model_type": "eta_prediction"}
        fake_demand = {"status": "success", "model_type": "demand_forecast"}
        fake_slot = {"status": "failed", "error": "test fail"}
        fake_rec = {"status": "success", "model_type": "recommendation_engine"}
        fake_vendor = {"status": "success", "model_type": "vendor_ranking"}

        with (
            patch.object(trainer.builder, "get_data_source_inventory", return_value=dummy_inventory),
            patch.object(trainer, "train_eta", return_value=fake_eta),
            patch.object(trainer, "train_demand", return_value=fake_demand),
            patch.object(trainer, "train_slot_recommendation", return_value=fake_slot),
            patch.object(trainer, "train_recommendation", return_value=fake_rec),
            patch.object(trainer, "train_vendor_ranking", return_value=fake_vendor),
            patch("app.ml.registry.ModelRegistry.get_registry_summary", return_value=dummy_summary),
        ):
            res = trainer.train_all(days=30)

        assert res["training_window_days"] == 30
        assert res["data_inventory"] == dummy_inventory
        assert res["registry_summary"] == dummy_summary
        assert res["total_models_trained"] == 4  # 4 success status out of 5
        assert "trained_at" in res

    def test_retraining_service_methods(self, db_session):
        """RetrainingService session-management wrappers call trainer methods."""
        session_maker = lambda: db_session

        service = RetrainingService(session_maker)
        fake_all = {"status": "ok", "total_models_trained": 5}
        fake_eta = {"status": "success", "model_type": "eta_prediction"}
        fake_demand = {"status": "success", "model_type": "demand_forecast"}

        with (
            patch.object(ModelTrainer, "train_all", return_value=fake_all),
            patch.object(ModelTrainer, "train_eta", return_value=fake_eta),
            patch.object(ModelTrainer, "train_demand", return_value=fake_demand),
        ):
            res_all = service.retrain_all()
            res_eta = service.retrain_eta(days=60)
            res_demand = service.retrain_demand(days=45)

        assert res_all == fake_all
        assert res_eta == fake_eta
        assert res_demand == fake_demand

    def test_standalone_wrapper_functions(self, db_session):
        """Standalone module-level wrapper functions delegate to ModelTrainer."""
        fake_res = {"status": "success"}

        with (
            patch.object(ModelTrainer, "train_all", return_value=fake_res),
            patch.object(ModelTrainer, "train_eta", return_value=fake_res),
            patch.object(ModelTrainer, "train_demand", return_value=fake_res),
            patch.object(ModelTrainer, "train_slot_recommendation", return_value=fake_res),
            patch.object(ModelTrainer, "train_vendor_ranking", return_value=fake_res),
        ):
            assert run_full_training_pipeline(db_session, 60) == fake_res
            assert train_eta_models(db_session, 60) == fake_res
            assert train_demand_forecast(db_session, vendor_id=1, days=60) == fake_res
            assert train_vendor_ranking(db_session) == fake_res
            assert train_slot_recommendation(db_session) == fake_res
            assert train_eta(db_session, 60) == fake_res
            assert train_demand(db_session, 60) == fake_res
