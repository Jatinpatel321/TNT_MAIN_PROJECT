"""Tests for Orders API endpoints."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.core.security import create_access_token as create_user_token
from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStatus
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.menu.model import MenuItem
from app.modules.slots.model import Slot, SlotStatus
from app.modules.vendors.auth_service import _create_access_token as create_vendor_token


class TestOrdersAPI:
    """Test order management endpoints."""

    def _seed(self, db: Session) -> dict:
        """Create student, approved vendor owner, vendor, slot, and menu item."""
        student = User(phone="+919999999601", role=UserRole.STUDENT, is_active=True)
        db.add(student)
        db.commit()

        owner = User(
            phone="+919999999602", role=UserRole.VENDOR, is_active=True, is_approved=True
        )
        db.add(owner)
        db.commit()

        vendor = Vendor(
            vendor_name="Orders Test Shop",
            category="food",
            owner_id=owner.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        start = utcnow_naive() + timedelta(hours=1)
        slot = Slot(
            vendor_id=owner.id,
            start_time=start,
            end_time=start + timedelta(hours=1),
            max_orders=10,
            current_orders=0,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot)

        item = MenuItem(
            vendor_id=owner.id,
            name="Test Item",
            description="Test",
            price=100.00,  # rupees
            category="food",
            is_available=True,
            prep_time_minutes=10,
            available_quantity=100,  # column default is 0 = out of stock
        )
        db.add(item)
        db.commit()
        db.refresh(slot)
        db.refresh(item)

        return {
            "student": student,
            "owner": owner,
            "vendor": vendor,
            "slot": slot,
            "item": item,
        }

    def _student_header(self, student: User) -> dict:
        token = create_user_token(
            {"sub": str(student.id), "phone": student.phone, "role": "student"},
            expires_delta=60,
        )
        return {"Authorization": f"Bearer {token}"}

    def _vendor_header(self, vendor_id: int) -> dict:
        token = create_vendor_token(vendor_id, "vendor_owner")
        return {"Authorization": f"Bearer {token}"}

    def test_create_order(self, client: TestClient, db: Session):
        """Test a student placing an order into a slot."""
        seed = self._seed(db)

        response = client.post(
            f"/v1/orders/{seed['slot'].id}",
            headers=self._student_header(seed["student"]),
            json=[{"menu_item_id": seed["item"].id, "quantity": 2}],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_amount"] == 200.0  # 2 x Rs100
        assert data["status"] == OrderStatus.PLACED.value

        order = db.query(Order).filter(Order.id == data["order_id"]).first()
        assert order is not None
        assert order.vendor_id == seed["owner"].id

    def test_get_orders(self, client: TestClient, db: Session):
        """Test vendor listing incoming orders."""
        seed = self._seed(db)

        for i in range(3):
            order = Order(
                vendor_id=seed["owner"].id,
                user_id=seed["student"].id,
                slot_id=seed["slot"].id,
                total_amount=100 + i * 50,
                status=OrderStatus.PLACED,
            )
            db.add(order)
        db.commit()

        response = client.get(
            "/v1/orders/vendor",
            headers=self._vendor_header(seed["vendor"].vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_order_by_id(self, client: TestClient, db: Session):
        """Test vendor fetching a specific order."""
        seed = self._seed(db)

        order = Order(
            vendor_id=seed["owner"].id,
            user_id=seed["student"].id,
            slot_id=seed["slot"].id,
            total_amount=200,
            status=OrderStatus.PLACED,
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        response = client.get(
            f"/v1/orders/vendor/{order.id}",
            headers=self._vendor_header(seed["vendor"].vendor_id),
        )
        assert response.status_code == 200
        assert response.json()["order_id"] == order.id

    def test_update_order_status(self, client: TestClient, db: Session):
        """Test the vendor action endpoints advancing order status."""
        seed = self._seed(db)

        order = Order(
            vendor_id=seed["owner"].id,
            user_id=seed["student"].id,
            slot_id=seed["slot"].id,
            total_amount=200,
            status=OrderStatus.PLACED,
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        headers = self._vendor_header(seed["vendor"].vendor_id)

        # PLACED -> CONFIRMED
        response = client.post(f"/v1/orders/{order.id}/confirm", headers=headers)
        assert response.status_code == 200
        db.refresh(order)
        assert order.status == OrderStatus.CONFIRMED

        # CONFIRMED -> PREPARING
        response = client.post(f"/v1/orders/{order.id}/preparing", headers=headers)
        assert response.status_code == 200
        db.refresh(order)
        assert order.status == OrderStatus.PREPARING

    def test_order_with_items(self, client: TestClient, db: Session):
        """Test order with multiple items records OrderItem rows."""
        seed = self._seed(db)

        second_item = MenuItem(
            vendor_id=seed["owner"].id,
            name="Second Item",
            description="Test",
            price=50.00,
            category="food",
            is_available=True,
            prep_time_minutes=5,
            available_quantity=100,
        )
        db.add(second_item)
        db.commit()
        db.refresh(second_item)

        response = client.post(
            f"/v1/orders/{seed['slot'].id}",
            headers=self._student_header(seed["student"]),
            json=[
                {"menu_item_id": seed["item"].id, "quantity": 2},
                {"menu_item_id": second_item.id, "quantity": 1},
            ],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_amount"] == 250.0  # 2x100 + 1x50

        order_items = (
            db.query(OrderItem).filter(OrderItem.order_id == data["order_id"]).all()
        )
        assert len(order_items) == 2

    def test_unauthorized_order_access(self, client: TestClient):
        """Test unauthorized access to orders."""
        response = client.get("/v1/orders/vendor")
        assert response.status_code in (401, 403)

        response = client.post("/v1/orders/1", json=[])
        assert response.status_code in (401, 403)

    def test_staff_can_view_orders(self, client: TestClient, db: Session):
        """Test staff can view vendor orders."""
        seed = self._seed(db)

        from app.modules.vendors.model import VendorStaff
        staff = VendorStaff(
            vendor_id=seed["vendor"].vendor_id,
            name="Staff User",
            role="staff",
            phone="+919888888888",
            password_hash=VendorStaff.hash_password("pass"),
            is_active=True,
        )
        db.add(staff)
        db.commit()
        db.refresh(staff)

        order = Order(
            vendor_id=seed["owner"].id,
            user_id=seed["student"].id,
            slot_id=seed["slot"].id,
            total_amount=200,
            status=OrderStatus.PLACED,
        )
        db.add(order)
        db.commit()

        staff_token = create_vendor_token(seed["vendor"].vendor_id, "vendor_staff", staff.id)
        response = client.get(
            "/v1/orders/vendor",
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert response.status_code == 200

    def test_order_status_transitions(self, client: TestClient, db: Session):
        """Test the canonical PLACED -> CONFIRMED -> PREPARING -> READY chain."""
        seed = self._seed(db)

        order = Order(
            vendor_id=seed["owner"].id,
            user_id=seed["student"].id,
            slot_id=seed["slot"].id,
            total_amount=200,
            status=OrderStatus.PLACED,
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        headers = self._vendor_header(seed["vendor"].vendor_id)

        for action, expected in (
            ("confirm", OrderStatus.CONFIRMED),
            ("preparing", OrderStatus.PREPARING),
            ("ready", OrderStatus.READY),
        ):
            response = client.post(f"/v1/orders/{order.id}/{action}", headers=headers)
            assert response.status_code == 200, f"{action} failed: {response.text}"
            db.refresh(order)
            assert order.status == expected


class TestOrderModel:
    """Test Order and OrderItem models."""

    def test_create_order_with_items(self, db: Session):
        """Test creating order with items."""
        user = User(phone="+919999999603", role=UserRole.STUDENT, is_active=True)
        db.add(user)
        db.commit()

        vendor_user = User(
            phone="+919999999604", role=UserRole.VENDOR, is_active=True, is_approved=True
        )
        db.add(vendor_user)
        db.commit()

        start = utcnow_naive() + timedelta(hours=1)
        slot = Slot(
            vendor_id=vendor_user.id,
            start_time=start,
            end_time=start + timedelta(hours=1),
            max_orders=10,
            current_orders=0,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)

        order = Order(
            vendor_id=vendor_user.id,
            user_id=user.id,
            slot_id=slot.id,
            total_amount=300,
            status=OrderStatus.PLACED,
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
                price_at_time=100,
            )
            db.add(item)
        db.commit()

        assert order.id is not None
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        assert len(order_items) == 2
        assert float(order.total_amount) == 300.0
