"""Comprehensive tests for the enhanced Feedback module.

Covers:
  - Submit feedback (PICKED + COMPLETED orders allowed)
  - Duplicate feedback prevention
  - Order status validation (non-eligible orders rejected)
  - My feedback list
  - Get order feedback
  - Submit vendor review
  - List vendor reviews (anonymous handling)
  - Vendor feedback summary with rating distribution
  - Access control for vendor summary
"""
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
from app.modules.orders.model import Order, OrderStatus
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture()
def test_db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def seed_data(test_db_session):
    student = User(phone="8800000001", name="Test Student", role=UserRole.STUDENT, is_active=True)
    vendor = User(phone="8800000010", name="Test Vendor", role=UserRole.VENDOR, is_active=True, is_approved=True)
    other_vendor = User(phone="8800000002", name="Other Vendor", role=UserRole.VENDOR, is_active=True, is_approved=True)
    admin = User(phone="8800000020", name="Admin", role=UserRole.ADMIN, is_active=True)

    test_db_session.add_all([student, vendor, other_vendor, admin])
    test_db_session.commit()
    test_db_session.refresh(student)
    test_db_session.refresh(vendor)
    test_db_session.refresh(other_vendor)
    test_db_session.refresh(admin)

    slot = Slot(
        vendor_id=vendor.id,
        start_time=utcnow_naive() + timedelta(hours=1),
        end_time=utcnow_naive() + timedelta(hours=2),
        max_orders=10,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    test_db_session.add(slot)
    test_db_session.commit()
    test_db_session.refresh(slot)

    completed_order = Order(
        user_id=student.id, slot_id=slot.id, vendor_id=vendor.id,
        status=OrderStatus.COMPLETED, total_amount=100,
    )
    picked_order = Order(
        user_id=student.id, slot_id=slot.id, vendor_id=vendor.id,
        status=OrderStatus.PICKED, total_amount=200,
    )
    pending_order = Order(
        user_id=student.id, slot_id=slot.id, vendor_id=vendor.id,
        status=OrderStatus.PENDING, total_amount=50,
    )
    test_db_session.add_all([completed_order, picked_order, pending_order])
    test_db_session.commit()
    test_db_session.refresh(completed_order)
    test_db_session.refresh(picked_order)
    test_db_session.refresh(pending_order)

    return {
        "student": student,
        "vendor": vendor,
        "other_vendor": other_vendor,
        "admin": admin,
        "completed_order": completed_order,
        "picked_order": picked_order,
        "pending_order": pending_order,
    }


@pytest.fixture()
def auth_context(seed_data):
    student = seed_data["student"]
    return {"id": student.id, "phone": student.phone, "role": student.role.value}


@pytest.fixture()
def client(test_db_session, auth_context):
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    def override_get_current_user():
        return auth_context

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_submit_feedback_completed_order(client, seed_data):
    order = seed_data["completed_order"]
    resp = client.post(
        f"/feedback/orders/{order.id}",
        json={"quality_rating": 5, "time_rating": 4, "behavior_rating": 5, "comment": "Great!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["quality_rating"] == 5
    assert data["overall_rating"] == 5  # round((5+4+5)/3) = 5
    assert data["comment"] == "Great!"


def test_submit_feedback_picked_order(client, seed_data):
    order = seed_data["picked_order"]
    resp = client.post(
        f"/feedback/orders/{order.id}",
        json={"quality_rating": 4, "time_rating": 3, "behavior_rating": 4},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_rating"] == 4  # round((4+3+4)/3) = 4


def test_submit_feedback_with_explicit_overall(client, seed_data):
    order = seed_data["completed_order"]
    resp = client.post(
        f"/feedback/orders/{order.id}",
        json={"quality_rating": 5, "time_rating": 5, "behavior_rating": 5, "overall_rating": 4},
    )
    assert resp.status_code == 200
    assert resp.json()["overall_rating"] == 4


def test_submit_feedback_pending_order_rejected(client, seed_data):
    order = seed_data["pending_order"]
    resp = client.post(
        f"/feedback/orders/{order.id}",
        json={"quality_rating": 3, "time_rating": 3, "behavior_rating": 3},
    )
    assert resp.status_code == 400
    assert "picked or completed" in resp.json()["detail"].lower()


def test_duplicate_feedback_rejected(client, seed_data):
    order = seed_data["completed_order"]
    client.post(
        f"/feedback/orders/{order.id}",
        json={"quality_rating": 5, "time_rating": 4, "behavior_rating": 5},
    )
    dup = client.post(
        f"/feedback/orders/{order.id}",
        json={"quality_rating": 1, "time_rating": 1, "behavior_rating": 1},
    )
    assert dup.status_code == 400
    assert "already submitted" in dup.json()["detail"].lower()


def test_my_feedback_list(client, seed_data):
    completed = seed_data["completed_order"]
    picked = seed_data["picked_order"]
    client.post(f"/feedback/orders/{completed.id}", json={"quality_rating": 5, "time_rating": 4, "behavior_rating": 5})
    client.post(f"/feedback/orders/{picked.id}", json={"quality_rating": 4, "time_rating": 3, "behavior_rating": 4})

    resp = client.get("/feedback/me")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["overall_rating"] is not None


def test_get_order_feedback(client, seed_data):
    order = seed_data["completed_order"]
    client.post(f"/feedback/orders/{order.id}", json={"quality_rating": 5, "time_rating": 4, "behavior_rating": 5})

    resp = client.get(f"/feedback/orders/{order.id}")
    assert resp.status_code == 200
    assert resp.json()["quality_rating"] == 5


def test_get_order_feedback_not_found(client, seed_data):
    order = seed_data["pending_order"]
    resp = client.get(f"/feedback/orders/{order.id}")
    assert resp.status_code == 404


def test_submit_vendor_review(client, seed_data, auth_context):
    vendor = seed_data["vendor"]
    order = seed_data["completed_order"]

    resp = client.post(
        f"/feedback/vendors/{vendor.id}/reviews",
        json={"rating": 5, "title": "Great vendor", "review_text": "Excellent service!", "order_id": order.id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rating"] == 5
    assert data["title"] == "Great vendor"
    assert data["reviewer_name"] == "Test Student"
    assert data["is_anonymous"] is False


def test_submit_vendor_review_anonymous(client, seed_data, auth_context):
    vendor = seed_data["vendor"]

    resp = client.post(
        f"/feedback/vendors/{vendor.id}/reviews",
        json={"rating": 4, "review_text": "Good but could be better", "is_anonymous": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_anonymous"] is True
    assert data["reviewer_name"] is None


def test_list_vendor_reviews(client, seed_data, auth_context):
    vendor = seed_data["vendor"]
    client.post(
        f"/feedback/vendors/{vendor.id}/reviews",
        json={"rating": 5, "title": "Review 1", "is_anonymous": False},
    )
    client.post(
        f"/feedback/vendors/{vendor.id}/reviews",
        json={"rating": 3, "title": "Review 2", "is_anonymous": True},
    )

    resp = client.get(f"/feedback/vendors/{vendor.id}/reviews")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # First review has name, second is anonymous
    names = [r["reviewer_name"] for r in data]
    assert "Test Student" in names
    assert None in names


def test_vendor_feedback_summary(client, seed_data, auth_context):
    vendor = seed_data["vendor"]
    completed = seed_data["completed_order"]
    picked = seed_data["picked_order"]

    client.post(f"/feedback/orders/{completed.id}", json={"quality_rating": 5, "time_rating": 4, "behavior_rating": 5})
    client.post(f"/feedback/orders/{picked.id}", json={"quality_rating": 3, "time_rating": 3, "behavior_rating": 3})

    resp = client.get(f"/feedback/vendors/{vendor.id}/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_reviews"] == 2
    assert data["avg_quality_rating"] == 4.0
    assert data["avg_overall_rating"] > 0
    assert isinstance(data["rating_distribution"], dict)


def test_vendor_summary_not_found_vendor(client, seed_data, auth_context):
    resp = client.get("/feedback/vendors/99999/summary")
    assert resp.status_code == 404
