"""
Tests for notification endpoints:
  GET  /notifications/        – list my notifications
  POST /notifications/{id}/read – mark one as read
"""
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.notifications.model import Notification
from app.modules.users.model import User, UserRole


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Fixtures
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
    student = User(
        phone="8500000001", name="Student", role=UserRole.STUDENT, is_active=True
    )
    other = User(
        phone="8500000002", name="Other", role=UserRole.STUDENT, is_active=True
    )
    test_db_session.add_all([student, other])
    test_db_session.commit()
    test_db_session.refresh(student)
    test_db_session.refresh(other)

    # Two notifications for student, one for other
    n1 = Notification(user_id=student.id, title="Hello", message="Msg 1", is_read=False)
    n2 = Notification(user_id=student.id, title="Update", message="Msg 2", is_read=False)
    n_other = Notification(user_id=other.id, title="Other", message="Not yours", is_read=False)
    test_db_session.add_all([n1, n2, n_other])
    test_db_session.commit()
    for obj in (n1, n2, n_other):
        test_db_session.refresh(obj)

    return {"student": student, "other": other, "n1": n1, "n2": n2, "n_other": n_other}


def _make_client(db_session, user: User) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: {
        "id": user.id,
        "phone": user.phone,
        "role": user.role.value,
    }
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# GET /notifications/
# ---------------------------------------------------------------------------


def test_get_notifications_returns_own_only(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["student"])
    resp = client.get("/notifications/")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    ids = {n["id"] for n in data}
    assert seed_data["n1"].id in ids
    assert seed_data["n2"].id in ids
    # Other user's notification must NOT appear
    assert seed_data["n_other"].id not in ids


def test_get_notifications_correct_count(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["student"])
    resp = client.get("/notifications/")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_notifications_empty_for_user_with_none(test_db_session, seed_data):
    # Use "other" user who has notifications, but let's create a brand-new user
    vendor = User(phone="8500000099", name="Fresh", role=UserRole.VENDOR, is_active=True, is_approved=True)
    test_db_session.add(vendor)
    test_db_session.commit()
    test_db_session.refresh(vendor)

    client = _make_client(test_db_session, vendor)
    resp = client.get("/notifications/")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json() == []


def test_get_notifications_contains_message_fields(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["student"])
    resp = client.get("/notifications/")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    first = resp.json()[0]
    assert "title" in first
    assert "message" in first
    assert "is_read" in first


def test_get_notifications_requires_auth(test_db_session):
    # No dependency override → bare client → 401
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/notifications/")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /notifications/{id}/read
# ---------------------------------------------------------------------------


def test_mark_notification_as_read_succeeds(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["student"])
    resp = client.post(f"/notifications/{seed_data['n1'].id}/read")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert "read" in resp.json().get("message", "").lower()


def test_mark_notification_persists_in_db(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["student"])
    client.post(f"/notifications/{seed_data['n1'].id}/read")
    app.dependency_overrides.clear()

    test_db_session.refresh(seed_data["n1"])
    assert seed_data["n1"].is_read is True


def test_mark_notification_does_not_affect_other_notification(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["student"])
    client.post(f"/notifications/{seed_data['n1'].id}/read")
    app.dependency_overrides.clear()

    test_db_session.refresh(seed_data["n2"])
    assert seed_data["n2"].is_read is False


def test_mark_notification_returns_404_for_wrong_user(test_db_session, seed_data):
    # student tries to read other user's notification
    client = _make_client(test_db_session, seed_data["student"])
    resp = client.post(f"/notifications/{seed_data['n_other'].id}/read")
    app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_mark_notification_returns_404_for_nonexistent(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["student"])
    resp = client.post("/notifications/99999/read")
    app.dependency_overrides.clear()

    assert resp.status_code == 404
