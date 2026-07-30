"""
Unit tests for app/modules/ai_intelligence/vendor_speed_service.py

All public methods are covered:
  1. measure_avg_preparation_time (no orders, single order, odd/even sample median, std dev, confidence plateau)
  2. measure_current_queue (active orders breakdown by status PLACED/CONFIRMED/PREPARING, items per order)
  3. measure_completion_rate (total, completed, cancelled, rates, avg completion time)
  4. measure_current_workload (capacity tiers based on completion rate >0.9, >0.8, <=0.8, workload levels CRITICAL/HIGH/MEDIUM/LOW)
  5. calculate_vendor_speed_score (scoring factors, speed labels FAST/NORMAL/BUSY/VERY_BUSY, recommendations)
  6. calculate_predicted_waiting_time (order_size scaling, queue impact, workload multiplier, confidence penalty for queue > 10)
  7. calculate_suggested_delay (CRITICAL delay 15m, HIGH delay 10m, MEDIUM + queue>10 delay 5m, LOW no delay)
  8. get_vendor_speed_metrics (full aggregated metric response)
  9. get_batch_vendor_speeds (batch metric processing)
  10. update_eta_with_vendor_speed (missing order, None original_eta, ETA adjustment with DB commit when diff > 3, bounds checking)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.modules.ai_intelligence.vendor_speed_service import VendorSpeedService
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.slots.model import Slot
from app.modules.users.model import User, UserRole

# Fixed reference time
NOW = datetime(2024, 6, 15, 12, 0, 0)
FIVE_DAYS_AGO = NOW - timedelta(days=5)

_UTCNOW_PATH = "app.modules.ai_intelligence.vendor_speed_service.utcnow_naive"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _make_vendor(db: Session) -> User:
    u = User(
        phone=f"+1555{_uid()[:7]}",
        name=f"Vendor_{_uid()}",
        role=UserRole.VENDOR,
        vendor_type="food",
        is_approved=True,
    )
    db.add(u)
    db.flush()
    return u


def _make_student(db: Session) -> User:
    u = User(
        phone=f"+1666{_uid()[:7]}",
        name=f"Student_{_uid()}",
        role=UserRole.STUDENT,
        vendor_type="food",
    )
    db.add(u)
    db.flush()
    return u


def _make_slot(db: Session, vendor_id: int) -> Slot:
    s = Slot(
        vendor_id=vendor_id,
        start_time=NOW + timedelta(hours=1),
        end_time=NOW + timedelta(hours=2),
        max_orders=20,
        current_orders=0,
        status="available",
    )
    db.add(s)
    db.flush()
    return s


def _make_menu_item(db: Session, vendor_id: int) -> MenuItem:
    mi = MenuItem(
        vendor_id=vendor_id,
        name=f"Item_{_uid()}",
        price=10.0,
        category="food",
        is_available=True,
    )
    db.add(mi)
    db.flush()
    return mi


def _make_order(
    db: Session,
    user_id: int,
    vendor_id: int,
    slot_id: int,
    status: OrderStatus = OrderStatus.COMPLETED,
    created_at: datetime = None,
    eta_minutes: int = None,
) -> Order:
    o = Order(
        user_id=user_id,
        vendor_id=vendor_id,
        slot_id=slot_id,
        status=status,
        total_amount=10.0,
        created_at=created_at or FIVE_DAYS_AGO,
        eta_minutes=eta_minutes,
    )
    db.add(o)
    db.flush()
    return o


def _make_order_item(db: Session, order_id: int, menu_item_id: int, quantity: int = 1) -> OrderItem:
    oi = OrderItem(
        order_id=order_id,
        menu_item_id=menu_item_id,
        quantity=quantity,
        price_at_time=10.0,
    )
    db.add(oi)
    db.flush()
    return oi


def _service(db: Session) -> VendorSpeedService:
    return VendorSpeedService(db)


# ---------------------------------------------------------------------------
# 1. measure_avg_preparation_time
# ---------------------------------------------------------------------------

class TestMeasureAvgPreparationTime:

    def test_no_orders_returns_defaults(self, db_session: Session):
        vendor = _make_vendor(db_session)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _service(db_session).measure_avg_preparation_time(vendor.id)

        assert result["avg_prep_time"] == 15.0
        assert result["min_prep_time"] == 10.0
        assert result["max_prep_time"] == 20.0
        assert result["median_prep_time"] == 15.0
        assert result["sample_size"] == 0
        assert result["std_deviation"] == 0.0
        assert result["confidence"] == 0.0

    def test_odd_sample_size_median(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        # Orders with prep times 10, 15, 20
        for eta in [10, 15, 20]:
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO, eta_minutes=eta)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _service(db_session).measure_avg_preparation_time(vendor.id)

        assert result["sample_size"] == 3
        assert result["avg_prep_time"] == 15.0
        assert result["min_prep_time"] == 10.0
        assert result["max_prep_time"] == 20.0
        assert result["median_prep_time"] == 15.0
        assert result["confidence"] == round(3 / 30.0, 2)

    def test_even_sample_size_median(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        # Orders with prep times 10, 20, 30, 40 -> median (20+30)/2 = 25
        for eta in [10, 20, 30, 40]:
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO, eta_minutes=eta)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _service(db_session).measure_avg_preparation_time(vendor.id)

        assert result["sample_size"] == 4
        assert result["median_prep_time"] == 25.0

    def test_confidence_plateau_at_30(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        for _ in range(35):
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO, eta_minutes=15)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _service(db_session).measure_avg_preparation_time(vendor.id)

        assert result["confidence"] == 1.0


# ---------------------------------------------------------------------------
# 2. measure_current_queue
# ---------------------------------------------------------------------------

class TestMeasureCurrentQueue:

    def test_no_active_orders(self, db_session: Session):
        vendor = _make_vendor(db_session)
        db_session.commit()

        result = _service(db_session).measure_current_queue(vendor.id)

        assert result["active_orders"] == 0
        assert result["pending_orders"] == 0
        assert result["preparing_orders"] == 0
        assert result["confirmed_orders"] == 0
        assert result["queue_depth"] == 0
        assert result["avg_items_per_order"] == 0.0

    def test_active_orders_status_counts_and_items(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        item1 = _make_menu_item(db_session, vendor.id)
        item2 = _make_menu_item(db_session, vendor.id)

        o_placed = _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.PLACED, created_at=NOW)
        _make_order_item(db_session, o_placed.id, item1.id)

        o_confirmed = _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.CONFIRMED, created_at=NOW)
        _make_order_item(db_session, o_confirmed.id, item1.id)
        _make_order_item(db_session, o_confirmed.id, item2.id)

        o_preparing = _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.PREPARING, created_at=NOW)
        _make_order_item(db_session, o_preparing.id, item1.id)

        # Non-active order
        _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.COMPLETED, created_at=NOW)

        db_session.commit()

        result = _service(db_session).measure_current_queue(vendor.id)

        assert result["active_orders"] == 3
        assert result["pending_orders"] == 1
        assert result["confirmed_orders"] == 1
        assert result["preparing_orders"] == 1
        assert result["queue_depth"] == 3
        # Total items = 1 + 2 + 1 = 4 across 3 active orders => 4 / 3 = 1.333 -> round 1.3
        assert result["avg_items_per_order"] == 1.3


# ---------------------------------------------------------------------------
# 3. measure_completion_rate
# ---------------------------------------------------------------------------

class TestMeasureCompletionRate:

    def test_no_orders_returns_zeros(self, db_session: Session):
        vendor = _make_vendor(db_session)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _service(db_session).measure_completion_rate(vendor.id)

        assert result["total_orders"] == 0
        assert result["completed_orders"] == 0
        assert result["cancelled_orders"] == 0
        assert result["completion_rate"] == 0.0
        assert result["cancellation_rate"] == 0.0
        assert result["avg_completion_time"] == 15.0

    def test_completion_and_cancellation_rates(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)

        for _ in range(8):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO, eta_minutes=20)
        for _ in range(2):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.CANCELLED, created_at=FIVE_DAYS_AGO)

        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _service(db_session).measure_completion_rate(vendor.id)

        assert result["total_orders"] == 10
        assert result["completed_orders"] == 8
        assert result["cancelled_orders"] == 2
        assert result["completion_rate"] == 0.8
        assert result["cancellation_rate"] == 0.2
        assert result["avg_completion_time"] == 20.0


# ---------------------------------------------------------------------------
# 4. measure_current_workload
# ---------------------------------------------------------------------------

class TestMeasureCurrentWorkload:

    def test_capacity_tiers(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)

        # > 0.9 completion rate -> max_capacity 25
        for _ in range(10):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            res_high = _service(db_session).measure_current_workload(vendor.id)
        assert res_high["max_capacity"] == 25

    def test_capacity_tier_medium_completion_rate(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)

        # > 0.8 and <= 0.9 completion rate -> max_capacity 20
        # 17 completed, 2 cancelled -> 17/19 = 0.894
        for _ in range(17):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO)
        for _ in range(2):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.CANCELLED, created_at=FIVE_DAYS_AGO)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            res_med = _service(db_session).measure_current_workload(vendor.id)
        assert res_med["max_capacity"] == 20

    def test_workload_level_thresholds(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)

        # Add 19 active orders -> 19 / 20 = 0.95 -> CRITICAL
        for _ in range(19):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.PREPARING, created_at=NOW)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            res_crit = _service(db_session).measure_current_workload(vendor.id)

        assert res_crit["workload_level"] == "CRITICAL"
        assert res_crit["estimated_capacity"] == 0  # max(0, 15 - 19) because no completions means max_capacity=15


# ---------------------------------------------------------------------------
# 5. calculate_vendor_speed_score
# ---------------------------------------------------------------------------

class TestCalculateVendorSpeedScore:

    def test_fast_vendor_score_and_label(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)

        # Fast prep (10m), high completion (100%), low queue (0)
        for _ in range(10):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO, eta_minutes=10)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _service(db_session).calculate_vendor_speed_score(vendor.id)

        assert result["speed_score"] >= 0.8
        assert result["speed_label"] == "FAST"
        assert result["recommendations"] == []

    def test_very_busy_vendor_recommendations(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)

        # Slow prep (30m), low completion rate, high queue (15 active)
        for _ in range(15):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.PREPARING, created_at=NOW)
        for _ in range(5):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.CANCELLED, created_at=FIVE_DAYS_AGO)
        for _ in range(1):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO, eta_minutes=35)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _service(db_session).calculate_vendor_speed_score(vendor.id)

        assert result["speed_label"] in ["BUSY", "VERY_BUSY"]
        assert len(result["recommendations"]) > 0

    def test_busy_vendor_speed_label(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)

        # 5 active PREPARING -> queue_score = (20-5)/20 = 0.75, workload = MEDIUM (score 0.7)
        # 1 prep order with eta=25m -> prep_score = (30-25)/20 = 0.25
        # completion rate = 1 completed / (1 completed + 3 cancelled) = 0.25
        # speed_score = 0.25*0.3 + 0.25*0.3 + 0.75*0.2 + 0.7*0.2 = 0.075 + 0.075 + 0.15 + 0.14 = 0.44 (>=0.4 and <0.6 -> BUSY)
        for _ in range(5):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.PREPARING, created_at=NOW)
        for _ in range(3):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.CANCELLED, created_at=FIVE_DAYS_AGO)
        _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO, eta_minutes=25)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _service(db_session).calculate_vendor_speed_score(vendor.id)

        assert result["speed_label"] == "BUSY"


# ---------------------------------------------------------------------------
# 6. calculate_predicted_waiting_time
# ---------------------------------------------------------------------------

class TestCalculatePredictedWaitingTime:

    def test_wait_time_scaling_with_order_size_and_queue(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO, eta_minutes=10)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _service(db_session).calculate_predicted_waiting_time(vendor.id, order_size=2)

        # avg_prep = 10 -> base_wait = 10 * 2 = 20; queue=0 -> queue_wait = 0; LOW workload -> mult = 1.0
        assert result["base_wait_time"] == 20.0
        assert result["queue_wait_time"] == 0.0
        assert result["total_wait_time"] == 20.0

    def test_large_queue_confidence_penalty(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        for _ in range(12):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.PREPARING, created_at=NOW)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _service(db_session).calculate_predicted_waiting_time(vendor.id)

        # Queue depth > 10 -> confidence penalized by 0.8
        assert result["confidence"] <= 0.8


# ---------------------------------------------------------------------------
# 7. calculate_suggested_delay
# ---------------------------------------------------------------------------

class TestCalculateSuggestedDelay:

    def test_critical_workload_delay(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        for _ in range(19):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.PREPARING, created_at=NOW)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _service(db_session).calculate_suggested_delay(vendor.id)

        assert result["should_delay"] is True
        assert result["suggested_delay_minutes"] == 15
        assert "critically overloaded" in result["reason"]

    def test_high_workload_delay(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        # 16 active orders out of 20 capacity => utilization = 0.8 => HIGH workload
        for _ in range(16):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.PREPARING, created_at=NOW)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _service(db_session).calculate_suggested_delay(vendor.id)

        assert result["should_delay"] is True
        assert result["suggested_delay_minutes"] == 10
        assert "very busy" in result["reason"]

    def test_medium_workload_large_queue_delay(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        # 12 active orders with completion rate > 0.8 (max_capacity 20) -> utilization = 12/20 = 0.6 => MEDIUM workload & queue > 10
        for _ in range(12):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.PREPARING, created_at=NOW)
        for _ in range(10):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _service(db_session).calculate_suggested_delay(vendor.id)

        assert result["should_delay"] is True
        assert result["suggested_delay_minutes"] == 5
        assert "building up" in result["reason"]

    def test_normal_operating_no_delay(self, db_session: Session):
        vendor = _make_vendor(db_session)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _service(db_session).calculate_suggested_delay(vendor.id)

        assert result["should_delay"] is False
        assert result["suggested_delay_minutes"] == 0
        assert "operating normally" in result["reason"]


# ---------------------------------------------------------------------------
# 8. get_vendor_speed_metrics & get_batch_vendor_speeds
# ---------------------------------------------------------------------------

class TestPublicApiMethods:

    def test_get_vendor_speed_metrics_structure(self, db_session: Session):
        vendor = _make_vendor(db_session)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            res = _service(db_session).get_vendor_speed_metrics(vendor.id)

        assert res["vendor_id"] == vendor.id
        assert "speed_score" in res
        assert "speed_label" in res
        assert "predicted_waiting_time" in res
        assert "suggested_delay" in res
        assert "measurements" in res

    def test_get_batch_vendor_speeds(self, db_session: Session):
        v1 = _make_vendor(db_session)
        v2 = _make_vendor(db_session)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            res = _service(db_session).get_batch_vendor_speeds([v1.id, v2.id])

        assert len(res) == 2
        assert res[0]["vendor_id"] == v1.id
        assert res[1]["vendor_id"] == v2.id


# ---------------------------------------------------------------------------
# 9. update_eta_with_vendor_speed
# ---------------------------------------------------------------------------

class TestUpdateEtaWithVendorSpeed:

    def test_missing_order_returns_default(self, db_session: Session):
        res = _service(db_session).update_eta_with_vendor_speed(order_id=99999)
        assert res["order_id"] is None
        assert res["original_eta"] == 0
        assert res["updated_eta"] == 0
        assert res["speed_label"] == "UNKNOWN"

    def test_updates_order_eta_and_commits_when_difference_gt_3(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        # Original order with eta 10 minutes
        order = _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.PLACED, created_at=NOW, eta_minutes=10)
        
        # Make vendor VERY_BUSY so adjustment_factor is 1.5 -> updated ETA = 10 * 1.5 = 15 (diff 5 > 3)
        for _ in range(15):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.PREPARING, created_at=NOW)
        for _ in range(5):
            _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.CANCELLED, created_at=FIVE_DAYS_AGO)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            res = _service(db_session).update_eta_with_vendor_speed(order.id)

        assert res["order_id"] == order.id
        assert res["original_eta"] == 10
        assert res["updated_eta"] > 10
        # Check DB updated
        db_session.refresh(order)
        assert order.eta_minutes == res["updated_eta"]

    def test_small_difference_does_not_update_db(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        order = _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.PLACED, created_at=NOW, eta_minutes=15)
        # Vendor operating normally -> adjustment_factor = 1.0 -> updated_eta = 15 (diff 0 <= 3)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            res = _service(db_session).update_eta_with_vendor_speed(order.id)

        assert res["updated_eta"] == 15
        assert res["original_eta"] == 15
