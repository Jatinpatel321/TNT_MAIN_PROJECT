"""
Tests for admin-specific endpoints:
  GET  /admin/vendors                       – list all vendors
  POST /admin/vendors/{id}/approve          – approve a vendor
  POST /admin/vendors/{id}/reject           – reject a vendor
  POST /admin/announce                      – send global announcement to all users
  GET  /admin/analytics                     – comprehensive analytics dashboard
"""
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.notifications.model import Notification
from app.modules.orders.model import Order, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def seed_data(test_db_session):
    admin = User(phone="8900000001", name="Admin", role=UserRole.ADMIN, is_active=True)
    student = User(phone="8900000002", name="Student", role=UserRole.STUDENT, is_active=True)
    approved_vendor = User(
        phone="8900000003",
        name="ApprovedVendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
        vendor_type="food",
    )
    pending_vendor = User(
        phone="8900000004",
        name="PendingVendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=False,
        vendor_type="food",
    )
    test_db_session.add_all([admin, student, approved_vendor, pending_vendor])
    test_db_session.commit()
    for u in (admin, student, approved_vendor, pending_vendor):
        test_db_session.refresh(u)

    # Seed a slot + order + payment for analytics
    slot = Slot(
        vendor_id=approved_vendor.id,
        start_time=utcnow_naive() - timedelta(hours=2),
        end_time=utcnow_naive() - timedelta(hours=1),
        max_orders=10,
        current_orders=1,
        status=SlotStatus.AVAILABLE,
    )
    test_db_session.add(slot)
    test_db_session.commit()
    test_db_session.refresh(slot)

    order = Order(
        user_id=student.id,
        slot_id=slot.id,
        vendor_id=approved_vendor.id,
        status=OrderStatus.CONFIRMED,
        total_amount=15000,
    )
    test_db_session.add(order)
    test_db_session.commit()
    test_db_session.refresh(order)

    payment = Payment(
        order_id=order.id,
        amount=15000,
        status=PaymentStatus.SUCCESS,
    )
    test_db_session.add(payment)
    test_db_session.commit()
    test_db_session.refresh(payment)

    return {
        "admin": admin,
        "student": student,
        "approved_vendor": approved_vendor,
        "pending_vendor": pending_vendor,
        "order": order,
        "payment": payment,
    }


def _make_client(db_session, user: User) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: {
        "id": user.id,
        "phone": user.phone,
        "role": user.role.value,
    }
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# GET /admin/vendors
# ---------------------------------------------------------------------------


def test_admin_can_list_vendors(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/admin/vendors")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_vendors_includes_approved_vendor(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/admin/vendors")
    app.dependency_overrides.clear()

    ids = [v["id"] for v in resp.json()]
    assert seed_data["approved_vendor"].id in ids


