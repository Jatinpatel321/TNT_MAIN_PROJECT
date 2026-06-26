"""
Slot Scheduling System — test_slot_scheduling.py

Covers:
  POST /slots/{id}/book    — booking with SlotBooking record creation
  POST /slots/{id}/cancel  — cancel a booking, restore capacity
  POST /slots/{id}/lock    — vendor locks a slot
  POST /slots/{id}/unlock  — vendor unlocks a slot
  GET  /slots/my-bookings  — list user's bookings
  GET  /slots/             — slot listing with new fields
  Overbooking prevention
  Faculty priority
  Duplicate booking prevention
"""
from __future__ import annotations

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
from app.modules.slots.model import Slot, SlotBooking, SlotStatus, BookingStatus
from app.modules.users.model import User, UserRole


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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
def vendor(db):
    v = User(
        phone="9900000001",
        name="Test Vendor",
        role=UserRole.VENDOR,
        vendor_type="food",
        is_active=True,
        is_approved=True,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@pytest.fixture()
def student(db):
    s = User(
        phone="9900000010",
        name="Test Student",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@pytest.fixture()
def student2(db):
    s = User(
        phone="9900000011",
        name="Test Student 2",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@pytest.fixture()
def faculty(db):
    f = User(
        phone="9900000020",
        name="Prof Test",
        role=UserRole.FACULTY,
        is_active=True,
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


@pytest.fixture()
def slot(db, vendor):
    s = Slot(
        vendor_id=vendor.id,
        start_time=utcnow() + timedelta(hours=1),
        end_time=utcnow() + timedelta(hours=2),
        max_orders=5,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _make_client(db_session, user: User | None) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db_session
    if user:
        app.dependency_overrides[get_current_user] = lambda: {
            "id": user.id,
            "phone": user.phone,
            "role": user.role.value,
            "is_active": True,
        }
    else:
        app.dependency_overrides.pop(get_current_user, None)
    return TestClient(app, raise_server_exceptions=False)


def _cleanup():
    app.dependency_overrides.clear()


# ── Booking with SlotBooking record ────────────────────────────────────────


class TestSlotBooking:
    def test_book_creates_booking_record(self, db, slot, student):
        client = _make_client(db, student)
        resp = client.post(f"/slots/{slot.id}/book")
        _cleanup()
        assert resp.status_code == 200
        data = resp.json()
        assert "booking_id" in data
        assert data["current_orders"] == 1

        # Verify booking record in DB
        booking = db.query(SlotBooking).filter(SlotBooking.slot_id == slot.id).first()
        assert booking is not None
        assert booking.user_id == student.id
        assert booking.status == BookingStatus.CONFIRMED

    def test_duplicate_booking_prevented(self, db, slot, student):
        client = _make_client(db, student)
        resp1 = client.post(f"/slots/{slot.id}/book")
        _cleanup()
        assert resp1.status_code == 200

        # Try booking again
        client = _make_client(db, student)
        resp2 = client.post(f"/slots/{slot.id}/book")
        _cleanup()
        assert resp2.status_code == 409

    def test_multiple_users_can_book_same_slot(self, db, slot, student, student2):
        client1 = _make_client(db, student)
        resp1 = client1.post(f"/slots/{slot.id}/book")
        _cleanup()
        assert resp1.status_code == 200

        client2 = _make_client(db, student2)
        resp2 = client2.post(f"/slots/{slot.id}/book")
        _cleanup()
        assert resp2.status_code == 200

        db.refresh(slot)
        assert slot.current_orders == 2

    def test_booking_full_slot_returns_400(self, db, slot, student):
        slot.current_orders = slot.max_orders
        slot.status = SlotStatus.FULL
        db.commit()

        client = _make_client(db, student)
        resp = client.post(f"/slots/{slot.id}/book")
        _cleanup()
        assert resp.status_code == 400

    def test_booking_includes_available_capacity(self, db, slot, student):
        client = _make_client(db, student)
        resp = client.post(f"/slots/{slot.id}/book")
        _cleanup()
        assert resp.status_code == 200
        data = resp.json()
        assert data["available_capacity"] == slot.max_orders - 1


# ── Cancel Booking ────────────────────────────────────────────────────────


class TestCancelBooking:
    def test_cancel_reduces_current_orders(self, db, slot, student):
        client = _make_client(db, student)
        book_resp = client.post(f"/slots/{slot.id}/book")
        _cleanup()
        assert book_resp.status_code == 200

        db.refresh(slot)
        assert slot.current_orders == 1

        client = _make_client(db, student)
        cancel_resp = client.post(f"/slots/{slot.id}/cancel")
        _cleanup()
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["current_orders"] == 0

    def test_cancel_marks_booking_cancelled(self, db, slot, student):
        client = _make_client(db, student)
        client.post(f"/slots/{slot.id}/book")
        _cleanup()

        client = _make_client(db, student)
        client.post(f"/slots/{slot.id}/cancel")
        _cleanup()

        booking = db.query(SlotBooking).filter(SlotBooking.slot_id == slot.id).first()
        assert booking is not None
        assert booking.status == BookingStatus.CANCELLED
        assert booking.cancelled_at is not None

    def test_cancel_reopens_full_slot(self, db, slot, student):
        slot.current_orders = slot.max_orders
        slot.status = SlotStatus.FULL
        db.commit()

        # Create a confirmed booking
        booking = SlotBooking(
            slot_id=slot.id,
            user_id=student.id,
            status=BookingStatus.CONFIRMED,
        )
        db.add(booking)
        db.commit()

        client = _make_client(db, student)
        resp = client.post(f"/slots/{slot.id}/cancel")
        _cleanup()
        assert resp.status_code == 200

        db.refresh(slot)
        assert slot.current_orders == slot.max_orders - 1
        assert slot.status != SlotStatus.FULL

    def test_cancel_nonexistent_booking_returns_404(self, db, slot, student):
        client = _make_client(db, student)
        resp = client.post(f"/slots/{slot.id}/cancel")
        _cleanup()
        assert resp.status_code == 404


# ── Slot Locking ────────────────────────────────────────────────────────────


class TestSlotLocking:
    def test_vendor_can_lock_slot(self, db, slot, vendor):
        client = _make_client(db, vendor)
        resp = client.post(f"/slots/{slot.id}/lock")
        _cleanup()
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_locked"] is True

        db.refresh(slot)
        assert slot.is_locked is True

    def test_vendor_can_unlock_slot(self, db, slot, vendor):
        slot.is_locked = True
        slot.locked_by = f"vendor:{vendor.id}"
        db.commit()

        client = _make_client(db, vendor)
        resp = client.post(f"/slots/{slot.id}/unlock")
        _cleanup()
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_locked"] is False

    def test_locked_slot_cannot_be_booked(self, db, slot, student, vendor):
        slot.is_locked = True
        slot.locked_by = f"vendor:{vendor.id}"
        db.commit()

        client = _make_client(db, student)
        resp = client.post(f"/slots/{slot.id}/book")
        _cleanup()
        assert resp.status_code == 423

    def test_student_cannot_lock_slot(self, db, slot, student):
        client = _make_client(db, student)
        resp = client.post(f"/slots/{slot.id}/lock")
        _cleanup()
        assert resp.status_code == 403

    def test_cannot_lock_already_locked_slot(self, db, slot, vendor):
        slot.is_locked = True
        slot.locked_by = f"vendor:{vendor.id}"
        db.commit()

        client = _make_client(db, vendor)
        resp = client.post(f"/slots/{slot.id}/lock")
        _cleanup()
        assert resp.status_code == 409

    def test_cannot_unlock_already_unlocked_slot(self, db, slot, vendor):
        client = _make_client(db, vendor)
        resp = client.post(f"/slots/{slot.id}/unlock")
        _cleanup()
        assert resp.status_code == 409


# ── Slot Listing with new fields ────────────────────────────────────────────


class TestSlotListing:
    def test_list_slots_includes_new_fields(self, db, slot, student):
        client = _make_client(db, student)
        resp = client.get("/slots/", params={"vendor_id": slot.vendor_id})
        _cleanup()
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        first = data[0]
        assert "is_locked" in first
        assert "available_capacity" in first
        assert "faculty_priority" in first
        assert "queue_size" in first
        assert "estimated_wait" in first

    def test_list_slots_shows_capacity(self, db, slot, student):
        slot.current_orders = 3
        db.commit()

        client = _make_client(db, student)
        resp = client.get("/slots/", params={"vendor_id": slot.vendor_id})
        _cleanup()
        data = resp.json()
        first = data[0]
        assert first["available_capacity"] == slot.max_orders - 3


# ── My Bookings ────────────────────────────────────────────────────────────


class TestMyBookings:
    def test_my_bookings_returns_confirmed(self, db, slot, student):
        client = _make_client(db, student)
        client.post(f"/slots/{slot.id}/book")
        _cleanup()

        client = _make_client(db, student)
        resp = client.get("/slots/my-bookings")
        _cleanup()
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["status"] == "confirmed"
        assert data[0]["slot_id"] == slot.id

    def test_my_bookings_excludes_cancelled(self, db, slot, student):
        client = _make_client(db, student)
        client.post(f"/slots/{slot.id}/book")
        _cleanup()

        client = _make_client(db, student)
        client.post(f"/slots/{slot.id}/cancel")
        _cleanup()

        client = _make_client(db, student)
        resp = client.get("/slots/my-bookings", params={"active_only": True})
        _cleanup()
        data = resp.json()
        assert len(data) == 0

    def test_my_bookings_includes_cancelled_when_requested(self, db, slot, student):
        client = _make_client(db, student)
        client.post(f"/slots/{slot.id}/book")
        _cleanup()

        client = _make_client(db, student)
        client.post(f"/slots/{slot.id}/cancel")
        _cleanup()

        client = _make_client(db, student)
        resp = client.get("/slots/my-bookings", params={"active_only": False})
        _cleanup()
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["status"] == "cancelled"


# ── Overbooking Prevention ─────────────────────────────────────────────────


class TestOverbookingPrevention:
    def test_cannot_exceed_max_orders(self, db, vendor, student, student2):
        slot = Slot(
            vendor_id=vendor.id,
            start_time=utcnow() + timedelta(hours=1),
            end_time=utcnow() + timedelta(hours=2),
            max_orders=1,
            current_orders=0,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)

        # First booking succeeds
        client1 = _make_client(db, student)
        resp1 = client1.post(f"/slots/{slot.id}/book")
        _cleanup()
        assert resp1.status_code == 200

        # Second booking fails (overbooking)
        client2 = _make_client(db, student2)
        resp2 = client2.post(f"/slots/{slot.id}/book")
        _cleanup()
        assert resp2.status_code == 400

    def test_status_transitions_correctly(self, db, vendor, student, student2):
        slot = Slot(
            vendor_id=vendor.id,
            start_time=utcnow() + timedelta(hours=1),
            end_time=utcnow() + timedelta(hours=2),
            max_orders=10,
            current_orders=0,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)

        # Fill to 70% threshold (7 orders)
        for i in range(7):
            s = User(phone=f"9900{1000+i}", name=f"Student {i}", role=UserRole.STUDENT, is_active=True)
            db.add(s)
            db.commit()
            db.refresh(s)
            client = _make_client(db, s)
            resp = client.post(f"/slots/{slot.id}/book")
            _cleanup()
            assert resp.status_code == 200

        db.refresh(slot)
        assert slot.status == SlotStatus.LIMITED
