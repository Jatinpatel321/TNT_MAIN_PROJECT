"""Smoke tests for the endpoints added to close the API↔frontend contract gaps.

Exercises (against a real SQLite DB + dependency overrides):
  - GET  /v1/vendors/reviews            (list, stats embedded)
  - GET  /v1/vendors/reviews/stats      (aggregate)
  - POST /v1/vendors/reviews/{id}/reply (writes the new vendor_reply columns)
  - GET  /v1/stationery/services        (list)
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
from app.modules.feedback.model import VendorReview
from app.modules.stationery.service_model import StationeryService
from app.modules.users.model import User, UserRole


def _naive_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def seed(db_session):
    student = User(phone="9900000001", name="Reviewer", role=UserRole.STUDENT, is_active=True)
    vendor = User(phone="9900000010", name="Vendor One", role=UserRole.VENDOR, is_active=True, is_approved=True)
    admin = User(phone="9900000020", name="Admin", role=UserRole.ADMIN, is_active=True)
    db_session.add_all([student, vendor, admin])
    db_session.commit()
    for u in (student, vendor, admin):
        db_session.refresh(u)

    r1 = VendorReview(vendor_id=vendor.id, user_id=student.id, order_id=None, rating=5,
                      title="Great", review_text="Loved it", is_anonymous=False, created_at=_naive_now())
    r2 = VendorReview(vendor_id=vendor.id, user_id=student.id, order_id=None, rating=3,
                      title="Okay", review_text="Fine", is_anonymous=True, created_at=_naive_now())
    svc = StationeryService(vendor_id=vendor.id, name="Colour Print", price_per_unit=500, unit="page")
    db_session.add_all([r1, r2, svc])
    db_session.commit()
    db_session.refresh(r1)
    return {"student": student, "vendor": vendor, "admin": admin, "review": r1}


def _client(db_session, user_ctx):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user_ctx
    return TestClient(app)


def _ctx(u: User) -> dict:
    return {"id": u.id, "phone": u.phone, "role": u.role.value, "is_active": True}


def test_list_vendor_reviews(db_session, seed):
    client = _client(db_session, _ctx(seed["vendor"]))
    try:
        res = client.get("/v1/vendors/reviews")
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["total"] == 2
        assert len(body["reviews"]) == 2
        # anonymous review hides the user name
        anon = [r for r in body["reviews"] if r["rating"] == 3][0]
        assert anon["user_name"] is None
        named = [r for r in body["reviews"] if r["rating"] == 5][0]
        assert named["user_name"] == "Reviewer"
        assert named["comment"] == "Loved it"
        assert body["stats"]["total_reviews"] == 2
        assert body["stats"]["average_rating"] == 4.0
        assert body["stats"]["distribution"]["5"] == 1
    finally:
        app.dependency_overrides.clear()


def test_review_stats(db_session, seed):
    client = _client(db_session, _ctx(seed["vendor"]))
    try:
        res = client.get("/v1/vendors/reviews/stats")
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["total_reviews"] == 2
        assert body["average_rating"] == 4.0
    finally:
        app.dependency_overrides.clear()


def test_reply_to_review(db_session, seed):
    client = _client(db_session, _ctx(seed["vendor"]))
    try:
        rid = seed["review"].id
        res = client.post(f"/v1/vendors/reviews/{rid}/reply", json={"reply": "Thank you!"})
        assert res.status_code == 200, res.text
        assert res.json()["vendor_reply"] == "Thank you!"
        assert res.json()["vendor_reply_at"] is not None
        # empty reply rejected
        bad = client.post(f"/v1/vendors/reviews/{rid}/reply", json={"reply": "  "})
        assert bad.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_reply_rejects_foreign_review(db_session, seed):
    # A different vendor cannot reply to this vendor's review
    other = User(phone="9900000099", name="Other Vendor", role=UserRole.VENDOR, is_active=True, is_approved=True)
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)
    client = _client(db_session, _ctx(other))
    try:
        res = client.post(f"/v1/vendors/reviews/{seed['review'].id}/reply", json={"reply": "x"})
        assert res.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_list_stationery_services_admin(db_session, seed):
    client = _client(db_session, _ctx(seed["admin"]))
    try:
        res = client.get("/v1/stationery/services")
        assert res.status_code == 200, res.text
        services = res.json()
        assert len(services) == 1
        assert services[0]["name"] == "Colour Print"
        assert services[0]["vendor_name"] == "Vendor One"
    finally:
        app.dependency_overrides.clear()
