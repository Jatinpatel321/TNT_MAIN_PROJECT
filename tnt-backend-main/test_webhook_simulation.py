"""
Razorpay Webhook Simulation Tests
==================================
Tests POST /webhooks/razorpay/ for all event types with valid/invalid HMAC,
idempotency (duplicate events), and unknown payment IDs.

Scenarios:
  • payment.captured  → payment SUCCESS, order CONFIRMED, status:ok
  • payment.failed    → payment FAILED,  order CANCELLED, status:ok
  • refund.processed  → payment REFUNDED, order CANCELLED, status:ok
  • Invalid HMAC signature         → 400
  • Duplicate event                → 200, status:duplicate_ignored
  • Unknown razorpay_payment_id    → 200, status:ignored
  • Unknown event type             → 200, status:ok (no-op)

Phone number range: 8600000xxx
"""

import hashlib
import hmac as hmac_lib
import json
from datetime import UTC, datetime, timedelta

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.modules.payments.webhook as _webhook_module
from app.core.deps import get_db
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.orders.model import Order, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = "test_webhook_secret_8600"


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def make_sig(body: bytes) -> str:
    """Replicate the HMAC-SHA256 signature Razorpay sends."""
    return hmac_lib.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


def webhook_post(client: TestClient, payload: dict, secret: str = WEBHOOK_SECRET) -> object:
    """POST a signed webhook payload, returning the response."""
    body = json.dumps(payload).encode()
    sig = hmac_lib.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post(
        "/webhooks/razorpay/",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": sig,
        },
    )


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
    vendor = User(
        phone="8600000010",
        name="Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )
    student = User(phone="8600000001", name="Student", role=UserRole.STUDENT, is_active=True)
    test_db_session.add_all([vendor, student])
    test_db_session.commit()
    test_db_session.refresh(vendor)
    test_db_session.refresh(student)

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

    order = Order(
        user_id=student.id,
        slot_id=slot.id,
        vendor_id=vendor.id,
        status=OrderStatus.PLACED,
        total_amount=5000,
    )
    test_db_session.add(order)
    test_db_session.commit()
    test_db_session.refresh(order)

    payment = Payment(
        order_id=order.id,
        amount=5000,
        status=PaymentStatus.INITIATED,
        razorpay_payment_id="pay_test_8600",
        razorpay_order_id="order_test_8600",
    )
    test_db_session.add(payment)
    test_db_session.commit()
    test_db_session.refresh(payment)

    return {"vendor": vendor, "student": student, "slot": slot, "order": order, "payment": payment}


@pytest.fixture()
def client(test_db_session, seed_data):
    # Webhooks don't use get_current_user but we still override get_db
    # so the handler operates on the same in-memory SQLite as the test.
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    def override_get_current_user():
        student = seed_data["student"]
        return {"id": student.id, "phone": student.phone, "role": student.role.value}

    # The webhook module imports redis_client via `from app.core.redis import
    # redis_client`, creating a module-level alias that isn't covered by the
    # conftest autouse patch on app.core.redis.redis_client. Patch the alias
    # directly so each test gets an isolated in-memory Redis.
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    original_redis = _webhook_module.redis_client
    _webhook_module.redis_client = fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as c:
        yield c

    _webhook_module.redis_client = original_redis
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def set_webhook_secret(monkeypatch):
    """Ensure the webhook handler uses the same secret as make_sig()."""
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)


def _captured_payload(payment_id: str = "pay_test_8600") -> dict:
    return {"event": "payment.captured", "payload": {"payment": {"entity": {"id": payment_id}}}}


def _failed_payload(payment_id: str = "pay_test_8600") -> dict:
    return {"event": "payment.failed", "payload": {"payment": {"entity": {"id": payment_id}}}}


def _refund_payload(payment_id: str = "pay_test_8600") -> dict:
    return {"event": "refund.processed", "payload": {"payment": {"entity": {"id": payment_id}}}}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_payment_captured_marks_payment_success_and_order_confirmed(
    client, seed_data, test_db_session
):
    resp = webhook_post(client, _captured_payload())
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    test_db_session.expire_all()
    payment = test_db_session.get(Payment, seed_data["payment"].id)
    order = test_db_session.get(Order, seed_data["order"].id)
    assert payment.status == PaymentStatus.SUCCESS
    assert order.status == OrderStatus.CONFIRMED


def test_payment_failed_marks_payment_failed_and_order_cancelled(
    client, seed_data, test_db_session
):
    resp = webhook_post(client, _failed_payload())
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    test_db_session.expire_all()
    payment = test_db_session.get(Payment, seed_data["payment"].id)
    order = test_db_session.get(Order, seed_data["order"].id)
    assert payment.status == PaymentStatus.FAILED
    assert order.status == OrderStatus.CANCELLED


def test_refund_processed_marks_payment_refunded_and_order_cancelled(
    client, seed_data, test_db_session
):
    # First mark the payment as SUCCESS (refunds occur after capture)
    payment = seed_data["payment"]
    payment.status = PaymentStatus.SUCCESS
    test_db_session.commit()

    resp = webhook_post(client, _refund_payload())
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    test_db_session.expire_all()
    payment = test_db_session.get(Payment, seed_data["payment"].id)
    order = test_db_session.get(Order, seed_data["order"].id)
    assert payment.status == PaymentStatus.REFUNDED
    assert order.status == OrderStatus.CANCELLED


def test_invalid_hmac_signature_returns_400(client, seed_data):
    payload = _captured_payload()
    body = json.dumps(payload).encode()
    resp = client.post(
        "/webhooks/razorpay/",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": "deadbeef" * 8,  # wrong signature
        },
    )
    assert resp.status_code == 400


def test_duplicate_event_returns_duplicate_ignored(client, seed_data):
    # First call succeeds
    first = webhook_post(client, _captured_payload())
    assert first.status_code == 200
    assert first.json()["status"] == "ok"

    # Identical second call → idempotency guard fires
    second = webhook_post(client, _captured_payload())
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate_ignored"


def test_unknown_razorpay_payment_id_returns_ignored(client, seed_data):
    resp = webhook_post(client, _captured_payload(payment_id="pay_nonexistent_xyz"))
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


def test_unknown_event_type_returns_ok_and_does_not_crash(client, seed_data, test_db_session):
    payload = {
        "event": "some.unknown.event",
        "payload": {"payment": {"entity": {"id": "pay_test_8600"}}},
    }
    resp = webhook_post(client, payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Payment and order should be untouched (no handler branch matched)
    test_db_session.expire_all()
    payment = test_db_session.get(Payment, seed_data["payment"].id)
    assert payment.status == PaymentStatus.INITIATED
