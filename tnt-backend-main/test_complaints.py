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
    student = User(phone="8900000001", name="Student", role=UserRole.STUDENT, is_active=True)
    vendor = User(phone="8900000010", name="Vendor", role=UserRole.VENDOR, is_active=True, is_approved=True)
    admin = User(phone="8900000020", name="Admin", role=UserRole.ADMIN, is_active=True)
    other_student = User(phone="8900000030", name="Other", role=UserRole.STUDENT, is_active=True)

    test_db_session.add_all([student, vendor, admin, other_student])
    test_db_session.commit()
    test_db_session.refresh(student)
    test_db_session.refresh(vendor)
    test_db_session.refresh(admin)
    test_db_session.refresh(other_student)

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
        user_id=student.id,
        slot_id=slot.id,
        vendor_id=vendor.id,
        status=OrderStatus.COMPLETED,
        total_amount=100,
    )
    test_db_session.add(order)
    test_db_session.commit()
    test_db_session.refresh(order)

    return {"student": student, "vendor": vendor, "admin": admin, "other_student": other_student, "order": order}


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


def test_complaint_lifecycle(client, seed_data, auth_context):
    order = seed_data["order"]
    vendor = seed_data["vendor"]
    admin = seed_data["admin"]
    other_student = seed_data["other_student"]

    create_resp = client.post(
        "/complaints/",
        json={
            "category": "late_order",
            "title": "Order delayed",
            "description": "Pickup was late",
            "order_id": order.id,
        },
    )
    assert create_resp.status_code == 200
    complaint_id = create_resp.json()["complaint_id"]

    my_resp = client.get("/complaints/my")
    assert my_resp.status_code == 200
    assert len(my_resp.json()) == 1

    auth_context.update({"id": other_student.id, "phone": other_student.phone, "role": other_student.role.value})
    list_denied = client.get("/complaints/")
    assert list_denied.status_code == 403

    auth_context.update({"id": admin.id, "phone": admin.phone, "role": admin.role.value})
    list_resp = client.get("/complaints/")
    assert list_resp.status_code == 200
    resp_data = list_resp.json()
    # Handle paginated response
    items = resp_data.get("items", resp_data) if isinstance(resp_data, dict) else resp_data
    assert len(items) == 1

    assign_resp = client.post(f"/complaints/{complaint_id}/assign?vendor_id={vendor.id}")
    assert assign_resp.status_code == 200

    status_resp = client.post(
        f"/complaints/{complaint_id}/status",
        json={"status": "in_progress"},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "in_progress"

    escalate_resp = client.post(f"/complaints/{complaint_id}/escalate")
    assert escalate_resp.status_code == 200
    assert escalate_resp.json()["status"] == "escalated"
