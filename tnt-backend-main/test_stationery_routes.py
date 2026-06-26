"""
Stationery routes — test_stationery_routes.py

Covers:
  POST /stationery/services          — stationery vendor creates a service
  POST /stationery/jobs              — student submits a print job (file upload)
  POST /stationery/jobs/{id}/status  — vendor updates job status
"""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.stationery.job_model import JobStatus, StationeryJob
from app.modules.stationery.service_model import StationeryService
from app.modules.users.model import User, UserRole


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _make_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


def _session(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _auth(user: User):
    return lambda: {"id": user.id, "phone": user.phone, "role": user.role.value}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def engine():
    eng = _make_engine()
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture()
def db(engine):
    session = _session(engine)
    yield session
    session.close()


@pytest.fixture()
def stationery_vendor(db) -> User:
    u = User(
        phone="9600000010",
        name="Print Shop",
        role=UserRole.VENDOR,
        vendor_type="stationery",
        is_active=True,
        is_approved=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def food_vendor(db) -> User:
    u = User(
        phone="9600000011",
        name="Food Vendor",
        role=UserRole.VENDOR,
        vendor_type="food",
        is_active=True,
        is_approved=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def student(db) -> User:
    u = User(
        phone="9600000020",
        name="Print Student",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def service(db, stationery_vendor) -> StationeryService:
    svc = StationeryService(
        vendor_id=stationery_vendor.id,
        name="A4 Printing",
        price_per_unit=200,
        unit="page",
        is_available=True,
    )
    db.add(svc)
    db.commit()
    db.refresh(svc)
    return svc


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


def _client(engine, db_session, user: User):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = _auth(user)
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# POST /stationery/services
# ---------------------------------------------------------------------------

class TestAddService:
    def test_stationery_vendor_can_create_service(self, engine, db, stationery_vendor):
        client = _client(engine, db, stationery_vendor)
        resp = client.post(
            "/stationery/services",
            data={"name": "Binding", "price_per_unit": 500, "unit": "copy"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Binding"
        assert data["price_per_unit"] == 500
        assert data["unit"] == "copy"

    def test_service_persisted_in_db(self, engine, db, stationery_vendor):
        client = _client(engine, db, stationery_vendor)
        client.post(
            "/stationery/services",
            data={"name": "Lamination", "price_per_unit": 1000, "unit": "sheet"},
        )
        svc = db.query(StationeryService).filter(StationeryService.name == "Lamination").first()
        assert svc is not None
        assert svc.vendor_id == stationery_vendor.id

    def test_food_vendor_cannot_create_service(self, engine, db, food_vendor):
        client = _client(engine, db, food_vendor)
        resp = client.post(
            "/stationery/services",
            data={"name": "Printing", "price_per_unit": 200, "unit": "page"},
        )
        assert resp.status_code == 403

    def test_student_cannot_create_service(self, engine, db, student):
        client = _client(engine, db, student)
        resp = client.post(
            "/stationery/services",
            data={"name": "Printing", "price_per_unit": 200, "unit": "page"},
        )
        assert resp.status_code in (401, 403)

    def test_service_response_includes_vendor_id(self, engine, db, stationery_vendor):
        client = _client(engine, db, stationery_vendor)
        resp = client.post(
            "/stationery/services",
            data={"name": "Spiral Binding", "price_per_unit": 800, "unit": "copy"},
        )
        assert resp.status_code == 200
        assert resp.json()["vendor_id"] == stationery_vendor.id


# ---------------------------------------------------------------------------
# POST /stationery/jobs
# ---------------------------------------------------------------------------

class TestSubmitJob:
    def _fake_file(self):
        return ("document.pdf", io.BytesIO(b"%PDF-1.4 fake content"), "application/pdf")

    def test_student_can_submit_job(self, engine, db, student, service):
        client = _client(engine, db, student)
        with patch("app.modules.stationery.router.save_stationery_file", return_value="/uploads/doc.pdf"), \
             patch("app.modules.stationery.router.notify_user"):
            resp = client.post(
                "/stationery/jobs",
                data={"service_id": service.id, "quantity": 5},
                files={"file": self._fake_file()},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == student.id
        assert data["service_id"] == service.id
        assert data["quantity"] == 5

    def test_job_persisted_in_db(self, engine, db, student, service):
        client = _client(engine, db, student)
        with patch("app.modules.stationery.router.save_stationery_file", return_value="/uploads/doc.pdf"), \
             patch("app.modules.stationery.router.notify_user"):
            client.post(
                "/stationery/jobs",
                data={"service_id": service.id, "quantity": 3},
                files={"file": self._fake_file()},
            )
        job = db.query(StationeryJob).filter(StationeryJob.user_id == student.id).first()
        assert job is not None
        assert job.quantity == 3
        assert job.status == JobStatus.SUBMITTED

    def test_job_status_defaults_to_submitted(self, engine, db, student, service):
        client = _client(engine, db, student)
        with patch("app.modules.stationery.router.save_stationery_file", return_value="/uploads/doc.pdf"), \
             patch("app.modules.stationery.router.notify_user"):
            resp = client.post(
                "/stationery/jobs",
                data={"service_id": service.id, "quantity": 1},
                files={"file": self._fake_file()},
            )
        assert resp.json()["status"] == "submitted"

    def test_vendor_notified_after_submission(self, engine, db, student, service):
        client = _client(engine, db, student)
        with patch("app.modules.stationery.router.save_stationery_file", return_value="/uploads/f.pdf"), \
             patch("app.modules.stationery.router.notify_user") as mock_notify:
            client.post(
                "/stationery/jobs",
                data={"service_id": service.id, "quantity": 2},
                files={"file": self._fake_file()},
            )
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args[1] if mock_notify.call_args[1] else mock_notify.call_args[0]

    def test_nonexistent_service_returns_404(self, engine, db, student):
        client = _client(engine, db, student)
        with patch("app.modules.stationery.router.save_stationery_file", return_value="/uploads/f.pdf"):
            resp = client.post(
                "/stationery/jobs",
                data={"service_id": 99999, "quantity": 1},
                files={"file": self._fake_file()},
            )
        assert resp.status_code == 404

    def test_unavailable_service_returns_404(self, engine, db, student, service):
        service.is_available = False
        db.commit()
        client = _client(engine, db, student)
        with patch("app.modules.stationery.router.save_stationery_file", return_value="/uploads/f.pdf"):
            resp = client.post(
                "/stationery/jobs",
                data={"service_id": service.id, "quantity": 1},
                files={"file": self._fake_file()},
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /stationery/jobs/{id}/status
# ---------------------------------------------------------------------------

class TestUpdateJobStatus:
    def _seed_job(self, db, student, service) -> StationeryJob:
        job = StationeryJob(
            user_id=student.id,
            vendor_id=service.vendor_id,
            service_id=service.id,
            quantity=2,
            file_url="/uploads/test.pdf",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def test_vendor_can_set_status_to_in_progress(self, engine, db, stationery_vendor, student, service):
        job = self._seed_job(db, student, service)
        client = _client(engine, db, stationery_vendor)
        resp = client.post(f"/stationery/jobs/{job.id}/status", params={"status": "in_progress"})
        assert resp.status_code == 200
        db.expire_all()
        assert db.query(StationeryJob).get(job.id).status == JobStatus.IN_PROGRESS

    def test_vendor_can_set_status_to_ready_and_notifies_student(
        self, engine, db, stationery_vendor, student, service
    ):
        job = self._seed_job(db, student, service)
        client = _client(engine, db, stationery_vendor)
        with patch("app.modules.stationery.router.notify_user") as mock_notify:
            resp = client.post(f"/stationery/jobs/{job.id}/status", params={"status": "ready"})
        assert resp.status_code == 200
        mock_notify.assert_called_once()

    def test_status_persisted_in_db(self, engine, db, stationery_vendor, student, service):
        job = self._seed_job(db, student, service)
        client = _client(engine, db, stationery_vendor)
        client.post(f"/stationery/jobs/{job.id}/status", params={"status": "collected"})
        db.expire_all()
        assert db.query(StationeryJob).get(job.id).status == JobStatus.COLLECTED

    def test_food_vendor_returns_403(self, engine, db, food_vendor, student, service):
        job = self._seed_job(db, student, service)
        client = _client(engine, db, food_vendor)
        resp = client.post(f"/stationery/jobs/{job.id}/status", params={"status": "in_progress"})
        assert resp.status_code == 403

    def test_nonexistent_job_returns_404(self, engine, db, stationery_vendor):
        client = _client(engine, db, stationery_vendor)
        resp = client.post("/stationery/jobs/99999/status", params={"status": "in_progress"})
        assert resp.status_code == 404

    def test_student_cannot_update_status(self, engine, db, student, service):
        job = self._seed_job(db, student, service)
        client = _client(engine, db, student)
        resp = client.post(f"/stationery/jobs/{job.id}/status", params={"status": "in_progress"})
        assert resp.status_code in (401, 403)

    def test_invalid_status_returns_422(self, engine, db, stationery_vendor, student, service):
        job = self._seed_job(db, student, service)
        client = _client(engine, db, stationery_vendor)
        resp = client.post(f"/stationery/jobs/{job.id}/status", params={"status": "invalid_status"})
        assert resp.status_code == 422
