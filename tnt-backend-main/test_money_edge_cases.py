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
        (10, 1000),
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
        (1000, Decimal("10.00")),
        (999999, Decimal("9999.99")),
        (7350, Decimal("73.50")),
        (1, Decimal("0.01")),
    ],
)
def test_from_paise_boundary_values(paise, expected_rupees):
    assert from_paise(paise) == expected_rupees


@pytest.mark.parametrize("rupees", [0, 0.5, 1, 10, 9999.99, 73.5, 0.01, 12345.67])
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
        (Decimal("1"), 100),
        (Decimal("10"), 1000),
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


def test_custom_split_cents_precision_can_spuriously_fail_validation(test_db_session):
    # Characterizes an existing (pre-migration) design gap, not a bug
    # introduced by this migration: _build_split_reconciliation's CUSTOM
    # branch does `round(split.amount or 0)` with no ndigits, which snaps
    # each member's Decimal custom amount straight to the nearest whole
    # rupee (Python's zero-arg round() on Decimal returns an int) *before*
    # comparing the sum against the group total. A perfectly valid,
    # cents-summing custom split (33.34 + 33.33 + 33.33 == 100.00 exactly)
    # gets rounded member-by-member to 33 + 33 + 33 = 99, which then fails
    # to match the (separately, whole-rupee-pre-rounded) group total of 100
    # — a spurious 400 for a customer who did the math correctly. Flagged
    # for a product decision, not fixed here (same whole-rupee-granularity
    # design already flagged in the money-migration memory notes).
    from fastapi import HTTPException
    from app.modules.group_cart.model import GroupPaymentSplit, PaymentSplitType

    svc = GroupCartService(test_db_session)
    splits = [
        GroupPaymentSplit(group_id=1, user_id=1, amount=Decimal("33.34"), split_type=PaymentSplitType.CUSTOM),
        GroupPaymentSplit(group_id=1, user_id=2, amount=Decimal("33.33"), split_type=PaymentSplitType.CUSTOM),
        GroupPaymentSplit(group_id=1, user_id=3, amount=Decimal("33.33"), split_type=PaymentSplitType.CUSTOM),
    ]
    test_db_session.add_all(splits)
    test_db_session.commit()

    member_totals = {1: 33, 2: 33, 3: 34}  # sums to 100, whole-rupee per upstream rounding
    with pytest.raises(HTTPException) as exc_info:
        svc._build_split_reconciliation(group_id=1, member_totals=member_totals, owner_id=1)
    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Refunds — full-amount boundary + partial-refund characterization
# ---------------------------------------------------------------------------

def _mock_razorpay_refund(monkeypatch):
    captured = {}

    class _FakePaymentApi:
        def refund(self, razorpay_payment_id, payload):
            captured["razorpay_payment_id"] = razorpay_payment_id
            captured.update(payload)
            return {"id": "rfnd_test_1"}

    class _FakeClient:
        payment = _FakePaymentApi()

    monkeypatch.setattr("app.modules.payments.service.client", _FakeClient())
    return captured


def _make_paid_order(db, total_amount):
    from app.modules.payments.model import Payment, PaymentStatus

    student, order = _make_order(db, total_amount)
    order.status = OrderStatus.CONFIRMED
    payment = Payment(
        order_id=order.id, amount=total_amount, status=PaymentStatus.SUCCESS,
        razorpay_order_id="order_rzp_test", razorpay_payment_id="pay_rzp_test",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return student, order, payment


@pytest.mark.parametrize("rupees,expected_paise", [(Decimal("1"), 100), (Decimal("9999.99"), 999999)])
def test_refund_sends_exact_paise_amount(test_db_session, monkeypatch, rupees, expected_paise):
    student, order, payment = _make_paid_order(test_db_session, rupees)
    client = _client_for(test_db_session, student)
    captured = _mock_razorpay_refund(monkeypatch)
    try:
        response = client.post(f"/payments/razorpay/refund/{payment.id}")
        assert response.status_code == 200
        assert captured["amount"] == expected_paise
    finally:
        app.dependency_overrides.clear()


def test_partial_refund_request_still_executes_full_gateway_refund(test_db_session, monkeypatch):
    # Characterizes a pre-existing (not migration-introduced) product gap:
    # RefundRequest.amount lets an admin/customer record a partial-refund
    # *request*, but admin/router.py's approve_refund_request() delegates to
    # payments/service.py::refund_payment(), which always refunds the FULL
    # payment.amount via Razorpay — RefundRequest.amount is persisted but
    # never actually passed to the gateway. There is no partial-refund
    # execution path in this codebase today.
    from app.modules.payments.model import RefundRequest, RefundRequestStatus
    from app.modules.users.model import User, UserRole
    from app.core.security import get_current_user as _guc

    student, order, payment = _make_paid_order(test_db_session, Decimal("100.00"))
    admin = User(phone="8400000099", name="Admin", role=UserRole.ADMIN, is_active=True)
    test_db_session.add(admin)
    test_db_session.commit()
    test_db_session.refresh(admin)

    partial_request = RefundRequest(
        order_id=order.id, payment_id=payment.id, user_id=student.id,
        amount=Decimal("25.00"),  # customer/admin only ever wanted a quarter refunded
        status=RefundRequestStatus.PENDING,
    )
    test_db_session.add(partial_request)
    test_db_session.commit()
    test_db_session.refresh(partial_request)

    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    def override_get_current_user():
        return {"id": admin.id, "phone": admin.phone, "role": "admin"}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[_guc] = override_get_current_user
    captured = _mock_razorpay_refund(monkeypatch)
    try:
        client = TestClient(app)
        response = client.post(f"/admin/refund-requests/{partial_request.id}/approve")
        assert response.status_code == 200
        # The gateway actually received the FULL payment amount (10000 paise),
        # not the requested partial amount (2500 paise) — documents current
        # behavior, not a migration bug.
        assert captured["amount"] == 10000
        assert captured["amount"] != to_paise(partial_request.amount)
    finally:
        app.dependency_overrides.clear()
