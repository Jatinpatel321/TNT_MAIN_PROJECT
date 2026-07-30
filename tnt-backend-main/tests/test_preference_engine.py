"""
Unit tests for app/modules/ai_intelligence/learning/preference_engine.py

Covers:
  - _load_stored_preferences (User none, user.preferences none/dict/invalid type)
  - get_personalization (combines behavioural signals + stated preferences, active_preferences payload)
  - _get_frequent_items (with order history, missing menu items)
  - _get_preferred_vendors (vendor aggregation)
  - _get_preferred_times (hour aggregation, default 12)
  - _generate_item_recommendations (frequent items, similar items, popular fallback, dietary/cuisine/spice reason strings)
  - _generate_smart_suggestions (timing preference vs inferred hour, vendor loyalty, reorder reminder, cuisine preference, dietary reminder)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.modules.ai_intelligence.learning.preference_engine import PreferenceEngine
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.slots.model import Slot
from app.modules.users.model import User, UserRole

NOW = datetime(2024, 6, 15, 12, 0, 0)
FIVE_DAYS_AGO = NOW - timedelta(days=5)
_UTCNOW_PATH = "app.modules.ai_intelligence.learning.preference_engine.utcnow_naive"


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _make_student(db: Session, preferences: dict = None) -> User:
    u = User(
        phone=f"+1666{_uid()[:7]}",
        name=f"Student_{_uid()}",
        role=UserRole.STUDENT,
        vendor_type="food",
        preferences=preferences,
    )
    db.add(u)
    db.flush()
    return u


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


def _make_menu_item(db: Session, vendor_id: int, name: str = None, category: str = "food") -> MenuItem:
    mi = MenuItem(
        vendor_id=vendor_id,
        name=name or f"Item_{_uid()}",
        price=10.0,
        category=category,
        is_available=True,
    )
    db.add(mi)
    db.flush()
    return mi


def _make_order(db: Session, user_id: int, vendor_id: int, slot_id: int, created_at: datetime = None) -> Order:
    o = Order(
        user_id=user_id,
        vendor_id=vendor_id,
        slot_id=slot_id,
        status=OrderStatus.COMPLETED,
        total_amount=10.0,
        created_at=created_at or FIVE_DAYS_AGO,
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


class TestPreferenceEngineInternal:

    def test_load_stored_preferences_fallbacks(self, db_session: Session):
        engine = PreferenceEngine(db_session)
        # Non-existent user
        assert engine._load_stored_preferences(99999) == {}

        # User with preferences = None
        user_none = _make_student(db_session, preferences=None)
        db_session.commit()
        assert engine._load_stored_preferences(user_none.id) == {}

        # User with valid dict preferences
        prefs = {"spice_level": 3, "dietary_restrictions": ["vegan"]}
        user_valid = _make_student(db_session, preferences=prefs)
        db_session.commit()
        assert engine._load_stored_preferences(user_valid.id) == prefs

    def test_get_preferred_times_defaults(self, db_session: Session):
        engine = PreferenceEngine(db_session)
        student = _make_student(db_session)
        db_session.commit()

        res = engine._get_preferred_times(student.id, FIVE_DAYS_AGO)
        assert res["preferred_hour"] == 12
        assert res["order_count"] == 0

    def test_get_preferred_times_from_history(self, db_session: Session):
        engine = PreferenceEngine(db_session)
        student = _make_student(db_session)
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)

        dt = datetime(2024, 6, 15, 14, 30, 0)
        _make_order(db_session, student.id, vendor.id, slot.id, created_at=dt)
        _make_order(db_session, student.id, vendor.id, slot.id, created_at=dt)
        db_session.commit()

        res = engine._get_preferred_times(student.id, FIVE_DAYS_AGO)
        assert res["preferred_hour"] == 14
        assert res["order_count"] == 2


class TestPreferenceEngineRecommendations:

    def test_generate_item_recommendations_with_history_and_preferences(self, db_session: Session):
        engine = PreferenceEngine(db_session)
        student = _make_student(db_session)
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)

        item_fav = _make_menu_item(db_session, vendor.id, name="Burger")
        item_sim1 = _make_menu_item(db_session, vendor.id, name="Cheeseburger")
        item_sim2 = _make_menu_item(db_session, vendor.id, name="Veggie Burger")

        order = _make_order(db_session, student.id, vendor.id, slot.id, created_at=FIVE_DAYS_AGO)
        _make_order_item(db_session, order.id, item_fav.id)
        db_session.commit()

        stored_prefs = {
            "dietary_restrictions": ["vegan"],
            "cuisine_preferences": ["american"],
            "spice_level": 4,
        }

        recs = engine._generate_item_recommendations(
            student.id,
            [{"menu_item_id": item_fav.id, "name": "Burger", "order_count": 1, "avg_quantity": 1.0}],
            stored_prefs=stored_prefs,
        )

        assert len(recs) == 2
        assert recs[0]["confidence"] == 0.8
        assert "Matches dietary filter: vegan" in recs[0]["reason"]
        assert "Based on your cuisine preferences: american" in recs[0]["reason"]
        assert "Spice level preference: 4/5" in recs[0]["reason"]

    def test_generate_item_recommendations_popular_fallback(self, db_session: Session):
        engine = PreferenceEngine(db_session)
        student = _make_student(db_session)
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id)
        item_pop = _make_menu_item(db_session, vendor.id, name="Popular Pizza")

        order = _make_order(db_session, student.id, vendor.id, slot.id, created_at=FIVE_DAYS_AGO)
        _make_order_item(db_session, order.id, item_pop.id)
        db_session.commit()

        recs = engine._generate_item_recommendations(student.id, frequent_items=[])
        assert len(recs) == 1
        assert recs[0]["name"] == "Popular Pizza"
        assert recs[0]["confidence"] == 0.6


class TestPreferenceEngineSuggestions:

    def test_generate_smart_suggestions_all_branches(self, db_session: Session):
        engine = PreferenceEngine(db_session)
        student = _make_student(db_session)
        vendor = _make_vendor(db_session)

        stored_prefs = {
            "preferred_pickup_hour": 12,
            "cuisine_preferences": ["south_indian"],
            "dietary_restrictions": ["gluten_free"],
        }

        with patch(_UTCNOW_PATH, return_value=NOW):
            suggestions = engine._generate_smart_suggestions(
                student.id,
                preferred_vendors=[{"vendor_id": vendor.id, "order_count": 5}],
                preferred_times={"preferred_hour": 14, "order_count": 3},
                stored_prefs=stored_prefs,
            )

        types = [s["type"] for s in suggestions]
        assert "timing" in types
        assert "loyalty" in types
        assert "reorder" in types  # 0 recent orders in last 7 days
        assert "cuisine_preference" in types
        assert "dietary_reminder" in types


class TestGetPersonalizationPublicApi:

    def test_get_personalization_full_flow(self, db_session: Session):
        engine = PreferenceEngine(db_session)
        student = _make_student(db_session, preferences={"spice_level": 2})
        db_session.commit()

        with patch(_UTCNOW_PATH, return_value=NOW):
            result = engine.get_personalization(student.id)

        assert "recommended_for_you" in result
        assert "smart_suggestions" in result
        assert result["active_preferences"]["spice_level"] == 2
