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
    student = User(phone="8800000001", name="Student", role=UserRole.STUDENT, is_active=True)
    other_vendor = User(phone="8800000002", name="OtherVendor", role=UserRole.VENDOR, is_active=True, is_approved=True)
    vendor = User(phone="8800000010", name="Vendor", role=UserRole.VENDOR, is_active=True, is_approved=True)
    admin = User(phone="8800000020", name="Admin", role=UserRole.ADMIN, is_active=True)

    test_db_session.add_all([student, other_vendor, vendor, admin])
    test_db_session.commit()
    test_db_session.refresh(student)
    test_db_session.refresh(other_vendor)
    test_db_session.refresh(vendor)
    test_db_session.refresh(admin)

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

    completed_order = Order(
        user_id=student.id,
        slot_id=slot.id,
        vendor_id=vendor.id,
        status=OrderStatus.COMPLETED,
        total_amount=100,
    )
    pending_order = Order(
        user_id=student.id,
        slot_id=slot.id,
        vendor_id=vendor.id,
        status=OrderStatus.PENDING,
        total_amount=100,
    )
    test_db_session.add_all([completed_order, pending_order])
    test_db_session.commit()
    test_db_session.refresh(completed_order)
    test_db_session.refresh(pending_order)

    return {
        "student": student,
        "vendor": vendor,
        "other_vendor": other_vendor,
        "admin": admin,
        "completed_order": completed_order,
        "pending_order": pending_order,
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


def test_feedback_submit_list_and_summary_access(client, seed_data, auth_context):
    completed_order = seed_data["completed_order"]
    pending_order = seed_data["pending_order"]
    vendor = seed_data["vendor"]
    other_vendor = seed_data["other_vendor"]
    admin = seed_data["admin"]

    submit = client.post(
        f"/feedback/orders/{completed_order.id}",
        json={
            "quality_rating": 5,
            "time_rating": 4,
            "behavior_rating": 5,
            "comment": "Great service",
        },
    )
    assert submit.status_code == 200

    duplicate = client.post(
        f"/feedback/orders/{completed_order.id}",
        json={
            "quality_rating": 5,
            "time_rating": 4,
            "behavior_rating": 5,
            "comment": "Duplicate",
        },
    )
    assert duplicate.status_code == 400

    pending_submit = client.post(
        f"/feedback/orders/{pending_order.id}",
        json={
            "quality_rating": 4,
            "time_rating": 4,
            "behavior_rating": 4,
        },
    )
    assert pending_submit.status_code == 400

    mine = client.get("/feedback/me")
    assert mine.status_code == 200
    assert len(mine.json()) == 1

    auth_context.update({"id": vendor.id, "phone": vendor.phone, "role": vendor.role.value})
    vendor_summary = client.get(f"/feedback/vendors/{vendor.id}/summary")
    assert vendor_summary.status_code == 200
    assert vendor_summary.json()["total_reviews"] == 1

    auth_context.update({"id": other_vendor.id, "phone": other_vendor.phone, "role": other_vendor.role.value})
    other_vendor_summary = client.get(f"/feedback/vendors/{vendor.id}/summary")
    assert other_vendor_summary.status_code == 200
    assert other_vendor_summary.json()["total_reviews"] == 1

    auth_context.update({"id": admin.id, "phone": admin.phone, "role": admin.role.value})
    admin_summary = client.get(f"/feedback/vendors/{vendor.id}/summary")
    assert admin_summary.status_code == 200
    assert admin_summary.json()["total_reviews"] == 1
