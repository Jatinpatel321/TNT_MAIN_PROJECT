"""
Tests for slot endpoints:
  POST /slots/          – vendor creates a slot
  POST /slots/{id}/book – authenticated user books a slot
"""
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
from app.modules.slots.model import Slot, SlotStatus
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
    vendor = User(
        phone="8600000001",
        name="Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
        vendor_type="food",
    )
    unapproved_vendor = User(
        phone="8600000002",
        name="PendingVendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=False,
        vendor_type="food",
    )
    student = User(phone="8600000010", name="Student", role=UserRole.STUDENT, is_active=True)
    test_db_session.add_all([vendor, unapproved_vendor, student])
    test_db_session.commit()
    for u in (vendor, unapproved_vendor, student):
        test_db_session.refresh(u)

    slot = Slot(
        vendor_id=vendor.id,
        start_time=utcnow_naive() + timedelta(hours=1),
        end_time=utcnow_naive() + timedelta(hours=2),
        max_orders=5,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    test_db_session.add(slot)
    test_db_session.commit()
    test_db_session.refresh(slot)

    return {
        "vendor": vendor,
        "unapproved_vendor": unapproved_vendor,
        "student": student,
        "slot": slot,
    }


def _make_client(db_session, user: User) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: {
        "id": user.id,
        "phone": user.phone,
        "role": user.role.value,
    }
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# POST /slots/ – vendor creates a slot
# ---------------------------------------------------------------------------


def test_vendor_can_create_slot(test_db_session, seed_data):
    start = (utcnow_naive() + timedelta(hours=3)).isoformat()
    end = (utcnow_naive() + timedelta(hours=4)).isoformat()

    client = _make_client(test_db_session, seed_data["vendor"])
    resp = client.post("/slots/", json={"start_time": start, "end_time": end, "max_orders": 10})
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["max_orders"] == 10
    assert data["current_orders"] == 0
    assert data["vendor_id"] == seed_data["vendor"].id


def test_created_slot_persisted_in_db(test_db_session, seed_data):
    start = (utcnow_naive() + timedelta(hours=5)).isoformat()
    end = (utcnow_naive() + timedelta(hours=6)).isoformat()

    client = _make_client(test_db_session, seed_data["vendor"])
    resp = client.post("/slots/", json={"start_time": start, "end_time": end, "max_orders": 8})
    app.dependency_overrides.clear()

    slot_id = resp.json()["id"]
    slot = test_db_session.query(Slot).filter(Slot.id == slot_id).first()
    assert slot is not None
    assert slot.max_orders == 8


def test_create_slot_response_has_load_label(test_db_session, seed_data):
    start = (utcnow_naive() + timedelta(hours=7)).isoformat()
    end = (utcnow_naive() + timedelta(hours=8)).isoformat()

    client = _make_client(test_db_session, seed_data["vendor"])
    resp = client.post("/slots/", json={"start_time": start, "end_time": end, "max_orders": 5})
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert "load_label" in resp.json()
    assert "express_pickup_eligible" in resp.json()


def test_create_slot_invalid_timing_returns_400(test_db_session, seed_data):
    # end_time before start_time
    start = (utcnow_naive() + timedelta(hours=5)).isoformat()
    end = (utcnow_naive() + timedelta(hours=4)).isoformat()

    client = _make_client(test_db_session, seed_data["vendor"])
    resp = client.post("/slots/", json={"start_time": start, "end_time": end, "max_orders": 5})
    app.dependency_overrides.clear()

    assert resp.status_code == 400


def test_unapproved_vendor_cannot_create_slot(test_db_session, seed_data):
    start = (utcnow_naive() + timedelta(hours=3)).isoformat()
    end = (utcnow_naive() + timedelta(hours=4)).isoformat()

    client = _make_client(test_db_session, seed_data["unapproved_vendor"])
    resp = client.post("/slots/", json={"start_time": start, "end_time": end, "max_orders": 5})
    app.dependency_overrides.clear()

    assert resp.status_code == 403


def test_student_cannot_create_slot(test_db_session, seed_data):
    start = (utcnow_naive() + timedelta(hours=3)).isoformat()
    end = (utcnow_naive() + timedelta(hours=4)).isoformat()

    client = _make_client(test_db_session, seed_data["student"])
    resp = client.post("/slots/", json={"start_time": start, "end_time": end, "max_orders": 5})
    app.dependency_overrides.clear()

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /slots/{id}/book – book an existing slot
# ---------------------------------------------------------------------------


def test_student_can_book_available_slot(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["student"])
    resp = client.post(f"/slots/{seed_data['slot'].id}/book")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["slot_id"] == seed_data["slot"].id
    assert data["current_orders"] == 1


def test_booking_increments_current_orders_in_db(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["student"])
    client.post(f"/slots/{seed_data['slot'].id}/book")
    app.dependency_overrides.clear()

    test_db_session.refresh(seed_data["slot"])
    assert seed_data["slot"].current_orders == 1


def test_booking_returns_load_label(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["student"])
    resp = client.post(f"/slots/{seed_data['slot'].id}/book")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert "load_label" in resp.json()
    assert "express_pickup_eligible" in resp.json()


def test_book_nonexistent_slot_returns_404(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["student"])
    resp = client.post("/slots/99999/book")
    app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_booking_full_slot_returns_400(test_db_session, seed_data):
    # Fill the slot to max_orders
    slot = seed_data["slot"]
    slot.current_orders = slot.max_orders
    slot.status = SlotStatus.FULL
    test_db_session.commit()

    client = _make_client(test_db_session, seed_data["student"])
    resp = client.post(f"/slots/{slot.id}/book")
    app.dependency_overrides.clear()

    assert resp.status_code == 400


def test_booking_slot_status_becomes_limited_at_70_pct(test_db_session, seed_data):
    # max_orders=5 → 70% = 3.5 → status LIMITED at current_orders >= 4
    slot = seed_data["slot"]
    slot.current_orders = 3  # 60% – next booking (4 = 80%) should flip to LIMITED
    test_db_session.commit()

    client = _make_client(test_db_session, seed_data["student"])
    resp = client.post(f"/slots/{slot.id}/book")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    test_db_session.refresh(slot)
    assert slot.status == SlotStatus.LIMITED


# ---------------------------------------------------------------------------
# GET /slots/recommend/{vendor_id} – AI powered slot recommendation
# ---------------------------------------------------------------------------


def test_recommend_slot_picks_lowest_load_upcoming_slot(test_db_session, seed_data):
    vendor = seed_data["vendor"]

    # Add a second slot with higher utilization and a third slot with lower utilization.
    now = utcnow_naive()
    slot_high = Slot(
        vendor_id=vendor.id,
        start_time=now + timedelta(hours=1, minutes=10),
        end_time=now + timedelta(hours=1, minutes=20),
        max_orders=5,
        current_orders=4,
        status=SlotStatus.LIMITED,
    )
    slot_best = Slot(
        vendor_id=vendor.id,
        start_time=now + timedelta(hours=1, minutes=20),
        end_time=now + timedelta(hours=1, minutes=30),
        max_orders=10,
        current_orders=1,
        status=SlotStatus.AVAILABLE,
    )
    test_db_session.add_all([slot_high, slot_best])
    test_db_session.commit()

    client = _make_client(test_db_session, seed_data["student"])
    resp = client.get(f"/slots/recommend/{vendor.id}")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"recommended_slot", "estimated_wait", "reason"}
    assert isinstance(data["recommended_slot"], str) and data["recommended_slot"]
    assert data["estimated_wait"].endswith("minutes")
