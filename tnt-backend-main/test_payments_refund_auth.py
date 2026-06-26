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
from app.modules.payments.model import Payment, PaymentStatus
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
    owner = User(phone="8100000001", name="Owner", role=UserRole.STUDENT, is_active=True)
    other_user = User(phone="8100000002", name="Other", role=UserRole.STUDENT, is_active=True)
    admin = User(phone="8100000003", name="Admin", role=UserRole.ADMIN, is_active=True)
    vendor = User(
        phone="8100000010",
        name="Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )

    test_db_session.add_all([owner, other_user, admin, vendor])
    test_db_session.commit()
    test_db_session.refresh(owner)
    test_db_session.refresh(other_user)
    test_db_session.refresh(admin)
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

    order = Order(
        user_id=owner.id,
        slot_id=slot.id,
        vendor_id=vendor.id,
        status=OrderStatus.CONFIRMED,
    )
    test_db_session.add(order)
    test_db_session.commit()
    test_db_session.refresh(order)

    payment = Payment(
        order_id=order.id,
        amount=5000,
        status=PaymentStatus.SUCCESS,
        razorpay_order_id="order_test",
        razorpay_payment_id="pay_test",
    )
    test_db_session.add(payment)
    test_db_session.commit()
    test_db_session.refresh(payment)

    return {
        "owner": owner,
        "other_user": other_user,
        "admin": admin,
        "vendor": vendor,
        "order": order,
        "payment": payment,
    }


@pytest.fixture()
def auth_context(seed_data):
    owner = seed_data["owner"]
    return {"id": owner.id, "phone": owner.phone, "role": owner.role.value}


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


@pytest.fixture()
def client_no_auth(test_db_session):
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _mock_refund(monkeypatch):
    class _FakePaymentApi:
        def refund(self, razorpay_payment_id, payload):
            assert razorpay_payment_id
            assert "amount" in payload
            return {"id": "rfnd_test_1"}

    class _FakeClient:
        payment = _FakePaymentApi()

    monkeypatch.setattr("app.modules.payments.service.client", _FakeClient())


def test_refund_requires_auth(client_no_auth, seed_data, monkeypatch):
    _mock_refund(monkeypatch)

    response = client_no_auth.post(f"/payments/razorpay/refund/{seed_data['payment'].id}")
    assert response.status_code in (401, 403)


def test_refund_denies_non_owner_non_admin(client, seed_data, auth_context, monkeypatch):
    _mock_refund(monkeypatch)

    other_user = seed_data["other_user"]
    auth_context.update({"id": other_user.id, "phone": other_user.phone, "role": other_user.role.value})

    response = client.post(f"/payments/razorpay/refund/{seed_data['payment'].id}")
    assert response.status_code == 403


def test_refund_allows_owner(client, seed_data, auth_context, test_db_session, monkeypatch):
    _mock_refund(monkeypatch)

    owner = seed_data["owner"]
    auth_context.update({"id": owner.id, "phone": owner.phone, "role": owner.role.value})

    response = client.post(f"/payments/razorpay/refund/{seed_data['payment'].id}")
    assert response.status_code == 200

    payment = test_db_session.query(Payment).filter(Payment.id == seed_data["payment"].id).first()
    assert payment is not None
    assert payment.status == PaymentStatus.REFUNDED


def test_refund_allows_admin(client, seed_data, auth_context, test_db_session, monkeypatch):
    _mock_refund(monkeypatch)

    payment = test_db_session.query(Payment).filter(Payment.id == seed_data["payment"].id).first()
    payment.status = PaymentStatus.SUCCESS
    test_db_session.commit()

    admin = seed_data["admin"]
    auth_context.update({"id": admin.id, "phone": admin.phone, "role": admin.role.value})

    response = client.post(f"/payments/razorpay/refund/{seed_data['payment'].id}")
    assert response.status_code == 200
