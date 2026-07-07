"""
Integration tests for the active-user authentication guard.

These tests exercise get_current_user() end-to-end (real JWT + real DB lookup)
via GET /users/me so that toggling is_active is reflected immediately on the
next request.  The dependency_overrides pattern used elsewhere in the suite
*replaces* get_current_user, which would defeat the purpose of these tests —
here we override only get_db and send a real bearer token.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import _BLOCKED_USER_DETAIL, create_access_token
from app.database.base import Base
from app.main import app
from app.modules.users.model import User, UserRole


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
def active_user(test_db_session):
    user = User(
        phone="9000000001",
        name="Active Student",
        role=UserRole.STUDENT,
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture()
def blocked_user(test_db_session):
    user = User(
        phone="9000000002",
        name="Blocked Student",
        role=UserRole.STUDENT,
        is_active=False,
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


def _make_token(user: User) -> str:
    """Mint a real JWT for the given User object."""
    return create_access_token(
        data={"sub": str(user.id), "phone": user.phone, "role": user.role.value},
        expires_delta=60,
    )


@pytest.fixture()
def client_with_db(test_db_session):
    """
    TestClient that uses the in-memory test DB but does NOT override
    get_current_user — we want the real active-user guard to run.
    """
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_active_user_can_authenticate(client_with_db, active_user):
    """A user with is_active=True gets a 200 on an authenticated endpoint."""
    token = _make_token(active_user)
    resp = client_with_db.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["phone"] == active_user.phone


def test_blocked_user_gets_403(client_with_db, blocked_user):
    """A user with is_active=False is rejected with exactly 403."""
    token = _make_token(blocked_user)
    resp = client_with_db.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_blocked_user_error_message(client_with_db, blocked_user):
    """The 403 response body matches the product-defined message."""
    token = _make_token(blocked_user)
    resp = client_with_db.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["detail"] == _BLOCKED_USER_DETAIL


def test_toggling_is_active_blocks_immediately(client_with_db, active_user, test_db_session):
    """
    Toggling is_active=False (simulating POST /admin/users/{id}/toggle) must
    block the user on the very next request — no token re-issue required.
    """
    token = _make_token(active_user)

    # Confirm access while active
    resp = client_with_db.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # Admin blocks the user
    active_user.is_active = False
    test_db_session.commit()

    # Same token — now blocked
    resp = client_with_db.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == _BLOCKED_USER_DETAIL


def test_re_activating_user_restores_access(client_with_db, blocked_user, test_db_session):
    """
    Admin re-activating a blocked user (is_active=True) must restore access
    immediately on the next request.
    """
    token = _make_token(blocked_user)

    # Confirm currently blocked
    resp = client_with_db.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403

    # Admin unblocks
    blocked_user.is_active = True
    test_db_session.commit()

    # Access restored
    resp = client_with_db.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_nonexistent_user_in_token_gets_401(client_with_db):
    """A token referencing a user ID that doesn't exist in the DB returns 401."""
    token = create_access_token(
        data={"sub": "99999", "phone": "9000000099", "role": "student"},
        expires_delta=60,
    )

    resp = client_with_db.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


def test_blocked_user_blocked_on_vendor_route(client_with_db, test_db_session):
    """
    require_role() inherits the active-user guard — a blocked vendor is
    also blocked on vendor-gated routes.
    """
    vendor = User(
        phone="9000000003",
        name="Blocked Vendor",
        role=UserRole.VENDOR,
        is_active=False,
        is_approved=True,
    )
    test_db_session.add(vendor)
    test_db_session.commit()
    test_db_session.refresh(vendor)

    token = _make_token(vendor)

    # GET /orders/vendor is require_role("vendor") gated
    resp = client_with_db.get(
        "/orders/vendor",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == _BLOCKED_USER_DETAIL


def test_blocked_user_logs_monitoring_event(client_with_db, blocked_user, caplog):
    """
    The structured monitoring log event=blocked_login_attempt must be emitted
    when a blocked user attempts authentication.
    """
    import logging

    token = _make_token(blocked_user)

    with caplog.at_level(logging.WARNING, logger="tnt.security"):
        client_with_db.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert any(
        "blocked_login_attempt" in record.message
        for record in caplog.records
    ), "Expected 'blocked_login_attempt' monitoring event in logs"
