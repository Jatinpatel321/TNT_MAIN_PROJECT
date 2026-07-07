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
    student = User(phone="7000000001", name="Student", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="7000000010",
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
        name="Combo Meal",
        description="Test item",
        price=120,
        image_url="https://example.com/item.png",
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


def test_order_lifecycle_flow(client, test_db_session, seed_data, auth_context):
    slot = seed_data["slot"]
    menu_item = seed_data["menu_item"]
    vendor = seed_data["vendor"]
    student = seed_data["student"]

    place_resp = client.post(
        f"/orders/{slot.id}",
        json=[{"menu_item_id": menu_item.id, "quantity": 2}],
    )
    assert place_resp.status_code == 200
    place_body = place_resp.json()
    order_id = place_body["order_id"]
    assert place_body["pickup_load_label"] == "LOW"
    assert place_body["express_pickup_eligible"] is True

    my_orders_resp = client.get("/orders/my")
    assert my_orders_resp.status_code == 200
    assert any(order["id"] == order_id for order in my_orders_resp.json())

    auth_context.update({"id": vendor.id, "phone": vendor.phone, "role": vendor.role.value})

    confirm_resp = client.post(f"/orders/{order_id}/confirm")
    assert confirm_resp.status_code == 200

    complete_resp = client.post(f"/orders/{order_id}/ready")
    assert complete_resp.status_code == 200

    auth_context.update({"id": student.id, "phone": student.phone, "role": student.role.value})

    # READY is non-terminal; student can still cancel
    cancel_of_ready = client.post(f"/orders/{order_id}/cancel")
    assert cancel_of_ready.status_code == 200

    # Now CANCELLED (terminal) — a second cancel must fail
    cancel_of_cancelled = client.post(f"/orders/{order_id}/cancel")
    assert cancel_of_cancelled.status_code == 400

    order_record = test_db_session.query(Order).filter(Order.id == order_id).first()
    assert order_record is not None
    assert order_record.total_amount == place_body["total_amount"]
    assert order_record.status.value == "cancelled"
