from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.faculty_policy import set_faculty_priority_policy
from app.core.security import get_current_user
from app.core.university_policy import set_university_policy
from app.database.base import Base
from app.main import app
from app.modules.menu.model import MenuItem
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture(autouse=True)
def reset_policies():
    set_faculty_priority_policy(False, 12, 14)
    set_university_policy(False, 12, 14, 3, 15)
    yield
    set_faculty_priority_policy(False, 12, 14)
    set_university_policy(False, 12, 14, 3, 15)


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
    student = User(phone="9500000001", name="Student", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="9500000010",
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
        max_orders=2,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    item = MenuItem(
        vendor_id=vendor.id,
        name="Item",
        description="Pipeline test item",
        price=100,
        image_url="https://example.com/item.png",
        is_available=True,
    )

    test_db_session.add_all([slot, item])
    test_db_session.commit()
    test_db_session.refresh(slot)
    test_db_session.refresh(item)

    return {"student": student, "vendor": vendor, "slot": slot, "item": item}


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


def test_menu_item_deleted_mid_flow_rejected(client, seed_data, test_db_session):
    slot = seed_data["slot"]
    item = seed_data["item"]

    test_db_session.delete(item)
    test_db_session.commit()

    response = client.post(
        f"/orders/{slot.id}",
        json=[{"menu_item_id": item.id, "quantity": 1}],
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


def test_slot_full_during_booking_rejected(client, seed_data, test_db_session):
    slot = seed_data["slot"]
    item = seed_data["item"]

    slot.current_orders = slot.max_orders
    slot.status = SlotStatus.FULL
    test_db_session.commit()

    response = client.post(
        f"/orders/{slot.id}",
        json=[{"menu_item_id": item.id, "quantity": 1}],
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Slot full"


def test_vendor_disabled_mid_flow_rejected(client, seed_data, test_db_session):
    slot = seed_data["slot"]
    item = seed_data["item"]
    vendor = seed_data["vendor"]

    vendor.is_active = False
    test_db_session.commit()

    response = client.post(
        f"/orders/{slot.id}",
        json=[{"menu_item_id": item.id, "quantity": 1}],
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Vendor is not available"


def test_duplicate_order_submission_with_same_idempotency_key_rejected(client, seed_data):
    slot = seed_data["slot"]
    item = seed_data["item"]
    idempotency_key = f"dup-{uuid4().hex}"

    first = client.post(
        f"/orders/{slot.id}?idempotency_key={idempotency_key}",
        json=[{"menu_item_id": item.id, "quantity": 1}],
    )
    assert first.status_code == 200

    second = client.post(
        f"/orders/{slot.id}?idempotency_key={idempotency_key}",
        json=[{"menu_item_id": item.id, "quantity": 1}],
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "Duplicate request"


def test_invalid_jwt_rejected_safely(client_no_auth, seed_data):
    slot = seed_data["slot"]
    item = seed_data["item"]

    response = client_no_auth.post(
        f"/orders/{slot.id}",
        json=[{"menu_item_id": item.id, "quantity": 1}],
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"
