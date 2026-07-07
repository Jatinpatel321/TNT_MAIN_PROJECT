"""Tests for Vendor Profile API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStaff, VendorStatus
from app.modules.vendors.profile_models import VendorProfile, VendorStaffPermission
from app.core.security import create_access_token


class TestVendorProfileAPI:
    """Test vendor profile endpoints."""

    def _create_vendor(self, db: Session) -> Vendor:
        """Helper to create a test vendor."""
        user = User(phone="+919999999801", role=UserRole.VENDOR, is_active=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Profile Test Shop",
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

    def test_get_profile_success(self, client: TestClient, db: Session):
        """Test getting vendor profile."""
        vendor = self._create_vendor(db)
        response = client.get(
            "/v1/vendors/profile/",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["business_name"] == "Profile Test Shop"
        assert data["category"] == "food"

    def test_get_profile_unauthorized(self, client: TestClient):
        """Test getting profile without auth fails."""
        response = client.get("/v1/vendors/profile/")
        assert response.status_code == 401

    def test_update_profile_success(self, client: TestClient, db: Session):
        """Test updating vendor profile."""
        vendor = self._create_vendor(db)
        response = client.put(
            "/v1/vendors/profile/",
            headers=self._get_auth_header(vendor.vendor_id),
            json={
                "business_name": "Updated Shop Name",
                "description": "New description",
                "phone": "+919999999999",
                "email": "updated@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["business_name"] == "Updated Shop Name"
        assert data["description"] == "New description"
        assert data["phone"] == "+919999999999"

    def test_update_profile_business_hours(self, client: TestClient, db: Session):
        """Test updating business hours."""
        vendor = self._create_vendor(db)
        hours = {
            "monday": {"open": "08:00", "close": "20:00"},
            "tuesday": {"open": "08:00", "close": "20:00"},
        }
        response = client.put(
            "/v1/vendors/profile/",
            headers=self._get_auth_header(vendor.vendor_id),
            json={"business_hours": hours},
        )
        assert response.status_code == 200
        assert response.json()["business_hours"] == hours

    def test_update_profile_holidays(self, client: TestClient, db: Session):
        """Test updating holidays."""
        vendor = self._create_vendor(db)
        holidays = [
            {"date": "2024-12-25", "reason": "Christmas"},
            {"date": "2025-01-01", "reason": "New Year"},
        ]
        response = client.put(
            "/v1/vendors/profile/",
            headers=self._get_auth_header(vendor.vendor_id),
            json={"holidays": holidays},
        )
        assert response.status_code == 200
        assert response.json()["holidays"] == holidays

    def test_update_profile_location(self, client: TestClient, db: Session):
        """Test updating location."""
        vendor = self._create_vendor(db)
        response = client.put(
            "/v1/vendors/profile/",
            headers=self._get_auth_header(vendor.vendor_id),
            json={
                "location": "123 Main St",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["location"] == "123 Main St"
        assert data["latitude"] == 12.9716
        assert data["longitude"] == 77.5946


class TestStaffManagementAPI:
    """Test staff management endpoints."""

    def _create_vendor_with_owner(self, db: Session) -> Vendor:
        """Helper to create vendor and return it."""
        user = User(phone="+919999999802", role=UserRole.VENDOR, is_active=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Staff Test Shop",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)
        return vendor

    def _get_owner_header(self, vendor_id: int) -> dict:
        token = create_access_token(vendor_id, "vendor_owner")
        return {"Authorization": f"Bearer {token}"}

    def test_add_staff_success(self, client: TestClient, db: Session):
        """Test adding staff member."""
        vendor = self._create_vendor_with_owner(db)
        response = client.post(
            "/v1/vendors/profile/staff",
            headers=self._get_owner_header(vendor.vendor_id),
            json={
                "name": "New Staff Member",
                "role": "staff",
                "phone": "+919888888888",
                "password": "staffpass123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Staff Member"
        assert data["role"] == "staff"
        assert "permissions" in data

    def test_add_staff_invalid_role(self, client: TestClient, db: Session):
        """Test adding staff with invalid role fails."""
        vendor = self._create_vendor_with_owner(db)
        response = client.post(
            "/v1/vendors/profile/staff",
            headers=self._get_owner_header(vendor.vendor_id),
            json={
                "name": "Bad Staff",
                "role": "invalid_role",
                "phone": "+919888888888",
            },
        )
        assert response.status_code == 400

    def test_list_staff_success(self, client: TestClient, db: Session):
        """Test listing staff members."""
        vendor = self._create_vendor_with_owner(db)

        # Add staff
        client.post(
            "/v1/vendors/profile/staff",
            headers=self._get_owner_header(vendor.vendor_id),
            json={"name": "Staff 1", "role": "staff", "phone": "+919888888881"},
        )
        client.post(
            "/v1/vendors/profile/staff",
            headers=self._get_owner_header(vendor.vendor_id),
            json={"name": "Staff 2", "role": "manager", "phone": "+919888888882"},
        )

        response = client.get(
            "/v1/vendors/profile/staff",
            headers=self._get_owner_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["staff"]) == 2

    def test_update_staff_success(self, client: TestClient, db: Session):
        """Test updating staff member."""
        vendor = self._create_vendor_with_owner(db)

        # Add staff
        add_resp = client.post(
            "/v1/vendors/profile/staff",
            headers=self._get_owner_header(vendor.vendor_id),
            json={"name": "Original Name", "role": "staff", "phone": "+919888888883"},
        )
        staff_id = add_resp.json()["id"]

        # Update staff
        response = client.put(
            f"/v1/vendors/profile/staff/{staff_id}",
            headers=self._get_owner_header(vendor.vendor_id),
            json={"name": "Updated Name", "role": "manager"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        assert response.json()["role"] == "manager"

    def test_delete_staff_success(self, client: TestClient, db: Session):
        """Test deleting staff member."""
        vendor = self._create_vendor_with_owner(db)

        # Add staff
        add_resp = client.post(
            "/v1/vendors/profile/staff",
            headers=self._get_owner_header(vendor.vendor_id),
            json={"name": "To Delete", "role": "staff", "phone": "+919888888884"},
        )
        staff_id = add_resp.json()["id"]

        # Delete staff
        response = client.delete(
            f"/v1/vendors/profile/staff/{staff_id}",
            headers=self._get_owner_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        assert "removed" in response.json()["message"]

        # Verify deleted
        list_resp = client.get(
            "/v1/vendors/profile/staff",
            headers=self._get_owner_header(vendor.vendor_id),
        )
        assert list_resp.json()["total"] == 0

    def test_staff_cannot_manage_staff(self, client: TestClient, db: Session):
        """Test staff cannot add other staff."""
        vendor = self._create_vendor_with_owner(db)

        # Create staff user
        from app.modules.vendors.model import VendorStaff
        staff = VendorStaff(
            vendor_id=vendor.vendor_id,
            name="Staff User",
            role="staff",
            phone="+919888888885",
            password_hash=VendorStaff.hash_password("pass"),
            is_active=True,
        )
        db.add(staff)
        db.commit()
        db.refresh(staff)

        staff_token = create_access_token(vendor.vendor_id, "vendor_staff", staff.id)
        response = client.post(
            "/v1/vendors/profile/staff",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={"name": "New Staff", "role": "staff", "phone": "+919888888886"},
        )
        assert response.status_code == 403

    def test_get_permissions(self, client: TestClient, db: Session):
        """Test getting available permissions."""
        vendor = self._create_vendor_with_owner(db)
        response = client.get(
            "/v1/vendors/profile/permissions",
            headers=self._get_owner_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "groups" in data
        assert "owner_permissions" in data
        assert "staff_defaults" in data
        assert "manager_defaults" in data
        assert len(data["owner_permissions"]) == 22  # Total permissions


class TestVendorProfileModel:
    """Test VendorProfile and VendorStaffPermission models."""

    def test_create_vendor_profile(self, db: Session):
        """Test creating vendor profile."""
        user = User(phone="+919999999803", role=UserRole.VENDOR, is_active=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Profile Model Test",
            category="stationery",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        profile = VendorProfile(
            vendor_id=vendor.vendor_id,
            business_name="Profile Model Test",
            category="stationery",
            description="Test description",
            phone="+919999999999",
            email="test@example.com",
            location="Test Location",
            latitude=12.9716,
            longitude=77.5946,
            business_hours={"monday": {"open": "09:00", "close": "18:00"}},
            pickup_instructions="Pick up from counter",
            holidays=[{"date": "2024-12-25", "reason": "Christmas"}],
            is_open=True,
            max_pickup_distance_km=5.0,
            prep_time_minutes=15,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

        assert profile.id is not None
        assert profile.business_name == "Profile Model Test"
        assert profile.business_hours["monday"]["open"] == "09:00"

    def test_create_staff_permission(self, db: Session):
        """Test creating staff permission."""
        user = User(phone="+919999999804", role=UserRole.VENDOR, is_active=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Permission Test",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        staff = VendorStaff(
            vendor_id=vendor.vendor_id,
            name="Test Staff",
            role="staff",
            phone="+919888888887",
            password_hash=VendorStaff.hash_password("pass"),
            is_active=True,
        )
        db.add(staff)
        db.commit()
        db.refresh(staff)

        permission = VendorStaffPermission(
            staff_id=staff.id,
            permission="orders.view",
            is_granted=True,
        )
        db.add(permission)
        db.commit()
        db.refresh(permission)

        assert permission.id is not None
        assert permission.permission == "orders.view"
        assert permission.is_granted is True
