"""
Stationery Payment Audit Trail — QA tests
POST /stationery/payments/initiate/{job_id}
POST /stationery/payments/verify/{job_id}
POST /payments/razorpay/refund/{payment_id}

Acceptance criteria (PROMPT 7):
  • Every stationery job payment creates a traceable Payment record.
  • Payment.stationery_job_id is set; Payment.order_id is NULL.
  • Payment moves INITIATED → SUCCESS on verify; amount and razorpay ids recorded.
  • Refund endpoint works for stationery payments:
      - Payment flips to REFUNDED.
      - Only SUCCESS payments are refundable.
      - Unauthorized users cannot trigger a refund.
"""

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.stationery.job_model import JobStatus, StationeryJob
from app.modules.stationery.service_model import StationeryService
from app.modules.users.model import User, UserRole


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RAZORPAY_SECRET = "test_secret"
FAKE_RZP_ORDER_ID = "order_stationery_abc123"
FAKE_RZP_PAYMENT_ID = "pay_stationery_xyz789"


def _make_signature(razorpay_order_id: str, razorpay_payment_id: str) -> str:
    body = f"{razorpay_order_id}|{razorpay_payment_id}"
    return hmac.new(
        bytes(RAZORPAY_SECRET, "utf-8"),
        bytes(body, "utf-8"),
        hashlib.sha256,
    ).hexdigest()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
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
def seed(db_session):
    """Minimal graph: student, stationery vendor, service, job (READY, unpaid)."""
    student = User(
        phone="9800000001", name="PrintStudent", role=UserRole.STUDENT, is_active=True
    )
    vendor = User(
        phone="9800000002",
        name="PrintVendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )
    db_session.add_all([student, vendor])
    db_session.commit()
    db_session.refresh(student)
    db_session.refresh(vendor)

    service = StationeryService(
        vendor_id=vendor.id,
        name="B&W Print",
        price_per_unit=200,
        unit="page",
        is_available=True,
    )
    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)

    job = StationeryJob(
        user_id=student.id,
        vendor_id=vendor.id,
        service_id=service.id,
        quantity=5,
        amount=1000,  # 5 × 200 paise
        is_paid=False,
        status=JobStatus.READY,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    return {
        "student": student,
        "vendor": vendor,
        "service": service,
        "job": job,
    }


def _make_client(db_session, user: User) -> TestClient:
    """Build a TestClient with DB and auth overrides for *user*."""
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: {
        "id": user.id,
        "phone": user.phone,
        "role": user.role.value,
    }
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Test 1 — initiate creates Payment row with stationery_job_id
# ---------------------------------------------------------------------------


def test_initiate_creates_payment_record(db_session, seed):
    job = seed["job"]
    student = seed["student"]

    mock_rzp_order = {"id": FAKE_RZP_ORDER_ID, "amount": job.amount}

    with (
        patch("app.modules.stationery.payment_router.client") as mock_client,
        patch.dict("os.environ", {"RAZORPAY_KEY_ID": "rzp_test_key"}),
    ):
        mock_client.order.create.return_value = mock_rzp_order

        client = _make_client(db_session, student)
        resp = client.post(f"/stationery/payments/initiate/{job.id}")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "payment_id" in body
    assert body["razorpay_order_id"] == FAKE_RZP_ORDER_ID
    assert body["amount"] == job.amount

    # Verify the Payment row was actually persisted
    payment = db_session.query(Payment).filter(Payment.id == body["payment_id"]).first()
    assert payment is not None
    assert payment.stationery_job_id == job.id
    assert payment.order_id is None
    assert payment.status == PaymentStatus.INITIATED
    assert payment.amount == job.amount
    assert payment.razorpay_order_id == FAKE_RZP_ORDER_ID


# ---------------------------------------------------------------------------
# Test 2 — verify flips Payment to SUCCESS and stores razorpay ids
# ---------------------------------------------------------------------------


def test_verify_updates_payment_to_success(db_session, seed):
    job = seed["job"]
    student = seed["student"]

    # Manually create the INITIATED payment (as initiate endpoint would)
    payment = Payment(
        stationery_job_id=job.id,
        order_id=None,
        amount=job.amount,
        razorpay_order_id=FAKE_RZP_ORDER_ID,
        status=PaymentStatus.INITIATED,
    )
    db_session.add(payment)
    job.razorpay_order_id = FAKE_RZP_ORDER_ID
    db_session.commit()
    db_session.refresh(payment)

    sig = _make_signature(FAKE_RZP_ORDER_ID, FAKE_RZP_PAYMENT_ID)

    with (
        patch("app.modules.stationery.payment_router.notify_user"),
        patch("app.modules.stationery.payment_router.add_ledger_entry"),
        patch.dict("os.environ", {"RAZORPAY_KEY_SECRET": RAZORPAY_SECRET}),
    ):
        client = _make_client(db_session, student)
        resp = client.post(
            f"/stationery/payments/verify/{job.id}",
            params={
                "razorpay_payment_id": FAKE_RZP_PAYMENT_ID,
                "razorpay_order_id": FAKE_RZP_ORDER_ID,
                "razorpay_signature": sig,
            },
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["payment_id"] == payment.id

    db_session.refresh(payment)
    assert payment.status == PaymentStatus.SUCCESS
    assert payment.razorpay_payment_id == FAKE_RZP_PAYMENT_ID
    assert payment.razorpay_signature == sig

    db_session.refresh(job)
    assert job.is_paid is True


# ---------------------------------------------------------------------------
# Test 3 — refund works for a stationery Payment
# ---------------------------------------------------------------------------


def test_refund_stationery_payment(db_session, seed):
    job = seed["job"]
    student = seed["student"]

    # Create a SUCCESS payment for the stationery job
    payment = Payment(
        stationery_job_id=job.id,
        order_id=None,
        amount=job.amount,
        razorpay_order_id=FAKE_RZP_ORDER_ID,
        razorpay_payment_id=FAKE_RZP_PAYMENT_ID,
        status=PaymentStatus.SUCCESS,
    )
    db_session.add(payment)
    job.is_paid = True
    db_session.commit()
    db_session.refresh(payment)

    mock_refund = {"id": "rfnd_abc123"}

    with (
        patch("app.modules.payments.service.client") as mock_client,
        patch("app.modules.payments.service.notify_user"),
        patch("app.modules.payments.service.add_ledger_entry"),
    ):
        mock_client.payment.refund.return_value = mock_refund
        client = _make_client(db_session, student)
        resp = client.post(f"/payments/razorpay/refund/{payment.id}")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["refund_id"] == "rfnd_abc123"

    db_session.refresh(payment)
    assert payment.status == PaymentStatus.REFUNDED
    assert payment.razorpay_refund_id == "rfnd_abc123"


# ---------------------------------------------------------------------------
# Test 4 — only SUCCESS payments are refundable
# ---------------------------------------------------------------------------


def test_refund_non_success_payment_is_rejected(db_session, seed):
    job = seed["job"]
    student = seed["student"]

    # INITIATED payment — must not be refundable
    payment = Payment(
        stationery_job_id=job.id,
        order_id=None,
        amount=job.amount,
        razorpay_order_id=FAKE_RZP_ORDER_ID,
        status=PaymentStatus.INITIATED,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)

    client = _make_client(db_session, student)
    resp = client.post(f"/payments/razorpay/refund/{payment.id}")

    assert resp.status_code == 400
    assert "Only successful payments" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Test 5 — unauthorized user cannot refund another user's stationery payment
# ---------------------------------------------------------------------------


def test_refund_unauthorized_user_rejected(db_session, seed):
    job = seed["job"]

    # A different student
    other = User(phone="9800000099", name="Other", role=UserRole.STUDENT, is_active=True)
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    payment = Payment(
        stationery_job_id=job.id,
        order_id=None,
        amount=job.amount,
        razorpay_order_id=FAKE_RZP_ORDER_ID,
        razorpay_payment_id=FAKE_RZP_PAYMENT_ID,
        status=PaymentStatus.SUCCESS,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)

    client = _make_client(db_session, other)  # other student — not the owner
    resp = client.post(f"/payments/razorpay/refund/{payment.id}")

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test 6 — Payment record has no order_id (null) for stationery payments
# ---------------------------------------------------------------------------


def test_payment_has_null_order_id(db_session, seed):
    job = seed["job"]

    payment = Payment(
        stationery_job_id=job.id,
        order_id=None,
        amount=500,
        status=PaymentStatus.INITIATED,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)

    assert payment.order_id is None
    assert payment.stationery_job_id == job.id


# ---------------------------------------------------------------------------
# Test 7 — job already paid guard still works
# ---------------------------------------------------------------------------


def test_initiate_blocked_when_already_paid(db_session, seed):
    job = seed["job"]
    student = seed["student"]
    job.is_paid = True
    db_session.commit()

    client = _make_client(db_session, student)
    resp = client.post(f"/stationery/payments/initiate/{job.id}")

    assert resp.status_code == 400
    assert "already paid" in resp.json()["detail"]
