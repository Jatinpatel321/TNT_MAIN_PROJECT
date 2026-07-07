"""
Users /me endpoints — test_users_me.py

Covers:
  GET  /users/me                — returns authenticated user's profile
  PUT  /users/me                — updates name, university_id, preferences
  GET  /users/me/preferences    — returns the structured preferences blob
  PUT  /users/me/preferences    — merges structured preference updates
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.users.model import User, UserRole


def _auth_for(user):
    return lambda: {"id": user.id, "phone": user.phone, "role": user.role.value}


def _make_client(db_session, user):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = _auth_for(user)
    return TestClient(app, raise_server_exceptions=False)


def _anon_client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides.pop(get_current_user, None)
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture()
def db(engine):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def student(db):
    u = User(phone="9500000001", name="Test Student", role=UserRole.STUDENT, university_id="STU001", is_active=True)
    db.add(u); db.commit(); db.refresh(u)
    return u


@pytest.fixture()
def vendor(db):
    u = User(phone="9500000002", name="Test Vendor", role=UserRole.VENDOR, vendor_type="food", is_active=True, is_approved=True)
    db.add(u); db.commit(); db.refresh(u)
    return u


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


class TestGetMe:
    def test_returns_own_profile(self, db, student):
        resp = _make_client(db, student).get("/users/me")
        assert resp.status_code == 200
        assert resp.json()["phone"] == student.phone
        assert resp.json()["role"] == "student"

    def test_response_includes_required_fields(self, db, student):
        data = _make_client(db, student).get("/users/me").json()
        for field in ("id", "phone", "name", "role"):
            assert field in data

    def test_university_id_returned(self, db, student):
        assert _make_client(db, student).get("/users/me").json()["university_id"] == "STU001"

    def test_unauthenticated_returns_403(self, db, student):
        assert _anon_client(db).get("/users/me").status_code in (401, 403)


class TestUpdateMe:
    def test_update_name_succeeds(self, db, student):
        resp = _make_client(db, student).put("/users/me", params={"name": "Updated Name", "university_id": "STU001"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    def test_name_persisted_in_db(self, db, student):
        _make_client(db, student).put("/users/me", params={"name": "Persisted Name", "university_id": "STU001"})
        db.expire_all()
        assert db.query(User).filter(User.id == student.id).first().name == "Persisted Name"

    def test_update_university_id(self, db, student):
        _make_client(db, student).put("/users/me", params={"name": "Test Student", "university_id": "STU999"})
        db.expire_all()
        assert db.query(User).filter(User.id == student.id).first().university_id == "STU999"

    def test_student_without_university_id_returns_400(self, db, student):
        assert _make_client(db, student).put("/users/me", params={"name": "No UID"}).status_code == 400

    def test_vendor_can_update_without_university_id(self, db, vendor):
        assert _make_client(db, vendor).put("/users/me", params={"name": "Vendor Updated"}).status_code == 200

    def test_unauthenticated_update_returns_403(self, db, student):
        assert _anon_client(db).put("/users/me", params={"name": "X", "university_id": "X"}).status_code in (401, 403)


class TestGetPreferences:
    def test_returns_empty_dict_by_default(self, db, student):
        resp = _make_client(db, student).get("/users/me/preferences")
        assert resp.status_code == 200
        assert isinstance(resp.json()["preferences"], dict)

    def test_reflects_stored_preferences(self, db, student):
        student.preferences = {"spice_level": 3, "cuisine_preferences": ["south_indian"]}
        db.commit()
        prefs = _make_client(db, student).get("/users/me/preferences").json()["preferences"]
        assert prefs["spice_level"] == 3
        assert "south_indian" in prefs["cuisine_preferences"]

    def test_unauthenticated_returns_403(self, db, student):
        assert _anon_client(db).get("/users/me/preferences").status_code in (401, 403)


class TestUpdatePreferences:
    def test_set_spice_level(self, db, student):
        resp = _make_client(db, student).put(
            "/users/me/preferences",
            json={"spice_level": 4, "enable_reorder_suggestions": True, "enable_offpeak_reminders": True},
        )
        assert resp.status_code == 200
        db.expire_all()
        assert db.query(User).filter(User.id == student.id).first().preferences["spice_level"] == 4

    def test_partial_update_merges_existing(self, db, student):
        student.preferences = {"spice_level": 2, "cuisine_preferences": ["fast_food"]}
        db.commit()
        resp = _make_client(db, student).put(
            "/users/me/preferences",
            json={"spice_level": 5, "enable_reorder_suggestions": True, "enable_offpeak_reminders": True},
        )
        assert resp.status_code == 200
        prefs = resp.json()["preferences"]
        assert prefs["spice_level"] == 5
        assert "fast_food" in prefs["cuisine_preferences"]

    def test_dietary_restrictions_stored_as_strings(self, db, student):
        resp = _make_client(db, student).put(
            "/users/me/preferences",
            json={"dietary_restrictions": ["vegetarian", "gluten_free"], "enable_reorder_suggestions": True, "enable_offpeak_reminders": True},
        )
        assert resp.status_code == 200
        prefs = resp.json()["preferences"]
        assert "vegetarian" in prefs["dietary_restrictions"]
        assert "gluten_free" in prefs["dietary_restrictions"]

    def test_invalid_spice_level_returns_422(self, db, student):
        assert _make_client(db, student).put("/users/me/preferences", json={"spice_level": 99}).status_code == 422

    def test_response_contains_preferences_key(self, db, student):
        resp = _make_client(db, student).put(
            "/users/me/preferences",
            json={"preferred_pickup_hour": 13, "enable_reorder_suggestions": True, "enable_offpeak_reminders": True},
        )
        assert resp.status_code == 200
        assert resp.json()["preferences"]["preferred_pickup_hour"] == 13

    def test_unauthenticated_returns_403(self, db, student):
        assert _anon_client(db).put("/users/me/preferences", json={"spice_level": 1}).status_code in (401, 403)
