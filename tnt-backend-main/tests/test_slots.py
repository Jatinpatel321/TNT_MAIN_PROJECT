"""Tests for Slots API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStatus
from app.modules.slots.model import Slot, SlotStatus
from app.core.security import create_access_token


class TestSlotsAPI:
    """Test slot management endpoints."""

    def _create_vendor(self, db: Session) -> Vendor:
        """Helper to create a test vendor."""
        user = User(phone="+919999999501", role=UserRole.VENDOR, is_verified=True)
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
        response = client.post(
            "/v1/slots",
            headers=self._get_auth_header(vendor.vendor_id),
            json={
                "vendor_id": vendor.vendor_id,
                "start_time": "09:00",
                "end_time": "10:00",
                "max_orders": 10,
                "current_orders": 0,
                "status": SlotStatus.AVAILABLE.value,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["start_time"] == "09:00"
        assert data["end_time"] == "10:00"
        assert data["max_orders"] == 10

    def test_get_slots(self, client: TestClient, db: Session):
        """Test getting slots."""
        vendor = self._create_vendor(db)

        # Create slots
        for i in range(3):
            slot = Slot(
                vendor_id=vendor.vendor_id,
                start_time=f"{9+i:02d}:00",
                end_time=f"{10+i:02d}:00",
                max_orders=10,
                current_orders=0,
                status=SlotStatus.AVAILABLE,
            )
            db.add(slot)
        db.commit()

        response = client.get(
            "/v1/slots",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_update_slot(self, client: TestClient, db: Session):
        """Test updating slot."""
        vendor = self._create_vendor(db)

        slot = Slot(
            vendor_id=vendor.vendor_id,
            start_time="09:00",
            end_time="10:00",
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

        slot = Slot(
            vendor_id=vendor.vendor_id,
            start_time="09:00",
            end_time="10:00",
            max_orders=10,
            current_orders=0,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)

        response = client.delete(
            f"/v1/slots/{slot.id}",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200

        # Verify deleted
        get_resp = client.get(
            f"/v1/slots/{slot.id}",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert get_resp.status_code == 404

    def test_slot_capacity_tracking(self, client: TestClient, db: Session):
        """Test slot capacity tracking."""
        vendor = self._create_vendor(db)

        slot = Slot(
            vendor_id=vendor.vendor_id,
            start_time="09:00",
            end_time="10:00",
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
        assert slot.is_available() is True

        # Fill to capacity
        slot.current_orders = 10
        db.commit()
        assert slot.is_available() is False

    def test_unauthorized_slot_access(self, client: TestClient):
        """Test unauthorized access to slots."""
        response = client.get("/v1/slots")
        assert response.status_code == 401

        response = client.post("/v1/slots", json={})
        assert response.status_code == 401

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
        slot = Slot(
            vendor_id=vendor.vendor_id,
            start_time="09:00",
            end_time="10:00",
            max_orders=10,
            current_orders=0,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot)
        db.commit()

        # Staff token
        staff_token = create_access_token(vendor.vendor_id, "vendor_staff", staff.id)
        response = client.get(
            "/v1/slots",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert response.status_code == 200

    def test_slot_status_enum(self, client: TestClient, db: Session):
        """Test slot status values."""
        vendor = self._create_vendor(db)
        
        # Test all status values
        statuses = [SlotStatus.AVAILABLE, SlotStatus.BLOCKED, SlotStatus.FULL]
        for status in statuses:
            slot = Slot(
                vendor_id=vendor.vendor_id,
                start_time="10:00",
                end_time="11:00",
                max_orders=10,
                current_orders=0,
                status=status,
            )
            db.add(slot)
        db.commit()

        slots = db.query(Slot).filter(Slot.vendor_id == vendor.vendor_id).all()
        assert len(slots) == 3
        assert slots[0].status == SlotStatus.AVAILABLE
        assert slots[1].status == SlotStatus.BLOCKED
        assert slots[2].status == SlotStatus.FULL


class TestSlotModel:
    """Test Slot model."""

    def test_create_slot(self, db: Session):
        """Test creating slot model."""
        from app.modules.users.model import User, UserRole
        from app.modules.vendors.model import Vendor, VendorStatus

        user = User(phone="+919999999502", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Slot Model Test",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        slot = Slot(
            vendor_id=vendor.vendor_id,
            start_time="09:00",
            end_time="10:00",
            max_orders=10,
            current_orders=0,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)

        assert slot.id is not None
        assert slot.vendor_id == vendor.vendor_id
        assert slot.start_time == "09:00"
        assert slot.end_time == "10:00"
        assert slot.max_orders == 10
        assert slot.is_available() is True

    def test_slot_availability_check(self, db: Session):
        """Test slot availability logic."""
        from app.modules.users.model import User, UserRole
        from app.modules.vendors.model import Vendor, VendorStatus

        user = User(phone="+919999999503", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Availability Test",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        # Available slot
        slot1 = Slot(
            vendor_id=vendor.vendor_id,
            start_time="09:00",
            end_time="10:00",
            max_orders=10,
            current_orders=5,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot1)

        # Full slot
        slot2 = Slot(
            vendor_id=vendor.vendor_id,
            start_time="10:00",
            end_time="11:00",
            max_orders=10,
            current_orders=10,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot2)

        # Blocked slot
        slot3 = Slot(
            vendor_id=vendor.vendor_id,
            start_time="11:00",
            end_time="12:00",
            max_orders=10,
            current_orders=0,
            status=SlotStatus.BLOCKED,
        )
        db.add(slot3)
        db.commit()

        assert slot1.is_available() is True
        assert slot2.is_available() is False
        assert slot3.is_available() is False