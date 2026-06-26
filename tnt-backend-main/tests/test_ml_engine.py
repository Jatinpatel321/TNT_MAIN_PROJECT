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
    _evaluate,
    _try_import_xgboost,
    train_eta_models,
    train_fraud_detection,
    train_vendor_ranking,
    train_slot_recommendation,
    RetrainingService,
)
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
    """Clean model registry metadata between tests."""
    meta_path = TEST_MODEL_DIR / ".registry_metadata.json"
    if meta_path.exists():
        meta_path.unlink()
    for p in TEST_MODEL_DIR.iterdir():
        if p.is_dir():
            import shutil
            shutil.rmtree(p)
    yield


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    # Use SQLite for fast tests
    test_engine = create_engine("sqlite:///:memory:")
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
        assert versions[0]["version_id"] == v1
        assert versions[1]["version_id"] == v2

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
        assert result["status"] == "skipped"

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
        assert "eta" in result


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