def test_list_vendors_includes_pending_vendor(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/admin/vendors")
    app.dependency_overrides.clear()

    ids = [v["id"] for v in resp.json()]
    assert seed_data["pending_vendor"].id in ids


def test_list_vendors_excludes_students(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/admin/vendors")
    app.dependency_overrides.clear()

    ids = [v["id"] for v in resp.json()]
    assert seed_data["student"].id not in ids


def test_student_cannot_list_vendors(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["student"])
    resp = client.get("/admin/vendors")
    app.dependency_overrides.clear()

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /admin/vendors/{id}/approve
# ---------------------------------------------------------------------------


def test_admin_can_approve_pending_vendor(test_db_session, seed_data):
    vendor_id = seed_data["pending_vendor"].id
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.post(f"/admin/vendors/{vendor_id}/approve")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["vendor_id"] == vendor_id


def test_approve_vendor_sets_is_approved_true(test_db_session, seed_data):
    vendor_id = seed_data["pending_vendor"].id
    client = _make_client(test_db_session, seed_data["admin"])
    client.post(f"/admin/vendors/{vendor_id}/approve")
    app.dependency_overrides.clear()

    test_db_session.refresh(seed_data["pending_vendor"])
    assert seed_data["pending_vendor"].is_approved is True


def test_approve_vendor_sets_is_active_true(test_db_session, seed_data):
    vendor = seed_data["pending_vendor"]
    vendor.is_active = False
    test_db_session.commit()

    client = _make_client(test_db_session, seed_data["admin"])
    client.post(f"/admin/vendors/{vendor.id}/approve")
    app.dependency_overrides.clear()

    test_db_session.refresh(vendor)
    assert vendor.is_active is True


def test_approve_nonexistent_vendor_returns_404(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.post("/admin/vendors/99999/approve")
    app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_approve_student_returns_404(test_db_session, seed_data):
    # Students are not vendors — should return 404
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.post(f"/admin/vendors/{seed_data['student'].id}/approve")
    app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_non_admin_cannot_approve_vendor(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["student"])
    resp = client.post(f"/admin/vendors/{seed_data['pending_vendor'].id}/approve")
    app.dependency_overrides.clear()

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /admin/vendors/{id}/reject
# ---------------------------------------------------------------------------


def test_admin_can_reject_vendor(test_db_session, seed_data):
    vendor_id = seed_data["approved_vendor"].id
    with patch("app.modules.notifications.service.send_sms"):
        client = _make_client(test_db_session, seed_data["admin"])
        resp = client.post(f"/admin/vendors/{vendor_id}/reject")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["vendor_id"] == vendor_id


def test_reject_vendor_sets_is_approved_false(test_db_session, seed_data):
    vendor = seed_data["approved_vendor"]
    with patch("app.modules.notifications.service.send_sms"):
        client = _make_client(test_db_session, seed_data["admin"])
        client.post(f"/admin/vendors/{vendor.id}/reject")
    app.dependency_overrides.clear()

    test_db_session.refresh(vendor)
    assert vendor.is_approved is False


def test_reject_vendor_sets_is_active_false(test_db_session, seed_data):
    vendor = seed_data["approved_vendor"]
    with patch("app.modules.notifications.service.send_sms"):
        client = _make_client(test_db_session, seed_data["admin"])
        client.post(f"/admin/vendors/{vendor.id}/reject")
    app.dependency_overrides.clear()

    test_db_session.refresh(vendor)
    assert vendor.is_active is False


def test_reject_vendor_creates_notification(test_db_session, seed_data):
    vendor = seed_data["approved_vendor"]
    with patch("app.modules.notifications.service.send_sms"):
        client = _make_client(test_db_session, seed_data["admin"])
        client.post(f"/admin/vendors/{vendor.id}/reject")
    app.dependency_overrides.clear()

    notification = (
        test_db_session.query(Notification)
        .filter(Notification.user_id == vendor.id)
        .first()
    )
    assert notification is not None
    assert "rejected" in notification.message.lower() or "rejected" in notification.title.lower()


def test_reject_nonexistent_vendor_returns_404(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.post("/admin/vendors/99999/reject")
    app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_non_admin_cannot_reject_vendor(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["student"])
    resp = client.post(f"/admin/vendors/{seed_data['approved_vendor'].id}/reject")
    app.dependency_overrides.clear()

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /admin/announce
# ---------------------------------------------------------------------------


def test_admin_can_send_announcement(test_db_session, seed_data):
    with patch("app.modules.notifications.service.send_sms"):
        client = _make_client(test_db_session, seed_data["admin"])
        resp = client.post("/admin/announce", params={"message": "System maintenance at midnight"})
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert "sent" in resp.json().get("message", "").lower()


def test_announce_creates_notification_for_every_user(test_db_session, seed_data):
    user_count = test_db_session.query(User).count()
    with patch("app.modules.notifications.service.send_sms"):
        client = _make_client(test_db_session, seed_data["admin"])
        client.post("/admin/announce", params={"message": "Hello everyone!"})
    app.dependency_overrides.clear()

    notifications = (
        test_db_session.query(Notification)
        .filter(Notification.title == "Admin Announcement")
        .all()
    )
    assert len(notifications) == user_count


def test_announce_notification_contains_message(test_db_session, seed_data):
    with patch("app.modules.notifications.service.send_sms"):
        client = _make_client(test_db_session, seed_data["admin"])
        client.post("/admin/announce", params={"message": "UniqueText42"})
    app.dependency_overrides.clear()

    notification = (
        test_db_session.query(Notification)
        .filter(Notification.message == "UniqueText42")
        .first()
    )
    assert notification is not None


def test_non_admin_cannot_announce(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["student"])
    resp = client.post("/admin/announce", params={"message": "Hack!"})
    app.dependency_overrides.clear()

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /admin/analytics
# ---------------------------------------------------------------------------


def test_admin_can_access_analytics(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/admin/analytics")
    app.dependency_overrides.clear()

    assert resp.status_code == 200


def test_analytics_has_required_top_level_keys(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/admin/analytics")
    app.dependency_overrides.clear()

    data = resp.json()
    for key in ("totals", "orders_by_day", "revenue_by_day", "order_status",
                "payment_status", "top_vendors", "peak_hours",
                "week_comparison", "fraud_stats"):
        assert key in data, f"Missing analytics key: {key}"


def test_analytics_totals_counts_users(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/admin/analytics")
    app.dependency_overrides.clear()

    totals = resp.json()["totals"]
    assert totals["users"] == 4  # admin + student + approved_vendor + pending_vendor


def test_analytics_totals_counts_vendors(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/admin/analytics")
    app.dependency_overrides.clear()

    totals = resp.json()["totals"]
    assert totals["vendors"] == 2  # approved + pending


def test_analytics_totals_counts_orders(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/admin/analytics")
    app.dependency_overrides.clear()

    totals = resp.json()["totals"]
    assert totals["orders"] == 1


def test_analytics_totals_revenue_matches_successful_payments(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/admin/analytics")
    app.dependency_overrides.clear()

    totals = resp.json()["totals"]
    # One successful payment of 15000 paise
    assert totals["revenue_paise"] == 15000


def test_analytics_top_vendors_includes_seeded_vendor(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/admin/analytics")
    app.dependency_overrides.clear()

    top_vendor_ids = [v["vendor_id"] for v in resp.json()["top_vendors"]]
    assert seed_data["approved_vendor"].id in top_vendor_ids


def test_analytics_fraud_stats_zero_when_no_fraud(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/admin/analytics")
    app.dependency_overrides.clear()

    fraud = resp.json()["fraud_stats"]
    assert fraud["total_flagged"] == 0
    assert fraud["fraud_rate_pct"] == 0.0


def test_analytics_fraud_stats_non_zero_after_flagging(test_db_session, seed_data):
    # Flag the seeded order
    order = seed_data["order"]
    order.fraud_flag = True
    order.flagged_at = utcnow_naive()
    test_db_session.commit()

    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/admin/analytics")
    app.dependency_overrides.clear()

    fraud = resp.json()["fraud_stats"]
    assert fraud["total_flagged"] == 1
    assert fraud["fraud_rate_pct"] == 100.0


def test_analytics_week_comparison_structure(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/admin/analytics")
    app.dependency_overrides.clear()

    wc = resp.json()["week_comparison"]
    assert "this_week" in wc
    assert "last_week" in wc
    assert "order_delta" in wc
    assert "revenue_delta_paise" in wc


def test_non_admin_cannot_access_analytics(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["student"])
    resp = client.get("/admin/analytics")
    app.dependency_overrides.clear()

    assert resp.status_code == 403


def test_vendor_cannot_access_analytics(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["approved_vendor"])
    resp = client.get("/admin/analytics")
    app.dependency_overrides.clear()

    assert resp.status_code == 403
