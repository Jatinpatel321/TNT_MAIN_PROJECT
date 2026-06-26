from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import get_current_user
from app.core.university_policy import set_university_policy
from app.database.base import Base
from app.main import app
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


@pytest.fixture(autouse=True)
def reset_university_policy():
    set_university_policy(False, 12, 14, 3, 15)
    yield
    set_university_policy(False, 12, 14, 3, 15)


def _next_time_with_hour(target_hour: int) -> datetime:
    now = datetime.now(UTC).replace(tzinfo=None)
    candidate = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
    if candidate <= now:
        candidate = candidate + timedelta(days=1)
    return candidate


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
    admin = User(phone="9001000001", name="Admin", role=UserRole.ADMIN, is_active=True)
    student = User(phone="9001000002", name="Student", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="9001000010",
        name="Vendor",
        role=UserRole.VENDOR,
        vendor_type="food",
        is_active=True,
        is_approved=True,
    )

    test_db_session.add_all([admin, student, vendor])
    test_db_session.commit()
    test_db_session.refresh(admin)
    test_db_session.refresh(student)
    test_db_session.refresh(vendor)

    menu_item = MenuItem(
        vendor_id=vendor.id,
        name="Policy Meal",
        description="Policy test item",
        price=70,
        image_url="https://example.com/policy.png",
        is_available=True,
    )
    test_db_session.add(menu_item)
    test_db_session.commit()
    test_db_session.refresh(menu_item)

    break_slot_start = _next_time_with_hour(13)
    non_break_slot_start = _next_time_with_hour(15)

    break_slot = Slot(
        vendor_id=vendor.id,
        start_time=break_slot_start,
        end_time=break_slot_start + timedelta(minutes=45),
        max_orders=10,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    non_break_slot = Slot(
        vendor_id=vendor.id,
        start_time=non_break_slot_start,
        end_time=non_break_slot_start + timedelta(minutes=45),
        max_orders=10,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    test_db_session.add_all([break_slot, non_break_slot])
    test_db_session.commit()
    test_db_session.refresh(break_slot)
    test_db_session.refresh(non_break_slot)

    return {
        "admin": admin,
        "student": student,
        "vendor": vendor,
        "menu_item": menu_item,
        "break_slot": break_slot,
        "non_break_slot": non_break_slot,
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


def test_university_policy_controls(client, seed_data, auth_context):
    admin = seed_data["admin"]
    student = seed_data["student"]
    vendor = seed_data["vendor"]
    menu_item = seed_data["menu_item"]
    break_slot = seed_data["break_slot"]
    non_break_slot = seed_data["non_break_slot"]

    auth_context.update({"id": admin.id, "phone": admin.phone, "role": admin.role.value})
    set_policy = client.post(
        "/admin/policies/university?enabled=true&break_start_hour=12&break_end_hour=14&max_orders_per_user=1&min_slot_duration_minutes=30"
    )
    assert set_policy.status_code == 200

    auth_context.update({"id": vendor.id, "phone": vendor.phone, "role": vendor.role.value})
    short_start = _next_time_with_hour(13)
    short_slot = client.post(
        "/slots/",
        json={
            "start_time": short_start.isoformat(),
            "end_time": (short_start + timedelta(minutes=20)).isoformat(),
            "max_orders": 10,
        },
    )
    assert short_slot.status_code == 400

    auth_context.update({"id": student.id, "phone": student.phone, "role": student.role.value})
    non_break_order = client.post(
        f"/orders/{non_break_slot.id}",
        json=[{"menu_item_id": menu_item.id, "quantity": 1}],
    )
    assert non_break_order.status_code == 400

    first_break_order = client.post(
        f"/orders/{break_slot.id}",
        json=[{"menu_item_id": menu_item.id, "quantity": 1}],
    )
    assert first_break_order.status_code == 200

    second_break_order = client.post(
        f"/orders/{break_slot.id}",
        json=[{"menu_item_id": menu_item.id, "quantity": 1}],
    )
    assert second_break_order.status_code == 400
