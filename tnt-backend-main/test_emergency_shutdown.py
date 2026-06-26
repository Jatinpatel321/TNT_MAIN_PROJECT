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
    admin = User(phone="8300000001", name="Admin", role=UserRole.ADMIN, is_active=True)
    student = User(phone="8300000002", name="Student", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="8300000010",
        name="Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )
    test_db_session.add_all([admin, student, vendor])
    test_db_session.commit()
    test_db_session.refresh(admin)
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
        name="Poha",
        description="Test item",
        price=45,
        image_url="https://example.com/poha.png",
        is_available=True,
    )
    test_db_session.add_all([slot, menu_item])
    test_db_session.commit()
    test_db_session.refresh(slot)
    test_db_session.refresh(menu_item)

    return {"admin": admin, "student": student, "slot": slot, "menu_item": menu_item}


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


def test_emergency_shutdown_blocks_and_unblocks_order_creation(client, seed_data, auth_context):
    admin = seed_data["admin"]
    student = seed_data["student"]
    slot = seed_data["slot"]
    menu_item = seed_data["menu_item"]

    auth_context.update({"id": admin.id, "phone": admin.phone, "role": admin.role.value})
    enable_resp = client.post("/admin/shutdown?enabled=true")
    assert enable_resp.status_code == 200
    assert enable_resp.json()["enabled"] is True

    auth_context.update({"id": student.id, "phone": student.phone, "role": student.role.value})
    blocked_resp = client.post(
        f"/orders/{slot.id}",
        json=[{"menu_item_id": menu_item.id, "quantity": 1}],
    )
    assert blocked_resp.status_code == 503
    assert blocked_resp.json().get("emergency_shutdown") is True

    auth_context.update({"id": admin.id, "phone": admin.phone, "role": admin.role.value})
    disable_resp = client.post("/admin/shutdown?enabled=false")
    assert disable_resp.status_code == 200
    assert disable_resp.json()["enabled"] is False

    auth_context.update({"id": student.id, "phone": student.phone, "role": student.role.value})
    allowed_resp = client.post(
        f"/orders/{slot.id}",
        json=[{"menu_item_id": menu_item.id, "quantity": 1}],
    )
    assert allowed_resp.status_code == 200
