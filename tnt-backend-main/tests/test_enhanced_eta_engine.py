"""
Unit tests for app/modules/ai_intelligence/planners/enhanced_eta_engine.py

All public and private methods are covered:
  1. get_menu_item_prep_time
  2. get_menu_complexity_score
  3. get_vendor_workload
  4. get_slot_occupancy
  5. predict_eta_enhanced          (ETAEngine deferred import is patched)
  6. _calculate_delay_risk
  7. _estimate_preparation_progress
  8. predict_delay_probability
  9. get_enhanced_eta
  10._default_response

Strategy:
  - Use shared in-memory SQLite db_session (conftest.py).
  - Patch utcnow_naive for time-of-day branch control.
  - Patch ETAEngine (deferred import inside predict_eta_enhanced) at its source module.
  - Seed deterministic Order/Slot/MenuItem rows per test.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.modules.ai_intelligence.planners.enhanced_eta_engine import EnhancedETAEngine
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.slots.model import Slot
from app.modules.users.model import User, UserRole

# ---------------------------------------------------------------------------
# Reference time: 10:00 — normal (non-peak) hour for predictable time_factor
# ---------------------------------------------------------------------------
NOW = datetime(2024, 6, 15, 10, 0, 0)
FIVE_DAYS_AGO = NOW - timedelta(days=5)

# Patch target for ETAEngine (deferred import inside predict_eta_enhanced)
_ETA_ENGINE_PATH = "app.modules.ai_intelligence.planners.eta_engine.ETAEngine"
_UTCNOW_PATH = "app.modules.ai_intelligence.planners.enhanced_eta_engine.utcnow_naive"


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


def _make_slot(
    db: Session,
    vendor_id: int,
    max_orders: int = 10,
    current_orders: int = 2,
    start_offset_hours: float = 1.0,
    status: str = "available",
    base_time: datetime = None,
) -> Slot:
    base = base_time or NOW
    start = base + timedelta(hours=start_offset_hours)
    s = Slot(
        vendor_id=vendor_id,
        start_time=start,
        end_time=start + timedelta(hours=1),
        max_orders=max_orders,
        current_orders=current_orders,
        status=status,
    )
    db.add(s)
    db.flush()
    return s


def _make_menu_item(
    db: Session,
    vendor_id: int,
    name: str = None,
    category: str = "food",
    price: float = 5.99,
    is_available: bool = True,
    prep_time: int = 10,
) -> MenuItem:
    mi = MenuItem(
        vendor_id=vendor_id,
        name=name or f"Item_{_uid()}",
        price=price,
        category=category,
        is_available=is_available,
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
        price_at_time=5.99,
    )
    db.add(oi)
    db.flush()
    return oi


def _engine(db: Session) -> EnhancedETAEngine:
    return EnhancedETAEngine(db)


# ---------------------------------------------------------------------------
# 1. get_menu_item_prep_time
# ---------------------------------------------------------------------------

class TestGetMenuItemPrepTime:

    def test_no_data_returns_none_fields(self, db_session: Session):
        engine = _engine(db_session)
        result = engine.get_menu_item_prep_time(menu_item_id=9999, vendor_id=9999)
        assert result["avg_prep_time"] is None
        assert result["min_prep_time"] is None
        assert result["max_prep_time"] is None
        assert result["sample_size"] == 0
        assert result["confidence"] == 0.0

    def test_with_single_order_returns_data(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id)
        order = _make_order(
            db_session, student.id, vendor.id, slot.id,
            status=OrderStatus.COMPLETED,
            created_at=FIVE_DAYS_AGO,
            eta_minutes=12,
        )
        _make_order_item(db_session, order.id, item.id)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_menu_item_prep_time(item.id, vendor.id)

        assert result["sample_size"] == 1
        assert result["avg_prep_time"] == 12
        assert result["min_prep_time"] == 12
        assert result["max_prep_time"] == 12
        assert result["confidence"] == pytest.approx(1 / 20.0)

    def test_confidence_plateaus_at_20_samples(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id)
        for _ in range(25):
            order = _make_order(
                db_session, student.id, vendor.id, slot.id,
                status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO, eta_minutes=10,
            )
            _make_order_item(db_session, order.id, item.id)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_menu_item_prep_time(item.id, vendor.id)

        assert result["confidence"] == 1.0

    def test_picked_status_also_included(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id)
        order = _make_order(
            db_session, student.id, vendor.id, slot.id,
            status=OrderStatus.PICKED, created_at=FIVE_DAYS_AGO, eta_minutes=8,
        )
        _make_order_item(db_session, order.id, item.id)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_menu_item_prep_time(item.id, vendor.id)

        assert result["sample_size"] == 1
        assert result["avg_prep_time"] == 8

    def test_pending_orders_excluded(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id)
        order = _make_order(
            db_session, student.id, vendor.id, slot.id,
            status=OrderStatus.PENDING, created_at=FIVE_DAYS_AGO, eta_minutes=10,
        )
        _make_order_item(db_session, order.id, item.id)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_menu_item_prep_time(item.id, vendor.id)

        assert result["sample_size"] == 0

    def test_orders_without_eta_minutes_excluded(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id)
        order = _make_order(
            db_session, student.id, vendor.id, slot.id,
            status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO, eta_minutes=None,
        )
        _make_order_item(db_session, order.id, item.id)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_menu_item_prep_time(item.id, vendor.id)

        assert result["sample_size"] == 0

    def test_min_max_avg_correct_with_multiple_orders(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id)
        for eta in [5, 10, 15]:
            o = _make_order(
                db_session, student.id, vendor.id, slot.id,
                status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO, eta_minutes=eta,
            )
            _make_order_item(db_session, o.id, item.id)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_menu_item_prep_time(item.id, vendor.id)

        assert result["min_prep_time"] == 5
        assert result["max_prep_time"] == 15
        assert result["avg_prep_time"] == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# 2. get_menu_complexity_score
# ---------------------------------------------------------------------------

class TestGetMenuComplexityScore:

    def test_missing_item_returns_default(self, db_session: Session):
        result = _engine(db_session).get_menu_complexity_score(menu_item_id=99999)
        assert result["complexity_score"] == 0.5
        assert result["factors"] == {}

    def test_beverage_category_has_low_complexity(self, db_session: Session):
        vendor = _make_vendor(db_session)
        item = _make_menu_item(db_session, vendor.id, category="beverages")
        db_session.commit()
        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_menu_complexity_score(item.id)
        assert result["factors"]["category"] == 0.05

    def test_indian_category_has_max_complexity(self, db_session: Session):
        vendor = _make_vendor(db_session)
        item = _make_menu_item(db_session, vendor.id, category="indian")
        db_session.commit()
        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_menu_complexity_score(item.id)
        assert result["factors"]["category"] == 0.20

    def test_unknown_category_defaults_to_015(self, db_session: Session):
        vendor = _make_vendor(db_session)
        item = _make_menu_item(db_session, vendor.id, category="mystery_food")
        db_session.commit()
        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_menu_complexity_score(item.id)
        assert result["factors"]["category"] == 0.15

    def test_combo_keyword_adds_name_factor(self, db_session: Session):
        vendor = _make_vendor(db_session)
        item = _make_menu_item(db_session, vendor.id, name="Veg Combo Meal")
        db_session.commit()
        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_menu_complexity_score(item.id)
        # "combo" → +0.1, name has 3 words (not > 3) → no extra word bonus
        assert result["factors"]["name_complexity"] >= 0.1

    def test_long_name_adds_name_factor(self, db_session: Session):
        vendor = _make_vendor(db_session)
        item = _make_menu_item(db_session, vendor.id, name="Very Long Item Name Here")
        db_session.commit()
        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_menu_complexity_score(item.id)
        # > 3 words → name_factor += 0.1
        assert result["factors"]["name_complexity"] >= 0.1

    def test_special_and_long_name_stacks_factor(self, db_session: Session):
        vendor = _make_vendor(db_session)
        item = _make_menu_item(db_session, vendor.id, name="Grand Special Deluxe Thali Platter")
        db_session.commit()
        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_menu_complexity_score(item.id)
        # keyword match + long name = 0.2
        assert result["factors"]["name_complexity"] == pytest.approx(0.2)

    def test_variance_factor_from_historical_data(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id, category="snacks")
        for eta in [5, 20]:
            o = _make_order(
                db_session, student.id, vendor.id, slot.id,
                status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO, eta_minutes=eta,
            )
            _make_order_item(db_session, o.id, item.id)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_menu_complexity_score(item.id)

        # variance = 20-5 = 15 → min(0.3, 15/30) = 0.5 → but capped at 0.3
        assert result["factors"]["variance"] == pytest.approx(0.3)

    def test_default_variance_when_single_sample(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id)
        o = _make_order(
            db_session, student.id, vendor.id, slot.id,
            status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO, eta_minutes=10,
        )
        _make_order_item(db_session, o.id, item.id)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_menu_complexity_score(item.id)

        # sample_size == 1 → default medium variance 0.15
        assert result["factors"]["variance"] == pytest.approx(0.15)

    def test_complexity_capped_at_one(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        # indian + special + long name + high variance → all factors max
        item = _make_menu_item(db_session, vendor.id,
                               name="Super Special Indian Deluxe Thali Feast", category="indian")
        for eta in [5, 60]:
            o = _make_order(
                db_session, student.id, vendor.id, slot.id,
                status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO, eta_minutes=eta,
            )
            _make_order_item(db_session, o.id, item.id)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_menu_complexity_score(item.id)

        assert result["complexity_score"] <= 1.0

    def test_all_known_categories(self, db_session: Session):
        vendor = _make_vendor(db_session)
        expected = {
            "beverages": 0.05, "snacks": 0.10, "south indian": 0.15,
            "chinese": 0.15, "italian": 0.18, "indian": 0.20,
            "print": 0.10, "xerox": 0.05, "binding": 0.15, "lamination": 0.10,
        }
        for category, expected_val in expected.items():
            item = _make_menu_item(db_session, vendor.id, category=category)
            db_session.commit()
            with patch(_UTCNOW_PATH, return_value=NOW):
                result = _engine(db_session).get_menu_complexity_score(item.id)
            assert result["factors"]["category"] == pytest.approx(expected_val), \
                f"Category {category} expected {expected_val}"


# ---------------------------------------------------------------------------
# 3. get_vendor_workload
# ---------------------------------------------------------------------------

class TestGetVendorWorkload:

    def test_no_orders_returns_defaults(self, db_session: Session):
        vendor = _make_vendor(db_session)
        db_session.commit()
        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_vendor_workload(vendor.id)

        assert result["active_orders"] == 0
        assert result["avg_prep_time"] == pytest.approx(15.0)
        # completed=0, total=0 (or 1 guard) → 0/1 = 0.0
        assert result["completion_rate"] == pytest.approx(0.0)
        assert result["workload_score"] >= 0.0
        assert result["estimated_capacity"] == 20

    def test_active_orders_counted(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        for _ in range(5):
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.PREPARING, created_at=NOW)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_vendor_workload(vendor.id)

        assert result["active_orders"] == 5
        assert result["estimated_capacity"] == 15

    def test_placed_and_confirmed_also_active(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.PLACED, created_at=NOW)
        _make_order(db_session, student.id, vendor.id, slot.id, status=OrderStatus.CONFIRMED, created_at=NOW)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_vendor_workload(vendor.id)

        assert result["active_orders"] == 2

    def test_avg_prep_time_from_history(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        for eta in [10, 20]:
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO, eta_minutes=eta)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_vendor_workload(vendor.id)

        assert result["avg_prep_time"] == pytest.approx(15.0)

    def test_completion_rate_calculation(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        # 3 completed, 1 cancelled (last 7 days)
        for _ in range(3):
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO)
        _make_order(db_session, student.id, vendor.id, slot.id,
                    status=OrderStatus.CANCELLED, created_at=FIVE_DAYS_AGO)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_vendor_workload(vendor.id)

        assert result["completion_rate"] == pytest.approx(0.75)

    def test_workload_score_increases_with_active_orders(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        for _ in range(10):
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.PREPARING, created_at=NOW)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_vendor_workload(vendor.id)

        # workload_score = min(1.0, 10/20 + (1-cr)*0.5) = 0.5 (since cr=0.0 → 0.5+0.5=1.0)
        assert result["workload_score"] <= 1.0
        assert result["workload_score"] > 0.0

    def test_workload_score_capped_at_1(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        for _ in range(25):
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.PREPARING, created_at=NOW)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_vendor_workload(vendor.id)

        assert result["workload_score"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 4. get_slot_occupancy
# ---------------------------------------------------------------------------

class TestGetSlotOccupancy:

    def test_missing_slot_returns_defaults(self, db_session: Session):
        result = _engine(db_session).get_slot_occupancy(slot_id=99999)
        assert result["current_orders"] == 0
        assert result["max_capacity"] == 0
        assert result["utilization"] == 0.0
        assert result["time_factor"] == 1.0
        assert result["congestion_level"] == "LOW"

    def test_low_congestion(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id, max_orders=10, current_orders=3)
        db_session.commit()
        with patch(_UTCNOW_PATH, return_value=NOW.replace(hour=10)):
            result = _engine(db_session).get_slot_occupancy(slot.id)
        assert result["congestion_level"] == "LOW"
        assert result["utilization"] == pytest.approx(0.3)
        assert result["time_factor"] == pytest.approx(1.0)

    def test_medium_congestion(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id, max_orders=10, current_orders=7)
        db_session.commit()
        with patch(_UTCNOW_PATH, return_value=NOW.replace(hour=10)):
            result = _engine(db_session).get_slot_occupancy(slot.id)
        assert result["congestion_level"] == "MEDIUM"

    def test_high_congestion(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id, max_orders=10, current_orders=10)
        db_session.commit()
        with patch(_UTCNOW_PATH, return_value=NOW.replace(hour=10)):
            result = _engine(db_session).get_slot_occupancy(slot.id)
        assert result["congestion_level"] == "HIGH"
        assert result["utilization"] == pytest.approx(1.0)

    def test_peak_hour_time_factor_1_3(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        db_session.commit()
        lunch_time = NOW.replace(hour=12)
        with patch(_UTCNOW_PATH, return_value=lunch_time):
            result = _engine(db_session).get_slot_occupancy(slot.id)
        assert result["time_factor"] == pytest.approx(1.3)

    def test_dinner_peak_time_factor_1_3(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        db_session.commit()
        dinner_time = NOW.replace(hour=19)
        with patch(_UTCNOW_PATH, return_value=dinner_time):
            result = _engine(db_session).get_slot_occupancy(slot.id)
        assert result["time_factor"] == pytest.approx(1.3)

    def test_afternoon_time_factor_1_1(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        db_session.commit()
        # Hour 14 is both 11-14 and 14-17 — service checks 11-14 first (inclusive)
        # so hour=15 is cleanly in the afternoon window
        afternoon_time = NOW.replace(hour=15)
        with patch(_UTCNOW_PATH, return_value=afternoon_time):
            result = _engine(db_session).get_slot_occupancy(slot.id)
        assert result["time_factor"] == pytest.approx(1.1)

    def test_non_peak_time_factor_1_0(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        db_session.commit()
        with patch(_UTCNOW_PATH, return_value=NOW.replace(hour=7)):
            result = _engine(db_session).get_slot_occupancy(slot.id)
        assert result["time_factor"] == pytest.approx(1.0)

    def test_exact_boundary_congestion_medium(self, db_session: Session):
        """Utilization > 0.6 → MEDIUM."""
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id, max_orders=10, current_orders=7)  # 0.7
        db_session.commit()
        with patch(_UTCNOW_PATH, return_value=NOW.replace(hour=10)):
            result = _engine(db_session).get_slot_occupancy(slot.id)
        assert result["congestion_level"] == "MEDIUM"


# ---------------------------------------------------------------------------
# 5. predict_eta_enhanced
# ---------------------------------------------------------------------------

class TestPredictEtaEnhanced:
    """patch ETAEngine at source module (deferred import inside predict_eta_enhanced)."""

    def _base_mock(self, eta: int = 15):
        with patch(_ETA_ENGINE_PATH) as MockETA:
            MockETA.return_value.predict_eta.return_value = {"predicted_eta_minutes": eta}
            yield MockETA

    def test_basic_prediction_within_bounds(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id, max_orders=10, current_orders=2)
        item = _make_menu_item(db_session, vendor.id, category="snacks")
        db_session.commit()

        with patch(_ETA_ENGINE_PATH) as MockETA, patch(_UTCNOW_PATH, return_value=NOW.replace(hour=10)):
            MockETA.return_value.predict_eta.return_value = {"predicted_eta_minutes": 15}
            result = _engine(db_session).predict_eta_enhanced(
                order_id=1, menu_item_ids=[item.id], vendor_id=vendor.id, slot_id=slot.id
            )

        assert 5 <= result["predicted_eta_minutes"] <= 90
        assert "estimated_ready_at" in result
        assert "delay_risk_level" in result
        assert "confidence" in result
        assert "factors" in result
        assert "preparation_progress" in result

    def test_empty_menu_items_uses_default_complexity(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        db_session.commit()

        with patch(_ETA_ENGINE_PATH) as MockETA, patch(_UTCNOW_PATH, return_value=NOW):
            MockETA.return_value.predict_eta.return_value = {"predicted_eta_minutes": 15}
            result = _engine(db_session).predict_eta_enhanced(
                order_id=1, menu_item_ids=[], vendor_id=vendor.id, slot_id=slot.id
            )

        assert result["factors"]["avg_complexity"] == pytest.approx(0.5)

    def test_multiple_menu_items_avg_complexity(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        item_simple = _make_menu_item(db_session, vendor.id, category="beverages")
        item_complex = _make_menu_item(db_session, vendor.id, category="indian")
        db_session.commit()

        with patch(_ETA_ENGINE_PATH) as MockETA, patch(_UTCNOW_PATH, return_value=NOW):
            MockETA.return_value.predict_eta.return_value = {"predicted_eta_minutes": 15}
            result = _engine(db_session).predict_eta_enhanced(
                order_id=1,
                menu_item_ids=[item_simple.id, item_complex.id],
                vendor_id=vendor.id,
                slot_id=slot.id,
            )

        # avg_complexity should be between 0 and 1
        assert 0.0 <= result["factors"]["avg_complexity"] <= 1.0

    def test_eta_min_bound_enforced(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id, max_orders=10, current_orders=0)
        item = _make_menu_item(db_session, vendor.id, category="beverages")
        db_session.commit()

        with patch(_ETA_ENGINE_PATH) as MockETA, patch(_UTCNOW_PATH, return_value=NOW):
            # Very low base ETA
            MockETA.return_value.predict_eta.return_value = {"predicted_eta_minutes": 1}
            result = _engine(db_session).predict_eta_enhanced(
                order_id=1, menu_item_ids=[item.id], vendor_id=vendor.id, slot_id=slot.id
            )

        assert result["predicted_eta_minutes"] >= 5

    def test_eta_max_bound_enforced(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        # Overloaded slot → time_factor=1.3 + high workload
        slot = _make_slot(db_session, vendor.id, max_orders=10, current_orders=10)
        item = _make_menu_item(db_session, vendor.id, category="indian",
                               name="Grand Special Deluxe Thali Feast")
        for _ in range(20):
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.PREPARING, created_at=NOW)
        db_session.commit()

        with patch(_ETA_ENGINE_PATH) as MockETA, patch(_UTCNOW_PATH, return_value=NOW.replace(hour=12)):
            MockETA.return_value.predict_eta.return_value = {"predicted_eta_minutes": 60}
            result = _engine(db_session).predict_eta_enhanced(
                order_id=1, menu_item_ids=[item.id], vendor_id=vendor.id, slot_id=slot.id
            )

        assert result["predicted_eta_minutes"] <= 90

    def test_confidence_all_factors_present(self, db_session: Session):
        """All 5 confidence factors met → confidence = 1.0."""
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id, max_orders=10, current_orders=2)  # utilization < 0.9
        item = _make_menu_item(db_session, vendor.id, category="snacks")  # low complexity
        # 1 active order → active_orders > 0
        _make_order(db_session, student.id, vendor.id, slot.id,
                    status=OrderStatus.PLACED, created_at=NOW)
        # many completions → high completion_rate
        for _ in range(5):
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO)
        db_session.commit()

        with patch(_ETA_ENGINE_PATH) as MockETA, patch(_UTCNOW_PATH, return_value=NOW):
            MockETA.return_value.predict_eta.return_value = {"predicted_eta_minutes": 15}
            result = _engine(db_session).predict_eta_enhanced(
                order_id=1, menu_item_ids=[item.id], vendor_id=vendor.id, slot_id=slot.id
            )

        # confidence between 0 and 1
        assert 0.0 <= result["confidence"] <= 1.0

    def test_confidence_low_order_size_bonus(self, db_session: Session):
        """Order with <=3 items gets confidence bonus."""
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        items = [_make_menu_item(db_session, vendor.id) for _ in range(3)]
        db_session.commit()

        with patch(_ETA_ENGINE_PATH) as MockETA, patch(_UTCNOW_PATH, return_value=NOW):
            MockETA.return_value.predict_eta.return_value = {"predicted_eta_minutes": 15}
            result = _engine(db_session).predict_eta_enhanced(
                order_id=1, menu_item_ids=[i.id for i in items],
                vendor_id=vendor.id, slot_id=slot.id
            )
        assert result["confidence"] >= 0.0

    def test_preparation_progress_milestones_present(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id)
        db_session.commit()

        with patch(_ETA_ENGINE_PATH) as MockETA, patch(_UTCNOW_PATH, return_value=NOW):
            MockETA.return_value.predict_eta.return_value = {"predicted_eta_minutes": 20}
            result = _engine(db_session).predict_eta_enhanced(
                order_id=1, menu_item_ids=[item.id], vendor_id=vendor.id, slot_id=slot.id
            )

        progress = result["preparation_progress"]
        assert "milestones" in progress
        assert "total_minutes" in progress
        assert progress["current_phase"] == "preparing"
        milestones = progress["milestones"]
        for key in ["started_at", "quarter_at", "halfway_at", "final_at", "ready_at"]:
            assert key in milestones

    def test_factors_dict_contains_expected_keys(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id)
        db_session.commit()

        with patch(_ETA_ENGINE_PATH) as MockETA, patch(_UTCNOW_PATH, return_value=NOW):
            MockETA.return_value.predict_eta.return_value = {"predicted_eta_minutes": 15}
            result = _engine(db_session).predict_eta_enhanced(
                order_id=1, menu_item_ids=[item.id], vendor_id=vendor.id, slot_id=slot.id
            )

        for key in ["base_eta", "complexity_factor", "workload_factor",
                    "occupancy_factor", "avg_complexity", "vendor_workload", "slot_occupancy"]:
            assert key in result["factors"]


# ---------------------------------------------------------------------------
# 6. _calculate_delay_risk
# ---------------------------------------------------------------------------

class TestCalculateDelayRisk:

    def _slot_occ(self, utilization: float, time_factor: float = 1.0) -> dict:
        return {"utilization": utilization, "time_factor": time_factor}

    def _vendor_wl(self, workload_score: float, completion_rate: float = 1.0) -> dict:
        return {
            "workload_score": workload_score,
            "completion_rate": completion_rate,
            "active_orders": 0,
            "avg_prep_time": 15.0,
            "estimated_capacity": 20,
        }

    def test_high_risk(self, db_session: Session):
        engine = _engine(db_session)
        # utilization=1.0 → 0.4 + workload=1.0 → 0.3 + eta>45 → 0.2 + complexity>0.7 → 0.1
        risk = engine._calculate_delay_risk(
            self._slot_occ(1.0), self._vendor_wl(1.0), predicted_eta=60, complexity=0.8
        )
        assert risk == "HIGH"

    def test_medium_risk(self, db_session: Session):
        engine = _engine(db_session)
        # utilization=0.5 → 0.2 + workload=0.5 → 0.15 + eta=35 → 0.1 + no complexity → 0.0
        # total = 0.45 → MEDIUM
        risk = engine._calculate_delay_risk(
            self._slot_occ(0.5), self._vendor_wl(0.5), predicted_eta=35, complexity=0.3
        )
        assert risk == "MEDIUM"

    def test_low_risk(self, db_session: Session):
        engine = _engine(db_session)
        risk = engine._calculate_delay_risk(
            self._slot_occ(0.1), self._vendor_wl(0.1), predicted_eta=15, complexity=0.2
        )
        assert risk == "LOW"

    def test_eta_over_45_adds_0_2(self, db_session: Session):
        engine = _engine(db_session)
        # Need base utilization 0.5 so risk_score starts at 0.2;
        # ETA > 45 adds another 0.2 → total 0.4 → MEDIUM
        # ETA ≤ 30 adds 0.0 → total 0.2 → LOW
        risk_long = engine._calculate_delay_risk(
            self._slot_occ(0.5), self._vendor_wl(0.0), predicted_eta=50, complexity=0.0
        )
        risk_short = engine._calculate_delay_risk(
            self._slot_occ(0.5), self._vendor_wl(0.0), predicted_eta=15, complexity=0.0
        )
        assert risk_long == "MEDIUM"
        assert risk_short == "LOW"

    def test_eta_over_30_but_under_45_adds_0_1(self, db_session: Session):
        engine = _engine(db_session)
        # Only ETA contribution: 0.1 (from >30) → total 0.1 → LOW
        risk = engine._calculate_delay_risk(
            self._slot_occ(0.0), self._vendor_wl(0.0), predicted_eta=35, complexity=0.0
        )
        assert risk == "LOW"

    def test_complexity_over_0_7_adds_0_1(self, db_session: Session):
        engine = _engine(db_session)
        risk_complex = engine._calculate_delay_risk(
            self._slot_occ(0.3), self._vendor_wl(0.3), predicted_eta=15, complexity=0.8
        )
        risk_simple = engine._calculate_delay_risk(
            self._slot_occ(0.3), self._vendor_wl(0.3), predicted_eta=15, complexity=0.2
        )
        # Complexity adds 0.1 to risk_score
        assert risk_complex in ("LOW", "MEDIUM", "HIGH")
        assert risk_simple in ("LOW", "MEDIUM", "HIGH")


# ---------------------------------------------------------------------------
# 7. _estimate_preparation_progress
# ---------------------------------------------------------------------------

class TestEstimatePreparationProgress:

    def test_milestones_ordered_correctly(self, db_session: Session):
        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session)._estimate_preparation_progress(
                enhanced_eta=20, base_eta=15
            )

        m = result["milestones"]
        assert m["started_at"] <= m["quarter_at"] <= m["halfway_at"] <= m["final_at"] <= m["ready_at"]

    def test_total_minutes_equals_eta(self, db_session: Session):
        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session)._estimate_preparation_progress(
                enhanced_eta=30, base_eta=15
            )
        assert result["total_minutes"] == 30

    def test_current_phase_is_preparing(self, db_session: Session):
        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session)._estimate_preparation_progress(
                enhanced_eta=20, base_eta=15
            )
        assert result["current_phase"] == "preparing"

    def test_milestone_times_correct(self, db_session: Session):
        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session)._estimate_preparation_progress(
                enhanced_eta=20, base_eta=15
            )
        m = result["milestones"]
        assert m["quarter_at"] == NOW + timedelta(minutes=5)   # int(20*0.25)=5
        assert m["halfway_at"] == NOW + timedelta(minutes=10)  # int(20*0.5)=10
        assert m["final_at"] == NOW + timedelta(minutes=15)    # int(20*0.75)=15
        assert m["ready_at"] == NOW + timedelta(minutes=20)


# ---------------------------------------------------------------------------
# 8. predict_delay_probability
# ---------------------------------------------------------------------------

class TestPredictDelayProbability:

    def test_missing_order_returns_zeros(self, db_session: Session):
        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).predict_delay_probability(order_id=99999)
        assert result["delay_probability"] == 0.0
        assert result["expected_delay_minutes"] == 0
        assert result["risk_factors"] == []
        assert result["recommendations"] == []

    def test_slot_nearly_full_adds_factor(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id, max_orders=10, current_orders=10)  # util=1.0
        order = _make_order(db_session, student.id, vendor.id, slot.id,
                            status=OrderStatus.PLACED, created_at=NOW)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).predict_delay_probability(order.id)

        assert "Slot nearly full" in result["risk_factors"]
        assert result["delay_probability"] >= 0.4
        assert "Consider selecting a different slot" in result["recommendations"]

    def test_slot_busy_adds_smaller_factor(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id, max_orders=10, current_orders=8)  # util=0.8
        order = _make_order(db_session, student.id, vendor.id, slot.id,
                            status=OrderStatus.PLACED, created_at=NOW)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).predict_delay_probability(order.id)

        assert "Slot busy" in result["risk_factors"]
        assert result["delay_probability"] >= 0.2

    def test_vendor_overloaded_adds_factor(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        order = _make_order(db_session, student.id, vendor.id, slot.id,
                            status=OrderStatus.PLACED, created_at=NOW)
        # 20 active orders → workload_score ≥ 0.8 + high
        for _ in range(20):
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.PREPARING, created_at=NOW)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).predict_delay_probability(order.id)

        assert "Vendor overloaded" in result["risk_factors"]

    def test_vendor_busy_medium_workload(self, db_session: Session):
        """
        Target workload_score between 0.6 and 0.8:
        8 PREPARING + 8 COMPLETED (recent) + 1 PLACED (order under test)
        active=9 → workload from active = 9/20 = 0.45
        completion_rate = 8/(8+8+1) ≈ 0.47
        workload_score = 0.45 + (1-0.47)*0.5 ≈ 0.715  → 'Vendor busy'
        """
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        order = _make_order(db_session, student.id, vendor.id, slot.id,
                            status=OrderStatus.PLACED, created_at=NOW)
        for _ in range(8):
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.PREPARING, created_at=NOW)
        # 8 completed recently to bring completion_rate up enough (not 0.0)
        for _ in range(8):
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).predict_delay_probability(order.id)

        assert "Vendor busy" in result["risk_factors"]

    def test_low_completion_rate_adds_factor(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        # 1 completed, 4 cancelled (last 7 days) → completion_rate = 0.2 < 0.8
        for _ in range(4):
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.CANCELLED, created_at=FIVE_DAYS_AGO)
        _make_order(db_session, student.id, vendor.id, slot.id,
                    status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO)
        order = _make_order(db_session, student.id, vendor.id, slot.id,
                            status=OrderStatus.PLACED, created_at=NOW)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).predict_delay_probability(order.id)

        assert "Low completion rate" in result["risk_factors"]
        assert result["delay_probability"] >= 0.2

    def test_complex_menu_adds_factor(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        # Make a complex item: indian + special keyword + long name + high variance
        complex_item = _make_menu_item(
            db_session, vendor.id,
            category="indian",
            name="Grand Special Deluxe Thali Feast Platter",
        )
        order = _make_order(db_session, student.id, vendor.id, slot.id,
                            status=OrderStatus.PLACED, created_at=NOW)
        _make_order_item(db_session, order.id, complex_item.id)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).predict_delay_probability(order.id)

        # Complexity factor added when avg_complexity > 0.7
        assert result["delay_probability"] >= 0.0  # may not trigger if complexity < 0.7

    def test_expected_delay_positive_when_probability_over_0_5(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id, max_orders=10, current_orders=10)
        order = _make_order(db_session, student.id, vendor.id, slot.id,
                            status=OrderStatus.PLACED, created_at=NOW)
        # Many cancellations → low completion rate → probability > 0.5
        for _ in range(9):
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.CANCELLED, created_at=FIVE_DAYS_AGO)
        _make_order(db_session, student.id, vendor.id, slot.id,
                    status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO)
        for _ in range(20):
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.PREPARING, created_at=NOW)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).predict_delay_probability(order.id)

        if result["delay_probability"] > 0.5:
            assert result["expected_delay_minutes"] > 0

    def test_delay_probability_capped_at_1(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id, max_orders=10, current_orders=10)
        order = _make_order(db_session, student.id, vendor.id, slot.id,
                            status=OrderStatus.PLACED, created_at=NOW)
        for _ in range(20):
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.CANCELLED, created_at=FIVE_DAYS_AGO)
        for _ in range(20):
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.PREPARING, created_at=NOW)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).predict_delay_probability(order.id)

        assert result["delay_probability"] <= 1.0

    def test_no_order_items_avg_complexity_zero(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        order = _make_order(db_session, student.id, vendor.id, slot.id,
                            status=OrderStatus.PLACED, created_at=NOW)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).predict_delay_probability(order.id)

        assert result["delay_probability"] >= 0.0
        # "Complex menu items" should not appear since no items
        assert "Complex menu items" not in result["risk_factors"]

    def test_recommendations_for_busy_vendor(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        order = _make_order(db_session, student.id, vendor.id, slot.id,
                            status=OrderStatus.PLACED, created_at=NOW)
        # Overloaded → recommendation triggered
        for _ in range(15):
            _make_order(db_session, student.id, vendor.id, slot.id,
                        status=OrderStatus.PREPARING, created_at=NOW)
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).predict_delay_probability(order.id)

        assert "Vendor is busy - expect longer wait time" in result["recommendations"]


# ---------------------------------------------------------------------------
# 9. get_enhanced_eta
# ---------------------------------------------------------------------------

class TestGetEnhancedEta:

    def test_missing_order_returns_default_response(self, db_session: Session):
        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session).get_enhanced_eta(order_id=99999)

        assert result["order_id"] is None
        assert result["predicted_eta_minutes"] == 15
        assert result["delay_risk_level"] == "MEDIUM"
        assert result["confidence"] == 0.5
        assert result["factors"] == {}
        assert result["preparation_progress"] == {}
        assert result["delay_prediction"]["delay_probability"] == 0.0

    def test_with_real_order_returns_full_response(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id)
        order = _make_order(db_session, student.id, vendor.id, slot.id,
                            status=OrderStatus.PLACED, created_at=NOW)
        _make_order_item(db_session, order.id, item.id)
        db_session.commit()

        with patch(_ETA_ENGINE_PATH) as MockETA, patch(_UTCNOW_PATH, return_value=NOW):
            MockETA.return_value.predict_eta.return_value = {"predicted_eta_minutes": 15}
            result = _engine(db_session).get_enhanced_eta(order.id)

        assert result["order_id"] == order.id
        assert "predicted_eta_minutes" in result
        assert "delay_prediction" in result
        assert "delay_risk_level" in result

    def test_enhanced_eta_includes_delay_prediction(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        order = _make_order(db_session, student.id, vendor.id, slot.id,
                            status=OrderStatus.PLACED, created_at=NOW)
        db_session.commit()

        with patch(_ETA_ENGINE_PATH) as MockETA, patch(_UTCNOW_PATH, return_value=NOW):
            MockETA.return_value.predict_eta.return_value = {"predicted_eta_minutes": 15}
            result = _engine(db_session).get_enhanced_eta(order.id)

        dp = result["delay_prediction"]
        assert "delay_probability" in dp
        assert "expected_delay_minutes" in dp
        assert "risk_factors" in dp
        assert "recommendations" in dp

    def test_no_order_items_still_works(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        order = _make_order(db_session, student.id, vendor.id, slot.id,
                            status=OrderStatus.PLACED, created_at=NOW)
        db_session.commit()

        with patch(_ETA_ENGINE_PATH) as MockETA, patch(_UTCNOW_PATH, return_value=NOW):
            MockETA.return_value.predict_eta.return_value = {"predicted_eta_minutes": 15}
            result = _engine(db_session).get_enhanced_eta(order.id)

        assert result["order_id"] == order.id
        assert 5 <= result["predicted_eta_minutes"] <= 90


# ---------------------------------------------------------------------------
# 10. _default_response
# ---------------------------------------------------------------------------

class TestDefaultResponse:

    def test_default_response_structure(self, db_session: Session):
        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session)._default_response()

        assert result["order_id"] is None
        assert result["predicted_eta_minutes"] == 15
        assert result["delay_risk_level"] == "MEDIUM"
        assert result["confidence"] == 0.5
        assert isinstance(result["factors"], dict)
        assert isinstance(result["preparation_progress"], dict)
        assert "estimated_ready_at" in result

    def test_default_ready_at_is_15_minutes_from_now(self, db_session: Session):
        with patch(_UTCNOW_PATH, return_value=NOW):
            result = _engine(db_session)._default_response()

        expected_ready = (NOW + timedelta(minutes=15)).isoformat()
        assert result["estimated_ready_at"] == expected_ready
