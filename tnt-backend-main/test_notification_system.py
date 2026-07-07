"""Tests for the Notification System.

Covers: CRUD, type filtering, unread count, mark-read, mark-all-read,
Redis queue, and order-lifecycle notification generation.
"""

import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from app.core.deps import get_db
from app.core.security import get_current_user
from app.core.time_utils import utcnow_naive
from app.database.base import Base
from app.main import app
from app.modules.menu.model import MenuItem
from app.modules.notifications.model import Notification, NotificationType
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


# ── Fixtures ──────────────────────────────────────────────────────────────────


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
def seed(test_db_session):
    now = utcnow_naive()
    student = User(
        name="Test Student",
        phone="9777000001",
        role=UserRole.STUDENT,
        vendor_type="food",
        is_active=True,
        is_approved=True,
    )
    vendor = User(
        name="Test Vendor",
        phone="9777000002",
        role=UserRole.VENDOR,
        vendor_type="food",
        is_active=True,
        is_approved=True,
    )
    test_db_session.add_all([student, vendor])
    test_db_session.commit()
    test_db_session.refresh(student)
    test_db_session.refresh(vendor)

    slot = Slot(
        vendor_id=vendor.id,
        start_time=now,
        end_time=now + timedelta(minutes=60),
        max_orders=30,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    mi = MenuItem(
        vendor_id=vendor.id,
        name="Test Burger",
        description="Test item",
        price=12900,
        image_url="https://example.com/burger.jpg",
        is_available=True,
    )
    test_db_session.add_all([slot, mi])
    test_db_session.commit()
    test_db_session.refresh(slot)
    test_db_session.refresh(mi)

    order = Order(
        user_id=student.id,
        vendor_id=vendor.id,
        slot_id=slot.id,
        status=OrderStatus.PLACED,
        total_amount=12900,
        eta_minutes=15,
    )
    test_db_session.add(order)
    test_db_session.flush()
    oi = OrderItem(order_id=order.id, menu_item_id=mi.id, quantity=1, price_at_time=12900)
    test_db_session.add(oi)
    test_db_session.commit()
    test_db_session.refresh(order)

    return {
        "student": student,
        "vendor": vendor,
        "order": order,
        "slot": slot,
        "menu_item": mi,
    }


@pytest.fixture()
def student_client(test_db_session, seed):
    student = seed["student"]
    auth_context = {"id": student.id, "phone": student.phone, "role": student.role.value}

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
        yield test_client, auth_context

    app.dependency_overrides.clear()


@pytest.fixture()
def vendor_client(test_db_session, seed):
    vendor = seed["vendor"]
    auth_context = {"id": vendor.id, "phone": vendor.phone, "role": vendor.role.value}

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
        yield test_client, auth_context

    app.dependency_overrides.clear()


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestNotificationModel:
    def test_notification_type_enum(self):
        assert NotificationType.ORDER_ACCEPTED.value == "order_accepted"
        assert NotificationType.DELAY_ALERT.value == "delay_alert"
        assert NotificationType.PICKUP_REMINDER.value == "pickup_reminder"
        assert NotificationType.ORDER_PREPARING.value == "order_preparing"
        assert NotificationType.ORDER_CANCELLED.value == "order_cancelled"
        assert NotificationType.PROMO.value == "promo"

    def test_create_notification_with_type(self, test_db_session, seed):
        n = Notification(
            user_id=seed["student"].id,
            title="Order Accepted",
            message="Your order has been accepted.",
            notification_type=NotificationType.ORDER_ACCEPTED,
            reference_id=seed["order"].id,
        )
        test_db_session.add(n)
        test_db_session.commit()

        fetched = test_db_session.query(Notification).filter(Notification.id == n.id).one()
        assert fetched.notification_type == NotificationType.ORDER_ACCEPTED
        assert fetched.reference_id == seed["order"].id
        assert fetched.is_read is False

    def test_default_notification_type_is_system(self, test_db_session, seed):
        n = Notification(
            user_id=seed["student"].id,
            title="Info",
            message="Some info",
        )
        test_db_session.add(n)
        test_db_session.commit()

        fetched = test_db_session.query(Notification).filter(Notification.id == n.id).one()
        assert fetched.notification_type == NotificationType.SYSTEM


class TestNotificationAPI:
    def test_get_notifications(self, student_client, test_db_session, seed):
        client, _ = student_client
        n1 = Notification(user_id=seed["student"].id, title="T1", message="M1", notification_type=NotificationType.ORDER_PLACED, reference_id=seed["order"].id)
        n2 = Notification(user_id=seed["student"].id, title="T2", message="M2", notification_type=NotificationType.ORDER_READY, reference_id=seed["order"].id, is_read=True)
        test_db_session.add_all([n1, n2])
        test_db_session.commit()

        resp = client.get("/notifications/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_get_unread_count(self, student_client, test_db_session, seed):
        client, _ = student_client
        test_db_session.add(Notification(user_id=seed["student"].id, title="U1", message="M", notification_type=NotificationType.ORDER_ACCEPTED))
        test_db_session.add(Notification(user_id=seed["student"].id, title="U2", message="M", notification_type=NotificationType.ORDER_PREPARING, is_read=True))
        test_db_session.commit()

        resp = client.get("/notifications/unread-count")
        assert resp.status_code == 200
        assert resp.json()["unread_count"] == 1

    def test_filter_unread_only(self, student_client, test_db_session, seed):
        client, _ = student_client
        test_db_session.add(Notification(user_id=seed["student"].id, title="U1", message="M", notification_type=NotificationType.ORDER_ACCEPTED))
        test_db_session.add(Notification(user_id=seed["student"].id, title="U2", message="M", notification_type=NotificationType.ORDER_PREPARING, is_read=True))
        test_db_session.commit()

        resp = client.get("/notifications/?unread_only=true")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["is_read"] is False

    def test_filter_by_type(self, student_client, test_db_session, seed):
        client, _ = student_client
        test_db_session.add(Notification(user_id=seed["student"].id, title="T1", message="M", notification_type=NotificationType.ORDER_ACCEPTED))
        test_db_session.add(Notification(user_id=seed["student"].id, title="T2", message="M", notification_type=NotificationType.DELAY_ALERT))
        test_db_session.commit()

        resp = client.get("/notifications/?notification_type=delay_alert")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["notification_type"] == "delay_alert"

    def test_mark_as_read(self, student_client, test_db_session, seed):
        client, _ = student_client
        n = Notification(user_id=seed["student"].id, title="T", message="M", notification_type=NotificationType.ORDER_READY)
        test_db_session.add(n)
        test_db_session.commit()
        test_db_session.refresh(n)

        resp = client.post(f"/notifications/{n.id}/read")
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_read"] is True

    def test_mark_all_read(self, student_client, test_db_session, seed):
        client, _ = student_client
        test_db_session.add(Notification(user_id=seed["student"].id, title="U1", message="M", notification_type=NotificationType.ORDER_ACCEPTED))
        test_db_session.add(Notification(user_id=seed["student"].id, title="U2", message="M", notification_type=NotificationType.PICKUP_REMINDER))
        test_db_session.add(Notification(user_id=seed["student"].id, title="U3", message="M", notification_type=NotificationType.DELAY_ALERT, is_read=True))
        test_db_session.commit()

        resp = client.post("/notifications/mark-all-read")
        assert resp.status_code == 200
        assert resp.json()["updated_count"] == 2

        count_resp = client.get("/notifications/unread-count")
        assert count_resp.json()["unread_count"] == 0

    def test_cannot_view_other_users_notifications(self, student_client, seed):
        client, _ = student_client
        resp = client.get(f"/notifications/{seed['vendor'].id}")
        assert resp.status_code == 403

    def test_vendor_can_view_any_users_notifications(self, vendor_client, test_db_session, seed):
        client, _ = vendor_client
        test_db_session.add(Notification(user_id=seed["student"].id, title="S1", message="M", notification_type=NotificationType.ORDER_ACCEPTED))
        test_db_session.commit()

        resp = client.get(f"/notifications/{seed['student'].id}")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_notification_response_includes_type_and_reference(self, student_client, test_db_session, seed):
        client, _ = student_client
        n = Notification(
            user_id=seed["student"].id,
            title="Order Ready",
            message="Ready!",
            notification_type=NotificationType.ORDER_READY,
            reference_id=seed["order"].id,
        )
        test_db_session.add(n)
        test_db_session.commit()

        resp = client.get("/notifications/")
        data = resp.json()
        found = [x for x in data if x["title"] == "Order Ready"]
        assert len(found) == 1
        assert found[0]["notification_type"] == "order_ready"
        assert found[0]["reference_id"] == seed["order"].id


class TestNotificationService:
    def test_notify_user_creates_with_type(self, test_db_session, seed):
        from app.modules.notifications.service import notify_user
        n = notify_user(
            user_id=seed["student"].id,
            phone=seed["student"].phone,
            title="Order Preparing",
            message="Your order is being prepared.",
            db=test_db_session,
            notification_type=NotificationType.ORDER_PREPARING,
            reference_id=seed["order"].id,
            send_sms_flag=False,
        )
        test_db_session.commit()
        assert n.notification_type == NotificationType.ORDER_PREPARING
        assert n.reference_id == seed["order"].id
        assert n.is_read is False

    def test_get_unread_count(self, test_db_session, seed):
        from app.modules.notifications.service import get_unread_count, notify_user
        notify_user(seed["student"].id, seed["student"].phone, "T1", "M1", test_db_session, send_sms_flag=False)
        notify_user(seed["student"].id, seed["student"].phone, "T2", "M2", test_db_session, send_sms_flag=False)
        test_db_session.commit()

        count = get_unread_count(seed["student"].id, test_db_session)
        assert count == 2

    def test_mark_all_read(self, test_db_session, seed):
        from app.modules.notifications.service import mark_all_read, notify_user
        notify_user(seed["student"].id, seed["student"].phone, "T1", "M1", test_db_session, send_sms_flag=False)
        notify_user(seed["student"].id, seed["student"].phone, "T2", "M2", test_db_session, send_sms_flag=False)
        test_db_session.commit()

        count = mark_all_read(seed["student"].id, test_db_session)
        assert count == 2

    def test_redis_queue_enqueued(self, test_db_session, seed):
        from app.modules.notifications.service import notify_user, REDIS_QUEUE_KEY
        from app.core.redis import redis_client
        notify_user(
            seed["student"].id,
            seed["student"].phone,
            "Redis Test",
            "Queue test msg",
            test_db_session,
            notification_type=NotificationType.PICKUP_REMINDER,
            send_sms_flag=False,
        )
        test_db_session.commit()

        items = redis_client.lrange(REDIS_QUEUE_KEY, 0, -1)
        assert len(items) >= 1
        payload = json.loads(items[-1])
        assert payload["title"] == "Redis Test"
        assert payload["type"] == "pickup_reminder"
