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
from app.modules.orders.model import Order, OrderItem, OrderStatus
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
    student = User(phone="8600000001", name="Student", role=UserRole.STUDENT, is_active=True)
    other_student = User(phone="8600000002", name="Other", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="8600000010",
        name="Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )
    test_db_session.add_all([student, other_student, vendor])
    test_db_session.commit()
    test_db_session.refresh(student)
    test_db_session.refresh(other_student)
    test_db_session.refresh(vendor)

    old_slot = Slot(
        vendor_id=vendor.id,
        start_time=utcnow_naive() - timedelta(hours=2),
        end_time=utcnow_naive() - timedelta(hours=1),
        max_orders=10,
        current_orders=1,
        status=SlotStatus.AVAILABLE,
    )
    future_slot = Slot(
        vendor_id=vendor.id,
        start_time=utcnow_naive() + timedelta(minutes=30),
        end_time=utcnow_naive() + timedelta(hours=1, minutes=30),
        max_orders=10,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    test_db_session.add_all([old_slot, future_slot])
    test_db_session.commit()
    test_db_session.refresh(old_slot)
    test_db_session.refresh(future_slot)

    menu_item = MenuItem(
        vendor_id=vendor.id,
        name="Maggi",
        description="Test item",
        price=60,
        image_url="https://example.com/maggi.png",
        is_available=True,
    )
    test_db_session.add(menu_item)
    test_db_session.commit()
    test_db_session.refresh(menu_item)

    original_order = Order(
        user_id=student.id,
        slot_id=old_slot.id,
        vendor_id=vendor.id,
        status=OrderStatus.COMPLETED,
        total_amount=120,
        created_at=utcnow_naive() - timedelta(days=1),
    )
    test_db_session.add(original_order)
    test_db_session.commit()
    test_db_session.refresh(original_order)

    original_item = OrderItem(
        order_id=original_order.id,
        menu_item_id=menu_item.id,
        quantity=2,
        price_at_time=60,
    )
    test_db_session.add(original_item)

    active_order = Order(
        user_id=student.id,
        slot_id=future_slot.id,
        vendor_id=vendor.id,
        status=OrderStatus.CONFIRMED,
        total_amount=60,
    )
    test_db_session.add(active_order)
    test_db_session.commit()
    test_db_session.refresh(active_order)

    return {
        "student": student,
        "other_student": other_student,
        "original_order": original_order,
        "active_order": active_order,
    }


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


def test_reorder_endpoint_creates_new_order(client, seed_data):
    response = client.post(f"/orders/{seed_data['original_order'].id}/reorder")
    assert response.status_code == 200

    body = response.json()
    assert body["order_id"] != seed_data["original_order"].id
    assert body["total_amount"] == 120
    assert "estimated_ready_at" in body
    assert body["pickup_load_label"] == "LOW"
    assert body["express_pickup_eligible"] is True


def test_eta_endpoint_works_for_owner_and_blocks_other_user(client, seed_data, auth_context):
    own_eta = client.get(f"/orders/{seed_data['active_order'].id}/eta")
    assert own_eta.status_code == 200
    own_body = own_eta.json()
    assert own_body["order_id"] == seed_data["active_order"].id
    assert "estimated_ready_at" in own_body
    assert own_body["pickup_load_label"] == "LOW"
    assert own_body["express_pickup_eligible"] is True

    other = seed_data["other_student"]
    auth_context.update({"id": other.id, "phone": other.phone, "role": other.role.value})

    forbidden_eta = client.get(f"/orders/{seed_data['active_order'].id}/eta")
    assert forbidden_eta.status_code == 404
