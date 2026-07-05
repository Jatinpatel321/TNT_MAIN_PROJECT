"""Tests for Notifications API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStatus
from app.modules.notifications.model import Notification, NotificationType
from app.modules.vendors.auth_service import _create_access_token as create_access_token


class TestNotificationsAPI:
    """Test notification endpoints."""

    def _create_vendor(self, db: Session) -> Vendor:
        """Helper to create a test vendor."""
        user = User(phone="+919999999401", role=UserRole.VENDOR, is_active=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Notif Test Shop",
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

    def test_get_notifications(self, client: TestClient, db: Session):
        """Test getting notifications."""
        vendor = self._create_vendor(db)

        # Create notifications
        for i in range(3):
            notif = Notification(
                user_id=vendor.owner_id,
                title=f"Test Notification {i}",
                message=f"Message {i}",
                notification_type=NotificationType.ORDER_PLACED,
                is_read=False,
            )
            db.add(notif)
        db.commit()

        response = client.get(
            "/v1/notifications",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3

    def test_mark_notification_read(self, client: TestClient, db: Session):
        """Test marking notification as read."""
        vendor = self._create_vendor(db)

        notif = Notification(
            user_id=vendor.owner_id,
            title="Test",
            message="Test message",
            notification_type=NotificationType.ORDER_PLACED,
            is_read=False,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)

        response = client.patch(
            f"/v1/notifications/{notif.id}/read",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        assert response.json()["is_read"] is True

    def test_delete_notification(self, client: TestClient, db: Session):
        """Test deleting notification."""
        vendor = self._create_vendor(db)

        notif = Notification(
            user_id=vendor.owner_id,
            title="To Delete",
            message="Will be deleted",
            notification_type=NotificationType.SYSTEM,
            is_read=False,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)

        response = client.delete(
            f"/v1/notifications/{notif.id}",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200

    def test_unauthorized_access(self, client: TestClient):
        """Test unauthorized access."""
        response = client.get("/v1/notifications")
        assert response.status_code == 401

    def test_notification_types(self, client: TestClient, db: Session):
        """Test different notification types."""
        vendor = self._create_vendor(db)

        types = [
            NotificationType.ORDER_PLACED,
            NotificationType.PROMO,
            NotificationType.SYSTEM,
            NotificationType.ALERT,
        ]
        for notif_type in types:
            notif = Notification(
                user_id=vendor.owner_id,
                title=f"{notif_type.value} notification",
                message=f"Test {notif_type.value}",
                notification_type=notif_type,
                is_read=False,
            )
            db.add(notif)
        db.commit()

        response = client.get(
            "/v1/notifications",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 4
        types_found = {n["notification_type"] for n in data["items"]}
        assert types_found == {t.value for t in types}

    def test_vendor_notify_endpoints(self, client: TestClient, db: Session):
        """Test notify_delay, notify_ready, and notify_custom endpoints."""
        from app.modules.orders.model import Order, OrderStatus
        
        vendor = self._create_vendor(db)
        
        # Create student user
        student = User(phone="+918888888888", role=UserRole.STUDENT, is_active=True)
        db.add(student)
        db.commit()
        db.refresh(student)

        # Create slot
        from app.modules.slots.model import Slot, SlotStatus
        from datetime import datetime, timedelta
        slot = Slot(
            vendor_id=vendor.owner_id,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            max_orders=10,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)

        # Create order owned by student, fulfilled by vendor
        # Note: vendor.owner_id is the vendor's user_id in the db
        order = Order(
            vendor_id=vendor.owner_id,
            user_id=student.id,
            slot_id=slot.id,
            total_amount=500.0,
            status=OrderStatus.PLACED,
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        auth_headers = self._get_auth_header(vendor.vendor_id)

        # 1. Test notify-delay
        delay_payload = {
            "order_id": order.id,
            "delay_minutes": 15,
            "reason": "Kitchen backlog",
        }
        res_delay = client.post(
            "/v1/notifications/vendor/notify-delay",
            json=delay_payload,
            headers=auth_headers,
        )
        assert res_delay.status_code == 200
        assert res_delay.json()["order_id"] == order.id

        # 2. Test notify-ready
        ready_payload = {
            "order_id": order.id,
        }
        res_ready = client.post(
            "/v1/notifications/vendor/notify-ready",
            json=ready_payload,
            headers=auth_headers,
        )
        assert res_ready.status_code == 200
        assert res_ready.json()["order_id"] == order.id

        # 3. Test notify-custom
        custom_payload = {
            "order_id": order.id,
            "message": "Custom test note",
        }
        res_custom = client.post(
            "/v1/notifications/vendor/notify-custom",
            json=custom_payload,
            headers=auth_headers,
        )
        assert res_custom.status_code == 200
        assert res_custom.json()["order_id"] == order.id


class TestNotificationModel:
    """Test Notification model."""

    def test_create_notification(self, db: Session):
        """Test creating notification."""
        from app.modules.users.model import User, UserRole
        from app.modules.vendors.model import Vendor, VendorStatus

        user = User(phone="+919999999402", role=UserRole.VENDOR, is_active=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Notif Model Test",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        notif = Notification(
            user_id=vendor.owner_id,
            title="Test Notification",
            message="Test message",
            notification_type=NotificationType.ORDER_PLACED,
            is_read=False,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)

        assert notif.id is not None
        assert notif.user_id == vendor.owner_id
        assert notif.is_read is False

