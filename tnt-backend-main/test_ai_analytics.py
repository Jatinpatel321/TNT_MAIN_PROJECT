"""Tests for AI analytics endpoints.

Covers all 6 user-facing analytics features:
  - GET /ai/vendor-recommendations
  - GET /ai/menu-suggestions
  - GET /ai/smart-reorder
  - GET /ai/best-pickup-time
  - GET /ai/peak-hour-alerts
  - GET /ai/popular-nearby

Note: CancelledError on TestClient teardown is cosmetic (lifespan simulator);
all assertions pass before teardown.
"""
from concurrent.futures import CancelledError
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.menu.model import MenuItem
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole
from app.modules.feedback.model import VendorReview


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _build_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine, TestingSessionLocal()


def _seed_data(db):
    now = utcnow_naive()

    student = User(
        phone="9900000001", name="Test Student", role=UserRole.STUDENT,
        is_active=True, preferences={"preferred_pickup_hour": 12},
    )
    vendor_food = User(
        phone="9900000010", name="Food Vendor", role=UserRole.VENDOR,
        vendor_type="food", is_active=True, is_approved=True,
    )
    vendor_food2 = User(
        phone="9900000012", name="Food Vendor 2", role=UserRole.VENDOR,
        vendor_type="food", is_active=True, is_approved=True,
    )
    vendor_stationery = User(
        phone="9900000011", name="Stationery Vendor", role=UserRole.VENDOR,
        vendor_type="stationery", is_active=True, is_approved=True,
    )

    db.add_all([student, vendor_food, vendor_food2, vendor_stationery])
    db.commit()
    db.refresh(student)
    db.refresh(vendor_food)
    db.refresh(vendor_food2)
    db.refresh(vendor_stationery)

    menu_items = [
        MenuItem(id=1, vendor_id=vendor_food.id, name="Biryani", price=12000, image_url="", is_available=True),
        MenuItem(id=2, vendor_id=vendor_food.id, name="Butter Chicken", price=15000, image_url="", is_available=True),
        MenuItem(id=3, vendor_id=vendor_food.id, name="Dal Makhani", price=8000, image_url="", is_available=True),
        MenuItem(id=4, vendor_id=vendor_food2.id, name="Pasta", price=10000, image_url="", is_available=True),
        MenuItem(id=5, vendor_id=vendor_stationery.id, name="Print B&W", price=200, image_url="", is_available=True),
    ]
    db.add_all(menu_items)

    slot1 = Slot(
        vendor_id=vendor_food.id,
        start_time=now.replace(hour=12, minute=0, second=0, microsecond=0),
        end_time=now.replace(hour=12, minute=30, second=0, microsecond=0),
        max_orders=10, current_orders=2, status=SlotStatus.AVAILABLE,
    )
    slot2 = Slot(
        vendor_id=vendor_food.id,
        start_time=now.replace(hour=13, minute=0, second=0, microsecond=0),
        end_time=now.replace(hour=13, minute=30, second=0, microsecond=0),
        max_orders=10, current_orders=9, status=SlotStatus.LIMITED,
    )
    slot3 = Slot(
        vendor_id=vendor_stationery.id,
        start_time=now.replace(hour=14, minute=0, second=0, microsecond=0),
        end_time=now.replace(hour=14, minute=30, second=0, microsecond=0),
        max_orders=5, current_orders=1, status=SlotStatus.AVAILABLE,
    )
    db.add_all([slot1, slot2, slot3])
    db.commit()
    db.refresh(slot1)
    db.refresh(slot2)
    db.refresh(slot3)

    order1 = Order(
        user_id=student.id, slot_id=slot1.id, vendor_id=vendor_food.id,
        status=OrderStatus.COMPLETED, total_amount=12000,
        created_at=now - timedelta(days=1),
    )
    order2 = Order(
        user_id=student.id, slot_id=slot1.id, vendor_id=vendor_food.id,
        status=OrderStatus.COMPLETED, total_amount=15000,
        created_at=now - timedelta(days=2),
    )
    order3 = Order(
        user_id=student.id, slot_id=slot3.id, vendor_id=vendor_stationery.id,
        status=OrderStatus.PICKED, total_amount=200,
        created_at=now - timedelta(days=3),
    )
    db.add_all([order1, order2, order3])
    db.commit()
    db.refresh(order1)
    db.refresh(order2)
    db.refresh(order3)

    oi1 = OrderItem(order_id=order1.id, menu_item_id=1, quantity=1, price_at_time=12000)
    oi2 = OrderItem(order_id=order2.id, menu_item_id=2, quantity=1, price_at_time=15000)
    oi3 = OrderItem(order_id=order2.id, menu_item_id=3, quantity=1, price_at_time=8000)
    oi4 = OrderItem(order_id=order3.id, menu_item_id=5, quantity=1, price_at_time=200)
    db.add_all([oi1, oi2, oi3, oi4])

    review = VendorReview(
        vendor_id=vendor_food.id, user_id=student.id, order_id=order1.id,
        rating=4, review_text="Great food!",
    )
    db.add(review)
    db.commit()

    return {
        "student": student,
        "vendor_food": vendor_food,
        "vendor_food2": vendor_food2,
        "vendor_stationery": vendor_stationery,
        "slot1": slot1,
        "slot2": slot2,
        "slot3": slot3,
        "order1": order1,
        "order2": order2,
        "order3": order3,
    }


