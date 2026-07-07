from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.redis import redis_client
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order
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
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def seed_data(test_db_session):
    student = User(phone="9600000001", name="Student", role=UserRole.STUDENT, is_active=True)
    vendor_a = User(
        phone="9600000010",
        name="Vendor A",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )
    vendor_b = User(
        phone="9600000011",
        name="Vendor B",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )
    test_db_session.add_all([student, vendor_a, vendor_b])
    test_db_session.commit()
    test_db_session.refresh(student)
    test_db_session.refresh(vendor_a)
    test_db_session.refresh(vendor_b)

    slot = Slot(
        vendor_id=vendor_a.id,
        start_time=utcnow_naive() + timedelta(hours=1),
        end_time=utcnow_naive() + timedelta(hours=2),
        max_orders=10,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    item_a1 = MenuItem(
        vendor_id=vendor_a.id,
        name="Burger",
        description="A1",
        price=120,
        image_url="https://example.com/a1.png",
        is_available=True,
    )
    item_a2 = MenuItem(
        vendor_id=vendor_a.id,
        name="Fries",
        description="A2",
        price=80,
        image_url="https://example.com/a2.png",
        is_available=True,
    )
    item_b1 = MenuItem(
        vendor_id=vendor_b.id,
        name="Wrap",
        description="B1",
        price=90,
        image_url="https://example.com/b1.png",
        is_available=True,
    )

    test_db_session.add_all([slot, item_a1, item_a2, item_b1])
    test_db_session.commit()
    test_db_session.refresh(slot)
    test_db_session.refresh(item_a1)
    test_db_session.refresh(item_a2)
    test_db_session.refresh(item_b1)

    return {
        "student": student,
        "slot": slot,
        "item_a1": item_a1,
        "item_a2": item_a2,
        "item_b1": item_b1,
    }


@pytest.fixture()
def auth_context(seed_data):
    student = seed_data["student"]
    return {"id": student.id, "phone": student.phone, "role": student.role.value}


@pytest.fixture(autouse=True)
def clear_solo_cart(seed_data):
    key = f"tnt:cart:user:{seed_data['student'].id}"
    redis_client.delete(key)
    yield
    redis_client.delete(key)


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


def test_solo_cart_add_multiple_items_same_vendor(client, seed_data):
    add_1 = client.post(
        "/cart/items",
        json={"menu_item_id": seed_data["item_a1"].id, "quantity": 2},
    )
    assert add_1.status_code == 200

    add_2 = client.post(
        "/cart/items",
        json={"menu_item_id": seed_data["item_a2"].id, "quantity": 1},
    )
    assert add_2.status_code == 200

    cart = client.get("/cart/")
    assert cart.status_code == 200
    body = cart.json()

    assert body["vendor_id"] == seed_data["item_a1"].vendor_id
    assert body["total_items"] == 3
    assert body["total_amount"] == (2 * seed_data["item_a1"].price) + seed_data["item_a2"].price
    assert len(body["items"]) == 2


def test_solo_cart_rejects_cross_vendor_items(client, seed_data):
    add_a = client.post(
        "/cart/items",
        json={"menu_item_id": seed_data["item_a1"].id, "quantity": 1},
    )
    assert add_a.status_code == 200

    add_b = client.post(
        "/cart/items",
        json={"menu_item_id": seed_data["item_b1"].id, "quantity": 1},
    )
    assert add_b.status_code == 400
    assert add_b.json()["detail"] == "Cannot add items from multiple vendors"


def test_solo_cart_remove_and_clear(client, seed_data):
    add = client.post(
        "/cart/items",
        json={"menu_item_id": seed_data["item_a1"].id, "quantity": 1},
    )
    assert add.status_code == 200

    remove = client.delete(f"/cart/items/{seed_data['item_a1'].id}")
    assert remove.status_code == 200
    assert remove.json()["total_items"] == 0

    add_again = client.post(
        "/cart/items",
        json={"menu_item_id": seed_data["item_a2"].id, "quantity": 2},
    )
    assert add_again.status_code == 200

    clear = client.delete("/cart/")
    assert clear.status_code == 200

    cart = client.get("/cart/")
    assert cart.status_code == 200
    assert cart.json()["total_items"] == 0
    assert cart.json()["total_amount"] == 0


def _mock_razorpay_create(monkeypatch):
    class _FakeOrderApi:
        def create(self, payload):
            return {"id": "order_rzp_solo_cart"}

    class _FakeClient:
        order = _FakeOrderApi()

    monkeypatch.setattr("app.modules.payments.service.client", _FakeClient())


def _mock_razorpay_create_fail(monkeypatch):
    class _FakeOrderApi:
        def create(self, payload):
            raise RuntimeError("razorpay unavailable")

    class _FakeClient:
        order = _FakeOrderApi()

    monkeypatch.setattr("app.modules.payments.service.client", _FakeClient())


def test_solo_cart_checkout_pipes_to_order_and_payment(client, seed_data, test_db_session, monkeypatch):
    add_1 = client.post(
        "/cart/items",
        json={"menu_item_id": seed_data["item_a1"].id, "quantity": 1},
    )
    assert add_1.status_code == 200

    add_2 = client.post(
        "/cart/items",
        json={"menu_item_id": seed_data["item_a2"].id, "quantity": 2},
    )
    assert add_2.status_code == 200

    checkout = client.post(f"/cart/checkout/{seed_data['slot'].id}")
    assert checkout.status_code == 200
    checkout_body = checkout.json()
    assert str(checkout_body["status"]).lower().endswith("placed")

    order_id = checkout_body["order_id"]
    order = test_db_session.query(Order).filter(Order.id == order_id).first()
    assert order is not None
    assert order.total_amount == seed_data["item_a1"].price + (2 * seed_data["item_a2"].price)

    cart = client.get("/cart/")
    assert cart.status_code == 200
    assert cart.json()["total_items"] == 0

    _mock_razorpay_create(monkeypatch)
    initiate = client.post(f"/payments/razorpay/initiate/{order_id}")
    assert initiate.status_code == 200
    assert initiate.json()["amount"] == order.total_amount


def test_solo_cart_checkout_pay_returns_order_and_payment(client, seed_data, test_db_session, monkeypatch):
    _mock_razorpay_create(monkeypatch)

    client.post("/cart/items", json={"menu_item_id": seed_data["item_a1"].id, "quantity": 1})
    client.post("/cart/items", json={"menu_item_id": seed_data["item_a2"].id, "quantity": 1})

    response = client.post(f"/cart/checkout/{seed_data['slot'].id}/pay")
    assert response.status_code == 200
    body = response.json()

    assert body["order_created"] is True
    assert body["payment_initiated"] is True
    assert body["order"]["order_id"] > 0
    assert body["payment"]["payment_id"] > 0
    assert body["payment_error"] is None

    order = test_db_session.query(Order).filter(Order.id == body["order"]["order_id"]).first()
    assert order is not None


def test_solo_cart_checkout_pay_keeps_order_when_payment_init_fails(client, seed_data, test_db_session, monkeypatch):
    _mock_razorpay_create_fail(monkeypatch)

    client.post("/cart/items", json={"menu_item_id": seed_data["item_a1"].id, "quantity": 1})

    response = client.post(f"/cart/checkout/{seed_data['slot'].id}/pay")
    assert response.status_code == 200
    body = response.json()

    assert body["order_created"] is True
    assert body["payment_initiated"] is False
    assert body["order"]["order_id"] > 0
    assert body["payment"] is None
    assert body["payment_error"] is not None

    order = test_db_session.query(Order).filter(Order.id == body["order"]["order_id"]).first()
    assert order is not None
    assert order.total_amount == seed_data["item_a1"].price


def test_solo_cart_checkout_pay_idempotent_replay(client, seed_data, monkeypatch):
    _mock_razorpay_create(monkeypatch)
    idem_key = f"solo-pay-{uuid4().hex}"

    client.post("/cart/items", json={"menu_item_id": seed_data["item_a1"].id, "quantity": 1})
    first = client.post(
        f"/cart/checkout/{seed_data['slot'].id}/pay?checkout_idempotency_key={idem_key}"
    )
    assert first.status_code == 200

    second = client.post(
        f"/cart/checkout/{seed_data['slot'].id}/pay?checkout_idempotency_key={idem_key}"
    )
    assert second.status_code == 200
    assert second.json() == first.json()
