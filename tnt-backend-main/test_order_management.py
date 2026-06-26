"""
test_order_management.py
========================
Tests for the complete Order Management system including:
  1. PREPARING status transitions
  2. Full lifecycle: PLACED → CONFIRMED → PREPARING → READY → PICKED
  3. Order timeline retrieval
  4. Order ETA endpoint
  5. QR generation and pickup
  6. Reorder from collected orders
  7. Cancel at various stages
  8. Vendor analytics with preparing count
  9. My orders with ETA/delay data
  10. Invalid transitions at each stage
"""
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.menu.model import MenuItem
from app.modules.orders.history_model import OrderHistory
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.orders.state_machine import validate_transition
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ─── fixtures ────────────────────────────────────────────────────────────────


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
    student = User(phone="9300000001", name="Test Student", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="9300000010",
        name="Test Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )
    test_db_session.add_all([student, vendor])
    test_db_session.commit()
    test_db_session.refresh(student)
    test_db_session.refresh(vendor)

    slot = Slot(
        vendor_id=vendor.id,
        start_time=utcnow_naive() + timedelta(hours=1),
        end_time=utcnow_naive() + timedelta(hours=2),
        max_orders=10,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    menu_item = MenuItem(
        vendor_id=vendor.id,
        name="Test Burger",
        description="A test item",
        price=12900,
        image_url="https://example.com/burger.png",
        is_available=True,
    )
    test_db_session.add_all([slot, menu_item])
    test_db_session.commit()
    test_db_session.refresh(slot)
    test_db_session.refresh(menu_item)

    return {"student": student, "vendor": vendor, "slot": slot, "menu_item": menu_item}


@pytest.fixture()
def student_client(test_db_session, seed_data):
    student = seed_data["student"]
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
def vendor_client(test_db_session, seed_data):
    vendor = seed_data["vendor"]
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


# ─── Unit tests: PREPARING status ──────────────────────────────────────────────


class TestPreparingTransitions:
    """Unit tests for PREPARING status in state machine."""

    def test_confirmed_to_preparing_valid(self):
        validate_transition(OrderStatus.CONFIRMED, OrderStatus.PREPARING)

    def test_preparing_to_ready_valid(self):
        validate_transition(OrderStatus.PREPARING, OrderStatus.READY)

    def test_preparing_to_cancelled_valid(self):
        validate_transition(OrderStatus.PREPARING, OrderStatus.CANCELLED)

    def test_placed_cannot_skip_to_preparing(self):
        with pytest.raises(HTTPException) as exc:
            validate_transition(OrderStatus.PLACED, OrderStatus.PREPARING)
        assert exc.value.status_code == 422

    def test_preparing_cannot_go_back_to_confirmed(self):
        with pytest.raises(HTTPException) as exc:
            validate_transition(OrderStatus.PREPARING, OrderStatus.CONFIRMED)
        assert exc.value.status_code == 422

    def test_preparing_cannot_skip_to_picked(self):
        with pytest.raises(HTTPException) as exc:
            validate_transition(OrderStatus.PREPARING, OrderStatus.PICKED)
        assert exc.value.status_code == 422

    def test_preparing_enum_value(self):
        assert OrderStatus.PREPARING.value == "preparing"


# ─── Integration tests: Full lifecycle with PREPARING ──────────────────────────


class TestFullLifecycleWithPreparing:
    """Full lifecycle: PLACED → CONFIRMED → PREPARING → READY → PICKED."""

    def test_full_lifecycle_with_preparing_step(self, student_client, test_db_session, seed_data):
        client, auth = student_client
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]
        vendor = seed_data["vendor"]
        student = seed_data["student"]

        # 1. Place order
        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        assert resp.status_code == 200
        order_id = resp.json()["order_id"]

        order = test_db_session.get(Order, order_id)
        assert order.status == OrderStatus.PLACED

        # 2. Vendor confirms
        auth.update({"id": vendor.id, "phone": vendor.phone, "role": vendor.role.value})
        r = client.post(f"/orders/{order_id}/confirm")
        assert r.status_code == 200
        test_db_session.refresh(order)
        assert order.status == OrderStatus.CONFIRMED

        # 3. Vendor marks preparing
        r = client.post(f"/orders/{order_id}/preparing")
        assert r.status_code == 200
        test_db_session.refresh(order)
        assert order.status == OrderStatus.PREPARING

        # 4. Vendor marks ready
        r = client.post(f"/orders/{order_id}/ready")
        assert r.status_code == 200
        test_db_session.refresh(order)
        assert order.status == OrderStatus.READY

        # 5. Student generates QR
        auth.update({"id": student.id, "phone": student.phone, "role": student.role.value})
        r = client.post(f"/orders/{order_id}/qr")
        assert r.status_code == 200
        qr_code = r.json()["qr_code"]
        assert qr_code

        # 6. Vendor confirms pickup
        auth.update({"id": vendor.id, "phone": vendor.phone, "role": vendor.role.value})
        r = client.post(f"/orders/qr/pickup/confirm?qr_code={qr_code}")
        assert r.status_code == 200
        test_db_session.refresh(order)
        assert order.status == OrderStatus.PICKED

    def test_confirm_then_ready_without_preparing_rejected(self, student_client, test_db_session, seed_data):
        """CONFIRMED → READY is no longer valid; must go through PREPARING."""
        client, auth = student_client
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]
        vendor = seed_data["vendor"]

        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        order_id = resp.json()["order_id"]

        auth.update({"id": vendor.id, "phone": vendor.phone, "role": vendor.role.value})
        r = client.post(f"/orders/{order_id}/confirm")
        assert r.status_code == 200

        # Try going directly READY (skip PREPARING) — should fail
        r = client.post(f"/orders/{order_id}/ready")
        assert r.status_code == 422


