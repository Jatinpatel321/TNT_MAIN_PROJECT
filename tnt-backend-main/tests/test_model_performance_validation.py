"""
Tests for Model Performance Validation:
1. backtest_eta:
   - insufficient data (< 20 orders)
   - sufficient data (>= 20 orders)
   - within_3_min_pct
   - within_5_min_pct
   - mae_minutes
2. backtest_vendor_ranking:
   - insufficient data (< 20 orders)
   - sufficient data (>= 20 orders)
   - top_1_hit_rate
   - top_3_hit_rate
3. train_fraud_detection training output:
   - accuracy
   - precision
   - recall
   - f1
   - cv_f1
4. Metrics sample size threshold validation (insufficient data safety gate).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.ml.backtest import backtest_eta, backtest_vendor_ranking
from app.ml.training_pipeline import train_fraud_detection
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.slots.model import Slot
from app.modules.users.model import User, UserRole

NOW = datetime(2024, 6, 15, 12, 0, 0)


def _uid() -> str:
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Test Fixtures & Data Generators
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_vendor_and_user(db_session: Session):
    vendor = User(
        phone=f"+1555{_uid()[:7]}",
        name="Backtest Test Vendor",
        role=UserRole.VENDOR,
        vendor_type="food",
        is_approved=True,
    )
    student = User(
        phone=f"+1666{_uid()[:7]}",
        name="Backtest Test Student",
        role=UserRole.STUDENT,
        vendor_type="food",
    )
    db_session.add_all([vendor, student])
    db_session.flush()

    slot = Slot(
        vendor_id=vendor.id,
        start_time=NOW + timedelta(hours=1),
        end_time=NOW + timedelta(hours=2),
        max_orders=50,
        current_orders=20,
        status="available",
    )
    db_session.add(slot)
    db_session.flush()

    menu_item = MenuItem(
        vendor_id=vendor.id,
        name="Burger",
        price=10.0,
        is_available=True,
    )
    db_session.add(menu_item)
    db_session.commit()

    return {
        "vendor": vendor,
        "student": student,
        "slot": slot,
        "menu_item": menu_item,
    }


def _seed_completed_orders(db_session: Session, context: dict, count: int):
    """Seed `count` completed orders with known completion times for backtesting."""
    vendor = context["vendor"]
    student = context["student"]
    slot = context["slot"]
    menu_item = context["menu_item"]

    orders = []
    for i in range(count):
        created_at = NOW - timedelta(days=(i % 25) + 1)
        order = Order(
            user_id=student.id,
            vendor_id=vendor.id,
            slot_id=slot.id,
            status=OrderStatus.COMPLETED,
            total_amount=10.0,
            actual_completion_minutes=15.0,  # Exactly 15 mins actual time
            pickup_confirmed_at=created_at + timedelta(minutes=15),
            created_at=created_at,
        )
        db_session.add(order)
        db_session.flush()

        item = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            quantity=1,
            price_at_time=10.0,
        )
        db_session.add(item)
        orders.append(order)

    db_session.commit()
    return orders


# ===========================================================================
# 1. Tests for backtest_eta
# ===========================================================================

class TestBacktestETA:

    def test_backtest_eta_insufficient_data(self, db_session: Session, seeded_vendor_and_user: dict):
        """Should return status='insufficient_data' when < 20 qualifying orders exist."""
        # Seed 10 orders (< 20 threshold)
        _seed_completed_orders(db_session, seeded_vendor_and_user, 10)

        with patch("app.ml.backtest.utcnow_naive", return_value=NOW):
            res = backtest_eta(db_session, days=30)

        assert res["status"] == "insufficient_data"
        assert res["total_orders"] == 10
        assert res["days"] == 30
        assert "Fewer than 20 qualifying orders" in res["reason"]

    def test_backtest_eta_sufficient_data_and_metric_fields(
        self, db_session: Session, seeded_vendor_and_user: dict
    ):
        """Should calculate within_3_min_pct, within_5_min_pct, and mae_minutes when >= 20 orders exist."""
        # Seed 25 completed orders (>= 20 threshold)
        _seed_completed_orders(db_session, seeded_vendor_and_user, 25)

        # Mock MLPredictionService.predict_eta to return predicted_eta_minutes=15 (0 error)
        with patch("app.ml.backtest.utcnow_naive", return_value=NOW), \
             patch("app.ml.predictions.MLPredictionService.predict_eta", return_value={"predicted_eta_minutes": 15}):

            res = backtest_eta(db_session, days=30)

        assert res["status"] == "success"
        assert res["days"] == 30
        assert res["total_orders"] == 25
        assert "within_3_min_pct" in res
        assert "within_5_min_pct" in res
        assert "mae_minutes" in res

        # Since actual is 15.0 and predicted is 15.0, error is 0.0 -> 100% within 3/5 min and MAE = 0.0
        assert res["within_3_min_pct"] == 100.0
        assert res["within_5_min_pct"] == 100.0
        assert res["mae_minutes"] == 0.0

    def test_backtest_eta_error_margin_metrics(
        self, db_session: Session, seeded_vendor_and_user: dict
    ):
        """Validates accurate calculation of within_3_min_pct, within_5_min_pct, and mae_minutes under varied prediction errors."""
        _seed_completed_orders(db_session, seeded_vendor_and_user, 20)

        # Mock predictions with varying errors:
        # 10 orders with error 2 min (<=3)
        # 5 orders with error 4 min (<=5)
        # 5 orders with error 8 min (>5)
        call_count = 0

        def mock_predict_eta(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 10:
                return {"predicted_eta_minutes": 17.0}  # error = 2 min
            elif call_count <= 15:
                return {"predicted_eta_minutes": 19.0}  # error = 4 min
            else:
                return {"predicted_eta_minutes": 23.0}  # error = 8 min

        with patch("app.ml.backtest.utcnow_naive", return_value=NOW), \
             patch("app.ml.predictions.MLPredictionService.predict_eta", side_effect=mock_predict_eta):

            res = backtest_eta(db_session, days=30)

        assert res["status"] == "success"
        assert res["total_orders"] == 20
        # 10/20 = 50% within 3 min
        assert res["within_3_min_pct"] == 50.0
        # 15/20 = 75% within 5 min
        assert res["within_5_min_pct"] == 75.0
        # MAE = (10*2 + 5*4 + 5*8) / 20 = (20 + 20 + 40) / 20 = 80 / 20 = 4.0 min
        assert res["mae_minutes"] == 4.0


# ===========================================================================
# 2. Tests for backtest_vendor_ranking
# ===========================================================================

class TestBacktestVendorRanking:

    def test_backtest_vendor_ranking_insufficient_data(
        self, db_session: Session, seeded_vendor_and_user: dict
    ):
        """Should return status='insufficient_data' when < 20 qualifying orders exist."""
        _seed_completed_orders(db_session, seeded_vendor_and_user, 5)

        with patch("app.ml.backtest.utcnow_naive", return_value=NOW):
            res = backtest_vendor_ranking(db_session, days=30)

        assert res["status"] == "insufficient_data"
        assert res["total_orders"] == 5
        assert res["days"] == 30
        assert "Fewer than 20 qualifying orders" in res["reason"]

    def test_backtest_vendor_ranking_sufficient_data_and_hit_rates(
        self, db_session: Session, seeded_vendor_and_user: dict
    ):
        """Should calculate top_1_hit_rate and top_3_hit_rate when >= 20 orders exist."""
        orders = _seed_completed_orders(db_session, seeded_vendor_and_user, 20)
        vendor_id = seeded_vendor_and_user["vendor"].id

        # Mock rank_vendors to rank the chosen vendor as #1
        mock_rankings = [{"vendor_id": vendor_id, "rank": 1}]

        with patch("app.ml.backtest.utcnow_naive", return_value=NOW), \
             patch("app.ml.predictions.MLPredictionService.rank_vendors", return_value=mock_rankings):

            res = backtest_vendor_ranking(db_session, days=30)

        assert res["status"] == "success"
        assert res["total_orders"] == 20
        assert "top_1_hit_rate" in res
        assert "top_3_hit_rate" in res
        assert "caveat" in res

        # Chosen vendor was ranked #1 for all 20 orders -> top_1 = 1.0, top_3 = 1.0
        assert res["top_1_hit_rate"] == 1.0
        assert res["top_3_hit_rate"] == 1.0


# ===========================================================================
# 3. Tests for train_fraud_detection Output Metrics
# ===========================================================================

class TestFraudTrainingOutputMetrics:

    def test_fraud_training_output_includes_all_classification_metrics(
        self, db_session: Session
    ):
        """Verify train_fraud_detection output dictionary contains accuracy, precision, recall, f1, and cv_f1."""
        # Create dummy feature vector and labels
        dummy_X = [[1.0, 2.0, 0.0, 1.0], [0.0, 1.0, 1.0, 0.0], [2.0, 3.0, 0.0, 1.0], [0.0, 0.0, 0.0, 0.0]]
        dummy_y = [1.0, 0.0, 1.0, 0.0]
        feature_cols = ["f1", "f2", "f3", "f4"]

        with patch("app.ml.features.extract_fraud_features", return_value=(dummy_X, dummy_y, feature_cols)), \
             patch("app.ml.registry.ModelRegistry.save", return_value="v1.0.test"):

            res = train_fraud_detection(db_session)

        assert res["status"] == "success"
        assert res["model_type"] == "fraud_detection"
        assert "version_id" in res
        assert "accuracy" in res
        assert "precision" in res
        assert "recall" in res
        assert "f1" in res
        assert "cv_f1" in res
        assert isinstance(res["accuracy"], float)
        assert isinstance(res["precision"], float)
        assert isinstance(res["recall"], float)
        assert isinstance(res["f1"], float)
        assert isinstance(res["cv_f1"], float)

    def test_fraud_training_persists_complete_metrics_to_registry(
        self, db_session: Session
    ):
        """Verify ModelRegistry.save is called with accuracy, precision, recall, f1, and cv_f1."""
        dummy_X = [[1.0, 2.0], [0.0, 1.0], [2.0, 3.0], [0.0, 0.0]]
        dummy_y = [1.0, 0.0, 1.0, 0.0]
        feature_cols = ["f1", "f2"]

        with patch("app.ml.features.extract_fraud_features", return_value=(dummy_X, dummy_y, feature_cols)), \
             patch("app.ml.registry.ModelRegistry.save") as mock_save:

            mock_save.return_value = "v1.0.saved"
            res = train_fraud_detection(db_session)

        mock_save.assert_called_once()
        save_kwargs = mock_save.call_args[1]
        metrics = save_kwargs["metrics"]

        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics
        assert "cv_f1" in metrics
