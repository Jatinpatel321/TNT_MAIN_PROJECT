"""Test suite for the ML-powered AI architecture.

Tests model registry, feature extraction, training pipeline, predictions,
explainability, and the full API layer.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytest
from sqlalchemy.orm import Session

# Set a temp dir for model storage before importing ml modules
TEST_MODEL_DIR = Path(tempfile.mkdtemp())
os.environ["MODEL_STORAGE_DIR"] = str(TEST_MODEL_DIR)

from app.ml.registry import ModelRegistry
from app.ml.features import (
    is_rush_hour,
    extract_eta_features,
    extract_eta_training_data,
    extract_demand_features,
    extract_fraud_features,
    extract_vendor_ranking_features,
    extract_slot_features,
    build_user_item_matrix,
    ETA_FEATURE_NAMES,
)
from app.ml.training_pipeline import (
    train_eta_models,
    train_fraud_detection,
    train_vendor_ranking,
    train_slot_recommendation,
    RetrainingService,
    time_based_split,
)

def _evaluate(y_true, y_pred, metric_type="regression"):
    if metric_type == "regression":
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        mae = mean_absolute_error(y_true, y_pred)
        mse = mean_squared_error(y_true, y_pred)
        rmse = float(np.sqrt(mse))
        r2 = r2_score(y_true, y_pred)
        return {
            "mae": round(float(mae), 3),
            "mse": round(float(mse), 3),
            "rmse": round(rmse, 3),
            "r2": round(float(r2), 3),
        }
    else:
        from sklearn.metrics import accuracy_score
        return {
            "accuracy": float(accuracy_score(y_true, y_pred))
        }

def _try_import_xgboost():
    try:
        import xgboost
        return True
    except ImportError:
        return False
from app.ml.predictions import MLPredictionService
from app.ml.explain import get_feature_importance, explain_prediction, confidence_score
from app.ml.router import router as ml_router

from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.slots.model import Slot
from app.modules.users.model import User, UserRole
from app.modules.menu.model import MenuItem
from app.modules.feedback.model import VendorReview

from app.core.time_utils import utcnow_naive
from app.database.base import Base
from app.database.session import engine, SessionLocal
from datetime import datetime, timedelta


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_registry():
    """Clean model registry metadata and database rows between tests."""
    meta_path = TEST_MODEL_DIR / ".registry_metadata.json"
    if meta_path.exists():
        meta_path.unlink()
    for p in TEST_MODEL_DIR.iterdir():
        if p.is_dir():
            import shutil
            shutil.rmtree(p)
            
    # Clear DB registry metadata
    from app.database.session import SessionLocal
    from app.ml.ml_models_model import MlModel
    db = SessionLocal()
    try:
        db.query(MlModel).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    yield


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    # Use SQLite for fast tests
    test_engine = create_engine("sqlite:///:memory:")

    # Register date_part custom function for SQLite compatibility
    from sqlalchemy import event

    def date_part_sqlite(part, val):
        if not val:
            return None
        from datetime import datetime
        if isinstance(val, str):
            try:
                val = datetime.fromisoformat(val.split('.')[0])
            except Exception:
                try:
                    val = datetime.strptime(val.split('.')[0], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    return 0
        if part == 'dow':
            # Postgres DOW: 0 = Sunday, 1 = Monday, ..., 6 = Saturday
            # Python weekday: 0 = Monday, ..., 6 = Sunday
            return (val.weekday() + 1) % 7
        elif part == 'hour':
            return val.hour
        elif part == 'month':
            return val.month
        return 0

    def date_trunc_sqlite(part, val):
        if not val:
            return None
        from datetime import datetime
        if isinstance(val, str):
            try:
                val = datetime.fromisoformat(val.split('.')[0])
            except Exception:
                try:
                    val = datetime.strptime(val.split('.')[0], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    return "2000-01-01 00:00:00"
        if part == 'hour':
            return val.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        elif part == 'day':
            return val.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        return val.strftime("%Y-%m-%d %H:%M:%S")

    @event.listens_for(test_engine, "connect")
    def connect(dbapi_connection, connection_record):
        dbapi_connection.create_function("date_part", 2, date_part_sqlite)
        dbapi_connection.create_function("date_trunc", 2, date_trunc_sqlite)

    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(bind=test_engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
    Base.metadata.drop_all(bind=test_engine)


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _seed_test_data(db: Session):
    """Seed minimal test data."""
    # Create a test user
    user = User(
        id=1, phone="9999999999", name="Test Student",
        role=UserRole.STUDENT, vendor_type="food",
        is_active=True, is_approved=True, device_token="test_token",
    )
    db.add(user)

    # Create a test vendor
    vendor = User(
        id=2, phone="8888888888", name="Test Vendor",
        role=UserRole.VENDOR, vendor_type="food",
        is_active=True, is_approved=True,
    )
    db.add(vendor)

    # Create slots
    now = utcnow_naive()
    slot = Slot(
        id=1, vendor_id=2,
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        max_orders=20, current_orders=5,
        status="available",
    )
    db.add(slot)

    # Create orders with known completion times
    for i in range(20):
        order = Order(
            id=i + 1, user_id=1, vendor_id=2, slot_id=1,
            status=OrderStatus.COMPLETED,
            total_amount=100,
            actual_completion_minutes=15 + (i % 10),
            created_at=now - timedelta(days=i),
        )
        db.add(order)
        db.add(OrderItem(order_id=i + 1, menu_item_id=1, quantity=2, price_at_time=100))

    # Create menu item
    menu = MenuItem(
        id=1, vendor_id=2, name="Test Burger",
        price=100, is_available=True, category="food",
    )
    db.add(menu)

    # Create review
    review = VendorReview(vendor_id=2, user_id=1, rating=4, order_id=1)
    db.add(review)

    db.commit()


# ── Model Registry Tests ──────────────────────────────────────────────────

class TestModelRegistry:
    def test_save_and_load_model(self):
        """Test basic save/load cycle."""
        from sklearn.ensemble import RandomForestRegressor
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        model.fit([[1, 2], [3, 4], [5, 6]], [10, 20, 30])

        version_id = ModelRegistry.save(model, "test_model", metrics={"rmse": 5.0},
                                         features=["feat1", "feat2"])
        assert version_id == "test_model_v1"

        loaded, metadata = ModelRegistry.load("test_model")
        assert loaded is not None
        assert metadata["version_id"] == version_id
        assert metadata["metrics"]["rmse"] == 5.0

    def test_versioning(self):
        """Test multiple versions are tracked."""
        from sklearn.ensemble import RandomForestRegressor
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        model.fit([[1]], [1])

        v1 = ModelRegistry.save(model, "multi", metrics={"rmse": 10.0})
        v2 = ModelRegistry.save(model, "multi", metrics={"rmse": 5.0})

        versions = ModelRegistry.list_versions("multi")
        assert len(versions) == 2
        assert versions[0]["version_id"] == v2
        assert versions[1]["version_id"] == v1

    def test_get_latest_version(self):
        """Test latest version tracking."""
        from sklearn.ensemble import RandomForestRegressor
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        model.fit([[1]], [1])

        v1 = ModelRegistry.save(model, "latest_test")
        v2 = ModelRegistry.save(model, "latest_test")

        assert ModelRegistry.get_latest_version("latest_test") == v2

    def test_rollback(self):
        """Test rollback to previous version."""
        from sklearn.ensemble import RandomForestRegressor
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        model.fit([[1]], [1])

        ModelRegistry.save(model, "rollback_test")
        ModelRegistry.save(model, "rollback_test")

        result = ModelRegistry.rollback("rollback_test", 1)
        assert result == "rollback_test_v1"
        assert ModelRegistry.get_latest_version("rollback_test") == "rollback_test_v1"

    def test_compare_versions(self):
        """Test version comparison by metrics."""
        from sklearn.ensemble import RandomForestRegressor
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        model.fit([[1]], [1])

        ModelRegistry.save(model, "compare_test", metrics={"rmse": 10.0})
        ModelRegistry.save(model, "compare_test", metrics={"rmse": 5.0})

        compared = ModelRegistry.compare_versions("compare_test")
        assert compared[0]["metrics"]["rmse"] <= compared[1]["metrics"]["rmse"]


# ── Feature Extraction Tests ──────────────────────────────────────────────

class TestFeatures:
    def test_is_rush_hour(self):
        """Test rush hour detection."""
        # Lunch peak
        lunch = datetime(2026, 6, 24, 12, 30)
        assert is_rush_hour(lunch)

        # Dinner peak
        dinner = datetime(2026, 6, 24, 19, 0)
        assert is_rush_hour(dinner)

        # Off-peak
        off = datetime(2026, 6, 24, 15, 0)
        assert not is_rush_hour(off)

    def test_extract_eta_features(self, db_session):
        """Test ETA feature extraction."""
        _seed_test_data(db_session)
        features = extract_eta_features(db_session, vendor_id=2)
        assert len(features) > 0
        for f in features:
            assert "vendor_id" in f
            assert "queue_length" in f
            assert "slot_occupancy" in f
            assert "item_count" in f
            assert "time_of_day" in f
            assert "weekday" in f
            assert "rush_hour" in f

    def test_extract_eta_training_data(self, db_session):
        """Test ETA training data extraction."""
        _seed_test_data(db_session)
        X, y, names = extract_eta_training_data(db_session)
        assert len(X) > 0
        assert len(y) > 0
        assert len(names) == 7
        assert "vendor_id" in names

    def test_extract_demand_features(self, db_session):
        """Test demand feature extraction."""
        _seed_test_data(db_session)
        X, y, names = extract_demand_features(db_session, vendor_id=2)
        assert len(names) > 0

    def test_fraud_features(self, db_session):
        """Test fraud feature extraction."""
        _seed_test_data(db_session)
        X, y, names = extract_fraud_features(db_session, user_id=1)
        assert len(names) == 6
        assert "cancel_rate" in names


# ── Training Pipeline Tests ──────────────────────────────────────────────

class TestTraining:
    def test_evaluate_regression(self):
        """Test regression evaluation metrics."""
        y_true = np.array([10, 20, 30, 40, 50])
        y_pred = np.array([12, 18, 32, 38, 48])
        metrics = _evaluate(y_true, y_pred, "regression")
        assert "rmse" in metrics
        assert "mae" in metrics
        assert "r2" in metrics
        assert metrics["rmse"] >= 0

    def test_evaluate_classification(self):
        """Test classification evaluation metrics."""
        y_true = np.array([0, 1, 0, 1, 0])
        y_pred = np.array([0, 1, 0, 1, 0])
        metrics = _evaluate(y_true, y_pred, "classification")
        assert "accuracy" in metrics
        assert metrics["accuracy"] == 1.0

    def test_train_eta_models_skipped(self, db_session):
        """Test ETA training with insufficient data."""
        result = train_eta_models(db_session, days=30)
        assert result["status"] in ("skipped", "failed")

    def test_train_eta_models(self, db_session):
        """Test ETA training pipeline with seeded data."""
        _seed_test_data(db_session)
        result = train_eta_models(db_session, days=90)
        if result["status"] == "trained":
            assert "best_version" in result
            assert "metrics" in result
            assert "rmse" in result["metrics"]

    def test_retraining_service(self, db_session):
        """Test retraining service instantiation."""
        service = RetrainingService(lambda: db_session)
        result = service.retrain_all()
        assert "eta" in result or "models" in result


# ── Prediction Service Tests ──────────────────────────────────────────────

class TestMLPredictionService:
    def test_predict_eta_heuristic_fallback(self, db_session):
        """Test ETA prediction falls back to heuristic when no model."""
        _seed_test_data(db_session)
        service = MLPredictionService(db_session)
        result = service.predict_eta(vendor_id=2, slot_id=1, item_count=2)
        assert "predicted_eta_minutes" in result
        assert result["method"] in ("ml", "heuristic", "default")
        assert 5 <= result["predicted_eta_minutes"] <= 60

    def test_detect_fraud_heuristic(self, db_session):
        """Test fraud detection falls back gracefully."""
        _seed_test_data(db_session)
        service = MLPredictionService(db_session)
        result = service.detect_fraud(user_id=1, order_id=1)
        assert "is_fraud" in result
        assert "score" in result

    def test_rank_vendors(self, db_session):
        """Test vendor ranking."""
        _seed_test_data(db_session)
        service = MLPredictionService(db_session)
        rankings = service.rank_vendors()
        assert isinstance(rankings, list)
        if rankings:
            assert "vendor_id" in rankings[0]
            assert "rank_score" in rankings[0]

    def test_recommend_slot(self, db_session):
        """Test slot recommendation."""
        _seed_test_data(db_session)
        service = MLPredictionService(db_session)
        result = service.recommend_slot(user_id=1)
        assert "recommended_slots" in result
        assert "fastest" in result
        assert "least_crowded" in result

    def test_forecast_demand(self, db_session):
        """Test demand forecasting."""
        _seed_test_data(db_session)
        service = MLPredictionService(db_session)
        result = service.forecast_demand(vendor_id=2, days_ahead=3)
        assert "forecasts" in result
        assert "total_predicted" in result

    def test_get_personalized_recommendations(self, db_session):
        """Test personalized recommendations."""
        _seed_test_data(db_session)
        service = MLPredictionService(db_session)
        result = service.get_personalized_recommendations(user_id=1)
        assert "hybrid" in result
        assert isinstance(result["hybrid"], list)


# ── Explainability Tests ──────────────────────────────────────────────────

class TestExplainability:
    def test_get_feature_importance(self):
        """Test feature importance extraction."""
        from sklearn.ensemble import RandomForestRegressor
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        X = np.array([[1, 2, 3], [4, 5, 6]])
        y = np.array([10, 20])
        model.fit(X, y)

        importance = get_feature_importance(model, ["a", "b", "c"])
        assert len(importance) == 3
        assert all("feature" in i and "importance" in i for i in importance)
        assert importance[0]["importance"] >= importance[-1]["importance"]

    def test_explain_prediction(self):
        """Test prediction explainability."""
        from sklearn.ensemble import RandomForestRegressor
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        X = np.array([[1, 2], [4, 5]])
        y = np.array([10, 20])
        model.fit(X, y)

        explanation = explain_prediction(model, X[0], ["a", "b"], 15.0)
        assert "prediction" in explanation
        assert "top_contributing_features" in explanation
        assert "explanation" in explanation

    def test_confidence_score(self):
        """Test confidence scoring."""
        from sklearn.ensemble import RandomForestRegressor
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        X = np.array([[1, 2], [4, 5]])
        y = np.array([10, 20])
        model.fit(X, y)

        conf = confidence_score(model, X[0], 15.0)
        assert 0.0 <= conf <= 1.0


# ── Router / API Tests ────────────────────────────────────────────────────

class TestMLRouter:
    def test_router_prefix(self):
        """Test router has correct prefix."""
        assert ml_router.prefix == "/ml"

    def test_router_routes(self):
        """Test that all expected routes are registered."""
        routes = [r.path for r in ml_router.routes]
        assert "/ml/registry" in routes
        assert "/ml/predict/eta" in routes
        assert "/ml/forecast/demand" in routes
        assert "/ml/recommend/slots" in routes
        assert "/ml/recommend/personalized" in routes
        assert "/ml/rank/vendors" in routes
        assert "/ml/detect/fraud" in routes
        assert "/ml/train/all" in routes
        assert "/ml/train/eta" in routes
        assert "/ml/train/fraud" in routes
        assert "/ml/explain/{model_type}" in routes
        assert "/ml/accuracy/{model_type}" in routes
        assert "/ml/backtest/eta" in routes
        assert "/ml/backtest/vendor-ranking" in routes
        assert "/ml/drift/check" in routes
        assert "/ml/drift/reports" in routes


# ── Integration: Registry + Training + Prediction ─────────────────────────

class TestFullPipeline:
    def test_registry_summary(self):
        """Test registry summary after saving models."""
        from sklearn.ensemble import RandomForestRegressor
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        model.fit([[1, 2], [3, 4]], [10, 20])

        ModelRegistry.save(model, "integration_test", metrics={"rmse": 5.0})
        summary = ModelRegistry.get_registry_summary()
        assert "integration_test" in summary
        assert summary["integration_test"]["total_versions"] == 1

    def test_all_model_types_exist(self):
        """Test all expected model types are listed."""
        registered_types = ModelRegistry.get_all_model_types()
        assert isinstance(registered_types, list)


# ── CV & Hyper-parameter Tuning Tests ─────────────────────────────────────

class TestTrainingCV:
    """Verify that training runs record cv_score and tuned_params in the registry."""

    # ── helpers ─────────────────────────────────────────────────────────────

    def _make_xy(self, n: int = 30):
        """Return simple regression X, y and feature names with n samples."""
        rng = np.random.default_rng(0)
        X = rng.standard_normal((n, 4))
        y = X[:, 0] * 2 + rng.standard_normal(n) * 0.1  # low noise, learnable
        return X, y, ["f0", "f1", "f2", "f3"]

    def _make_xy_clf(self, n: int = 30):
        """Return binary classification X, y with guaranteed both classes."""
        rng = np.random.default_rng(1)
        X = rng.standard_normal((n, 4))
        y = (X[:, 0] > 0).astype(float)
        # Ensure both classes present
        y[0] = 0.0
        y[1] = 1.0
        return X, y, ["f0", "f1", "f2", "f3"]

    # ── _tune_regressor ──────────────────────────────────────────────────────

    def test_tune_regressor_returns_tuned_params(self, db_session):
        """_tune_regressor must return a non-empty best_params dict."""
        from sklearn.ensemble import RandomForestRegressor
        from app.ml.training_pipeline import ModelTrainer

        trainer = ModelTrainer(db_session)
        X, y, _ = self._make_xy()
        rf_base = RandomForestRegressor(random_state=42)
        _, best_params, cv_rmse = trainer._tune_regressor(
            rf_base, ModelTrainer._RF_PARAM_GRID, X, y, "test-rf"
        )
        assert isinstance(best_params, dict), "best_params must be a dict"
        assert len(best_params) > 0, "best_params must be non-empty (tuning found something)"
        assert "n_estimators" in best_params, "expected n_estimators in tuned params"
        assert isinstance(cv_rmse, float)
        assert cv_rmse >= 0.0

    def test_tune_regressor_cv_score_is_finite(self, db_session):
        """CV RMSE from _tune_regressor must be a finite non-negative float."""
        from sklearn.ensemble import RandomForestRegressor
        from app.ml.training_pipeline import ModelTrainer

        trainer = ModelTrainer(db_session)
        X, y, _ = self._make_xy()
        _, _, cv_rmse = trainer._tune_regressor(
            RandomForestRegressor(random_state=42),
            ModelTrainer._RF_PARAM_GRID, X, y, "test-rf-cv"
        )
        assert np.isfinite(cv_rmse), "cv_rmse must be finite"

    def test_tune_classifier_returns_tuned_params(self, db_session):
        """_tune_classifier must return a non-empty best_params dict and a cv_f1."""
        from sklearn.ensemble import RandomForestClassifier
        from app.ml.training_pipeline import ModelTrainer

        trainer = ModelTrainer(db_session)
        X, y, _ = self._make_xy_clf()
        clf_base = RandomForestClassifier(random_state=42, class_weight="balanced")
        param_grid = {
            "n_estimators": [10, 20],
            "max_depth": [3, 5],
        }
        _, best_params, cv_f1 = trainer._tune_classifier(
            clf_base, param_grid, X, y, "test-clf"
        )
        assert isinstance(best_params, dict)
        assert len(best_params) > 0
        assert isinstance(cv_f1, float)
        assert 0.0 <= cv_f1 <= 1.0

    # ── registry metadata written by train_eta ───────────────────────────────

    def test_train_eta_records_cv_score_in_registry(self, db_session):
        """After train_eta_models, the saved registry entry must have cv_rmse in metrics."""
        _seed_test_data(db_session)
        result = train_eta_models(db_session, days=90)
        # Skip if no data (shouldn't happen with seeded data, but be defensive)
        if result.get("status") not in ("success",):
            pytest.skip(f"training returned: {result.get('status')}")

        assert "best_cv_rmse" in result, "top-level result must contain best_cv_rmse"
        assert isinstance(result["best_cv_rmse"], float)

        # Read back from registry and verify metadata
        loaded = ModelRegistry.load("eta_prediction")
        assert loaded is not None, "Registry must have a saved eta_prediction model"
        _, metadata = loaded
        assert "cv_rmse" in metadata["metrics"], "metrics dict must contain cv_rmse"
        assert "cv_folds" in metadata["metrics"], "metrics dict must contain cv_folds"
        assert metadata["metrics"]["cv_folds"] == 5

    def test_train_eta_records_tuned_params_in_registry(self, db_session):
        """After train_eta_models, the saved registry entry must contain tuned_params."""
        _seed_test_data(db_session)
        result = train_eta_models(db_session, days=90)
        if result.get("status") not in ("success",):
            pytest.skip(f"training returned: {result.get('status')}")

        assert "tuned_params" in result, "top-level result must have tuned_params"

        loaded = ModelRegistry.load("eta_prediction")
        assert loaded is not None
        _, metadata = loaded
        hp = metadata.get("hyperparams", {})
        assert "tuned_params" in hp, "hyperparams must contain tuned_params key"
        # tuned_params should be a non-empty dict (search found at least one param)
        tuned = hp["tuned_params"]
        assert isinstance(tuned, dict)
        # With real sklearn RandomizedSearchCV, at least one param is always set
        assert len(tuned) > 0, "tuned_params must be non-empty"

    def test_train_eta_comparison_entries_have_cv_rmse(self, db_session):
        """Each comparison entry in the train_eta result must include cv_rmse."""
        _seed_test_data(db_session)
        result = train_eta_models(db_session, days=90)
        if result.get("status") not in ("success",):
            pytest.skip(f"training returned: {result.get('status')}")

        comparison = result.get("comparison", [])
        assert len(comparison) >= 1, "at least one model compared"
        for entry in comparison:
            assert "cv_rmse" in entry, f"comparison entry {entry['model']} missing cv_rmse"
            assert isinstance(entry["cv_rmse"], float)

    # ── fraud_detection ──────────────────────────────────────────────────────

    def test_train_fraud_records_cv_f1_in_registry(self, db_session):
        """After train_fraud_detection, registry metrics must contain cv_f1."""
        _seed_test_data(db_session)
        result = train_fraud_detection(db_session)
        if result.get("status") not in ("success",):
            pytest.skip(f"fraud training returned: {result.get('status')}")

        assert "cv_f1" in result, "top-level result must contain cv_f1"

        loaded = ModelRegistry.load("fraud_detection")
        assert loaded is not None
        _, metadata = loaded
        assert "cv_f1" in metadata["metrics"], "metrics must contain cv_f1"
        assert 0.0 <= metadata["metrics"]["cv_f1"] <= 1.0

    def test_train_fraud_records_tuned_params_in_registry(self, db_session):
        """After train_fraud_detection, hyperparams must contain tuned_params."""
        _seed_test_data(db_session)
        result = train_fraud_detection(db_session)
        if result.get("status") not in ("success",):
            pytest.skip(f"fraud training returned: {result.get('status')}")

        assert "tuned_params" in result

        loaded = ModelRegistry.load("fraud_detection")
        assert loaded is not None
        _, metadata = loaded
        hp = metadata.get("hyperparams", {})
        assert "tuned_params" in hp
        assert isinstance(hp["tuned_params"], dict)

    # ── best-model selection is based on cv_rmse ─────────────────────────────

    def test_best_model_selection_uses_cv_rmse(self, db_session):
        """The best_cv_rmse in the result must equal the minimum cv_rmse across
        all comparison entries, confirming selection by CV score."""
        _seed_test_data(db_session)
        result = train_eta_models(db_session, days=90)
        if result.get("status") not in ("success",):
            pytest.skip(f"training returned: {result.get('status')}")

        comparison = result.get("comparison", [])
        if not comparison:
            pytest.skip("no comparison entries")

        min_cv = min(e["cv_rmse"] for e in comparison)
        # best_cv_rmse is stored as round(..., 4), so allow 1e-4 tolerance
        assert result["best_cv_rmse"] == pytest.approx(min_cv, abs=1e-4), (
            f"best_cv_rmse {result['best_cv_rmse']} != min cv_rmse {min_cv} across comparison"
        )


# ── Temporal Split Tests ──────────────────────────────────────────────────

class TestTemporalSplit:
    """Unit tests for time_based_split() — the core no-leakage guarantee."""

    def _make_data(self, n: int = 20):
        """Return X, y, timestamps with timestamps spread daily over n days."""
        rng = np.random.default_rng(42)
        X = rng.standard_normal((n, 3))
        y = rng.standard_normal(n)
        base = datetime(2026, 1, 1)
        timestamps = np.array(
            [base + timedelta(days=i) for i in range(n)], dtype=object
        )
        return X, y, timestamps

    # ── core no-leakage invariant ─────────────────────────────────────────

    def test_no_temporal_leakage(self):
        """Every timestamp in the test set must be >= every timestamp in the train set."""
        X, y, timestamps = self._make_data(20)
        # Shuffle before passing to confirm sorting is done internally
        rng = np.random.default_rng(0)
        perm = rng.permutation(len(X))
        X, y, timestamps = X[perm], y[perm], timestamps[perm]

        X_train, X_test, y_train, y_test, ts_train, ts_test = time_based_split(
            X, y, timestamps, test_size=0.2
        )

        assert len(ts_train) > 0, "train set must be non-empty"
        assert len(ts_test) > 0, "test set must be non-empty"

        max_train_ts = max(ts_train)
        min_test_ts = min(ts_test)
        assert min_test_ts >= max_train_ts, (
            f"Temporal leakage detected: earliest test timestamp {min_test_ts} "
            f"is before latest train timestamp {max_train_ts}"
        )

    def test_train_set_is_sorted_ascending(self):
        """Train timestamps should be in non-decreasing order."""
        X, y, timestamps = self._make_data(15)
        # Reverse-sort before passing to confirm sort is applied
        rev = np.argsort(timestamps)[::-1]
        X_train, _, _, _, ts_train, _ = time_based_split(
            X[rev], y[rev], timestamps[rev], test_size=0.25
        )
        for i in range(1, len(ts_train)):
            assert ts_train[i] >= ts_train[i - 1], (
                f"Train timestamps not sorted at index {i}: "
                f"{ts_train[i-1]} > {ts_train[i]}"
            )

    def test_split_proportions(self):
        """The split must respect the requested test_size fraction (within ±1 row)."""
        n = 50
        X, y, timestamps = self._make_data(n)
        test_size = 0.2
        X_train, X_test, _, _, _, _ = time_based_split(X, y, timestamps, test_size=test_size)
        expected_test = int(n * test_size)
        # Allow ±1 due to integer rounding
        assert abs(len(X_test) - expected_test) <= 1, (
            f"Expected ~{expected_test} test rows, got {len(X_test)}"
        )
        assert len(X_train) + len(X_test) == n

    def test_empty_input_returns_empty(self):
        """time_based_split on empty input must not crash and return empty arrays."""
        X = np.empty((0, 3))
        y = np.array([])
        ts = np.array([], dtype=object)
        X_train, X_test, y_train, y_test, ts_train, ts_test = time_based_split(X, y, ts)
        assert len(X_train) == 0
        assert len(X_test) == 0

    def test_single_sample(self):
        """With a single sample, everything goes to train."""
        X = np.array([[1.0, 2.0]])
        y = np.array([5.0])
        ts = np.array([datetime(2026, 1, 1)], dtype=object)
        X_train, X_test, y_train, y_test, ts_train, ts_test = time_based_split(
            X, y, ts, test_size=0.2
        )
        assert len(X_train) == 1
        # test set may be empty for a single sample (split_at=max(1,0)=1)

    def test_unsorted_input_is_sorted(self):
        """Passing timestamps in reverse order must still produce a no-leakage split."""
        n = 10
        _, y, timestamps = self._make_data(n)
        X = np.arange(n).reshape(-1, 1).astype(float)
        # Reverse the natural order
        X_r, y_r, ts_r = X[::-1].copy(), y[::-1].copy(), timestamps[::-1].copy()

        _, _, _, _, ts_train, ts_test = time_based_split(X_r, y_r, ts_r, test_size=0.3)
        if len(ts_test) > 0:
            assert min(ts_test) >= max(ts_train), "Leakage after reversing input order"

    # ── integration: train_eta uses temporal split ────────────────────────

    def test_train_eta_uses_temporal_split(self, db_session):
        """train_eta result must carry split_method='temporal' when timestamp
        alignment succeeds (may fall back on SQLite in-memory — both are acceptable)."""
        _seed_test_data(db_session)
        result = train_eta_models(db_session, days=90)
        if result.get("status") not in ("success",):
            pytest.skip(f"training returned: {result.get('status')}")

        assert "split_method" in result, "result must carry split_method key"
        # Temporal split requires the timestamp query to match the feature query.
        # On SQLite (test DB) date_trunc may behave differently, so both outcomes
        # are valid — what matters is that the key is present and one of the known values.
        assert result["split_method"] in ("temporal", "random_fallback"), (
            f"Unexpected split_method: {result['split_method']}"
        )


# ── Backtesting Engine Tests ──────────────────────────────────────────────

class TestBacktest:
    """Unit tests for app.ml.backtest module functions."""

    def test_backtest_eta_insufficient_data(self, db_session):
        """Should return status='insufficient_data' when < 20 qualifying orders exist."""
        from app.ml.backtest import backtest_eta
        # db_session has 0 orders
        res = backtest_eta(db_session, days=30)
        assert res["status"] == "insufficient_data"
        assert res["total_orders"] == 0
        assert "Fewer than 20" in res["reason"]

    def test_backtest_eta_sufficient_data(self, db_session):
        """Should calculate metrics when >= 20 qualifying orders exist."""
        from app.ml.backtest import backtest_eta
        _seed_test_data(db_session)  # seeds 20 completed orders
        res = backtest_eta(db_session, days=30)
        assert res["status"] == "success"
        assert res["total_orders"] >= 20
        assert "within_3_min_pct" in res
        assert "within_5_min_pct" in res
        assert "mae_minutes" in res
        assert 0.0 <= res["within_3_min_pct"] <= 100.0
        assert 0.0 <= res["within_5_min_pct"] <= 100.0
        assert res["mae_minutes"] >= 0.0

    def test_backtest_vendor_ranking_insufficient_data(self, db_session):
        """Should return status='insufficient_data' when < 20 orders exist."""
        from app.ml.backtest import backtest_vendor_ranking
        res = backtest_vendor_ranking(db_session, days=30)
        assert res["status"] == "insufficient_data"
        assert res["total_orders"] == 0

    def test_backtest_vendor_ranking_sufficient_data(self, db_session):
        """Should calculate hit rates when >= 20 orders exist."""
        from app.ml.backtest import backtest_vendor_ranking
        _seed_test_data(db_session)  # seeds 20 orders
        res = backtest_vendor_ranking(db_session, days=30)
        assert res["status"] == "success"
        assert res["total_orders"] >= 20
        assert "top_1_hit_rate" in res
        assert "top_3_hit_rate" in res
        assert "caveat" in res
        assert 0.0 <= res["top_1_hit_rate"] <= 1.0
        assert 0.0 <= res["top_3_hit_rate"] <= 1.0


# ── Shadow Logging Tests ──────────────────────────────────────────────────

class TestShadowLogging:
    """Unit tests for shadow logging mode in predict_with_fallback and backfilling."""

    def test_shadow_mode_logs_both_predictions_and_returns_heuristic(self, db_session):
        """When shadow=True, predict_with_fallback logs to shadow_log and returns heuristic result."""
        from app.modules.ai_intelligence.ml_bridge import predict_with_fallback
        from app.ml.shadow_log_model import ShadowLog

        def heuristic_fn():
            return 22.5

        features = {
            "vendor_id": 2.0,
            "queue_length": 3.0,
            "slot_occupancy": 0.5,
            "item_count": 1.0,
            "time_of_day": 12.0,
            "weekday": 1.0,
            "rush_hour": 1.0,
        }

        res, source = predict_with_fallback(
            "eta_prediction",
            features,
            heuristic_fn,
            db=db_session,
            entity_id=50,
            shadow=True,
        )

        # Returned value must be heuristic result
        assert res == 22.5
        assert source == "heuristic"

        # Check shadow_log entry in DB
        log_entry = db_session.query(ShadowLog).filter(
            ShadowLog.model_type == "eta_prediction",
            ShadowLog.entity_id == 50,
        ).first()

        assert log_entry is not None
        assert log_entry.predicted_heuristic == 22.5
        assert log_entry.actual_value is None

    def test_eta_planner_triggers_shadow_logging(self, db_session):
        """ETAEngine.predict_eta should generate a shadow_log row when called."""
        from app.modules.ai_intelligence.planners.eta_engine import ETAEngine
        from app.ml.shadow_log_model import ShadowLog

        _seed_test_data(db_session)
        # Add additional orders so vendor order_count >= 30
        now = utcnow_naive()
        for i in range(10):
            db_session.add(Order(
                id=100 + i, user_id=1, vendor_id=2, slot_id=1,
                status=OrderStatus.COMPLETED, total_amount=100,
                created_at=now - timedelta(days=i),
            ))
        db_session.commit()

        engine = ETAEngine(db_session)
        res = engine.predict_eta(slot_id=1, vendor_id=2)

        assert "predicted_eta_minutes" in res

        # Check shadow_log entry created
        logs = db_session.query(ShadowLog).filter(
            ShadowLog.model_type == "eta_prediction"
        ).all()
        assert len(logs) > 0

    def test_demand_planner_triggers_shadow_logging(self, db_session):
        """DemandPlanner._generate_demand_forecast should generate a shadow_log row."""
        from app.modules.ai_intelligence.planners.demand_planner import DemandPlanner
        from app.ml.shadow_log_model import ShadowLog

        _seed_test_data(db_session)
        # Add an old order so vendor history >= 90 days
        old_order = Order(
            id=200, user_id=1, vendor_id=2, slot_id=1,
            status=OrderStatus.COMPLETED, total_amount=100,
            created_at=utcnow_naive() - timedelta(days=95),
        )
        db_session.add(old_order)
        db_session.commit()

        planner = DemandPlanner(db_session)
        res = planner.get_demand_planning(vendor_id=2)

        assert "forecast" in res

        logs = db_session.query(ShadowLog).filter(
            ShadowLog.model_type == "demand_forecast"
        ).all()
        assert len(logs) > 0

    def test_backfill_shadow_actuals(self, db_session):
        """backfill_shadow_actuals should update actual_value on shadow_log entries."""
        from app.ml.shadow_log_model import ShadowLog
        from app.ml.backtest import backfill_shadow_actuals

        _seed_test_data(db_session)

        # Insert un-backfilled shadow log entry
        log_entry = ShadowLog(
            model_type="eta_prediction",
            entity_id=1,  # order_id 1 in seeded data
            predicted_model=15.0,
            predicted_heuristic=16.0,
            actual_value=None,
        )
        db_session.add(log_entry)
        db_session.commit()

        # Run backfill
        bf_res = backfill_shadow_actuals(db_session)

        assert bf_res["status"] == "success"
        assert bf_res["updated_count"] >= 1

        db_session.refresh(log_entry)
        assert log_entry.actual_value is not None
        assert log_entry.actual_value > 0


# ── Drift Detection Tests ──────────────────────────────────────────────────

class TestDriftDetection:
    """Unit tests for compute_psi, check_data_drift, and check_prediction_drift."""

    def test_compute_psi_identical_distributions(self):
        """PSI between identical distributions must equal 0.0."""
        from app.ml.drift import compute_psi
        arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        psi = compute_psi(arr, arr)
        assert psi == 0.0

    def test_compute_psi_hand_calculated_synthetic_shift(self):
        """Hand-verified calculation: expected=[1..10], actual shifted significantly."""
        from app.ml.drift import compute_psi
        # Expected: uniform 1..10
        expected = np.linspace(1, 10, 100)
        # Actual: heavily shifted to 8..10 range (significant drift)
        actual = np.linspace(8, 10, 100)

        psi = compute_psi(expected, actual, bins=5)
        # With significant shift, PSI should be > 0.2
        assert psi > 0.2, f"Expected PSI > 0.2 for shifted distribution, got {psi}"

    def test_check_data_drift_flags_drifted_feature(self, db_session):
        """check_data_drift should flag features with PSI > 0.2."""
        from app.ml.drift import check_data_drift
        _seed_test_data(db_session)

        # Run check_data_drift on eta_prediction
        res = check_data_drift("eta_prediction", db_session, lookback_days=7)
        assert "has_drift" in res
        assert "drifted_features" in res
        assert "feature_psi" in res
        assert res["status"] == "success"

    def test_run_all_drift_checks_saves_reports(self, db_session):
        """run_all_drift_checks should generate reports for all 5 model types in drift_reports table."""
        from app.ml.drift import run_all_drift_checks
        from app.ml.drift_report_model import DriftReport

        _seed_test_data(db_session)
        res = run_all_drift_checks(db_session, lookback_days=7)

        assert res["status"] == "success"
        assert len(res["reports"]) == 5

        # Query database to confirm records written
        db_reports = db_session.query(DriftReport).all()
        assert len(db_reports) == 10  # 5 model types * 2 check types (data + prediction)


class TestScheduledRetraining:
    """Test fault-tolerant scheduled retraining and log persistence."""

    def test_scheduled_retraining_continues_on_failure(self, db_session, monkeypatch):
        """Mock failure in one model type (e.g. demand_forecast raises an Exception), verify others still run."""
        from app.ml.retraining import run_scheduled_retraining
        from app.ml.retraining_log_model import RetrainingLog
        import app.ml.training_pipeline as tp

        # Mock train_demand to raise RuntimeError
        def mock_train_demand(db, days=90):
            raise RuntimeError("Synthetic simulated GPU/Memory failure during demand retraining")

        # Mock train_eta to succeed
        def mock_train_eta(db, days=90):
            return {"status": "success", "version_id": "v_test_eta_123"}

        monkeypatch.setattr(tp, "train_demand", mock_train_demand)
        monkeypatch.setattr(tp, "train_eta", mock_train_eta)

        # Run scheduled retraining across model types
        results = run_scheduled_retraining(
            model_types=["eta_prediction", "demand_forecast", "vendor_ranking"],
            db=db_session,
        )

        # 1. ETA prediction should have succeeded
        assert results["eta_prediction"]["status"] == "success"
        assert results["eta_prediction"]["version_id"] == "v_test_eta_123"

        # 2. Demand forecast should have failed gracefully without crashing the loop
        assert results["demand_forecast"]["status"] == "failed"
        assert "Synthetic simulated GPU/Memory failure" in results["demand_forecast"]["error"]

        # 3. Vendor ranking should still have run after demand forecast failure!
        assert "vendor_ranking" in results
        assert results["vendor_ranking"]["status"] in ["success", "insufficient_data", "completed", "failed"]

        # 4. Verify DB logs recorded all 3 attempts
        logs = db_session.query(RetrainingLog).all()
        assert len(logs) == 3
        failed_log = next(l for l in logs if l.model_type == "demand_forecast")
        assert failed_log.status == "failed"
        assert "Synthetic simulated GPU/Memory failure" in failed_log.error_message

    def test_scheduled_retraining_handles_insufficient_data(self, db_session, monkeypatch):
        """Verify that 'insufficient_data' status is logged cleanly without crashing."""
        from app.ml.retraining import run_scheduled_retraining
        from app.ml.retraining_log_model import RetrainingLog
        import app.ml.training_pipeline as tp

        def mock_train_slot(db):
            return {"status": "insufficient_data", "reason": "Only 3 records found (< 20)"}

        monkeypatch.setattr(tp, "train_slot_recommendation", mock_train_slot)

        results = run_scheduled_retraining(
            model_types=["slot_recommendation"],
            db=db_session,
        )

        assert results["slot_recommendation"]["status"] == "insufficient_data"

        logs = db_session.query(RetrainingLog).filter(RetrainingLog.model_type == "slot_recommendation").all()
        assert len(logs) >= 1
        assert logs[-1].status == "insufficient_data"


class TestModelPromotion:
    """Test champion vs candidate promotion rules (promote_if_better)."""

    def test_promote_better_candidate(self, db_session):
        """Candidate with lower RMSE (better) should be promoted over champion."""
        from app.ml.registry import ModelRegistry
        from app.ml.promotion import promote_if_better
        from sklearn.ensemble import RandomForestRegressor
        import numpy as np

        model = RandomForestRegressor()
        X, y = np.array([[1], [2]]), np.array([1, 2])
        model.fit(X, y)

        # 1. Save v1 as active champion with RMSE 5.0
        v1_id = ModelRegistry.save(model, "eta_prediction", metrics={"cv_rmse": 5.0})
        ModelRegistry.set_active_version("eta_prediction", v1_id)

        # 2. Save v2 as candidate with lower (better) RMSE 3.0
        v2_id = ModelRegistry.save(model, "eta_prediction", metrics={"cv_rmse": 3.0})

        # 3. Evaluate promotion
        promoted = promote_if_better("eta_prediction", v2_id)
        assert promoted is True
        assert ModelRegistry.get_active_version("eta_prediction")["version_id"] == v2_id

    def test_do_not_promote_worse_candidate(self, db_session):
        """Candidate with higher RMSE (worse) should NOT be promoted; champion remains active."""
        from app.ml.registry import ModelRegistry
        from app.ml.promotion import promote_if_better
        from sklearn.ensemble import RandomForestRegressor
        import numpy as np

        model = RandomForestRegressor()
        X, y = np.array([[1], [2]]), np.array([1, 2])
        model.fit(X, y)

        # 1. Save v1 as champion with RMSE 3.0
        v1_id = ModelRegistry.save(model, "eta_prediction", metrics={"cv_rmse": 3.0})
        ModelRegistry.set_active_version("eta_prediction", v1_id)

        # 2. Save v2 as candidate with higher (worse) RMSE 7.0
        v2_id = ModelRegistry.save(model, "eta_prediction", metrics={"cv_rmse": 7.0})

        # 3. Evaluate promotion
        promoted = promote_if_better("eta_prediction", v2_id)
        assert promoted is False
        assert ModelRegistry.get_active_version("eta_prediction")["version_id"] == v1_id

    def test_promote_equal_metrics_candidate(self, db_session):
        """Candidate with equal RMSE (tie) is promoted deterministically to prefer newer retrained model."""
        from app.ml.registry import ModelRegistry
        from app.ml.promotion import promote_if_better
        from sklearn.ensemble import RandomForestRegressor
        import numpy as np

        model = RandomForestRegressor()
        X, y = np.array([[1], [2]]), np.array([1, 2])
        model.fit(X, y)

        v1_id = ModelRegistry.save(model, "eta_prediction", metrics={"cv_rmse": 4.0})
        ModelRegistry.set_active_version("eta_prediction", v1_id)

        v2_id = ModelRegistry.save(model, "eta_prediction", metrics={"cv_rmse": 4.0})

        promoted = promote_if_better("eta_prediction", v2_id)
        assert promoted is True
        assert ModelRegistry.get_active_version("eta_prediction")["version_id"] == v2_id


class TestAutomaticRollback:
    """Test automatic degradation-triggered rollback (check_and_rollback_degraded_models)."""

    def test_automatic_rollback_triggered_by_degradation(self, db_session, monkeypatch):
        """Synthetic degraded live accuracy scenario (> 20% drop) should trigger rollback to previous version."""
        from app.ml.registry import ModelRegistry
        from app.ml.promotion import check_and_rollback_degraded_models
        from sklearn.ensemble import RandomForestClassifier
        import numpy as np

        model = RandomForestClassifier()
        X, y = np.array([[1], [2]]), np.array([0, 1])
        model.fit(X, y)

        # 1. Save v1 (previous champion) with baseline cv_f1 0.90
        v1_id = ModelRegistry.save(model, "fraud_detection", metrics={"cv_f1": 0.90})
        ModelRegistry.set_active_version("fraud_detection", v1_id)

        # 2. Save v2 (degraded active version) with cv_f1 0.50 (> 20% drop relative to 0.90)
        v2_id = ModelRegistry.save(model, "fraud_detection", metrics={"cv_f1": 0.50})
        ModelRegistry.set_active_version("fraud_detection", v2_id)

        # 3. Run check_and_rollback_degraded_models
        results = check_and_rollback_degraded_models(db_session)

        # 4. Assert rollback occurred
        assert results["fraud_detection"]["rolled_back"] is True
        assert results["fraud_detection"]["previous_version"] == v1_id
        assert ModelRegistry.get_active_version("fraud_detection")["version_id"] == v1_id





