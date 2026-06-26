from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.faculty_policy import set_faculty_priority_policy
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture(autouse=True)
def reset_policy():
    set_faculty_priority_policy(False, 12, 14)
    yield
    set_faculty_priority_policy(False, 12, 14)


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
    admin = User(phone="8500000001", name="Admin", role=UserRole.ADMIN, is_active=True)
    faculty = User(phone="8500000002", name="Faculty", role=UserRole.FACULTY, is_active=True)
    student = User(phone="8500000003", name="Student", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="8500000010",
        name="Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )
    test_db_session.add_all([admin, faculty, student, vendor])
    test_db_session.commit()
    test_db_session.refresh(admin)
    test_db_session.refresh(faculty)
    test_db_session.refresh(student)
    test_db_session.refresh(vendor)

    now = utcnow_naive()
    slot_start = now.replace(hour=13, minute=0, second=0, microsecond=0)
    if slot_start <= now:
        slot_start = slot_start + timedelta(days=1)

    slot = Slot(
        vendor_id=vendor.id,
        start_time=slot_start,
        end_time=slot_start + timedelta(hours=1),
        max_orders=10,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    test_db_session.add(slot)
    test_db_session.commit()
    test_db_session.refresh(slot)

    return {"admin": admin, "faculty": faculty, "student": student, "slot": slot}


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


def test_faculty_priority_policy_blocks_students_allows_faculty(client, seed_data, auth_context):
    admin = seed_data["admin"]
    faculty = seed_data["faculty"]
    student = seed_data["student"]
    slot = seed_data["slot"]

    auth_context.update({"id": admin.id, "phone": admin.phone, "role": admin.role.value})
    policy_resp = client.post("/admin/policies/faculty-priority?enabled=true&start_hour=12&end_hour=14")
    assert policy_resp.status_code == 200
    assert policy_resp.json()["enabled"] is True

    auth_context.update({"id": student.id, "phone": student.phone, "role": student.role.value})
    blocked = client.post(f"/slots/{slot.id}/book")
    assert blocked.status_code == 403

    auth_context.update({"id": faculty.id, "phone": faculty.phone, "role": faculty.role.value})
    allowed = client.post(f"/slots/{slot.id}/book")
    assert allowed.status_code == 200
    assert allowed.json()["slot_id"] == slot.id
