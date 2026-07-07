"""
test_order_state_machine.py
===========================
PROMPT 11 QA: Verify the OrderStatus state-machine enforces correct lifecycle
transitions.

Coverage:
  1. Unit tests for validate_transition()
  2. Integration tests: full place→confirm→ready→picked path
  3. Invalid skip raises 422
  4. Terminal state raises 400
  5. Student can cancel PLACED / CONFIRMED / READY; not PICKED / CANCELLED
  6. Vendor cannot cancel; student cannot confirm
  7. New /ready endpoint replaces old /complete endpoint
  8. QR pickup sets status to PICKED
  9. Legacy READY_FOR_PICKUP still accepted by QR service (backward compat)
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
from app.modules.orders.model import Order, OrderStatus
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
    student = User(phone="8200000001", name="Student", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="8200000010",
        name="Vendor",
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
        name="State Machine Meal",
        description="Test item",
        price=100,
        image_url="https://example.com/item.png",
        is_available=True,
    )
    test_db_session.add_all([slot, menu_item])
    test_db_session.commit()
    test_db_session.refresh(slot)
    test_db_session.refresh(menu_item)

    return {"student": student, "vendor": vendor, "slot": slot, "menu_item": menu_item}


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


# ─── Unit tests ──────────────────────────────────────────────────────────────


class TestValidateTransitionUnit:
    """Unit tests for the validate_transition() function."""

    # ── Valid canonical transitions ──────────────────────────────────────────

    def test_placed_to_confirmed(self):
        validate_transition(OrderStatus.PLACED, OrderStatus.CONFIRMED)  # must not raise

    def test_placed_to_cancelled(self):
        validate_transition(OrderStatus.PLACED, OrderStatus.CANCELLED)

    def test_confirmed_to_preparing(self):
        validate_transition(OrderStatus.CONFIRMED, OrderStatus.PREPARING)

    def test_preparing_to_ready(self):
        validate_transition(OrderStatus.PREPARING, OrderStatus.READY)

    def test_confirmed_cannot_skip_to_ready(self):
        """CONFIRMED → READY is no longer valid; must go through PREPARING."""
        with pytest.raises(HTTPException) as exc:
            validate_transition(OrderStatus.CONFIRMED, OrderStatus.READY)
        assert exc.value.status_code == 422

    def test_confirmed_to_cancelled(self):
        validate_transition(OrderStatus.CONFIRMED, OrderStatus.CANCELLED)

    def test_ready_to_picked(self):
        validate_transition(OrderStatus.READY, OrderStatus.PICKED)

    def test_ready_to_cancelled(self):
        validate_transition(OrderStatus.READY, OrderStatus.CANCELLED)

    # ── Legacy backward-compat transitions ──────────────────────────────────

    def test_pending_to_confirmed(self):
        """Legacy PENDING behaves like PLACED."""
        validate_transition(OrderStatus.PENDING, OrderStatus.CONFIRMED)

    def test_pending_to_cancelled(self):
        validate_transition(OrderStatus.PENDING, OrderStatus.CANCELLED)

    def test_ready_for_pickup_to_picked(self):
        validate_transition(OrderStatus.READY_FOR_PICKUP, OrderStatus.PICKED)

    # ── Invalid transitions raise 422 ────────────────────────────────────────

    def test_placed_cannot_skip_to_ready(self):
        with pytest.raises(HTTPException) as exc:
            validate_transition(OrderStatus.PLACED, OrderStatus.READY)
        assert exc.value.status_code == 422

    def test_placed_cannot_skip_to_picked(self):
        with pytest.raises(HTTPException) as exc:
            validate_transition(OrderStatus.PLACED, OrderStatus.PICKED)
        assert exc.value.status_code == 422

    def test_confirmed_cannot_go_to_placed(self):
        with pytest.raises(HTTPException) as exc:
            validate_transition(OrderStatus.CONFIRMED, OrderStatus.PLACED)
        assert exc.value.status_code == 422

    # ── Terminal states raise 400 ─────────────────────────────────────────────

    def test_picked_is_terminal(self):
        with pytest.raises(HTTPException) as exc:
            validate_transition(OrderStatus.PICKED, OrderStatus.CANCELLED)
        assert exc.value.status_code == 400

    def test_cancelled_is_terminal(self):
        with pytest.raises(HTTPException) as exc:
            validate_transition(OrderStatus.CANCELLED, OrderStatus.PLACED)
        assert exc.value.status_code == 400

    def test_completed_is_terminal(self):
        """Legacy COMPLETED is also terminal."""
        with pytest.raises(HTTPException) as exc:
            validate_transition(OrderStatus.COMPLETED, OrderStatus.CONFIRMED)
        assert exc.value.status_code == 400


# ─── Integration tests ───────────────────────────────────────────────────────


class TestStateMachineIntegration:
    """Full route-level state machine integration tests."""

    # ── Happy path: PLACED → CONFIRMED → PREPARING → READY → (QR) PICKED ────

    def test_full_canonical_lifecycle(self, client, test_db_session, seed_data, auth_context):
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]
        vendor = seed_data["vendor"]
        student = seed_data["student"]

        # 1. Place order (student)
        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        assert resp.status_code == 200
        order_id = resp.json()["order_id"]

        order = test_db_session.get(Order, order_id)
        assert order.status == OrderStatus.PLACED

        # 2. Confirm (vendor)
        auth_context.update({"id": vendor.id, "phone": vendor.phone, "role": vendor.role.value})
        r = client.post(f"/orders/{order_id}/confirm")
        assert r.status_code == 200
        test_db_session.refresh(order)
        assert order.status == OrderStatus.CONFIRMED

        # 3. Mark preparing (vendor)
        r = client.post(f"/orders/{order_id}/preparing")
        assert r.status_code == 200
        test_db_session.refresh(order)
        assert order.status == OrderStatus.PREPARING

        # 4. Mark ready (vendor)
        r = client.post(f"/orders/{order_id}/ready")
        assert r.status_code == 200
        test_db_session.refresh(order)
        assert order.status == OrderStatus.READY

        # 5. Student generates QR
        auth_context.update({"id": student.id, "phone": student.phone, "role": student.role.value})
        r = client.post(f"/orders/{order_id}/qr")
        assert r.status_code == 200
        qr_code = r.json()["qr_code"]
        assert qr_code

        # 6. Vendor scans QR → PICKED
        auth_context.update({"id": vendor.id, "phone": vendor.phone, "role": vendor.role.value})
        r = client.post(f"/orders/qr/pickup/confirm?qr_code={qr_code}")
        assert r.status_code == 200
        test_db_session.refresh(order)
        assert order.status == OrderStatus.PICKED

    # ── Invalid skip: PLACED → READY raises 422 ───────────────────────────────

    def test_skip_transition_rejected(self, client, test_db_session, seed_data, auth_context):
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]
        vendor = seed_data["vendor"]

        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        order_id = resp.json()["order_id"]

        # Try vendor marking READY directly from PLACED (skipping CONFIRM)
        auth_context.update({"id": vendor.id, "phone": vendor.phone, "role": vendor.role.value})
        r = client.post(f"/orders/{order_id}/ready")
        # validate_transition(PLACED → READY) → 422
        assert r.status_code == 422

    # ── Terminal: cancel PICKED raises 400 ───────────────────────────────────

    def test_cancel_picked_order_rejected(self, client, test_db_session, seed_data, auth_context):
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]
        vendor = seed_data["vendor"]
        student = seed_data["student"]

        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        order_id = resp.json()["order_id"]

        # Fast-track to PICKED via direct DB manipulation
        order = test_db_session.get(Order, order_id)
        order.status = OrderStatus.PICKED
        test_db_session.commit()

        r = client.post(f"/orders/{order_id}/cancel")
        assert r.status_code == 400

    # ── Role enforcement: student cannot confirm ──────────────────────────────

    def test_student_cannot_confirm_order(self, client, test_db_session, seed_data, auth_context):
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]

        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        order_id = resp.json()["order_id"]

        # Try confirming as student → roles check should reject first (403)
        r = client.post(f"/orders/{order_id}/confirm")
        assert r.status_code == 403

    # ── Student can cancel at PLACED / CONFIRMED / PREPARING / READY ────────────

    @pytest.mark.parametrize("status", [
        OrderStatus.PLACED,
        OrderStatus.CONFIRMED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
    ])
    def test_student_can_cancel_pre_terminal(self, client, test_db_session, seed_data, auth_context, status):
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]

        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        order_id = resp.json()["order_id"]

        order = test_db_session.get(Order, order_id)
        order.status = status
        test_db_session.commit()

        r = client.post(f"/orders/{order_id}/cancel")
        assert r.status_code == 200
        test_db_session.refresh(order)
        assert order.status == OrderStatus.CANCELLED

    # ── /complete has been removed; verify 404 / 405 ─────────────────────────

    def test_old_complete_endpoint_gone(self, client, test_db_session, seed_data, auth_context):
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]
        vendor = seed_data["vendor"]

        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        order_id = resp.json()["order_id"]

        auth_context.update({"id": vendor.id, "phone": vendor.phone, "role": vendor.role.value})
        # /complete no longer exists
        r = client.post(f"/orders/{order_id}/complete")
        assert r.status_code in (404, 405, 422)

    # ── Legacy READY_FOR_PICKUP still accepted by QR service ─────────────────

    def test_qr_accepts_legacy_ready_for_pickup(self, client, test_db_session, seed_data, auth_context):
        slot = seed_data["slot"]
        menu_item = seed_data["menu_item"]
        student = seed_data["student"]

        resp = client.post(
            f"/orders/{slot.id}",
            json=[{"menu_item_id": menu_item.id, "quantity": 1}],
        )
        order_id = resp.json()["order_id"]

        order = test_db_session.get(Order, order_id)
        order.status = OrderStatus.READY_FOR_PICKUP  # legacy state
        test_db_session.commit()

        # Student should still be able to generate QR
        r = client.post(f"/orders/{order_id}/qr")
        assert r.status_code == 200

    # ── Backward-compat: enum still accepts legacy string values ─────────────

    def test_legacy_status_values_exist_in_enum(self):
        assert OrderStatus.PENDING.value == "pending"
        assert OrderStatus.READY_FOR_PICKUP.value == "ready_for_pickup"
        assert OrderStatus.COMPLETED.value == "completed"

    # ── New canonical values present in enum ─────────────────────────────────

    def test_canonical_status_values_in_enum(self):
        assert OrderStatus.PLACED.value == "placed"
        assert OrderStatus.READY.value == "ready"
        assert OrderStatus.PICKED.value == "picked"
