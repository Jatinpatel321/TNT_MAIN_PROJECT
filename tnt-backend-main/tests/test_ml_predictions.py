"""Unit tests for MLPredictionService (app/ml/predictions.py).

Verifies public prediction methods, ML model lazy loading, caching,
heuristic fallbacks, exception handling, bound enforcement, confidence scoring,
risk level classifications, and personalized recommendations.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.ml.predictions import MLPredictionService
from app.modules.feedback.model import VendorReview
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.slots.model import Slot
from app.modules.users.model import User, UserRole


@pytest.fixture(autouse=True)
def reset_service_cache():
    """Ensure MLPredictionService model cache is clean before and after every test."""
    MLPredictionService._models_cache = {}
    yield
    MLPredictionService._models_cache = {}


# ── 1. Lazy Loading and Cache Tests ──────────────────────────────────────────

class TestPredictLazyLoading:
    def test_predict_lazy_load_success(self, db_session: Session):
        service = MLPredictionService(db_session)
        mock_model = MagicMock()
        mock_meta = {"version_id": "v1.0.0"}

        with patch("app.ml.registry.ModelRegistry.load", return_value=(mock_model, mock_meta)) as mock_load:
            result = service.predict("eta_prediction")
            assert result == (mock_model, mock_meta)
            assert mock_load.call_count == 1

            # Second call uses cache
            cached_result = service.predict("eta_prediction")
            assert cached_result == (mock_model, mock_meta)
            assert mock_load.call_count == 1

    def test_predict_lazy_load_none(self, db_session: Session):
        service = MLPredictionService(db_session)

        with patch("app.ml.registry.ModelRegistry.load", return_value=None):
            result = service.predict("nonexistent_model")
            assert result is None
            assert service._models_cache["nonexistent_model"] is None

    def test_predict_lazy_load_exception(self, db_session: Session):
        service = MLPredictionService(db_session)

        with patch("app.ml.registry.ModelRegistry.load", side_effect=RuntimeError("Registry error")):
            result = service.predict("failing_model")
            assert result is None
            assert service._models_cache["failing_model"] is None


# ── 2. ETA Prediction Tests ──────────────────────────────────────────────────

class TestPredictEta:
    def test_predict_eta_slot_not_found(self, db_session: Session):
        service = MLPredictionService(db_session)
        res = service.predict_eta(vendor_id=1, slot_id=99999, item_count=1)

        assert res["method"] == "default"
        assert res["model"] is None
        assert res["predicted_eta_minutes"] == 15
        assert res["confidence_score"] == 0.3
        assert res["delay_risk_level"] == "MEDIUM"
        assert "Slot not found" in res["explanation"]["explanation"]

    def test_predict_eta_ml_success(self, db_session: Session):
        service = MLPredictionService(db_session)
        now = utcnow_naive()
        slot = Slot(vendor_id=1, start_time=now, end_time=now + timedelta(hours=1), current_orders=2, max_orders=10, status="available")
        db_session.add(slot)
        db_session.commit()

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([24.7])
        mock_meta = {"version_id": "eta_v1"}

        with (
            patch.object(service, "predict", return_value=(mock_model, mock_meta)),
            patch("app.ml.predictions.confidence_score", return_value=0.85),
            patch("app.ml.predictions.explain_prediction", return_value={"prediction": 25, "top_contributing_features": []}),
        ):
            res = service.predict_eta(vendor_id=1, slot_id=slot.id, item_count=2)

        assert res["method"] == "ml"
        assert res["model"] == "eta_v1"
        assert res["predicted_eta_minutes"] == 25
        assert res["confidence_score"] == 0.85
        assert res["delay_risk_level"] == "LOW"
        assert "feature_names" in res

    def test_predict_eta_bounds_min_and_max(self, db_session: Session):
        service = MLPredictionService(db_session)
        now = utcnow_naive()
        slot = Slot(vendor_id=1, start_time=now, end_time=now + timedelta(hours=1), current_orders=1, max_orders=10, status="available")
        db_session.add(slot)
        db_session.commit()

        # Test lower bound (pred = 2.0 -> clamped to 5)
        mock_model_low = MagicMock()
        mock_model_low.predict.return_value = np.array([2.0])
        with patch.object(service, "predict", return_value=(mock_model_low, {})):
            res_low = service.predict_eta(vendor_id=1, slot_id=slot.id)
            assert res_low["predicted_eta_minutes"] == 5

        # Test upper bound (pred = 80.0 -> clamped to 60)
        mock_model_high = MagicMock()
        mock_model_high.predict.return_value = np.array([80.0])
        with patch.object(service, "predict", return_value=(mock_model_high, {})):
            res_high = service.predict_eta(vendor_id=1, slot_id=slot.id)
            assert res_high["predicted_eta_minutes"] == 60

    def test_predict_eta_ml_exception_fallback(self, db_session: Session):
        service = MLPredictionService(db_session)
        now = utcnow_naive()
        slot = Slot(vendor_id=1, start_time=now, end_time=now + timedelta(hours=1), current_orders=3, max_orders=10, status="available")
        db_session.add(slot)
        db_session.commit()

        mock_model = MagicMock()
        mock_model.predict.side_effect = RuntimeError("Prediction pipeline crash")

        with patch.object(service, "predict", return_value=(mock_model, {})):
            res = service.predict_eta(vendor_id=1, slot_id=slot.id)

        assert res["method"] == "heuristic"
        assert res["model"] is None
        assert 5 <= res["predicted_eta_minutes"] <= 60
        assert res["confidence_score"] == 0.5

    def test_predict_eta_missing_model_fallback(self, db_session: Session):
        service = MLPredictionService(db_session)
        now = utcnow_naive()
        slot = Slot(vendor_id=1, start_time=now, end_time=now + timedelta(hours=1), current_orders=5, max_orders=10, status="available")
        db_session.add(slot)
        db_session.commit()

        with patch.object(service, "predict", return_value=None):
            res = service.predict_eta(vendor_id=1, slot_id=slot.id)

        assert res["method"] == "heuristic"
        assert res["model"] is None

    def test_risk_level_classifications(self, db_session: Session):
        service = MLPredictionService(db_session)

        # High risk: util > 0.9 and eta > 30
        slot_high = Slot(current_orders=10, max_orders=10)
        assert service._risk_level(35.0, slot_high) == "HIGH"

        # Medium risk: util > 0.7 or eta > 25
        slot_med1 = Slot(current_orders=8, max_orders=10)
        assert service._risk_level(20.0, slot_med1) == "MEDIUM"

        slot_med2 = Slot(current_orders=2, max_orders=10)
        assert service._risk_level(28.0, slot_med2) == "MEDIUM"

        # Low risk
        slot_low = Slot(current_orders=2, max_orders=10)
        assert service._risk_level(15.0, slot_low) == "LOW"


# ── 3. Demand Forecasting Tests ─────────────────────────────────────────────

class TestForecastDemand:
    def test_forecast_demand_vendor_model_ml_success(self, db_session: Session):
        service = MLPredictionService(db_session)
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([4.2])
        mock_meta = {"version_id": "demand_v1", "features": ["hour", "weekday"]}

        def fake_predict(model_type):
            if model_type == "demand_forecast_vendor1":
                return (mock_model, mock_meta)
            return None

        with patch.object(service, "predict", side_effect=fake_predict):
            res = service.forecast_demand(vendor_id=1, days_ahead=2)

        assert res["vendor_id"] == 1
        assert res["method"] == "ml"
        assert len(res["forecasts"]) == 2 * 17  # 2 days * 17 hours (6..22)
        assert res["total_predicted"] > 0
        assert res["forecasts"][0]["predicted_orders"] == 4

    def test_forecast_demand_global_model_ml_success(self, db_session: Session):
        service = MLPredictionService(db_session)
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([3.0])

        def fake_predict(model_type):
            if model_type == "demand_forecast":
                return (mock_model, {})
            return None

        with patch.object(service, "predict", side_effect=fake_predict):
            res = service.forecast_demand(vendor_id=2, days_ahead=1)

        assert res["method"] == "ml"
        assert len(res["forecasts"]) == 17

    def test_forecast_demand_ml_exception_fallback(self, db_session: Session):
        service = MLPredictionService(db_session)
        mock_model = MagicMock()
        mock_model.predict.side_effect = Exception("Model prediction error")

        with patch.object(service, "predict", return_value=(mock_model, {})):
            res = service.forecast_demand(vendor_id=1, days_ahead=1)

        # Hourly predictions raise -> fallback appends 8 peak hour forecasts
        assert len(res["forecasts"]) == 8
        assert res["vendor_id"] == 1

    def test_forecast_demand_missing_model_heuristic(self, db_session: Session):
        service = MLPredictionService(db_session)

        # Add orders to DB for vendor 1 to populate daily_avg
        now = utcnow_naive()
        for i in range(15):
            order = Order(vendor_id=1, user_id=10, slot_id=1, total_amount=50.0, status=OrderStatus.COMPLETED, created_at=now - timedelta(days=i))
            db_session.add(order)
        db_session.commit()

        with patch.object(service, "predict", return_value=None):
            res = service.forecast_demand(vendor_id=1, days_ahead=1)

        assert res["method"] == "heuristic"
        assert len(res["forecasts"]) == 8
        assert res["vendor_id"] == 1


# ── 4. Slot Recommendation Tests ────────────────────────────────────────────

class TestRecommendSlot:
    def test_recommend_slot_filters_blocked_full_and_past(self, db_session: Session):
        service = MLPredictionService(db_session)
        now = utcnow_naive()

        # Slot 1: Valid future available slot
        s1 = Slot(id=101, vendor_id=1, start_time=now + timedelta(hours=2), end_time=now + timedelta(hours=3), current_orders=1, max_orders=10, status="available")
        # Slot 2: Full slot
        s2 = Slot(id=102, vendor_id=1, start_time=now + timedelta(hours=2), end_time=now + timedelta(hours=3), current_orders=10, max_orders=10, status="full")
        # Slot 3: Blocked slot
        s3 = Slot(id=103, vendor_id=1, start_time=now + timedelta(hours=2), end_time=now + timedelta(hours=3), current_orders=0, max_orders=10, status="blocked")
        # Slot 4: Past slot
        s4 = Slot(id=104, vendor_id=1, start_time=now - timedelta(hours=2), end_time=now - timedelta(hours=1), current_orders=1, max_orders=10, status="available")

        db_session.add_all([s1, s2, s3, s4])
        db_session.commit()

        with (
            patch.object(service, "predict", return_value=None),
            patch.object(service, "predict_eta", return_value={"predicted_eta_minutes": 15}),
        ):
            res = service.recommend_slot(user_id=1)

        recommended_ids = [s["slot_id"] for s in res["recommended_slots"]]
        assert 101 in recommended_ids
        assert 102 not in recommended_ids
        assert 103 not in recommended_ids
        assert 104 not in recommended_ids

    def test_recommend_slot_ml_success(self, db_session: Session):
        service = MLPredictionService(db_session)
        now = utcnow_naive()

        s1 = Slot(id=201, vendor_id=1, start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=2), current_orders=2, max_orders=10, status="available")
        s2 = Slot(id=202, vendor_id=1, start_time=now + timedelta(hours=3), end_time=now + timedelta(hours=4), current_orders=7, max_orders=10, status="available")
        db_session.add_all([s1, s2])
        db_session.commit()

        mock_model = MagicMock()
        # Returns score 0.1 for s1, 0.7 for s2
        mock_model.predict.side_effect = [np.array([0.1]), np.array([0.7])]

        with (
            patch.object(service, "predict", return_value=(mock_model, {})),
            patch.object(service, "predict_eta", return_value={"predicted_eta_minutes": 15}),
        ):
            res = service.recommend_slot(user_id=1)

        assert res["method"] == "ml"
        assert len(res["recommended_slots"]) == 2
        # rec_score = 1.0 - score -> s1 rec_score = 0.9, s2 rec_score = 0.3
        assert res["recommended_slots"][0]["slot_id"] == 201
        assert res["recommended_slots"][0]["recommendation_score"] == 0.9
        assert res["fastest"] is not None
        assert res["least_crowded"] is not None

    def test_recommend_slot_ml_exception_fallback(self, db_session: Session):
        service = MLPredictionService(db_session)
        now = utcnow_naive()
        s1 = Slot(id=301, vendor_id=1, start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=2), current_orders=2, max_orders=10, status="available")
        db_session.add(s1)
        db_session.commit()

        mock_model = MagicMock()
        mock_model.predict.side_effect = Exception("Slot model prediction error")

        with (
            patch.object(service, "predict", return_value=(mock_model, {})),
            patch.object(service, "predict_eta", return_value={"predicted_eta_minutes": 15}),
        ):
            res = service.recommend_slot(user_id=1)

        # Uses occupancy fallback score
        assert res["recommended_slots"][0]["occupancy_pct"] == 20
        assert res["recommended_slots"][0]["recommendation_score"] == 0.8  # 1.0 - 0.2

    def test_recommend_slot_congestion_and_reason_branches(self, db_session: Session):
        service = MLPredictionService(db_session)

        assert service._slot_reason("LOW", 0.85) == "Excellent slot choice - low congestion"
        assert service._slot_reason("MEDIUM", 0.65) == "Good option - medium congestion"
        assert service._slot_reason("HIGH", 0.4) == "High congestion expected - consider alternatives"
        assert service._slot_reason("LOW", 0.5) == "Average slot option"

    def test_recommend_slot_medium_occupancy_branch(self, db_session: Session):
        service = MLPredictionService(db_session)
        now = utcnow_naive()
        s = Slot(id=401, vendor_id=1, start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=2), current_orders=4, max_orders=10, status="available")
        db_session.add(s)
        db_session.commit()

        with (
            patch.object(service, "predict", return_value=None),
            patch.object(service, "predict_eta", return_value={"predicted_eta_minutes": 15}),
        ):
            res = service.recommend_slot(user_id=1)

        assert res["recommended_slots"][0]["congestion"] == "MEDIUM"


# ── 5. Personalized Recommendations Tests ────────────────────────────────────

class TestPersonalizedRecommendations:
    def test_personalized_recommendations_cold_start(self, db_session: Session):
        service = MLPredictionService(db_session)
        item1 = MenuItem(id=1, vendor_id=1, name="Special Pizza", price=12.99, is_available=True)
        item2 = MenuItem(id=2, vendor_id=1, name="Cold Drink", price=2.50, is_available=True)
        db_session.add_all([item1, item2])
        db_session.commit()

        empty_matrix_data = {
            "user_ids": [],
            "item_ids": [],
            "user_idx": {},
            "matrix": np.empty((0, 0)),
        }

        with patch("app.ml.predictions.build_user_item_matrix", return_value=empty_matrix_data):
            res = service.get_personalized_recommendations(user_id=999, limit=5)

        assert res["method"] == "cold_start_popularity"
        assert res["collaborative"] == []
        assert len(res["content_based"]) == 2
        assert len(res["hybrid"]) == 2
        assert res["content_based"][0]["reason"] == "Popular on campus"

    def test_personalized_recommendations_unavailable_item_branch(self, db_session: Session):
        service = MLPredictionService(db_session)
        u1 = User(id=1, phone="+15550000001", role=UserRole.STUDENT)
        u2 = User(id=2, phone="+15550000002", role=UserRole.STUDENT)
        v1 = User(id=10, phone="+15550000010", role=UserRole.VENDOR, is_approved=True)
        m1 = MenuItem(id=101, vendor_id=10, name="Unavailable Item", price=8.0, is_available=False)
        db_session.add_all([u1, u2, v1, m1])
        db_session.commit()

        matrix_data = {
            "user_ids": [1, 2],
            "item_ids": [101],
            "user_idx": {1: 0, 2: 1},
            "matrix": np.array([[0.0], [1.0]]),
        }

        with patch("app.ml.predictions.build_user_item_matrix", return_value=matrix_data):
            res = service.get_personalized_recommendations(user_id=1, limit=10)

        assert res["collaborative"] == []


    def test_personalized_recommendations_collaborative_and_content(self, db_session: Session):
        service = MLPredictionService(db_session)

        u1 = User(id=1, phone="+15550000001", role=UserRole.STUDENT, email="u1@test.com")
        u2 = User(id=2, phone="+15550000002", role=UserRole.STUDENT, email="u2@test.com")
        v1 = User(id=10, phone="+15550000010", role=UserRole.VENDOR, email="v1@test.com", is_approved=True)

        m1 = MenuItem(id=101, vendor_id=10, name="Burger", price=8.0, is_available=True)
        m2 = MenuItem(id=102, vendor_id=10, name="Fries", price=3.0, is_available=True)
        m3 = MenuItem(id=103, vendor_id=10, name="Shake", price=4.0, is_available=True)
        db_session.add_all([u1, u2, v1, m1, m2, m3])

        # User 1 ordered Burger from Vendor 10
        o1 = Order(id=1, user_id=1, vendor_id=10, slot_id=1, status=OrderStatus.COMPLETED, created_at=utcnow_naive() - timedelta(days=2))
        db_session.add(o1)
        db_session.commit()

        oi1 = OrderItem(order_id=1, menu_item_id=101, quantity=1, price_at_time=8.0)
        db_session.add(oi1)
        db_session.commit()

        # Matrix: user 1 ordered item 101; user 2 ordered items 101, 102, 103
        matrix_data = {
            "user_ids": [1, 2],
            "item_ids": [101, 102, 103],
            "user_idx": {1: 0, 2: 1},
            "matrix": np.array([
                [1.0, 0.0, 0.0],
                [1.0, 2.0, 3.0],
            ]),
        }

        with patch("app.ml.predictions.build_user_item_matrix", return_value=matrix_data):
            res = service.get_personalized_recommendations(user_id=1, limit=10)

        assert res["method"] == "collaborative_filtering + content_based"
        assert len(res["collaborative"]) > 0
        rec_ids = [r["item_id"] for r in res["collaborative"]]
        assert 102 in rec_ids or 103 in rec_ids
        assert len(res["hybrid"]) > 0


# ── 6. Vendor Ranking Tests ──────────────────────────────────────────────────

class TestRankVendors:
    def test_rank_vendors_ml_success(self, db_session: Session):
        service = MLPredictionService(db_session)

        vendor = User(id=10, phone="+15550000010", role=UserRole.VENDOR, name="Top Vendor", is_approved=True)
        db_session.add(vendor)
        db_session.commit()

        review = VendorReview(vendor_id=10, user_id=1, rating=4.5)
        now = utcnow_naive()
        order1 = Order(vendor_id=10, user_id=1, slot_id=1, status=OrderStatus.COMPLETED, created_at=now - timedelta(days=5))
        order2 = Order(vendor_id=10, user_id=1, slot_id=1, status=OrderStatus.CANCELLED, created_at=now - timedelta(days=2))
        db_session.add_all([review, order1, order2])
        db_session.commit()

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.88])

        with patch.object(service, "predict", return_value=(mock_model, {})):
            rankings = service.rank_vendors()

        assert len(rankings) == 1
        assert rankings[0]["vendor_id"] == 10
        assert rankings[0]["vendor_name"] == "Top Vendor"
        assert rankings[0]["rank_score"] == 88.0
        assert rankings[0]["method"] == "ml"

    def test_rank_vendors_ml_exception_fallback(self, db_session: Session):
        service = MLPredictionService(db_session)

        vendor = User(id=11, phone="+15550000011", role=UserRole.VENDOR, name="Fallback Vendor", is_approved=True)
        db_session.add(vendor)
        db_session.commit()

        mock_model = MagicMock()
        mock_model.predict.side_effect = RuntimeError("Vendor ranking prediction failed")

        with patch.object(service, "predict", return_value=(mock_model, {})):
            rankings = service.rank_vendors()

        assert len(rankings) == 1
        assert rankings[0]["method"] == "heuristic"

    def test_rank_vendors_missing_model_heuristic(self, db_session: Session):
        service = MLPredictionService(db_session)

        vendor = User(id=12, phone="+15550000012", role=UserRole.VENDOR, name="Heuristic Vendor", is_approved=True)
        db_session.add(vendor)
        db_session.commit()

        with patch.object(service, "predict", return_value=None):
            rankings = service.rank_vendors()

        assert len(rankings) == 1
        assert rankings[0]["method"] == "heuristic"


# ── 7. Fraud Detection Tests ─────────────────────────────────────────────────

class TestDetectFraud:
    def test_detect_fraud_user_not_found(self, db_session: Session):
        service = MLPredictionService(db_session)
        res = service.detect_fraud(user_id=99999, order_id=1)

        assert res["is_fraud"] is False
        assert res["reason"] == "User not found"
        assert res["score"] == 0.0

    def test_detect_fraud_ml_predict_proba_success(self, db_session: Session):
        service = MLPredictionService(db_session)
        user = User(id=1, phone="+15550000001", role=UserRole.STUDENT, device_token="token123")
        db_session.add(user)
        db_session.commit()

        mock_model = MagicMock()
        mock_model.predict_proba.return_value = np.array([[0.25, 0.75]])
        mock_meta = {"version_id": "fraud_v1"}

        with patch.object(service, "predict", return_value=(mock_model, mock_meta)):
            res = service.detect_fraud(user_id=1, order_id=1)

        assert res["is_fraud"] is True
        assert res["fraud_probability"] == 0.75
        assert res["score"] == 0.75
        assert res["risk_level"] == "HIGH"
        assert res["method"] == "ml"
        assert res["model"] == "fraud_v1"

    def test_detect_fraud_ml_predict_fallback(self, db_session: Session):
        service = MLPredictionService(db_session)
        user = User(id=2, phone="+15550000002", role=UserRole.STUDENT)
        db_session.add(user)
        db_session.commit()

        mock_model = MagicMock()
        mock_model.predict_proba.side_effect = AttributeError("predict_proba not implemented")
        mock_model.predict.return_value = np.array([0.4])

        with patch.object(service, "predict", return_value=(mock_model, {})):
            res = service.detect_fraud(user_id=2, order_id=1)

        assert res["is_fraud"] is False
        assert res["fraud_probability"] == 0.4
        assert res["risk_level"] == "MEDIUM"
        assert res["method"] == "ml"

    def test_detect_fraud_ml_all_exceptions_fallback(self, db_session: Session):
        service = MLPredictionService(db_session)
        user = User(id=3, phone="+15550000003", role=UserRole.STUDENT)
        db_session.add(user)
        db_session.commit()

        mock_model = MagicMock()
        mock_model.predict_proba.side_effect = RuntimeError("proba error")
        mock_model.predict.side_effect = RuntimeError("predict error")

        with patch.object(service, "predict", return_value=(mock_model, {})):
            res = service.detect_fraud(user_id=3, order_id=1)

        assert res["is_fraud"] is False
        assert res["fraud_probability"] == 0.0
        assert res["risk_level"] == "LOW"

    def test_detect_fraud_heuristic_order_not_found(self, db_session: Session):
        service = MLPredictionService(db_session)
        user = User(id=4, phone="+15550000004", role=UserRole.STUDENT)
        db_session.add(user)
        db_session.commit()

        with patch.object(service, "predict", return_value=None):
            res = service.detect_fraud(user_id=4, order_id=99999)

        assert res["is_fraud"] is False
        assert res["reason"] == "Order not found"
        assert res["score"] == 0.0

    def test_detect_fraud_heuristic_red_flags(self, db_session: Session):
        service = MLPredictionService(db_session)
        now = utcnow_naive()
        user = User(id=5, phone="+15550000005", role=UserRole.STUDENT)
        vendor = User(id=10, phone="+15550000010", role=UserRole.VENDOR)
        db_session.add_all([user, vendor])
        db_session.commit()

        # Add 6 cancelled orders out of 8 total orders to trigger red flags
        for i in range(6):
            o_cancelled = Order(user_id=5, vendor_id=10, slot_id=1, status=OrderStatus.CANCELLED, created_at=now - timedelta(days=i + 1), total_amount=10.0)
            db_session.add(o_cancelled)

        for i in range(2):
            o_ok = Order(user_id=5, vendor_id=10, slot_id=1, status=OrderStatus.COMPLETED, created_at=now - timedelta(days=i + 1), total_amount=10.0)
            db_session.add(o_ok)

        # Flagged order
        target_order = Order(user_id=5, vendor_id=10, slot_id=1, status=OrderStatus.PENDING, fraud_flag=True, created_at=now)
        db_session.add(target_order)
        db_session.commit()

        with patch.object(service, "predict", return_value=None):
            res = service.detect_fraud(user_id=5, order_id=target_order.id)

        assert res["method"] == "heuristic"
        assert res["is_fraud"] is True
        assert res["risk_level"] == "HIGH"
        assert res["score"] > 0.5


# ── 8. Model Registry Summary Test ───────────────────────────────────────────

class TestModelRegistrySummary:
    def test_get_model_registry_summary(self, db_session: Session):
        service = MLPredictionService(db_session)
        expected_summary = {"models": [{"type": "eta_prediction", "active_version": "v1"}]}

        with patch("app.ml.registry.ModelRegistry.get_registry_summary", return_value=expected_summary):
            summary = service.get_model_registry_summary()

        assert summary == expected_summary
