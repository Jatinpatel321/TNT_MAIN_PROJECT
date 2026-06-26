"""Tests for Notifications API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStatus
from app.modules.notifications.model import Notification
from app.core.security import create_access_token


class TestNotificationsAPI:
    """Test notification endpoints."""

    def _create_vendor(self, db: Session) -> Vendor:
        """Helper to create a test vendor."""
        user = User(phone="+919999999401", role=UserRole.VENDOR, is_verified=True)
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
                vendor_id=vendor.vendor_id,
                title=f"Test Notification {i}",
                message=f"Message {i}",
                notification_type="order",
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
        assert len(data) == 3

    def test_mark_notification_read(self, client: TestClient, db: Session):
        """Test marking notification as read."""
        vendor = self._create_vendor(db)

        notif = Notification(
            vendor_id=vendor.vendor_id,
            title="Test",
            message="Test message",
            notification_type="order",
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
            vendor_id=vendor.vendor_id,
            title="To Delete",
            message="Will be deleted",
            notification_type="system",
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

        types = ["order", "promotion", "system", "alert"]
        for notif_type in types:
            notif = Notification(
                vendor_id=vendor.vendor_id,
                title=f"{notif_type} notification",
                message=f"Test {notif_type}",
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
        assert len(data) == 4
        types_found = {n["notification_type"] for n in data}
        assert types_found == set(types)


class TestNotificationModel:
    """Test Notification model."""

    def test_create_notification(self, db: Session):
        """Test creating notification."""
        from app.modules.users.model import User, UserRole
        from app.modules.vendors.model import Vendor, VendorStatus

        user = User(phone="+919999999402", role=UserRole.VENDOR, is_verified=True)
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
            vendor_id=vendor.vendor_id,
            title="Test Notification",
            message="Test message",
            notification_type="order",
            is_read=False,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)

        assert notif.id is not None
        assert notif.vendor_id == vendor.vendor_id
        assert notif.is_read is False