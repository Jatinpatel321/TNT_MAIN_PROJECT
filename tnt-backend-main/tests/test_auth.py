"""Tests for Vendor Authentication API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStatus
from app.core.security import create_access_token


class TestVendorAuthAPI:
    """Test vendor authentication endpoints."""

    def test_register_vendor_success(self, client: TestClient, db: Session):
        """Test successful vendor registration."""
        # Create user first
        user = User(phone="+919999999901", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()
        db.refresh(user)

        response = client.post(
            "/v1/vendors/auth/register",
            json={
                "vendor_name": "Test Restaurant",
                "category": "food",
                "owner_phone": user.phone,
                "password": "securepass123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["vendor_name"] == "Test Restaurant"
        assert data["category"] == "food"
        assert "vendor_id" in data

    def test_register_vendor_duplicate_owner(self, client: TestClient, db: Session):
        """Test duplicate vendor registration fails."""
        user = User(phone="+919999999902", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()

        # First registration
        client.post(
            "/v1/vendors/auth/register",
            json={
                "vendor_name": "First Shop",
                "category": "food",
                "owner_phone": user.phone,
                "password": "pass123",
            },
        )

        # Second registration with same owner
        response = client.post(
            "/v1/vendors/auth/register",
            json={
                "vendor_name": "Second Shop",
                "category": "stationery",
                "owner_phone": user.phone,
                "password": "pass123",
            },
        )
        assert response.status_code == 409

    def test_register_vendor_user_not_found(self, client: TestClient):
        """Test registration with non-existent user fails."""
        response = client.post(
            "/v1/vendors/auth/register",
            json={
                "vendor_name": "Ghost Shop",
                "category": "food",
                "owner_phone": "+919999999999",
                "password": "pass123",
            },
        )
        assert response.status_code == 400

    def test_login_vendor_owner_success(self, client: TestClient, db: Session):
        """Test successful vendor owner login."""
        user = User(phone="+919999999903", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Login Test Cafe",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("testpass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()

        response = client.post(
            "/v1/vendors/auth/login",
            json={"vendor_id": vendor.vendor_id, "password": "testpass"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "vendor" in data
        assert data["vendor"]["vendor_name"] == "Login Test Cafe"

    def test_login_vendor_wrong_password(self, client: TestClient, db: Session):
        """Test login with wrong password fails."""
        user = User(phone="+919999999904", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Wrong Pass Shop",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("correctpass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()

        response = client.post(
            "/v1/vendors/auth/login",
            json={"vendor_id": vendor.vendor_id, "password": "wrongpass"},
        )
        assert response.status_code == 401

    def test_login_vendor_suspended(self, client: TestClient, db: Session):
        """Test suspended vendor cannot login."""
        user = User(phone="+919999999905", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Suspended Shop",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.SUSPENDED,
        )
        db.add(vendor)
        db.commit()

        response = client.post(
            "/v1/vendors/auth/login",
            json={"vendor_id": vendor.vendor_id, "password": "pass"},
        )
        assert response.status_code == 403

    def test_login_staff_success(self, client: TestClient, db: Session):
        """Test successful staff login."""
        user = User(phone="+919999999906", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Staff Test Shop",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("ownerpass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        from app.modules.vendors.model import VendorStaff
        staff = VendorStaff(
            vendor_id=vendor.vendor_id,
            name="Test Staff",
            role="staff",
            phone="+919888888888",
            password_hash=VendorStaff.hash_password("staffpass"),
            is_active=True,
        )
        db.add(staff)
        db.commit()

        response = client.post(
            "/v1/vendors/auth/login",
            json={"phone": staff.phone, "password": "staffpass"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "vendor" in data

    def test_login_staff_inactive(self, client: TestClient, db: Session):
        """Test inactive staff cannot login."""
        user = User(phone="+919999999907", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Inactive Staff Shop",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        from app.modules.vendors.model import VendorStaff
        staff = VendorStaff(
            vendor_id=vendor.vendor_id,
            name="Inactive Staff",
            role="staff",
            phone="+919888888887",
            password_hash=VendorStaff.hash_password("pass"),
            is_active=False,
        )
        db.add(staff)
        db.commit()

        response = client.post(
            "/v1/vendors/auth/login",
            json={"phone": staff.phone, "password": "pass"},
        )
        assert response.status_code == 403

    def test_refresh_token_success(self, client: TestClient, db: Session):
        """Test successful token refresh."""
        user = User(phone="+919999999908", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Refresh Test",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()

        # Login to get tokens
        login_resp = client.post(
            "/v1/vendors/auth/login",
            json={"vendor_id": vendor.vendor_id, "password": "pass"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        # Refresh
        response = client.post(
            "/v1/vendors/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()

    def test_refresh_token_invalid(self, client: TestClient):
        """Test invalid refresh token fails."""
        response = client.post(
            "/v1/vendors/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert response.status_code == 401

    def test_get_current_vendor_success(self, client: TestClient, db: Session):
        """Test getting current vendor info."""
        user = User(phone="+919999999909", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Current Vendor",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()

        token = create_access_token(vendor.vendor_id, "vendor_owner")
        response = client.get(
            "/v1/vendors/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["vendor_name"] == "Current Vendor"

    def test_get_current_vendor_unauthorized(self, client: TestClient):
        """Test getting current vendor without token fails."""
        response = client.get("/v1/vendors/auth/me")
        assert response.status_code == 401

    def test_login_nonexistent_vendor(self, client: TestClient):
        """Test login with non-existent vendor fails."""
        response = client.post(
            "/v1/vendors/auth/login",
            json={"vendor_id": 99999, "password": "pass"},
        )
        assert response.status_code == 401