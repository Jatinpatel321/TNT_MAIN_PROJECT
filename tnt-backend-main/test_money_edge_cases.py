"""Dedicated edge-case tests for the paise->rupees migration.

Covers: money.py helper correctness (rounding, boundary values), the
Razorpay paise boundary on a real HTTP round-trip, and group-cart bill
splitting under non-integer-rupee totals (a gap the migration exposed —
see the xfail below).
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.money import as_rupees, from_paise, to_paise
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.group_cart.service import GroupCartService
from app.modules.orders.model import Order, OrderStatus
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# app/core/money.py helpers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "rupees,expected_paise",
    [
        (0, 0),
        ("0", 0),
        (0.5, 50),
        (1, 100),
        (9999.99, 999999),
        (73.5, 7350),
        (0.01, 1),
    ],
)
def test_to_paise_boundary_values(rupees, expected_paise):
    assert to_paise(rupees) == expected_paise


@pytest.mark.parametrize(
    "paise,expected_rupees",
    [
        (0, Decimal("0.00")),
        (50, Decimal("0.50")),
        (100, Decimal("1.00")),
        (999999, Decimal("9999.99")),
        (7350, Decimal("73.50")),
        (1, Decimal("0.01")),
    ],
)
def test_from_paise_boundary_values(paise, expected_rupees):
    assert from_paise(paise) == expected_rupees


@pytest.mark.parametrize("rupees", [0, 0.5, 1, 9999.99, 73.5, 0.01, 12345.67])
def test_paise_round_trip_is_lossless(rupees):
    assert from_paise(to_paise(rupees)) == as_rupees(rupees)


def test_to_paise_rounds_half_up_on_sub_paise_input():
    # Razorpay only accepts integer paise; anything sub-paise must round,
    # not truncate.
    assert to_paise(Decimal("10.005")) == 1001
    assert to_paise(Decimal("10.004")) == 1000


def test_as_rupees_quantizes_to_two_places():
    assert as_rupees(None) == Decimal("0.00")
    assert as_rupees("49.9") == Decimal("49.90")
    assert as_rupees(Decimal("49.999")) == Decimal("50.00")


# ---------------------------------------------------------------------------
# Razorpay boundary — real HTTP round trip at ₹0.50 and ₹9999.99
# ---------------------------------------------------------------------------

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


def _make_order(db, total_amount):
    student = User(phone="8300000001", name="Student", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="8300000010", name="Vendor", role=UserRole.VENDOR, is_active=True, is_approved=True,
    )
    db.add_all([student, vendor])
    db.commit()
    db.refresh(student)
    db.refresh(vendor)

    slot = Slot(
        vendor_id=vendor.id,
        start_time=utcnow_naive() + timedelta(hours=1),
        end_time=utcnow_naive() + timedelta(hours=2),
        max_orders=10,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)

    order = Order(
        user_id=student.id, slot_id=slot.id, vendor_id=vendor.id,
        status=OrderStatus.PENDING, total_amount=total_amount,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return student, order


def _client_for(db, student):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_current_user():
        return {"id": student.id, "phone": student.phone, "role": "student"}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    client = TestClient(app)
    return client


def _mock_razorpay_create(monkeypatch):
    captured = {}

    class _FakeOrderApi:
        def create(self, payload):
            captured.update(payload)
            return {"id": "order_rzp_test_1"}

    class _FakeClient:
        order = _FakeOrderApi()

    monkeypatch.setattr("app.modules.payments.service.client", _FakeClient())
    return captured


@pytest.mark.parametrize(
    "rupees,expected_paise",
    [
        (Decimal("0.50"), 50),
        (Decimal("9999.99"), 999999),
    ],
)
def test_razorpay_initiate_amount_boundary(test_db_session, monkeypatch, rupees, expected_paise):
    student, order = _make_order(test_db_session, rupees)
    client = _client_for(test_db_session, student)
    captured = _mock_razorpay_create(monkeypatch)
    try:
        response = client.post(f"/payments/razorpay/initiate/{order.id}")
        assert response.status_code == 200
        body = response.json()
        assert body["amount"] == float(rupees)  # API returns rupees, unconverted
        assert captured["amount"] == expected_paise  # Razorpay always receives paise
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Group-cart equal split — rounding / conservation of total
# ---------------------------------------------------------------------------

def test_equal_split_whole_rupee_total_conserves_sum(test_db_session):
    # Paise-precise splitting: Rs100 / 3 isn't evenly divisible in any unit,
    # so the extra paisa lands on the first member (33.34/33.33/33.33), not
    # a whole extra rupee as the old whole-rupee-only split used to give.
    svc = GroupCartService(test_db_session)
    result = svc._equal_split([1, 2, 3], Decimal("100"))
    assert sum(result.values()) == Decimal("100")
    assert sorted(result.values()) == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]


def test_equal_split_fractional_total_conserves_sum(test_db_session):
    # _equal_split now distributes the remainder in integer paise (not whole
    # rupees), so a total that isn't evenly divisible among members no longer
    # fabricates or loses money: splitting Rs100.01 three ways must still sum
    # to exactly Rs100.01.
    svc = GroupCartService(test_db_session)
    result = svc._equal_split([1, 2, 3], Decimal("100.01"))
    assert sum(result.values()) == Decimal("100.01")
    assert sorted(result.values()) == [Decimal("33.33"), Decimal("33.34"), Decimal("33.34")]