# ─── Timeline tests ──────────────────────────────────────────────────────────


class TestOrderTimeline:
    """Order timeline endpoint tests."""

    def test_timeline_records_all_transitions(self, student_client, test_db_session, seed_data):
        client, auth = student_client
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]
        vendor = seed_data["vendor"]
        student = seed_data["student"]

        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        order_id = resp.json()["order_id"]

        # Confirm + preparing
        auth.update({"id": vendor.id, "phone": vendor.phone, "role": vendor.role.value})
        client.post(f"/orders/{order_id}/confirm")
        client.post(f"/orders/{order_id}/preparing")

        # Check timeline
        auth.update({"id": student.id, "phone": student.phone, "role": student.role.value})
        r = client.get(f"/orders/{order_id}/timeline")
        assert r.status_code == 200
        history = r.json()
        status_values = [h["status"] for h in history]
        assert "placed" in status_values
        assert "confirmed" in status_values
        assert "preparing" in status_values

    def test_timeline_empty_for_new_order(self, student_client, test_db_session, seed_data):
        """Orders placed via service.py create_order get a PLACED history entry."""
        client, auth = student_client
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]

        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        order_id = resp.json()["order_id"]

        r = client.get(f"/orders/{order_id}/timeline")
        assert r.status_code == 200
        history = r.json()
        assert len(history) >= 1
        assert history[0]["status"] == "placed"


# ─── ETA tests ────────────────────────────────────────────────────────────────


class TestOrderETA:
    """Order ETA endpoint tests."""

    def test_eta_returns_data(self, student_client, test_db_session, seed_data):
        client, auth = student_client
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]

        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        order_id = resp.json()["order_id"]

        r = client.get(f"/orders/{order_id}/eta")
        assert r.status_code == 200
        data = r.json()
        assert "order_id" in data
        assert "status" in data
        assert "estimated_ready_at" in data
        assert "is_delayed" in data

    def test_eta_cancelled_order_rejected(self, student_client, test_db_session, seed_data):
        client, auth = student_client
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]

        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        order_id = resp.json()["order_id"]

        # Cancel the order
        client.post(f"/orders/{order_id}/cancel")

        r = client.get(f"/orders/{order_id}/eta")
        assert r.status_code == 400


# ─── My orders tests ──────────────────────────────────────────────────────────


class TestMyOrders:
    """My orders endpoint with enriched data."""

    def test_my_orders_includes_eta_and_delay(self, student_client, test_db_session, seed_data):
        client, auth = student_client
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]

        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        assert resp.status_code == 200

        r = client.get("/orders/my")
        assert r.status_code == 200
        orders = r.json()
        assert len(orders) >= 1
        order = orders[0]
        assert "eta_minutes" in order
        assert "is_delayed" in order

    def test_my_orders_includes_vendor_name(self, student_client, test_db_session, seed_data):
        client, auth = student_client
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]

        client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )

        r = client.get("/orders/my")
        assert r.status_code == 200
        orders = r.json()
        assert any(o.get("vendor_name") for o in orders)


