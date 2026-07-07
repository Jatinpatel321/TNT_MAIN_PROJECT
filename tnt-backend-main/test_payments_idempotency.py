"""
Payment idempotency tests — POST /payments/razorpay/initiate/{order_id}

Verifies that sending an X-Idempotency-Key header prevents duplicate Razorpay
orders and duplicate Payment DB rows regardless of how many times the caller
retries the endpoint.

Acceptance criteria (from PROMPT 5):
  • Multiple initiate calls with the same key → only ONE Payment record in DB.
  • The second (and subsequent) calls return the *existing* payment_id.
  • Razorpay is NOT called again on a replay.
  • Calls without a key remain backward-compatible (no dedup applied).
  • A different key on the same order creates a distinct Payment record.
  • The same key used on two *different* orders creates two distinct records
    (the key is scoped per order).
"""

import uuid
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
from app.modules.payments.model import Payment
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
    """Minimal graph: student, vendor, slot, two orders."""
    student = User(phone="9900000001", name="Student", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="9900000010",
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
        max_orders=20,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    test_db_session.add(slot)
    test_db_session.commit()
    test_db_session.refresh(slot)

    order_a = Order(
        user_id=student.id,
        slot_id=slot.id,
        vendor_id=vendor.id,
        status=OrderStatus.PENDING,
        total_amount=10000,
    )
    order_b = Order(
        user_id=student.id,
        slot_id=slot.id,
        vendor_id=vendor.id,
        status=OrderStatus.PENDING,
        total_amount=20000,
    )
    test_db_session.add_all([order_a, order_b])
    test_db_session.commit()
    test_db_session.refresh(order_a)
    test_db_session.refresh(order_b)

    return {"student": student, "order_a": order_a, "order_b": order_b}


@pytest.fixture()
def api_client(test_db_session, seed):
    def override_db():
        try:
            yield test_db_session
        finally:
            pass

    def override_user():
        return {
            "id": seed["student"].id,
            "phone": seed["student"].phone,
            "role": "student",
        }

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Razorpay mock helper
# ---------------------------------------------------------------------------

_RAZORPAY_CALL_COUNT = 0


def _mock_razorpay(monkeypatch) -> list[dict]:
    """
    Replace the Razorpay client with a fake that records every call and returns
    a deterministic order id.  Returns the list that accumulates call records.
    """
    calls: list[dict] = []

    class _FakeOrderApi:
        _counter = 0

        def create(self, payload: dict) -> dict:
            _FakeOrderApi._counter += 1
            record = {**payload, "_call_index": _FakeOrderApi._counter}
            calls.append(record)
            return {"id": f"rzp_order_fake_{_FakeOrderApi._counter}"}

    class _FakeClient:
        order = _FakeOrderApi()

    monkeypatch.setattr("app.modules.payments.service.client", _FakeClient())
    return calls


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFirstCall:
    """The first call with or without a key behaves like the original endpoint."""

    def test_first_call_with_key_returns_200(self, api_client, seed, monkeypatch):
        _mock_razorpay(monkeypatch)
        key = str(uuid.uuid4())
        resp = api_client.post(
            f"/payments/razorpay/initiate/{seed['order_a'].id}",
            headers={"X-Idempotency-Key": key},
        )
        assert resp.status_code == 200

    def test_first_call_returns_idempotent_false(self, api_client, seed, monkeypatch):
        _mock_razorpay(monkeypatch)
        key = str(uuid.uuid4())
        body = api_client.post(
            f"/payments/razorpay/initiate/{seed['order_a'].id}",
            headers={"X-Idempotency-Key": key},
        ).json()
        assert body["idempotent"] is False

    def test_first_call_hits_razorpay(self, api_client, seed, monkeypatch):
        calls = _mock_razorpay(monkeypatch)
        key = str(uuid.uuid4())
        api_client.post(
            f"/payments/razorpay/initiate/{seed['order_a'].id}",
            headers={"X-Idempotency-Key": key},
        )
        assert len(calls) == 1

    def test_first_call_without_key_returns_200(self, api_client, seed, monkeypatch):
        _mock_razorpay(monkeypatch)
        resp = api_client.post(f"/payments/razorpay/initiate/{seed['order_a'].id}")
        assert resp.status_code == 200

    def test_first_call_without_key_returns_idempotent_false(
        self, api_client, seed, monkeypatch
    ):
        _mock_razorpay(monkeypatch)
        body = api_client.post(
            f"/payments/razorpay/initiate/{seed['order_a'].id}"
        ).json()
        assert body["idempotent"] is False


class TestReplay:
    """A second request with the same key must short-circuit without Razorpay."""

    def _initiate(self, api_client, order_id, key, monkeypatch, calls=None):
        """Helper that (optionally) mocks Razorpay and fires the request."""
        if calls is None:
            calls = _mock_razorpay(monkeypatch)
        return api_client.post(
            f"/payments/razorpay/initiate/{order_id}",
            headers={"X-Idempotency-Key": key},
        ), calls

    def test_replay_returns_same_payment_id(self, api_client, seed, monkeypatch):
        calls = _mock_razorpay(monkeypatch)
        key = str(uuid.uuid4())
        order_id = seed["order_a"].id

        first = api_client.post(
            f"/payments/razorpay/initiate/{order_id}",
            headers={"X-Idempotency-Key": key},
        ).json()
        second = api_client.post(
            f"/payments/razorpay/initiate/{order_id}",
            headers={"X-Idempotency-Key": key},
        ).json()

        assert first["payment_id"] == second["payment_id"]

    def test_replay_returns_idempotent_true(self, api_client, seed, monkeypatch):
        _mock_razorpay(monkeypatch)
        key = str(uuid.uuid4())
        order_id = seed["order_a"].id

        api_client.post(
            f"/payments/razorpay/initiate/{order_id}",
            headers={"X-Idempotency-Key": key},
        )
        second = api_client.post(
            f"/payments/razorpay/initiate/{order_id}",
            headers={"X-Idempotency-Key": key},
        ).json()

        assert second["idempotent"] is True

    def test_replay_does_not_call_razorpay_again(self, api_client, seed, monkeypatch):
        calls = _mock_razorpay(monkeypatch)
        key = str(uuid.uuid4())
        order_id = seed["order_a"].id

        for _ in range(5):  # 5 retries all with the same key
            api_client.post(
                f"/payments/razorpay/initiate/{order_id}",
                headers={"X-Idempotency-Key": key},
            )

        # Razorpay must have been called exactly once (the first request)
        assert len(calls) == 1

    def test_replay_produces_exactly_one_db_row(
        self, api_client, seed, monkeypatch, test_db_session
    ):
        _mock_razorpay(monkeypatch)
        key = str(uuid.uuid4())
        order_id = seed["order_a"].id

        for _ in range(4):
            api_client.post(
                f"/payments/razorpay/initiate/{order_id}",
                headers={"X-Idempotency-Key": key},
            )

        row_count = (
            test_db_session.query(Payment)
            .filter(Payment.order_id == order_id)
            .count()
        )
        assert row_count == 1

    def test_replay_returns_same_razorpay_order_id(self, api_client, seed, monkeypatch):
        _mock_razorpay(monkeypatch)
        key = str(uuid.uuid4())
        order_id = seed["order_a"].id

        first = api_client.post(
            f"/payments/razorpay/initiate/{order_id}",
            headers={"X-Idempotency-Key": key},
        ).json()
        second = api_client.post(
            f"/payments/razorpay/initiate/{order_id}",
            headers={"X-Idempotency-Key": key},
        ).json()

        assert first["razorpay_order_id"] == second["razorpay_order_id"]


class TestKeyScoping:
    """The key is scoped to (order_id); the same key on two orders is independent."""

    def test_same_key_different_orders_creates_two_payments(
        self, api_client, seed, monkeypatch, test_db_session
    ):
        _mock_razorpay(monkeypatch)
        key = str(uuid.uuid4())  # same key, two different orders

        resp_a = api_client.post(
            f"/payments/razorpay/initiate/{seed['order_a'].id}",
            headers={"X-Idempotency-Key": key},
        ).json()
        resp_b = api_client.post(
            f"/payments/razorpay/initiate/{seed['order_b'].id}",
            headers={"X-Idempotency-Key": key},
        ).json()

        # Both create new payments (idempotent=False) and have different IDs
        assert resp_a["idempotent"] is False
        assert resp_b["idempotent"] is False
        assert resp_a["payment_id"] != resp_b["payment_id"]

    def test_different_key_same_order_creates_new_payment(
        self, api_client, seed, monkeypatch, test_db_session
    ):
        calls = _mock_razorpay(monkeypatch)
        order_id = seed["order_a"].id

        resp_1 = api_client.post(
            f"/payments/razorpay/initiate/{order_id}",
            headers={"X-Idempotency-Key": str(uuid.uuid4())},
        ).json()
        resp_2 = api_client.post(
            f"/payments/razorpay/initiate/{order_id}",
            headers={"X-Idempotency-Key": str(uuid.uuid4())},
        ).json()

        # Different keys → two distinct payments, Razorpay called twice
        assert resp_1["payment_id"] != resp_2["payment_id"]
        assert resp_1["idempotent"] is False
        assert resp_2["idempotent"] is False
        assert len(calls) == 2

    def test_no_key_is_always_fresh(
        self, api_client, seed, monkeypatch, test_db_session
    ):
        """Requests without a key are never deduped (backward-compatible)."""
        _mock_razorpay(monkeypatch)
        order_id = seed["order_a"].id

        r1 = api_client.post(f"/payments/razorpay/initiate/{order_id}").json()
        r2 = api_client.post(f"/payments/razorpay/initiate/{order_id}").json()

        assert r1["payment_id"] != r2["payment_id"]
        row_count = (
            test_db_session.query(Payment)
            .filter(Payment.order_id == order_id)
            .count()
        )
        assert row_count == 2
