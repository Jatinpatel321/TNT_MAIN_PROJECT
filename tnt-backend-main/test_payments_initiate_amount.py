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
    test_db_session.add(slot)
    test_db_session.commit()
    test_db_session.refresh(slot)

    valid_order = Order(
        user_id=student.id,
        slot_id=slot.id,
        vendor_id=vendor.id,
        status=OrderStatus.PENDING,
        total_amount=7350,
    )
    invalid_order = Order(
        user_id=student.id,
        slot_id=slot.id,
        vendor_id=vendor.id,
        status=OrderStatus.PENDING,
        total_amount=0,
    )
    test_db_session.add_all([valid_order, invalid_order])
    test_db_session.commit()
    test_db_session.refresh(valid_order)
    test_db_session.refresh(invalid_order)

    return {"valid_order": valid_order, "invalid_order": invalid_order}


@pytest.fixture()
def auth_context(seed_data):
    student = seed_data["valid_order"]
    return {"id": student.user_id, "phone": "8200000001", "role": "student"}


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


def test_initiate_uses_persisted_order_total_amount(client, seed_data, monkeypatch):
    captured = _mock_razorpay_create(monkeypatch)

    response = client.post(f"/payments/razorpay/initiate/{seed_data['valid_order'].id}")
    assert response.status_code == 200

    body = response.json()
    assert body["amount"] == 7350
    assert captured["amount"] == 7350


def test_initiate_rejects_invalid_order_amount(client, seed_data, monkeypatch):
    _mock_razorpay_create(monkeypatch)

    response = client.post(f"/payments/razorpay/initiate/{seed_data['invalid_order'].id}")
    assert response.status_code == 400
    assert response.json()["detail"] == "Order amount is invalid"
