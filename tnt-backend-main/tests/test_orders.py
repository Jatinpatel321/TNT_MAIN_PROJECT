"""Tests for Orders API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStatus
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.menu.model import MenuItem
from app.core.security import create_access_token


class TestOrdersAPI:
    """Test order management endpoints."""

    def _create_vendor_and_user(self, db: Session) -> tuple[Vendor, User]:
        """Helper to create vendor and user."""
        user = User(phone="+919999999601", role=UserRole.STUDENT, is_active=True)
        db.add(user)
        db.commit()

        vendor_user = User(phone="+919999999602", role=UserRole.VENDOR, is_active=True)
        db.add(vendor_user)
        db.commit()

        vendor = Vendor(
            vendor_name="Orders Test Shop",
            category="food",
            owner_id=vendor_user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)
        return vendor, user

    def _get_auth_header(self, vendor_id: int) -> dict:
        """Helper to create auth header."""
        token = create_access_token(vendor_id, "vendor_owner")
        return {"Authorization": f"Bearer {token}"}

    def test_create_order(self, client: TestClient, db: Session):
        """Test creating an order."""
        vendor, user = self._create_vendor_and_user(db)

        # Create menu item
        item = MenuItem(
            vendor_id=vendor.vendor_id,
            name="Test Item",
            description="Test",
            price=100,
            category="main",
            is_available=True,
            preparation_time=10,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        response = client.post(
            "/v1/orders",
            headers=self._get_auth_header(vendor.vendor_id),
            json={
                "user_id": user.id,
                "vendor_id": vendor.vendor_id,
                "items": [{"menu_item_id": item.id, "quantity": 2}],
                "total_amount": 200,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["vendor_id"] == vendor.vendor_id
        assert data["total_amount"] == 200
        assert data["status"] == OrderStatus.PENDING.value

    def test_get_orders(self, client: TestClient, db: Session):
        """Test getting orders."""
        vendor, user = self._create_vendor_and_user(db)

        # Create orders
        for i in range(3):
            order = Order(
                vendor_id=vendor.vendor_id,
                user_id=user.id,
                total_amount=100 + i * 50,
                status=OrderStatus.PENDING,
            )
            db.add(order)
        db.commit()

        response = client.get(
            "/v1/orders",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_order_by_id(self, client: TestClient, db: Session):
        """Test getting specific order."""
        vendor, user = self._create_vendor_and_user(db)

        order = Order(
            vendor_id=vendor.vendor_id,
            user_id=user.id,
            total_amount=200,
            status=OrderStatus.PENDING,
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        response = client.get(
            f"/v1/orders/{order.id}",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        assert response.json()["id"] == order.id

    def test_update_order_status(self, client: TestClient, db: Session):
        """Test updating order status."""
        vendor, user = self._create_vendor_and_user(db)

        order = Order(
            vendor_id=vendor.vendor_id,
            user_id=user.id,
            total_amount=200,
            status=OrderStatus.PENDING,
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        # Accept order
        response = client.put(
            f"/v1/orders/{order.id}/status",
            headers=self._get_auth_header(vendor.vendor_id),
            json={"status": OrderStatus.ACCEPTED.value},
        )
        assert response.status_code == 200
        assert response.json()["status"] == OrderStatus.ACCEPTED.value

        # Update to preparing
        response = client.put(
            f"/v1/orders/{order.id}/status",
            headers=self._get_auth_header(vendor.vendor_id),
            json={"status": OrderStatus.PREPARING.value},
        )
        assert response.status_code == 200
        assert response.json()["status"] == OrderStatus.PREPARING.value

    def test_order_with_items(self, client: TestClient, db: Session):
        """Test order with multiple items."""
        vendor, user = self._create_vendor_and_user(db)

        # Create menu items
        items = []
        for i in range(3):
            item = MenuItem(
                vendor_id=vendor.vendor_id,
                name=f"Item {i}",
                description="Test",
                price=100,
                category="main",
                is_available=True,
                preparation_time=10,
            )
            db.add(item)
            db.commit()
            db.refresh(item)
            items.append(item)

        # Create order with items
        response = client.post(
            "/v1/orders",
            headers=self._get_auth_header(vendor.vendor_id),
            json={
                "user_id": user.id,
                "vendor_id": vendor.vendor_id,
                "items": [
                    {"menu_item_id": items[0].id, "quantity": 2},
                    {"menu_item_id": items[1].id, "quantity": 1},
                ],
                "total_amount": 300,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "order_items" in data
        assert len(data["order_items"]) == 2

    def test_unauthorized_order_access(self, client: TestClient):
        """Test unauthorized access to orders."""
        response = client.get("/v1/orders")
        assert response.status_code == 401

        response = client.post("/v1/orders", json={})
        assert response.status_code == 401

    def test_staff_can_view_orders(self, client: TestClient, db: Session):
        """Test staff can view orders."""
        vendor, user = self._create_vendor_and_user(db)

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

        # Create order
        order = Order(
            vendor_id=vendor.vendor_id,
            user_id=user.id,
            total_amount=200,
            status=OrderStatus.PENDING,
        )
        db.add(order)
        db.commit()

        # Staff token
        staff_token = create_access_token(vendor.vendor_id, "vendor_staff", staff.id)
        response = client.get(
            "/v1/orders",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert response.status_code == 200

    def test_order_status_transitions(self, client: TestClient, db: Session):
        """Test valid order status transitions."""
        vendor, user = self._create_vendor_and_user(db)

        order = Order(
            vendor_id=vendor.vendor_id,
            user_id=user.id,
            total_amount=200,
            status=OrderStatus.PENDING,
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        # Valid transition: PENDING → ACCEPTED
        response = client.put(
            f"/v1/orders/{order.id}/status",
            headers=self._get_auth_header(vendor.vendor_id),
            json={"status": OrderStatus.ACCEPTED.value},
        )
        assert response.status_code == 200

        # Valid transition: ACCEPTED → PREPARING
        response = client.put(
            f"/v1/orders/{order.id}/status",
            headers=self._get_auth_header(vendor.vendor_id),
            json={"status": OrderStatus.PREPARING.value},
        )
        assert response.status_code == 200

        # Valid transition: PREPARING → READY
        response = client.put(
            f"/v1/orders/{order.id}/status",
            headers=self._get_auth_header(vendor.vendor_id),
            json={"status": OrderStatus.READY.value},
        )
        assert response.status_code == 200

        # Valid transition: READY → COMPLETED
        response = client.put(
            f"/v1/orders/{order.id}/status",
            headers=self._get_auth_header(vendor.vendor_id),
            json={"status": OrderStatus.COMPLETED.value},
        )
        assert response.status_code == 200


class TestOrderModel:
    """Test Order and OrderItem models."""

    def test_create_order_with_items(self, db: Session):
        """Test creating order with items."""
        from app.modules.users.model import User, UserRole
        from app.modules.vendors.model import Vendor, VendorStatus

        user = User(phone="+919999999603", role=UserRole.STUDENT, is_active=True)
        db.add(user)
        db.commit()

        vendor_user = User(phone="+919999999604", role=UserRole.VENDOR, is_active=True)
        db.add(vendor_user)
        db.commit()

        vendor = Vendor(
            vendor_name="Model Test",
            category="food",
            owner_id=vendor_user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        order = Order(
            vendor_id=vendor.vendor_id,
            user_id=user.id,
            total_amount=300,
            status=OrderStatus.PENDING,
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        # Add order items
        for i in range(2):
            item = OrderItem(
                order_id=order.id,
                menu_item_id=i + 1,
                quantity=2,
                price=100,
            )
            db.add(item)
        db.commit()

        assert order.id is not None
        assert len(order.order_items) == 2
        assert order.total_amount == 300
