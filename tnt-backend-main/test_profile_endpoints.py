"""
Profile endpoints — test_profile_endpoints.py

Covers:
  GET  /profile/me           — returns full authenticated user profile
  PUT  /profile/update       — updates full_name, department, semester, university_id
  POST /profile/upload-image  — uploads/replaces profile image
"""

from __future__ import annotations

import io
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
    return lambda: {"id": user.id, "phone": user.phone, "role": user.role.value, "is_active": True}


def _make_client(db_session, user):
    app.dependency_overrides[get_db] = lambda: db_session
    if user:
        app.dependency_overrides[get_current_user] = _auth_for(user)
    else:
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
    u = User(
        phone="9500000101",
        name="Test Student",
        full_name="Test Student",
        role=UserRole.STUDENT,
        university_id="STU001",
        department="Computer Science",
        semester=4,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def faculty(db):
    u = User(
        phone="9500000102",
        name="Prof Faculty",
        full_name="Prof Faculty",
        role=UserRole.FACULTY,
        university_id="FAC001",
        department="Electronics",
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def vendor(db):
    u = User(
        phone="9500000103",
        name="Test Vendor",
        role=UserRole.VENDOR,
        vendor_type="food",
        is_active=True,
        is_approved=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


# ── GET /profile/me ──────────────────────────────────────────────────────


class TestGetProfile:
    def test_returns_own_profile(self, db, student):
        resp = _make_client(db, student).get("/profile/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["phone"] == student.phone
        assert data["role"] == "student"

    def test_includes_new_fields(self, db, student):
        data = _make_client(db, student).get("/profile/me").json()
        assert data["full_name"] == "Test Student"
        assert data["department"] == "Computer Science"
        assert data["semester"] == 4
        assert data["university_id"] == "STU001"
        assert "profile_image" in data
        assert "is_active" in data
        assert "is_approved" in data

    def test_null_fields_for_minimal_user(self, db, vendor):
        data = _make_client(db, vendor).get("/profile/me").json()
        assert data["full_name"] is None
        assert data["department"] is None
        assert data["semester"] is None
        assert data["profile_image"] is None

    def test_unauthenticated_returns_401(self, db, student):
        resp = _make_client(db, None).get("/profile/me")
        assert resp.status_code in (401, 403)


# ── PUT /profile/update ──────────────────────────────────────────────────


class TestUpdateProfile:
    def test_update_full_name(self, db, student):
        resp = _make_client(db, student).put(
            "/profile/update",
            json={"full_name": "Updated Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Updated Name"

    def test_update_department(self, db, student):
        resp = _make_client(db, student).put(
            "/profile/update",
            json={"department": "Mechanical"},
        )
        assert resp.status_code == 200
        assert resp.json()["department"] == "Mechanical"

    def test_update_semester(self, db, student):
        resp = _make_client(db, student).put(
            "/profile/update",
            json={"semester": 6},
        )
        assert resp.status_code == 200
        assert resp.json()["semester"] == 6

    def test_update_university_id(self, db, student):
        resp = _make_client(db, student).put(
            "/profile/update",
            json={"university_id": "STU999"},
        )
        assert resp.status_code == 200
        assert resp.json()["university_id"] == "STU999"

    def test_update_multiple_fields(self, db, student):
        resp = _make_client(db, student).put(
            "/profile/update",
            json={
                "full_name": "New Full Name",
                "department": "Civil",
                "semester": 8,
                "university_id": "STU008",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["full_name"] == "New Full Name"
        assert data["department"] == "Civil"
        assert data["semester"] == 8
        assert data["university_id"] == "STU008"

    def test_partial_update_preserves_other_fields(self, db, student):
        original_dept = student.department
        resp = _make_client(db, student).put(
            "/profile/update",
            json={"semester": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["semester"] == 5
        assert data["department"] == original_dept

    def test_semester_validation_min(self, db, student):
        resp = _make_client(db, student).put(
            "/profile/update",
            json={"semester": 0},
        )
        assert resp.status_code == 422

    def test_semester_validation_max(self, db, student):
        resp = _make_client(db, student).put(
            "/profile/update",
            json={"semester": 13},
        )
        assert resp.status_code == 422

    def test_full_name_length_validation(self, db, student):
        resp = _make_client(db, student).put(
            "/profile/update",
            json={"full_name": ""},
        )
        assert resp.status_code == 422

    def test_full_name_max_length(self, db, student):
        resp = _make_client(db, student).put(
            "/profile/update",
            json={"full_name": "A" * 101},
        )
        assert resp.status_code == 422

    def test_empty_update_returns_400(self, db, student):
        resp = _make_client(db, student).put(
            "/profile/update",
            json={},
        )
        assert resp.status_code == 400

    def test_persisted_in_db(self, db, student):
        _make_client(db, student).put(
            "/profile/update",
            json={"full_name": "Persisted Name", "department": "Biotechnology"},
        )
        db.expire_all()
        refreshed = db.query(User).filter(User.id == student.id).first()
        assert refreshed.full_name == "Persisted Name"
        assert refreshed.department == "Biotechnology"

    def test_unauthenticated_returns_401(self, db, student):
        resp = _make_client(db, None).put(
            "/profile/update",
            json={"full_name": "Hacked"},
        )
        assert resp.status_code in (401, 403)

    def test_faculty_can_update_department(self, db, faculty):
        resp = _make_client(db, faculty).put(
            "/profile/update",
            json={"department": "Physics"},
        )
        assert resp.status_code == 200
        assert resp.json()["department"] == "Physics"

    def test_vendor_can_update(self, db, vendor):
        resp = _make_client(db, vendor).put(
            "/profile/update",
            json={"full_name": "Vendor Full Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Vendor Full Name"


# ── POST /profile/upload-image ────────────────────────────────────────────


class TestUploadProfileImage:
    def test_upload_jpeg(self, db, student):
        img = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        resp = _make_client(db, student).post(
            "/profile/upload-image",
            files={"file": ("photo.jpg", img, "image/jpeg")},
        )
        assert resp.status_code == 200
        assert "profile_image" in resp.json()
        assert resp.json()["profile_image"].startswith("/uploads/profile/")

    def test_upload_png(self, db, student):
        img = io.BytesIO(b"\x89PNG" + b"\x00" * 100)
        resp = _make_client(db, student).post(
            "/profile/upload-image",
            files={"file": ("avatar.png", img, "image/png")},
        )
        assert resp.status_code == 200
        assert "profile_image" in resp.json()

    def test_upload_webp(self, db, student):
        img = io.BytesIO(b"RIFF" + b"\x00" * 100)
        resp = _make_client(db, student).post(
            "/profile/upload-image",
            files={"file": ("pic.webp", img, "image/webp")},
        )
        assert resp.status_code == 200

    def test_reject_invalid_format(self, db, student):
        txt = io.BytesIO(b"not an image")
        resp = _make_client(db, student).post(
            "/profile/upload-image",
            files={"file": ("doc.pdf", txt, "application/pdf")},
        )
        assert resp.status_code == 400
        assert "Invalid image format" in resp.json()["detail"]

    def test_reject_gif(self, db, student):
        gif = io.BytesIO(b"GIF89a" + b"\x00" * 100)
        resp = _make_client(db, student).post(
            "/profile/upload-image",
            files={"file": ("anim.gif", gif, "image/gif")},
        )
        assert resp.status_code == 400

    def test_profile_image_persisted_in_db(self, db, student):
        img = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        _make_client(db, student).post(
            "/profile/upload-image",
            files={"file": ("photo.jpg", img, "image/jpeg")},
        )
        db.expire_all()
        refreshed = db.query(User).filter(User.id == student.id).first()
        assert refreshed.profile_image is not None
        assert refreshed.profile_image.startswith("/uploads/profile/")

    def test_image_reflected_in_profile_me(self, db, student):
        img = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        _make_client(db, student).post(
            "/profile/upload-image",
            files={"file": ("photo.jpg", img, "image/jpeg")},
        )
        data = _make_client(db, student).get("/profile/me").json()
        assert data["profile_image"] is not None
        assert data["profile_image"].startswith("/uploads/profile/")

    def test_upload_replaces_old_image(self, db, student):
        img1 = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        resp1 = _make_client(db, student).post(
            "/profile/upload-image",
            files={"file": ("first.jpg", img1, "image/jpeg")},
        )
        first_path = resp1.json()["profile_image"]

        img2 = io.BytesIO(b"\x89PNG" + b"\x00" * 100)
        resp2 = _make_client(db, student).post(
            "/profile/upload-image",
            files={"file": ("second.png", img2, "image/png")},
        )
        second_path = resp2.json()["profile_image"]
        assert first_path != second_path

    def test_unauthenticated_returns_401(self, db, student):
        txt = io.BytesIO(b"nope")
        resp = _make_client(db, None).post(
            "/profile/upload-image",
            files={"file": ("f.jpg", txt, "image/jpeg")},
        )
        assert resp.status_code in (401, 403)

    def test_no_file_returns_422(self, db, student):
        resp = _make_client(db, student).post("/profile/upload-image")
        assert resp.status_code == 422


# ── Integration: GET /users/me returns new fields ────────────────────────


class TestUsersMeIncludesNewFields:
    def test_users_me_returns_full_name(self, db, student):
        resp = _make_client(db, student).get("/users/me")
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Test Student"

    def test_users_me_returns_department(self, db, student):
        data = _make_client(db, student).get("/users/me").json()
        assert data["department"] == "Computer Science"

    def test_users_me_returns_semester(self, db, student):
        data = _make_client(db, student).get("/users/me").json()
        assert data["semester"] == 4

    def test_users_me_returns_profile_image(self, db, student):
        data = _make_client(db, student).get("/users/me").json()
        assert "profile_image" in data

    def test_register_sets_full_name(self, db, student):
        client = _make_client(db, student)
        resp = client.post(
            "/users/register",
            json={"phone": "9900000002", "name": "Reg User", "role": "student"},
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Reg User"
