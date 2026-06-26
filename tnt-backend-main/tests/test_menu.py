"""Tests for Menu API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStatus
from app.modules.menu.model import MenuItem
from app.core.security import create_access_token


class TestMenuAPI:
    """Test menu management endpoints."""

    def _create_vendor(self, db: Session) -> Vendor:
        """Helper to create a test vendor."""
        user = User(phone="+919999999701", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Menu Test Shop",
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

    def test_create_menu_item(self, client: TestClient, db: Session):
        """Test creating menu item."""
        vendor = self._create_vendor(db)
        response = client.post(
            "/v1/menu",
            headers=self._get_auth_header(vendor.vendor_id),
            json={
                "name": "Test Item",
                "description": "Delicious test item",
                "price": 150,
                "category": "main",
                "preparation_time": 15,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Item"
        assert data["price"] == 150
        assert data["is_available"] is True

    def test_get_menu_items(self, client: TestClient, db: Session):
        """Test getting menu items."""
        vendor = self._create_vendor(db)

        # Create items
        for i in range(3):
            item = MenuItem(
                vendor_id=vendor.vendor_id,
                name=f"Item {i}",
                description=f"Description {i}",
                price=100 + i * 50,
                category="main",
                is_available=True,
                preparation_time=10,
            )
            db.add(item)
        db.commit()

        response = client.get(
            "/v1/menu",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_update_menu_item(self, client: TestClient, db: Session):
        """Test updating menu item."""
        vendor = self._create_vendor(db)

        item = MenuItem(
            vendor_id=vendor.vendor_id,
            name="Original Item",
            description="Original desc",
            price=100,
            category="starter",
            is_available=True,
            preparation_time=10,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        response = client.put(
            f"/v1/menu/{item.id}",
            headers=self._get_auth_header(vendor.vendor_id),
            json={
                "name": "Updated Item",
                "price": 200,
                "category": "main",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Item"
        assert data["price"] == 200
        assert data["category"] == "main"

    def test_delete_menu_item(self, client: TestClient, db: Session):
        """Test deleting menu item."""
        vendor = self._create_vendor(db)

        item = MenuItem(
            vendor_id=vendor.vendor_id,
            name="To Delete",
            description="Will be deleted",
            price=100,
            category="main",
            is_available=True,
            preparation_time=10,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        response = client.delete(
            f"/v1/menu/{item.id}",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200

        # Verify deleted
        get_resp = client.get(
            f"/v1/menu/{item.id}",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert get_resp.status_code == 404

    def test_toggle_availability(self, client: TestClient, db: Session):
        """Test toggling menu item availability."""
        vendor = self._create_vendor(db)

        item = MenuItem(
            vendor_id=vendor.vendor_id,
            name="Toggle Test",
            description="Test",
            price=100,
            category="main",
            is_available=True,
            preparation_time=10,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        # Toggle to unavailable
        response = client.patch(
            f"/v1/menu/{item.id}/availability",
            headers=self._get_auth_header(vendor.vendor_id),
            json={"is_available": False},
        )
        assert response.status_code == 200
        assert response.json()["is_available"] is False

        # Toggle back to available
        response = client.patch(
            f"/v1/menu/{item.id}/availability",
            headers=self._get_auth_header(vendor.vendor_id),
            json={"is_available": True},
        )
        assert response.status_code == 200
        assert response.json()["is_available"] is True

    def test_unauthorized_access(self, client: TestClient):
        """Test unauthorized access to menu endpoints."""
        response = client.get("/v1/menu")
        assert response.status_code == 401

        response = client.post("/v1/menu", json={"name": "Test"})
        assert response.status_code == 401

    def test_staff_can_view_menu(self, client: TestClient, db: Session):
        """Test staff can view menu."""
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

        # Create menu item
        item = MenuItem(
            vendor_id=vendor.vendor_id,
            name="Staff View Test",
            description="Test",
            price=100,
            category="main",
            is_available=True,
            preparation_time=10,
        )
        db.add(item)
        db.commit()

        # Staff token
        staff_token = create_access_token(vendor.vendor_id, "vendor_staff", staff.id)
        response = client.get(
            "/v1/menu",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert response.status_code == 200

    def test_menu_item_validation(self, client: TestClient, db: Session):
        """Test menu item validation."""
        vendor = self._create_vendor(db)

        # Missing required fields
        response = client.post(
            "/v1/menu",
            headers=self._get_auth_header(vendor.vendor_id),
            json={"name": "Test"},  # Missing price, category
        )
        assert response.status_code == 422

        # Invalid price (negative)
        response = client.post(
            "/v1/menu",
            headers=self._get_auth_header(vendor.vendor_id),
            json={
                "name": "Test",
                "price": -100,
                "category": "main",
            },
        )
        assert response.status_code == 422


class TestMenuItemModel:
    """Test MenuItem model."""

    def test_create_menu_item(self, db: Session):
        """Test creating menu item model."""
        from app.modules.users.model import User, UserRole
        from app.modules.vendors.model import Vendor, VendorStatus

        user = User(phone="+919999999702", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Model Test",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        item = MenuItem(
            vendor_id=vendor.vendor_id,
            name="Test Item",
            description="Test description",
            price=150,
            category="main",
            is_available=True,
            preparation_time=15,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        assert item.id is not None
        assert item.vendor_id == vendor.vendor_id
        assert item.price == 150
        assert item.is_available is True

    def test_menu_item_categories(self, db: Session):
        """Test menu item categories."""
        from app.modules.users.model import User, UserRole
        from app.modules.vendors.model import Vendor, VendorStatus

        user = User(phone="+919999999703", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Category Test",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        categories = ["main", "starter", "dessert", "beverage"]
        for cat in categories:
            item = MenuItem(
                vendor_id=vendor.vendor_id,
                name=f"{cat} item",
                description=f"A {cat} item",
                price=100,
                category=cat,
                is_available=True,
                preparation_time=10,
            )
            db.add(item)
        db.commit()

        items = db.query(MenuItem).filter(MenuItem.vendor_id == vendor.vendor_id).all()
        assert len(items) == 4
        assert set(item.category for item in items) == set(categories)