# ─── Cancel tests ────────────────────────────────────────────────────────────


class TestCancelOrder:
    """Cancel order at various stages."""

    def test_cancel_placed_order(self, student_client, test_db_session, seed_data):
        client, auth = student_client
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]

        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        order_id = resp.json()["order_id"]

        r = client.post(f"/orders/{order_id}/cancel")
        assert r.status_code == 200

        order = test_db_session.get(Order, order_id)
        assert order.status == OrderStatus.CANCELLED

    def test_cancel_preparing_order(self, student_client, test_db_session, seed_data):
        client, auth = student_client
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]
        vendor = seed_data["vendor"]

        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        order_id = resp.json()["order_id"]

        auth.update({"id": vendor.id, "phone": vendor.phone, "role": vendor.role.value})
        client.post(f"/orders/{order_id}/confirm")
        client.post(f"/orders/{order_id}/preparing")

        auth.update({"id": seed_data["student"].id, "phone": seed_data["student"].phone, "role": seed_data["student"].role.value})
        r = client.post(f"/orders/{order_id}/cancel")
        assert r.status_code == 200

    def test_cancel_ready_order(self, student_client, test_db_session, seed_data):
        client, auth = student_client
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]
        vendor = seed_data["vendor"]

        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        order_id = resp.json()["order_id"]

        auth.update({"id": vendor.id, "phone": vendor.phone, "role": vendor.role.value})
        client.post(f"/orders/{order_id}/confirm")
        client.post(f"/orders/{order_id}/preparing")
        client.post(f"/orders/{order_id}/ready")

        auth.update({"id": seed_data["student"].id, "phone": seed_data["student"].phone, "role": seed_data["student"].role.value})
        r = client.post(f"/orders/{order_id}/cancel")
        assert r.status_code == 200

    def test_cancel_picked_order_rejected(self, student_client, test_db_session, seed_data):
        client, auth = student_client
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]

        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        order_id = resp.json()["order_id"]

        order = test_db_session.get(Order, order_id)
        order.status = OrderStatus.PICKED
        test_db_session.commit()

        r = client.post(f"/orders/{order_id}/cancel")
        assert r.status_code == 400


# ─── Vendor analytics tests ──────────────────────────────────────────────────


class TestVendorAnalytics:
    """Vendor analytics includes preparing_orders count."""

    def test_analytics_includes_preparing_count(self, vendor_client, test_db_session, seed_data):
        client, auth = vendor_client
        vendor = seed_data["vendor"]
        student = seed_data["student"]
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]

        # Create an order and advance to PREPARING
        order = Order(
            user_id=student.id,
            vendor_id=vendor.id,
            slot_id=slot.id,
            status=OrderStatus.PREPARING,
            eta_minutes=15,
        )
        test_db_session.add(order)
        test_db_session.commit()

        r = client.get("/orders/vendor/analytics")
        assert r.status_code == 200
        data = r.json()
        assert "preparing_orders" in data
        assert data["preparing_orders"] >= 1


# ─── Vendor order detail tests ────────────────────────────────────────────────


class TestVendorOrderDetail:
    """Vendor can view order details."""

    def test_vendor_can_get_order_detail(self, vendor_client, test_db_session, seed_data):
        client, auth = vendor_client
        vendor = seed_data["vendor"]
        student = seed_data["student"]
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]

        order = Order(
            user_id=student.id,
            vendor_id=vendor.id,
            slot_id=slot.id,
            status=OrderStatus.CONFIRMED,
            total_amount=12900,
        )
        test_db_session.add(order)
        test_db_session.flush()

        oi = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            quantity=1,
            price_at_time=menu_item.price,
        )
        test_db_session.add(oi)
        test_db_session.commit()

        r = client.get(f"/orders/vendor/{order.id}")
        assert r.status_code == 200
        data = r.json()
        assert data["order_id"] == order.id
        assert len(data["items"]) >= 1
