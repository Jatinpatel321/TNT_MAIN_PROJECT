"""Tests for Slots API endpoints."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStatus
from app.modules.slots.model import Slot, SlotStatus
from app.modules.vendors.auth_service import _create_access_token as create_access_token


def _slot_window(hours_from_now: int = 1):
    start = utcnow_naive() + timedelta(hours=hours_from_now)
    return start, start + timedelta(hours=1)


class TestSlotsAPI:
    """Test slot management endpoints."""

    def _create_vendor(self, db: Session, phone: str = "+919999999501") -> Vendor:
        """Helper to create a test vendor with an approved owner user."""
        user = User(phone=phone, role=UserRole.VENDOR, is_active=True, is_approved=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Slots Test Shop",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)
        return vendor

    def _get_auth_header(self, vendor_id: int) -> dict:
        """Helper to create auth header."""
        token = create_access_token(vendor_id, "vendor_owner")
        return {"Authorization": f"Bearer {token}"}

    def test_create_slot(self, client: TestClient, db: Session):
        """Test creating a slot."""
        vendor = self._create_vendor(db)
        start, end = _slot_window()
        response = client.post(
            "/v1/slots/",
            headers=self._get_auth_header(vendor.vendor_id),
            json={
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "max_orders": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["max_orders"] == 10
        assert data["current_orders"] == 0
        # Slots are owned by the vendor's owner user id
        assert data["vendor_id"] == vendor.owner_id

    def test_get_slots(self, client: TestClient, db: Session):
        """Test getting slots."""
        vendor = self._create_vendor(db)

        # Create slots (owned by the vendor's owner user)
        for i in range(3):
            start, end = _slot_window(hours_from_now=1 + i)
            slot = Slot(
                vendor_id=vendor.owner_id,
                start_time=start,
                end_time=end,
                max_orders=10,
                current_orders=0,
                status=SlotStatus.AVAILABLE,
            )
            db.add(slot)
        db.commit()

        response = client.get(
            f"/v1/slots/?vendor_id={vendor.owner_id}",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_update_slot(self, client: TestClient, db: Session):
        """Test updating slot."""
        vendor = self._create_vendor(db)

        start, end = _slot_window()
        slot = Slot(
            vendor_id=vendor.owner_id,
            start_time=start,
            end_time=end,
            max_orders=10,
            current_orders=0,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)

        response = client.put(
            f"/v1/slots/{slot.id}",
            headers=self._get_auth_header(vendor.vendor_id),
            json={
                "max_orders": 15,
                "status": SlotStatus.BLOCKED.value,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["max_orders"] == 15
        assert data["status"] == SlotStatus.BLOCKED.value

    def test_delete_slot(self, client: TestClient, db: Session):
        """Test deleting slot."""
        vendor = self._create_vendor(db)

        start, end = _slot_window()
        slot = Slot(
            vendor_id=vendor.owner_id,
            start_time=start,
            end_time=end,
            max_orders=10,
            current_orders=0,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)
        slot_id = slot.id

        response = client.delete(
            f"/v1/slots/{slot_id}",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200

        # Verify deleted
        assert db.query(Slot).filter(Slot.id == slot_id).first() is None

    def test_slot_capacity_tracking(self, client: TestClient, db: Session):
        """Test slot capacity tracking."""
        vendor = self._create_vendor(db)

        start, end = _slot_window()
        slot = Slot(
            vendor_id=vendor.owner_id,
            start_time=start,
            end_time=end,
            max_orders=10,
            current_orders=5,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)

        # Check capacity
        assert slot.current_orders == 5
        assert slot.max_orders == 10
        assert slot.current_orders < slot.max_orders

        # Fill to capacity
        slot.current_orders = 10
        db.commit()
        assert slot.current_orders >= slot.max_orders

    def test_unauthorized_slot_access(self, client: TestClient):
        """Test unauthorized access to slots."""
        response = client.get("/v1/slots/")
        assert response.status_code in (401, 403)

        response = client.post("/v1/slots/", json={})
        assert response.status_code in (401, 403)

    def test_staff_can_view_slots(self, client: TestClient, db: Session):
        """Test staff can view slots."""
        vendor = self._create_vendor(db)

        # Create staff
        from app.modules.vendors.model import VendorStaff
        staff = VendorStaff(
            vendor_id=vendor.vendor_id,
            name="Staff User",
            role="staff",
            phone="+919888888888",
            password_hash=VendorStaff.hash_password("pass"),
            is_active=True,
        )
        db.add(staff)
        db.commit()
        db.refresh(staff)

        # Create slot
        start, end = _slot_window()
        slot = Slot(
            vendor_id=vendor.owner_id,
            start_time=start,
            end_time=end,
            max_orders=10,
            current_orders=0,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot)
        db.commit()

        # Staff token
        staff_token = create_access_token(vendor.vendor_id, "vendor_staff", staff.id)
        response = client.get(
            "/v1/slots/",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert response.status_code == 200

    def test_slot_status_enum(self, client: TestClient, db: Session):
        """Test slot status values."""
        vendor = self._create_vendor(db)

        # Test all status values
        statuses = [SlotStatus.AVAILABLE, SlotStatus.BLOCKED, SlotStatus.FULL]
        for i, status in enumerate(statuses):
            start, end = _slot_window(hours_from_now=1 + i)
            slot = Slot(
                vendor_id=vendor.owner_id,
                start_time=start,
                end_time=end,
                max_orders=10,
                current_orders=0,
                status=status,
            )
            db.add(slot)
        db.commit()

        slots = (
            db.query(Slot)
            .filter(Slot.vendor_id == vendor.owner_id)
            .order_by(Slot.start_time)
            .all()
        )
        assert len(slots) == 3
        assert slots[0].status == SlotStatus.AVAILABLE
        assert slots[1].status == SlotStatus.BLOCKED
        assert slots[2].status == SlotStatus.FULL


class TestSlotModel:
    """Test Slot model."""

    def _create_owner(self, db: Session, phone: str) -> User:
        user = User(phone=phone, role=UserRole.VENDOR, is_active=True, is_approved=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def test_create_slot(self, db: Session):
        """Test creating slot model."""
        owner = self._create_owner(db, "+919999999502")

        start, end = _slot_window()
        slot = Slot(
            vendor_id=owner.id,
            start_time=start,
            end_time=end,
            max_orders=10,
            current_orders=0,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)

        assert slot.id is not None
        assert slot.vendor_id == owner.id
        assert slot.start_time == start
        assert slot.end_time == end
        assert slot.max_orders == 10
        assert slot.current_orders < slot.max_orders

    def test_slot_availability_check(self, db: Session):
        """Test slot availability logic."""
        owner = self._create_owner(db, "+919999999503")

        # Available slot
        start1, end1 = _slot_window(hours_from_now=1)
        slot1 = Slot(
            vendor_id=owner.id,
            start_time=start1,
            end_time=end1,
            max_orders=10,
            current_orders=5,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot1)

        # Full slot
        start2, end2 = _slot_window(hours_from_now=2)
        slot2 = Slot(
            vendor_id=owner.id,
            start_time=start2,
            end_time=end2,
            max_orders=10,
            current_orders=10,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot2)

        # Blocked slot
        start3, end3 = _slot_window(hours_from_now=3)
        slot3 = Slot(
            vendor_id=owner.id,
            start_time=start3,
            end_time=end3,
            max_orders=10,
            current_orders=0,
            status=SlotStatus.BLOCKED,
        )
        db.add(slot3)
        db.commit()

        def is_bookable(s: Slot) -> bool:
            return s.status == SlotStatus.AVAILABLE and s.current_orders < s.max_orders

        assert is_bookable(slot1) is True
        assert is_bookable(slot2) is False
        assert is_bookable(slot3) is False
