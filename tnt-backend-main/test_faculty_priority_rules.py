"""
Faculty Priority Rule Tests
============================
Tests the faculty priority policy system at two levels:

  1. Unit tests — direct calls to the policy functions:
       • is_slot_in_faculty_priority_window() with edge-case hours
       • set_faculty_priority_policy() / get_faculty_priority_policy() round-trips

  2. Integration tests — HTTP slots booking endpoint:
       • Admin booking during priority window → allowed
       • Student booking outside the priority window → allowed
       • Student booking while policy is disabled → allowed

Note: student-blocked / faculty-allowed happy-path is already tested in
test_faculty_priority_policy.py; this file covers complementary edge cases.

Phone number range: 8700000xxx
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.faculty_policy import (
    get_faculty_priority_policy,
    is_slot_in_faculty_priority_window,
    set_faculty_priority_policy,
)
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Autouse: reset policy before and after every test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_policy():
    set_faculty_priority_policy(False, 12, 14)
    yield
    set_faculty_priority_policy(False, 12, 14)


# ---------------------------------------------------------------------------
# DB / HTTP fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def test_db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def seed_data(test_db_session):
    admin = User(phone="8700000001", name="Admin", role=UserRole.ADMIN, is_active=True)
    faculty = User(phone="8700000002", name="Faculty", role=UserRole.FACULTY, is_active=True)
    student = User(phone="8700000003", name="Student", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="8700000010",
        name="Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )
    test_db_session.add_all([admin, faculty, student, vendor])
    test_db_session.commit()
    for obj in [admin, faculty, student, vendor]:
        test_db_session.refresh(obj)

    # Slot whose hour (13) falls inside the default 12-14 faculty window
    tomorrow = utcnow_naive() + timedelta(days=1)
    slot_in_window = Slot(
        vendor_id=vendor.id,
        start_time=tomorrow.replace(hour=13, minute=0, second=0, microsecond=0),
        end_time=tomorrow.replace(hour=14, minute=0, second=0, microsecond=0),
        max_orders=10,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    # Slot outside the window (hour=10)
    slot_outside_window = Slot(
        vendor_id=vendor.id,
        start_time=tomorrow.replace(hour=10, minute=0, second=0, microsecond=0),
        end_time=tomorrow.replace(hour=11, minute=0, second=0, microsecond=0),
        max_orders=10,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    test_db_session.add_all([slot_in_window, slot_outside_window])
    test_db_session.commit()
    test_db_session.refresh(slot_in_window)
    test_db_session.refresh(slot_outside_window)

    return {
        "admin": admin,
        "faculty": faculty,
        "student": student,
        "vendor": vendor,
        "slot_in_window": slot_in_window,
        "slot_outside_window": slot_outside_window,
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

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Unit tests — is_slot_in_faculty_priority_window()
# ---------------------------------------------------------------------------

def test_window_always_false_when_policy_disabled():
    set_faculty_priority_policy(False, 12, 14)
    assert is_slot_in_faculty_priority_window(12) is False
    assert is_slot_in_faculty_priority_window(13) is False
    assert is_slot_in_faculty_priority_window(10) is False


def test_window_includes_start_hour():
    set_faculty_priority_policy(True, 12, 14)
    assert is_slot_in_faculty_priority_window(12) is True


def test_window_includes_hour_before_end():
    set_faculty_priority_policy(True, 12, 14)
    assert is_slot_in_faculty_priority_window(13) is True


def test_window_excludes_end_hour():
    set_faculty_priority_policy(True, 12, 14)
    assert is_slot_in_faculty_priority_window(14) is False


def test_window_excludes_hours_before_window():
    set_faculty_priority_policy(True, 12, 14)
    assert is_slot_in_faculty_priority_window(11) is False


def test_window_excludes_hours_after_window():
    set_faculty_priority_policy(True, 12, 14)
    assert is_slot_in_faculty_priority_window(15) is False


# ---------------------------------------------------------------------------
# Unit tests — set/get_faculty_priority_policy() round-trip
# ---------------------------------------------------------------------------

def test_policy_persists_enabled_flag():
    set_faculty_priority_policy(True, 9, 11)
    policy = get_faculty_priority_policy()
    assert policy["enabled"] is True
    assert policy["start_hour"] == 9
    assert policy["end_hour"] == 11


def test_policy_persists_disabled_flag():
    set_faculty_priority_policy(True, 9, 11)  # enable first
    set_faculty_priority_policy(False, 9, 11)  # then disable
    policy = get_faculty_priority_policy()
    assert policy["enabled"] is False


def test_policy_change_reflected_immediately():
    """Toggling the policy mid-test is immediately visible to the window check."""
    set_faculty_priority_policy(True, 12, 14)
    assert is_slot_in_faculty_priority_window(13) is True

    set_faculty_priority_policy(False, 12, 14)
    assert is_slot_in_faculty_priority_window(13) is False


# ---------------------------------------------------------------------------
# Integration tests — HTTP booking endpoint
# ---------------------------------------------------------------------------

def test_admin_can_book_slot_during_priority_window(client, seed_data, auth_context):
    admin = seed_data["admin"]
    auth_context.update({"id": admin.id, "phone": admin.phone, "role": admin.role.value})

    # Enable faculty priority
    policy_resp = client.post(
        "/admin/policies/faculty-priority?enabled=true&start_hour=12&end_hour=14"
    )
    assert policy_resp.status_code == 200

    slot = seed_data["slot_in_window"]
    resp = client.post(f"/slots/{slot.id}/book")
    assert resp.status_code == 200, resp.json()


def test_student_can_book_slot_outside_priority_window(client, seed_data, auth_context):
    # Enable priority window 12-14
    admin = seed_data["admin"]
    auth_context.update({"id": admin.id, "phone": admin.phone, "role": admin.role.value})
    client.post("/admin/policies/faculty-priority?enabled=true&start_hour=12&end_hour=14")

    # Student books hour=10 slot (outside 12-14 window) — must be allowed
    student = seed_data["student"]
    auth_context.update({"id": student.id, "phone": student.phone, "role": student.role.value})
    slot = seed_data["slot_outside_window"]
    resp = client.post(f"/slots/{slot.id}/book")
    assert resp.status_code == 200, resp.json()


def test_student_can_book_slot_when_policy_disabled(client, seed_data, auth_context):
    # Policy is disabled (reset_policy fixture ensures that)
    student = seed_data["student"]
    auth_context.update({"id": student.id, "phone": student.phone, "role": student.role.value})
    slot = seed_data["slot_in_window"]
    resp = client.post(f"/slots/{slot.id}/book")
    assert resp.status_code == 200, resp.json()
