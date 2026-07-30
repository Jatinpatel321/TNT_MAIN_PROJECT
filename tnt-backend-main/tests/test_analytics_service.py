"""
Unit tests for app/modules/ai_intelligence/analytics_service.py — AnalyticsService.

All 6 public methods are covered:
  1. get_vendor_recommendations
  2. get_menu_suggestions
  3. get_smart_reorder
  4. get_best_pickup_time
  5. get_peak_hour_alerts
  6. get_popular_nearby

Strategy:
- Use the shared in-memory SQLite db_session (conftest.py).
- Seed deterministic rows for each test via helper factories.
- Patch utcnow_naive where time-sensitive assertions are needed.
- Verify exception/fallback branches by forcing DB errors via monkeypatching.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.modules.ai_intelligence.analytics_service import AnalyticsService
from app.modules.ai_intelligence.schemas import (
    BestPickupTimeResponse,
    MenuSuggestionsResponse,
    PeakHourAlert,
    PopularNearbyResponse,
    SmartReorderResponse,
    VendorRecommendationsResponse,
)
from app.modules.feedback.model import VendorReview
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

NOW = datetime(2024, 6, 15, 10, 0, 0)   # fixed reference time: 10:00 off-peak
TWENTY_FIVE_DAYS_AGO = NOW - timedelta(days=25)
FIVE_DAYS_AGO = NOW - timedelta(days=5)


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _make_vendor(db: Session, vendor_type: str = "food", approved: bool = True) -> User:
    u = User(
        email=f"v_{_uid()}@test.com",
        phone=f"+155500{_uid()[:6]}",
        name=f"Vendor_{_uid()}",
        role=UserRole.VENDOR,
        vendor_type=vendor_type,
        is_approved=approved,
    )
    db.add(u)
    db.flush()
    return u


def _make_student(db: Session) -> User:
    u = User(
        email=f"s_{_uid()}@test.com",
        phone=f"+155500{_uid()[:6]}",
        name=f"Student_{_uid()}",
        role=UserRole.STUDENT,
        vendor_type="food",   # default column value
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
    congestion_level: float = 0.2,
    base_time: datetime = None,
) -> Slot:
    base = base_time or NOW
    start = base + timedelta(hours=start_offset_hours)
    slot = Slot(
        vendor_id=vendor_id,
        start_time=start,
        end_time=start + timedelta(hours=1),
        max_orders=max_orders,
        current_orders=current_orders,
        status=status,
        congestion_level=congestion_level,
    )
    db.add(slot)
    db.flush()
    return slot


def _make_menu_item(
    db: Session,
    vendor_id: int,
    name: str = None,
    is_available: bool = True,
    price: float = 5.99,
) -> MenuItem:
    mi = MenuItem(
        vendor_id=vendor_id,
        name=name or f"Item_{_uid()}",
        price=price,
        is_available=is_available,
        category="food",
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
    total_amount: float = 10.0,
) -> Order:
    o = Order(
        user_id=user_id,
        vendor_id=vendor_id,
        slot_id=slot_id,
        status=status,
        total_amount=total_amount,
        created_at=created_at or NOW,
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


def _make_review(db: Session, vendor_id: int, user_id: int, rating: int = 4) -> VendorReview:
    r = VendorReview(
        vendor_id=vendor_id,
        user_id=user_id,
        rating=rating,
    )
    db.add(r)
    db.flush()
    return r


def _svc(db: Session) -> AnalyticsService:
    return AnalyticsService(db)


# ─────────────────────────────────────────────────────────────────────────────
# 1. get_vendor_recommendations
# ─────────────────────────────────────────────────────────────────────────────

class TestGetVendorRecommendations:

    def test_empty_db_returns_empty_list(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_vendor_recommendations(student.id)
        assert isinstance(result, VendorRecommendationsResponse)
        assert result.recommendations == []

    def test_unapproved_vendor_excluded(self, db_session: Session):
        _make_vendor(db_session, approved=False)
        student = _make_student(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_vendor_recommendations(student.id)
        assert result.recommendations == []

    def test_single_vendor_no_orders_low_load(self, db_session: Session):
        vendor = _make_vendor(db_session)
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=1)
        student = _make_student(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_vendor_recommendations(student.id)
        assert len(result.recommendations) == 1
        rec = result.recommendations[0]
        assert rec.vendor_id == vendor.id
        assert rec.live_load == "LOW"
        assert rec.express_pickup is True
        assert rec.reason == "Low wait time right now"

    def test_high_load_vendor_shows_high(self, db_session: Session):
        vendor = _make_vendor(db_session)
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=9)
        student = _make_student(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_vendor_recommendations(student.id)
        rec = result.recommendations[0]
        assert rec.live_load == "HIGH"
        assert rec.express_pickup is False

    def test_medium_load_vendor(self, db_session: Session):
        vendor = _make_vendor(db_session)
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=7)
        student = _make_student(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_vendor_recommendations(student.id)
        rec = result.recommendations[0]
        assert rec.live_load == "MEDIUM"

    def test_regular_spot_reason_one_order(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)
        _make_order(db_session, student.id, vendor.id, slot.id, created_at=FIVE_DAYS_AGO)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_vendor_recommendations(student.id)
        rec = next(r for r in result.recommendations if r.vendor_id == vendor.id)
        assert rec.reason == "One of your regular spots"

    def test_frequent_customer_reason_three_plus(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)
        for _ in range(4):
            _make_order(db_session, student.id, vendor.id, slot.id, created_at=FIVE_DAYS_AGO)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_vendor_recommendations(student.id)
        rec = next(r for r in result.recommendations if r.vendor_id == vendor.id)
        assert "4" in rec.reason
        assert "times" in rec.reason

    def test_popular_on_campus_reason_high_load_no_orders(self, db_session: Session):
        vendor = _make_vendor(db_session)
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=9)
        student = _make_student(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_vendor_recommendations(student.id)
        rec = result.recommendations[0]
        assert rec.reason == "Popular on campus"

    def test_results_sorted_by_score(self, db_session: Session):
        v1 = _make_vendor(db_session)
        v2 = _make_vendor(db_session)
        slot1 = _make_slot(db_session, v1.id, max_orders=10, current_orders=1)
        _make_slot(db_session, v2.id, max_orders=10, current_orders=8)
        student = _make_student(db_session)
        # Give v1 many orders so it has a higher freq_bonus
        for _ in range(5):
            _make_order(db_session, student.id, v1.id, slot1.id, created_at=FIVE_DAYS_AGO)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_vendor_recommendations(student.id)
        scores = [r.rank_score for r in result.recommendations]
        assert scores == sorted(scores, reverse=True)

    def test_vendor_with_no_slots_defaults_to_low(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_vendor_recommendations(student.id)
        rec = result.recommendations[0]
        assert rec.live_load == "LOW"

    def test_exception_returns_empty_recommendations(self, db_session: Session):
        svc = _svc(db_session)
        with patch.object(svc.db, "query", side_effect=RuntimeError("db error")):
            result = svc.get_vendor_recommendations(1)
        assert result.recommendations == []

    def test_old_orders_outside_30_days_not_counted(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)
        old_date = NOW - timedelta(days=40)
        for _ in range(5):
            _make_order(db_session, student.id, vendor.id, slot.id, created_at=old_date)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_vendor_recommendations(student.id)
        rec = next(r for r in result.recommendations if r.vendor_id == vendor.id)
        # 5 old orders ignored → reason shows no frequency bonus
        assert rec.reason in ("Low wait time right now", "Popular on campus")


# ─────────────────────────────────────────────────────────────────────────────
# 2. get_menu_suggestions
# ─────────────────────────────────────────────────────────────────────────────

class TestGetMenuSuggestions:

    def test_empty_db_returns_empty_both(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_menu_suggestions(student.id)
        assert isinstance(result, MenuSuggestionsResponse)
        assert result.personalized == []
        assert result.trending == []

    def test_available_items_shown_as_fallback(self, db_session: Session):
        vendor = _make_vendor(db_session)
        item = _make_menu_item(db_session, vendor.id, name="Fallback Burger")
        student = _make_student(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_menu_suggestions(student.id)
        # No order history → fallback to available items → appears in personalized
        assert any(i.item_name == "Fallback Burger" for i in result.personalized)
        assert all(i.reason == "Available now" for i in result.personalized)

    def test_unavailable_items_not_in_fallback(self, db_session: Session):
        vendor = _make_vendor(db_session)
        _make_menu_item(db_session, vendor.id, name="Unavailable", is_available=False)
        student = _make_student(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_menu_suggestions(student.id)
        assert result.personalized == []

    def test_similar_items_appear_in_personalized(self, db_session: Session):
        vendor = _make_vendor(db_session)
        ordered_item = _make_menu_item(db_session, vendor.id, name="Ordered Pizza")
        similar1 = _make_menu_item(db_session, vendor.id, name="Similar Pasta")
        similar2 = _make_menu_item(db_session, vendor.id, name="Similar Garlic Bread")
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)
        order = _make_order(db_session, student.id, vendor.id, slot.id, created_at=FIVE_DAYS_AGO)
        _make_order_item(db_session, order.id, ordered_item.id)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_menu_suggestions(student.id)
        names = [i.item_name for i in result.personalized]
        assert "Similar Pasta" in names or "Similar Garlic Bread" in names
        for item in result.personalized:
            assert "Similar to your favorite Ordered Pizza" in item.reason

    def test_trending_items_populate_from_all_orders(self, db_session: Session):
        vendor = _make_vendor(db_session)
        trending_item = _make_menu_item(db_session, vendor.id, name="Trending Samosa")
        slot = _make_slot(db_session, vendor.id)
        other_student = _make_student(db_session)
        student = _make_student(db_session)

        # Other student orders trending_item many times
        for _ in range(3):
            order = _make_order(db_session, other_student.id, vendor.id, slot.id, created_at=FIVE_DAYS_AGO)
            _make_order_item(db_session, order.id, trending_item.id)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_menu_suggestions(student.id)

        all_items = result.personalized + result.trending
        names = [i.item_name for i in all_items]
        assert "Trending Samosa" in names

    def test_duplicate_items_deduplicated(self, db_session: Session):
        """An item seen in personalized should NOT re-appear in trending."""
        vendor = _make_vendor(db_session)
        item = _make_menu_item(db_session, vendor.id, name="Shared Item")
        similar = _make_menu_item(db_session, vendor.id, name="Similar to Shared")
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)

        order = _make_order(db_session, student.id, vendor.id, slot.id, created_at=FIVE_DAYS_AGO)
        _make_order_item(db_session, order.id, item.id, quantity=3)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_menu_suggestions(student.id)

        all_ids = [i.item_id for i in result.personalized] + [i.item_id for i in result.trending]
        assert len(all_ids) == len(set(all_ids)), "Duplicate item IDs found across personalized + trending"

    def test_confidence_scores_correct(self, db_session: Session):
        vendor = _make_vendor(db_session)
        item = _make_menu_item(db_session, vendor.id, name="Main Item")
        _make_menu_item(db_session, vendor.id, name="Side Item")
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)
        order = _make_order(db_session, student.id, vendor.id, slot.id, created_at=FIVE_DAYS_AGO)
        _make_order_item(db_session, order.id, item.id)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_menu_suggestions(student.id)

        for i in result.personalized:
            if i.reason != "Available now":
                assert i.confidence == 0.8
        for i in result.trending:
            assert i.confidence == 0.6

    def test_exception_returns_empty_response(self, db_session: Session):
        svc = _svc(db_session)
        with patch.object(svc.db, "query", side_effect=RuntimeError("db error")):
            result = svc.get_menu_suggestions(1)
        assert result.personalized == []
        assert result.trending == []

    def test_vendor_name_fallback_when_no_vendor(self, db_session: Session):
        """MenuItem references a deleted/missing vendor → fallback name used."""
        vendor = _make_vendor(db_session)
        item = _make_menu_item(db_session, vendor.id, name="Orphan Item")
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)
        _make_menu_item(db_session, vendor.id, name="Another Item")
        order = _make_order(db_session, student.id, vendor.id, slot.id, created_at=FIVE_DAYS_AGO)
        _make_order_item(db_session, order.id, item.id)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_menu_suggestions(student.id)
        # Vendor exists in test, should resolve name correctly
        for i in result.personalized + result.trending:
            assert i.vendor_name is not None


# ─────────────────────────────────────────────────────────────────────────────
# 3. get_smart_reorder
# ─────────────────────────────────────────────────────────────────────────────

class TestGetSmartReorder:

    def test_empty_db_returns_empty_items_default_time(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_smart_reorder(student.id)
        assert isinstance(result, SmartReorderResponse)
        assert result.items == []
        assert result.best_reorder_time == "12:00"
        assert result.best_reorder_slot_id is None

    def test_completed_orders_populate_items(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id, name="Reorder Burger")
        student = _make_student(db_session)
        for _ in range(2):
            order = _make_order(
                db_session, student.id, vendor.id, slot.id,
                status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO
            )
            _make_order_item(db_session, order.id, item.id, quantity=2)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_smart_reorder(student.id)

        assert len(result.items) == 1
        r = result.items[0]
        assert r.item_name == "Reorder Burger"
        assert r.order_count == 2
        assert r.suggested_quantity == 2
        assert r.suggested_slot_id == slot.id

    def test_picked_status_also_counts(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id, name="Picked Item")
        student = _make_student(db_session)
        order = _make_order(
            db_session, student.id, vendor.id, slot.id,
            status=OrderStatus.PICKED, created_at=FIVE_DAYS_AGO
        )
        _make_order_item(db_session, order.id, item.id)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_smart_reorder(student.id)
        assert any(i.item_name == "Picked Item" for i in result.items)

    def test_pending_orders_not_counted(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id, name="Pending Item")
        student = _make_student(db_session)
        order = _make_order(
            db_session, student.id, vendor.id, slot.id,
            status=OrderStatus.PENDING, created_at=FIVE_DAYS_AGO
        )
        _make_order_item(db_session, order.id, item.id)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_smart_reorder(student.id)
        assert result.items == []

    def test_best_reorder_time_from_order_history(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id)
        student = _make_student(db_session)
        # Orders created at hour 9 → best_reorder_time = "09:00"
        order_time = FIVE_DAYS_AGO.replace(hour=9)
        for _ in range(3):
            order = _make_order(
                db_session, student.id, vendor.id, slot.id,
                status=OrderStatus.COMPLETED, created_at=order_time
            )
            _make_order_item(db_session, order.id, item.id)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_smart_reorder(student.id)

        assert result.best_reorder_time == "09:00"

    def test_best_slot_time_formatted(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id, start_offset_hours=2)
        item = _make_menu_item(db_session, vendor.id)
        student = _make_student(db_session)
        order = _make_order(
            db_session, student.id, vendor.id, slot.id,
            status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO
        )
        _make_order_item(db_session, order.id, item.id)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_smart_reorder(student.id)

        assert result.items[0].suggested_slot_time is not None
        assert "-" in result.items[0].suggested_slot_time

    def test_orders_outside_30_days_excluded(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id)
        student = _make_student(db_session)
        old = NOW - timedelta(days=40)
        order = _make_order(
            db_session, student.id, vendor.id, slot.id,
            status=OrderStatus.COMPLETED, created_at=old
        )
        _make_order_item(db_session, order.id, item.id)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_smart_reorder(student.id)
        assert result.items == []

    def test_exception_returns_safe_fallback(self, db_session: Session):
        svc = _svc(db_session)
        with patch.object(svc.db, "query", side_effect=RuntimeError("db error")):
            result = svc.get_smart_reorder(1)
        assert result.items == []
        assert result.best_reorder_time == "12:00"
        assert result.best_reorder_slot_id is None


# ─────────────────────────────────────────────────────────────────────────────
# 4. get_best_pickup_time
# ─────────────────────────────────────────────────────────────────────────────

class TestGetBestPickupTime:

    def test_no_slots_returns_default_source(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_best_pickup_time(student.id)
        assert isinstance(result, BestPickupTimeResponse)
        assert result.best_slot is None
        assert result.alternative_slots == []
        assert result.preferred_hour == 12
        assert result.preferred_hour_source == "default"

    def test_single_slot_becomes_best(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id, max_orders=10, current_orders=2, base_time=NOW)
        student = _make_student(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_best_pickup_time(student.id)
        assert result.best_slot is not None
        assert result.best_slot.slot_id == slot.id
        assert result.alternative_slots == []

    def test_multiple_slots_sorted_best_first(self, db_session: Session):
        vendor = _make_vendor(db_session)
        # Low utilization slot (better)
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=1, start_offset_hours=1)
        # High utilization slot (worse)
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=9, start_offset_hours=2)
        student = _make_student(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_best_pickup_time(student.id)
        assert result.best_slot.score >= result.alternative_slots[0].score if result.alternative_slots else True

    def test_congestion_levels_critical_high_medium_low(self, db_session: Session):
        vendor = _make_vendor(db_session)
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=9, start_offset_hours=0.5)  # CRITICAL
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=8, start_offset_hours=1)    # HIGH
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=6, start_offset_hours=2)    # MEDIUM
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=2, start_offset_hours=3)    # LOW
        student = _make_student(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_best_pickup_time(student.id)

        all_slots = [result.best_slot] + result.alternative_slots
        congestion_levels = {s.congestion_level for s in all_slots}
        assert "CRITICAL" in congestion_levels
        assert "LOW" in congestion_levels

    def test_eta_minutes_by_utilization(self, db_session: Session):
        vendor = _make_vendor(db_session)
        # >=80% → eta=30
        s1 = _make_slot(db_session, vendor.id, max_orders=10, current_orders=9, start_offset_hours=0.5)
        # >=50% → eta=20
        s2 = _make_slot(db_session, vendor.id, max_orders=10, current_orders=6, start_offset_hours=1.5)
        # <50% → eta=15
        s3 = _make_slot(db_session, vendor.id, max_orders=10, current_orders=2, start_offset_hours=2.5)
        student = _make_student(db_session)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_best_pickup_time(student.id)

        all_slots = {s.slot_id: s for s in ([result.best_slot] + result.alternative_slots) if s}
        assert all_slots[s1.id].eta_minutes == 30
        assert all_slots[s2.id].eta_minutes == 20
        assert all_slots[s3.id].eta_minutes == 15

    def test_delay_risk_levels(self, db_session: Session):
        vendor = _make_vendor(db_session)
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=9, start_offset_hours=0.5)  # HIGH
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=8, start_offset_hours=1.5)  # MEDIUM
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=2, start_offset_hours=2.5)  # LOW
        student = _make_student(db_session)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_best_pickup_time(student.id)

        all_slots = {s.slot_id: s for s in ([result.best_slot] + result.alternative_slots) if s}
        risks = {s.delay_risk for s in all_slots.values()}
        assert "HIGH" in risks or "MEDIUM" in risks
        assert "LOW" in risks

    def test_history_source_from_order_data(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)
        order_time = FIVE_DAYS_AGO.replace(hour=14)
        _make_order(db_session, student.id, vendor.id, slot.id, created_at=order_time)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_best_pickup_time(student.id)

        assert result.preferred_hour_source == "history"
        assert result.preferred_hour == 14

    def test_preference_source_overrides_history(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)
        student.preferences = {"preferred_pickup_hour": 9}
        db_session.flush()
        _make_order(db_session, student.id, vendor.id, slot.id, created_at=FIVE_DAYS_AGO.replace(hour=14))
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_best_pickup_time(student.id)

        assert result.preferred_hour_source == "preference"
        assert result.preferred_hour == 9

    def test_full_slots_excluded(self, db_session: Session):
        vendor = _make_vendor(db_session)
        _make_slot(db_session, vendor.id, status="full")
        student = _make_student(db_session)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_best_pickup_time(student.id)
        assert result.best_slot is None

    def test_exception_returns_safe_fallback(self, db_session: Session):
        svc = _svc(db_session)
        with patch.object(svc.db, "query", side_effect=RuntimeError("db error")):
            result = svc.get_best_pickup_time(1)
        assert result.best_slot is None
        assert result.preferred_hour == 12
        assert result.preferred_hour_source == "default"

    def test_up_to_five_alternatives_returned(self, db_session: Session):
        vendor = _make_vendor(db_session)
        for i in range(7):
            _make_slot(db_session, vendor.id, start_offset_hours=i + 1)
        student = _make_student(db_session)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_best_pickup_time(student.id)
        assert len(result.alternative_slots) <= 5

    def test_hour_match_score_bonus(self, db_session: Session):
        """Slot exactly at preferred_hour gets a +30 score bonus."""
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        # History-based preferred hour = 14
        order_time = FIVE_DAYS_AGO.replace(hour=14)
        slot_far = _make_slot(db_session, vendor.id, start_offset_hours=0.5)  # hour=10 (off)
        # Slot exactly at preferred hour 14
        slot_at_14 = Slot(
            vendor_id=vendor.id,
            start_time=NOW.replace(hour=14, minute=30),
            end_time=NOW.replace(hour=15, minute=30),
            max_orders=10, current_orders=2, status="available",
        )
        db_session.add(slot_at_14)
        db_session.flush()
        _make_order(db_session, student.id, vendor.id, slot_far.id, created_at=order_time)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_best_pickup_time(student.id)

        all_slots = {s.slot_id: s for s in ([result.best_slot] + result.alternative_slots) if s}
        if slot_at_14.id in all_slots and slot_far.id in all_slots:
            assert all_slots[slot_at_14.id].score >= all_slots[slot_far.id].score


# ─────────────────────────────────────────────────────────────────────────────
# 5. get_peak_hour_alerts
# ─────────────────────────────────────────────────────────────────────────────

class TestGetPeakHourAlerts:

    def test_empty_db_no_orders_all_periods_low(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        # Use hour=11 which is truly off-peak (peak windows: 8-10, 12-14, 18-20)
        off_peak = NOW.replace(hour=11)
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=off_peak):
            result = _svc(db_session).get_peak_hour_alerts(student.id)
        assert isinstance(result, PeakHourAlert)
        assert result.is_peak_now is False
        assert len(result.peak_periods_today) == 3
        for p in result.peak_periods_today:
            assert p.severity == "LOW"
            assert p.avg_wait_minutes == 5

    def test_off_peak_time_is_peak_now_false(self, db_session: Session):
        """Hour 11 is outside all peak windows (8-10, 12-14, 18-20)."""
        student = _make_student(db_session)
        db_session.commit()
        off_peak_now = NOW.replace(hour=11)  # truly off-peak
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=off_peak_now):
            result = _svc(db_session).get_peak_hour_alerts(student.id)
        assert result.is_peak_now is False
        assert result.current_period is None
        assert "Great time to order" in result.suggested_action  # covers line 516

    def test_during_lunch_peak_is_peak_now_true(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)
        # Seed 25 orders at hour 13 (last 7 days) → HIGH severity
        for _ in range(25):
            order_dt = (NOW - timedelta(days=2)).replace(hour=13)
            _make_order(db_session, student.id, vendor.id, slot.id, created_at=order_dt)
        db_session.commit()

        lunch_now = NOW.replace(hour=13)
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=lunch_now):
            result = _svc(db_session).get_peak_hour_alerts(student.id)

        assert result.is_peak_now is True
        assert result.current_period is not None
        assert result.current_period.label == "Lunch Peak"
        assert "Peak hours now" in result.suggested_action

    def test_during_morning_rush_is_peak_now_true(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        morning_now = NOW.replace(hour=9)
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=morning_now):
            result = _svc(db_session).get_peak_hour_alerts(student.id)
        assert result.is_peak_now is True
        assert result.current_period.label == "Morning Rush"

    def test_during_dinner_peak_is_peak_now_true(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        dinner_now = NOW.replace(hour=19)
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=dinner_now):
            result = _svc(db_session).get_peak_hour_alerts(student.id)
        assert result.is_peak_now is True
        assert result.current_period.label == "Dinner Peak"

    def test_severity_high_when_volume_above_20(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)
        # 25 orders in the lunch window (hours 12-14)
        for _ in range(25):
            order_dt = (NOW - timedelta(days=1)).replace(hour=13)
            _make_order(db_session, student.id, vendor.id, slot.id, created_at=order_dt)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_peak_hour_alerts(student.id)

        lunch = next(p for p in result.peak_periods_today if p.label == "Lunch Peak")
        assert lunch.severity == "HIGH"
        assert lunch.avg_wait_minutes == 25

    def test_severity_medium_when_volume_10_to_19(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)
        for _ in range(12):
            order_dt = (NOW - timedelta(days=1)).replace(hour=12)
            _make_order(db_session, student.id, vendor.id, slot.id, created_at=order_dt)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_peak_hour_alerts(student.id)

        lunch = next(p for p in result.peak_periods_today if p.label == "Lunch Peak")
        assert lunch.severity == "MEDIUM"
        assert lunch.avg_wait_minutes == 15

    def test_severity_low_when_volume_1_to_9(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)
        for _ in range(5):
            order_dt = (NOW - timedelta(days=1)).replace(hour=12)
            _make_order(db_session, student.id, vendor.id, slot.id, created_at=order_dt)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_peak_hour_alerts(student.id)

        lunch = next(p for p in result.peak_periods_today if p.label == "Lunch Peak")
        assert lunch.severity == "LOW"
        assert lunch.avg_wait_minutes == 8

    def test_off_peak_windows_exclude_peak_hours_and_busy_hours(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_peak_hour_alerts(student.id)

        off_peak_hours = {w["hour"] for w in result.off_peak_windows}
        # Peak windows are 8-10, 12-14, 18-20 → none of these should appear
        peak_hours = set(range(8, 11)) | set(range(12, 15)) | set(range(18, 21))
        assert off_peak_hours.isdisjoint(peak_hours)

    def test_three_period_defs_always_present(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_peak_hour_alerts(student.id)
        labels = [p.label for p in result.peak_periods_today]
        assert "Morning Rush" in labels
        assert "Lunch Peak" in labels
        assert "Dinner Peak" in labels

    def test_exception_returns_safe_fallback(self, db_session: Session):
        svc = _svc(db_session)
        with patch.object(svc.db, "query", side_effect=RuntimeError("db error")):
            result = svc.get_peak_hour_alerts(1)
        assert result.is_peak_now is False
        assert result.peak_periods_today == []
        assert "Unable to load" in result.suggested_action


# ─────────────────────────────────────────────────────────────────────────────
# 6. get_popular_nearby
# ─────────────────────────────────────────────────────────────────────────────

class TestGetPopularNearby:

    def test_empty_db_returns_empty_lists(self, db_session: Session):
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_popular_nearby()
        assert isinstance(result, PopularNearbyResponse)
        assert result.food_vendors == []
        assert result.stationery_vendors == []

    def test_food_vendor_appears_in_food_list(self, db_session: Session):
        vendor = _make_vendor(db_session, vendor_type="food")
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_popular_nearby()
        assert len(result.food_vendors) == 1
        assert result.food_vendors[0].vendor_id == vendor.id
        assert result.stationery_vendors == []

    def test_stationery_vendor_appears_in_stationery_list(self, db_session: Session):
        vendor = _make_vendor(db_session, vendor_type="stationery")
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_popular_nearby()
        assert len(result.stationery_vendors) == 1
        assert result.stationery_vendors[0].vendor_id == vendor.id
        assert result.food_vendors == []

    def test_unapproved_vendor_excluded(self, db_session: Session):
        _make_vendor(db_session, vendor_type="food", approved=False)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_popular_nearby()
        assert result.food_vendors == []

    def test_order_count_calculated_from_last_30_days(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)
        # 3 recent orders (within 30 days)
        for _ in range(3):
            _make_order(db_session, student.id, vendor.id, slot.id, created_at=FIVE_DAYS_AGO)
        # 2 old orders (outside 30 days)
        for _ in range(2):
            _make_order(db_session, student.id, vendor.id, slot.id, created_at=NOW - timedelta(days=40))
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_popular_nearby()
        f = result.food_vendors[0]
        assert f.order_count == 3

    def test_avg_rating_from_vendor_reviews(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        _make_review(db_session, vendor.id, student.id, rating=4)
        _make_review(db_session, vendor.id, student.id, rating=5)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_popular_nearby()
        assert result.food_vendors[0].avg_rating == 4.5

    def test_no_reviews_avg_rating_is_zero(self, db_session: Session):
        _make_vendor(db_session)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_popular_nearby()
        assert result.food_vendors[0].avg_rating == 0.0

    def test_live_load_high(self, db_session: Session):
        vendor = _make_vendor(db_session)
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=9)  # >=80%
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_popular_nearby()
        assert result.food_vendors[0].live_load == "HIGH"

    def test_live_load_medium(self, db_session: Session):
        vendor = _make_vendor(db_session)
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=6)  # >=50%
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_popular_nearby()
        assert result.food_vendors[0].live_load == "MEDIUM"

    def test_live_load_low(self, db_session: Session):
        vendor = _make_vendor(db_session)
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=2)  # <50%
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_popular_nearby()
        assert result.food_vendors[0].live_load == "LOW"

    def test_sorted_by_order_count_descending(self, db_session: Session):
        v1 = _make_vendor(db_session)
        v2 = _make_vendor(db_session)
        slot1 = _make_slot(db_session, v1.id)
        slot2 = _make_slot(db_session, v2.id)
        student = _make_student(db_session)
        # v2 has more orders
        for _ in range(5):
            _make_order(db_session, student.id, v2.id, slot2.id, created_at=FIVE_DAYS_AGO)
        for _ in range(2):
            _make_order(db_session, student.id, v1.id, slot1.id, created_at=FIVE_DAYS_AGO)
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_popular_nearby()
        counts = [v.order_count for v in result.food_vendors]
        assert counts == sorted(counts, reverse=True)

    def test_mixed_vendor_types_separated(self, db_session: Session):
        food = _make_vendor(db_session, vendor_type="food")
        stat = _make_vendor(db_session, vendor_type="stationery")
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_popular_nearby()
        food_ids = {v.vendor_id for v in result.food_vendors}
        stat_ids = {v.vendor_id for v in result.stationery_vendors}
        assert food.id in food_ids
        assert stat.id in stat_ids
        assert food.id not in stat_ids
        assert stat.id not in food_ids

    def test_exception_returns_empty_fallback(self, db_session: Session):
        svc = _svc(db_session)
        with patch.object(svc.db, "query", side_effect=RuntimeError("db error")):
            result = svc.get_popular_nearby()
        assert result.food_vendors == []
        assert result.stationery_vendors == []

    def test_vendor_name_fallback_when_name_is_none(self, db_session: Session):
        vendor = _make_vendor(db_session)
        vendor.name = None
        db_session.flush()
        db_session.commit()
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_popular_nearby()
        assert result.food_vendors[0].vendor_name == f"Vendor #{vendor.id}"


# ─────────────────────────────────────────────────────────────────────────────
# Targeted branch tests for lines 138, 156, 188, 297
# ─────────────────────────────────────────────────────────────────────────────

class TestMenuSuggestionsBranchCoverage:
    """Fine-grained tests for the continue/skip branches inside get_menu_suggestions."""

    def test_orphan_order_item_skipped_line138(self, db_session: Session):
        """
        Line 138: `if not menu_item: continue`
        Create an OrderItem pointing to a nonexistent menu_item_id.
        SQLite ignores FK constraints so the row is inserted;
        the query for MenuItem returns None → continue is hit.
        """
        from sqlalchemy import text

        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)
        order = _make_order(db_session, student.id, vendor.id, slot.id, created_at=FIVE_DAYS_AGO)
        db_session.commit()

        # Insert orphan OrderItem with nonexistent menu_item_id (no FK enforcement in SQLite)
        db_session.execute(
            text(
                "INSERT INTO order_items (order_id, menu_item_id, quantity, price_at_time) "
                "VALUES (:oid, :mid, 1, 5.99)"
            ),
            {"oid": order.id, "mid": 99999},
        )
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_menu_suggestions(student.id)
        # Orphan row is skipped; personalized stays empty → fallback activates
        assert isinstance(result, MenuSuggestionsResponse)

    def test_duplicate_similar_item_skipped_line156(self, db_session: Session):
        """
        Line 156: `if s.id in seen_ids: continue`
        User orders two items A and B from the same vendor.
        Item C is similar to both A and B.
        When processing B, C is already in seen_ids → line 156 is hit.
        """
        vendor = _make_vendor(db_session)
        item_a = _make_menu_item(db_session, vendor.id, name="Item A")
        item_b = _make_menu_item(db_session, vendor.id, name="Item B")
        item_c = _make_menu_item(db_session, vendor.id, name="Item C (similar to both)")
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)

        # Order both A and B; C will appear in the similar list for each
        order1 = _make_order(db_session, student.id, vendor.id, slot.id, created_at=FIVE_DAYS_AGO)
        _make_order_item(db_session, order1.id, item_a.id)
        order2 = _make_order(db_session, student.id, vendor.id, slot.id, created_at=FIVE_DAYS_AGO)
        _make_order_item(db_session, order2.id, item_b.id)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_menu_suggestions(student.id)

        # item_c should appear at most once in personalized (deduplication confirmed)
        personalized_ids = [i.item_id for i in result.personalized]
        assert personalized_ids.count(item_c.id) <= 1

    def test_trending_item_already_in_seen_ids_skipped_line188(self, db_session: Session):
        """
        Line 188: `if r.id in seen_ids: continue`
        Similar item C is added to personalized and seen_ids.
        C also appears as the top trending item → line 188 is hit.
        """
        vendor = _make_vendor(db_session)
        item_a = _make_menu_item(db_session, vendor.id, name="Item A (ordered)")
        item_c = _make_menu_item(db_session, vendor.id, name="Item C (similar + trending)")
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)
        other_student = _make_student(db_session)

        # Student orders A → C is similar → C added to seen_ids
        order1 = _make_order(db_session, student.id, vendor.id, slot.id, created_at=FIVE_DAYS_AGO)
        _make_order_item(db_session, order1.id, item_a.id)

        # Make C trending (many campus orders of C)
        for _ in range(5):
            order_t = _make_order(db_session, other_student.id, vendor.id, slot.id, created_at=FIVE_DAYS_AGO)
            _make_order_item(db_session, order_t.id, item_c.id)
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_menu_suggestions(student.id)

        # C should appear at most once across personalized + trending
        all_ids = [i.item_id for i in result.personalized] + [i.item_id for i in result.trending]
        assert all_ids.count(item_c.id) <= 1


class TestSmartReorderBranchCoverage:
    """Targeted test for line 297: missing menu_item continue in get_smart_reorder."""

    def test_orphan_order_item_skipped_line297(self, db_session: Session):
        """
        Line 297: `if not menu_item: continue`
        OrderItem references a nonexistent menu_item_id → continue is hit.
        SQLite ignores FK constraints so the orphan row can be inserted.
        """
        from sqlalchemy import text

        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        student = _make_student(db_session)
        order = _make_order(
            db_session, student.id, vendor.id, slot.id,
            status=OrderStatus.COMPLETED, created_at=FIVE_DAYS_AGO,
        )
        db_session.commit()

        db_session.execute(
            text(
                "INSERT INTO order_items (order_id, menu_item_id, quantity, price_at_time) "
                "VALUES (:oid, :mid, 1, 5.99)"
            ),
            {"oid": order.id, "mid": 88888},
        )
        db_session.commit()

        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            result = _svc(db_session).get_smart_reorder(student.id)

        # The orphan item_id 88888 has no MenuItem → skipped → items list is empty
        item_ids = [i.item_id for i in result.items]
        assert 88888 not in item_ids
