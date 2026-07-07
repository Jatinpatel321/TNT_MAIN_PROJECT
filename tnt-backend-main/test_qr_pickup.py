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
from app.modules.menu.model import MenuItem
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
    student = User(phone="7100000001", name="Student", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="7100000010",
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
        name="Samosa",
        description="Test item",
        price=30,
        image_url="https://example.com/samosa.png",
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


def test_qr_pickup_flow(client, test_db_session, seed_data, auth_context):
    slot = seed_data["slot"]
    menu_item = seed_data["menu_item"]
    vendor = seed_data["vendor"]

    place_resp = client.post(
        f"/orders/{slot.id}",
        json=[{"menu_item_id": menu_item.id, "quantity": 1}],
    )
    assert place_resp.status_code == 200
    order_id = place_resp.json()["order_id"]

    order = test_db_session.query(Order).filter(Order.id == order_id).first()
    assert order is not None
    order.status = OrderStatus.READY_FOR_PICKUP
    test_db_session.commit()

    qr_resp = client.post(f"/orders/{order_id}/qr")
    assert qr_resp.status_code == 200
    qr_code = qr_resp.json()["qr_code"]

    auth_context.update({"id": vendor.id, "phone": vendor.phone, "role": vendor.role.value})

    get_qr_resp = client.get(f"/orders/qr/{qr_code}")
    assert get_qr_resp.status_code == 200
    assert get_qr_resp.json()["order_id"] == order_id

    confirm_resp = client.post(f"/orders/qr/pickup/confirm?qr_code={qr_code}")
    assert confirm_resp.status_code == 200

    refreshed = test_db_session.query(Order).filter(Order.id == order_id).first()
    assert refreshed is not None
    assert refreshed.status == OrderStatus.PICKED
    assert refreshed.pickup_confirmed_by == vendor.id
