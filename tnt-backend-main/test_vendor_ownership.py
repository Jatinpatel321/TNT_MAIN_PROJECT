"""
Security tests: vendor ownership enforcement on order mutations.

Verifies that POST /orders/{id}/confirm and POST /orders/{id}/ready
are scoped to the authenticated vendor's own orders only.
Cross-vendor mutations must return 404 (security masking).
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
def seed(test_db_session):
    """Create two independent vendors and one student, each with their own slot and order."""
    student = User(phone="6100000001", name="Student", role=UserRole.STUDENT, is_active=True)

    vendor_a = User(
        phone="6100000010",
        name="Vendor A",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )
    vendor_b = User(
        phone="6100000020",
        name="Vendor B",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )

    test_db_session.add_all([student, vendor_a, vendor_b])
    test_db_session.commit()
    for obj in (student, vendor_a, vendor_b):
        test_db_session.refresh(obj)

    slot_a = Slot(
        vendor_id=vendor_a.id,
        start_time=utcnow_naive() + timedelta(hours=1),
        end_time=utcnow_naive() + timedelta(hours=2),
        max_orders=10,
        current_orders=1,
        status=SlotStatus.AVAILABLE,
    )
    slot_b = Slot(
        vendor_id=vendor_b.id,
        start_time=utcnow_naive() + timedelta(hours=1),
        end_time=utcnow_naive() + timedelta(hours=2),
        max_orders=10,
        current_orders=1,
        status=SlotStatus.AVAILABLE,
    )
    test_db_session.add_all([slot_a, slot_b])
    test_db_session.commit()
    test_db_session.refresh(slot_a)
    test_db_session.refresh(slot_b)

    order_a = Order(
        user_id=student.id,
        slot_id=slot_a.id,
        vendor_id=vendor_a.id,
        status=OrderStatus.PENDING,
        total_amount=5000,
    )
    order_b = Order(
        user_id=student.id,
        slot_id=slot_b.id,
        vendor_id=vendor_b.id,
        status=OrderStatus.PENDING,
        total_amount=3000,
    )
    test_db_session.add_all([order_a, order_b])
    test_db_session.commit()
    test_db_session.refresh(order_a)
    test_db_session.refresh(order_b)

    return {
        "student": student,
        "vendor_a": vendor_a,
        "vendor_b": vendor_b,
        "order_a": order_a,   # belongs to vendor_a
        "order_b": order_b,   # belongs to vendor_b
    }


def _client_as_vendor(test_db_session, vendor: User):
    """Return a TestClient authenticated as the given vendor."""
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    def override_get_current_user():
        return {"id": vendor.id, "phone": vendor.phone, "role": "vendor", "is_active": True}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    client = TestClient(app, raise_server_exceptions=True)
    return client


# ---------------------------------------------------------------------------
# Tests — cross-vendor mutations (must fail with 404)
# ---------------------------------------------------------------------------

def test_vendor_a_cannot_confirm_vendor_b_order(seed, test_db_session):
    """Vendor A attempting to confirm Vendor B's order must receive 404."""
    client = _client_as_vendor(test_db_session, seed["vendor_a"])
    try:
        resp = client.post(f"/orders/{seed['order_b'].id}/confirm")
        assert resp.status_code == 404, (
            f"Expected 404 (cross-vendor confirm blocked), got {resp.status_code}: {resp.json()}"
        )
    finally:
        app.dependency_overrides.clear()


def test_vendor_a_cannot_complete_vendor_b_order(seed, test_db_session):
    """Vendor A attempting to mark Vendor B's order ready must receive 404."""
    client = _client_as_vendor(test_db_session, seed["vendor_a"])
    try:
        resp = client.post(f"/orders/{seed['order_b'].id}/ready")
        assert resp.status_code == 404, (
            f"Expected 404 (cross-vendor ready blocked), got {resp.status_code}: {resp.json()}"
        )
    finally:
        app.dependency_overrides.clear()


def test_vendor_b_cannot_confirm_vendor_a_order(seed, test_db_session):
    """Reverse direction: Vendor B cannot touch Vendor A's order either."""
    client = _client_as_vendor(test_db_session, seed["vendor_b"])
    try:
        resp = client.post(f"/orders/{seed['order_a'].id}/confirm")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_vendor_b_cannot_complete_vendor_a_order(seed, test_db_session):
    """Reverse direction: Vendor B cannot mark Vendor A's order ready."""
    client = _client_as_vendor(test_db_session, seed["vendor_b"])
    try:
        resp = client.post(f"/orders/{seed['order_a'].id}/ready")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_cross_vendor_confirm_does_not_mutate_order_status(seed, test_db_session):
    """Even if the HTTP response is already 404, verify DB state is untouched."""
    original_status = seed["order_b"].status

    client = _client_as_vendor(test_db_session, seed["vendor_a"])
    try:
        client.post(f"/orders/{seed['order_b'].id}/confirm")
    finally:
        app.dependency_overrides.clear()

    test_db_session.refresh(seed["order_b"])
    assert seed["order_b"].status == original_status, (
        "Cross-vendor confirm must not mutate the target order's status"
    )


def test_cross_vendor_complete_does_not_mutate_order_status(seed, test_db_session):
    """Same status-immutability guarantee for the ready endpoint."""
    original_status = seed["order_b"].status

    client = _client_as_vendor(test_db_session, seed["vendor_a"])
    try:
        client.post(f"/orders/{seed['order_b'].id}/ready")
    finally:
        app.dependency_overrides.clear()

    test_db_session.refresh(seed["order_b"])
    assert seed["order_b"].status == original_status


# ---------------------------------------------------------------------------
# Tests — own-order mutations (must succeed)
# ---------------------------------------------------------------------------

def test_vendor_a_can_confirm_own_order(seed, test_db_session):
    """Vendor A must be able to confirm their own order."""
    client = _client_as_vendor(test_db_session, seed["vendor_a"])
    try:
        resp = client.post(f"/orders/{seed['order_a'].id}/confirm")
        assert resp.status_code == 200, (
            f"Expected 200 for own-order confirm, got {resp.status_code}: {resp.json()}"
        )
    finally:
        app.dependency_overrides.clear()


def test_vendor_b_can_confirm_own_order(seed, test_db_session):
    """Vendor B must be able to confirm their own order."""
    client = _client_as_vendor(test_db_session, seed["vendor_b"])
    try:
        resp = client.post(f"/orders/{seed['order_b'].id}/confirm")
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_vendor_a_can_complete_own_order(seed, test_db_session):
    """Vendor A must be able to mark their own order as ready."""
    # Set to PREPARING first so the status transition PREPARING → READY is valid
    seed["order_a"].status = OrderStatus.PREPARING
    test_db_session.commit()

    client = _client_as_vendor(test_db_session, seed["vendor_a"])
    try:
        resp = client.post(f"/orders/{seed['order_a'].id}/ready")
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_nonexistent_order_returns_404_for_any_vendor(seed, test_db_session):
    """A completely absent order ID returns 404 regardless of vendor identity."""
    client = _client_as_vendor(test_db_session, seed["vendor_a"])
    try:
        resp = client.post("/orders/999999/confirm")
        assert resp.status_code == 404
        resp2 = client.post("/orders/999999/ready")
        assert resp2.status_code == 404
    finally:
        app.dependency_overrides.clear()