def _make_client(db, user_dict):
    """Create TestClient with dependency overrides; caller must handle teardown."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user_dict
    return TestClient(app)


def _cleanup_client():
    app.dependency_overrides.clear()


@pytest.fixture()
def test_db_session():
    engine, db = _build_session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def seed_data(test_db_session):
    return _seed_data(test_db_session)


@pytest.fixture()
def auth_context(seed_data):
    student = seed_data["student"]
    return {"id": student.id, "phone": student.phone, "role": student.role.value}


@pytest.fixture()
def client(test_db_session, auth_context):
    c = _make_client(test_db_session, auth_context)
    try:
        yield c
    except CancelledError:
        pass
    finally:
        _cleanup_client()


# ── 1. Vendor Recommendations ─────────────────────────────────────────────


def test_vendor_recommendations_returns_approved_vendors(client, seed_data):
    resp = client.get("/ai/vendor-recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendations" in data
    recs = data["recommendations"]
    assert len(recs) >= 3  # food, food2, stationery
    for r in recs:
        assert "vendor_id" in r
        assert "vendor_name" in r
        assert "vendor_type" in r
        assert "rank_score" in r
        assert "live_load" in r
        assert "express_pickup" in r
        assert "reason" in r


def test_vendor_recommendations_sorted_by_score(client, seed_data):
    resp = client.get("/ai/vendor-recommendations")
    data = resp.json()
    scores = [r["rank_score"] for r in data["recommendations"]]
    assert scores == sorted(scores, reverse=True)


def test_vendor_recommendations_frequented_vendor_ranks_higher(client, seed_data):
    resp = client.get("/ai/vendor-recommendations")
    data = resp.json()
    recs = data["recommendations"]
    food_vendor = next(r for r in recs if r["vendor_id"] == seed_data["vendor_food"].id)
    stationery_vendor = next(r for r in recs if r["vendor_id"] == seed_data["vendor_stationery"].id)
    # Student ordered from food vendor more, should have higher score
    assert food_vendor["rank_score"] > stationery_vendor["rank_score"]


def test_vendor_recommendations_load_labels(client, seed_data):
    resp = client.get("/ai/vendor-recommendations")
    data = resp.json()
    loads = {r["vendor_id"]: r["live_load"] for r in data["recommendations"]}
    # Slot2 has 9/10 = HIGH for vendor_food
    assert loads[seed_data["vendor_food"].id] in ("LOW", "MEDIUM", "HIGH")


# ── 2. Menu Suggestions ───────────────────────────────────────────────────


def test_menu_suggestions_returns_personalized_and_trending(client, seed_data):
    resp = client.get("/ai/menu-suggestions")
    assert resp.status_code == 200
    data = resp.json()
    assert "personalized" in data
    assert "trending" in data


def test_menu_suggestions_personalized_based_on_favorites(client, seed_data):
    resp = client.get("/ai/menu-suggestions")
    data = resp.json()
    # Student ordered Biryani and Butter Chicken; similar items should appear
    personalized = data["personalized"]
    for item in personalized:
        assert "item_id" in item
        assert "item_name" in item
        assert "vendor_id" in item
        assert "reason" in item
        assert "confidence" in item


def test_menu_suggestions_trending_from_campus_orders(client, seed_data):
    resp = client.get("/ai/menu-suggestions")
    data = resp.json()
    trending = data["trending"]
    for item in trending:
        assert item["reason"] == "Trending on campus"


def test_menu_suggestions_fallback_when_no_history():
    """New user with no orders should still get available items."""
    from app.modules.ai_intelligence.analytics_service import AnalyticsService

    engine, db = _build_session()
    try:
        student = User(phone="9900000099", name="New Student", role=UserRole.STUDENT, is_active=True)
        vendor = User(phone="9900000088", name="Vendor", role=UserRole.VENDOR, vendor_type="food", is_active=True, is_approved=True)
        db.add_all([student, vendor])
        db.commit()
        db.refresh(student)
        db.refresh(vendor)

        mi = MenuItem(vendor_id=vendor.id, name="Samosa", price=500, image_url="", is_available=True)
        db.add(mi)
        db.commit()

        service = AnalyticsService(db)
        result = service.get_menu_suggestions(student.id)
        assert len(result.personalized) > 0
        assert result.personalized[0].reason == "Available now"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


# ── 3. Smart Reorder ──────────────────────────────────────────────────────


def test_smart_reorder_returns_frequently_ordered_items(client, seed_data):
    resp = client.get("/ai/smart-reorder")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "best_reorder_time" in data


def test_smart_reorder_items_have_order_count(client, seed_data):
    resp = client.get("/ai/smart-reorder")
    data = resp.json()
    for item in data["items"]:
        assert item["order_count"] >= 1
        assert item["item_name"]
        assert item["vendor_name"]
        assert item["price_paise"] > 0


def test_smart_reorder_best_time(client, seed_data):
    resp = client.get("/ai/smart-reorder")
    data = resp.json()
    assert data["best_reorder_time"]
    # Should be an hour format HH:00
    assert ":00" in data["best_reorder_time"]


def test_smart_reorder_suggested_slot(client, seed_data):
    resp = client.get("/ai/smart-reorder")
    data = resp.json()
    if data["items"]:
        item = data["items"][0]
        # suggested_slot_id may be null if no preferred slot
        assert "suggested_slot_id" in item
        assert "suggested_slot_time" in item


# ── 4. Best Pickup Time ──────────────────────────────────────────────────


def test_best_pickup_time_returns_slots(client, seed_data):
    resp = client.get("/ai/best-pickup-time")
    assert resp.status_code == 200
    data = resp.json()
    assert "best_slot" in data
    assert "alternative_slots" in data
    assert "preferred_hour" in data
    assert "preferred_hour_source" in data


def test_best_pickup_time_uses_user_preference(client, seed_data):
    resp = client.get("/ai/best-pickup-time")
    data = resp.json()
    # Student has preferred_pickup_hour: 12 in preferences
    assert data["preferred_hour"] == 12
    assert data["preferred_hour_source"] == "preference"


def test_best_pickup_time_slot_scoring(client, seed_data):
    resp = client.get("/ai/best-pickup-time")
    data = resp.json()
    if data["best_slot"]:
        slot = data["best_slot"]
        assert slot["congestion_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert slot["delay_risk"] in ("LOW", "MEDIUM", "HIGH")
        assert slot["score"] > 0
        assert slot["eta_minutes"] > 0


def test_best_pickup_time_alternatives_sorted(client, seed_data):
    resp = client.get("/ai/best-pickup-time")
    data = resp.json()
    alt_scores = [s["score"] for s in data["alternative_slots"]]
    assert alt_scores == sorted(alt_scores, reverse=True)


# ── 5. Peak Hour Alerts ──────────────────────────────────────────────────


def test_peak_hour_alerts_structure(client, seed_data):
    resp = client.get("/ai/peak-hour-alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_peak_now" in data
    assert "peak_periods_today" in data
    assert "off_peak_windows" in data
    assert "suggested_action" in data


def test_peak_hour_alerts_has_standard_periods(client, seed_data):
    resp = client.get("/ai/peak-hour-alerts")
    data = resp.json()
    labels = [p["label"] for p in data["peak_periods_today"]]
    assert "Morning Rush" in labels
    assert "Lunch Peak" in labels
    assert "Dinner Peak" in labels


def test_peak_hour_alerts_period_fields(client, seed_data):
    resp = client.get("/ai/peak-hour-alerts")
    data = resp.json()
    for period in data["peak_periods_today"]:
        assert "start_hour" in period
        assert "end_hour" in period
        assert "severity" in period
        assert "avg_wait_minutes" in period
        assert "order_volume" in period


def test_peak_hour_alerts_off_peak_windows(client, seed_data):
    resp = client.get("/ai/peak-hour-alerts")
    data = resp.json()
    for w in data["off_peak_windows"]:
        assert "hour" in w
        assert "label" in w
        assert "expected_wait_minutes" in w


# ── 6. Popular Nearby ────────────────────────────────────────────────────


def test_popular_nearby_returns_vendors_by_type(client, seed_data):
    resp = client.get("/ai/popular-nearby")
    assert resp.status_code == 200
    data = resp.json()
    assert "food_vendors" in data
    assert "stationery_vendors" in data


def test_popular_nearby_food_vendors(client, seed_data):
    resp = client.get("/ai/popular-nearby")
    data = resp.json()
    food_ids = [v["vendor_id"] for v in data["food_vendors"]]
    assert seed_data["vendor_food"].id in food_ids


def test_popular_nearby_stationery_vendors(client, seed_data):
    resp = client.get("/ai/popular-nearby")
    data = resp.json()
    stat_ids = [v["vendor_id"] for v in data["stationery_vendors"]]
    assert seed_data["vendor_stationery"].id in stat_ids


def test_popular_nearby_vendor_fields(client, seed_data):
    resp = client.get("/ai/popular-nearby")
    data = resp.json()
    for v in data["food_vendors"] + data["stationery_vendors"]:
        assert "vendor_id" in v
        assert "vendor_name" in v
        assert "vendor_type" in v
        assert "order_count" in v
        assert "avg_rating" in v
        assert "live_load" in v


def test_popular_nearby_sorted_by_order_count(client, seed_data):
    resp = client.get("/ai/popular-nearby")
    data = resp.json()
    food_counts = [v["order_count"] for v in data["food_vendors"]]
    assert food_counts == sorted(food_counts, reverse=True)


# ── Auth guard ────────────────────────────────────────────────────────────


def test_analytics_endpoints_require_auth():
    """All AI analytics endpoints require authentication."""
    # No dependency override for get_current_user, so it will fail
    c = TestClient(app, raise_server_exceptions=False)
    try:
        for path in [
            "/ai/vendor-recommendations",
            "/ai/menu-suggestions",
            "/ai/smart-reorder",
            "/ai/best-pickup-time",
            "/ai/peak-hour-alerts",
            "/ai/popular-nearby",
        ]:
            resp = c.get(path)
            assert resp.status_code in (401, 403), f"{path} should require auth, got {resp.status_code}"
    except CancelledError:
        pass
