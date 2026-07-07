"""Vendor Notification Router — device registration and vendor-specific push endpoints.

This router provides:
1. Device token registration for vendor push notifications (FCM).
2. Sending targeted push notifications to vendors.
3. Slot-full capacity alerts.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.users.model import User

logger = logging.getLogger("tnt.vendors.notifications")

router = APIRouter(prefix="/vendors/notifications", tags=["Vendor Notifications"])


def _get_vendor_user(db: Session, user: dict) -> User:
    """Resolve the authenticated user dict → ORM User; raises 404 if missing."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.post("/register-device", summary="Register FCM device token for vendor push")
def register_device(
    device_token: str,
    platform: str = "android",
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Register a device token for push notifications to this vendor.

    This is called by the vendor frontend after obtaining an FCM token.
    The token is stored on the User record and used by ``send_push()``
    when the backend needs to deliver a push notification to this vendor.

    Args:
        device_token: The FCM registration token from the device.
        platform: 'android', 'ios', or 'web'.

    Returns:
        Confirmation message.
    """
    db_user = _get_vendor_user(db, user)

    # Update the user's device token
    db_user.device_token = device_token
    db_user.push_enabled = True
    db.flush()

    logger.info(
        "vendor_device_registered user_id=%s platform=%s token_prefix=%s",
        db_user.id,
        platform,
        device_token[:10] if device_token else "none",
    )

    return {"message": "Device registered successfully", "device_token_prefix": device_token[:10]}


@router.delete("/unregister-device", summary="Unregister device token")
def unregister_device(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Remove the device token for push notifications."""
    db_user = _get_vendor_user(db, user)
    db_user.device_token = None
    db_user.push_enabled = False
    db.flush()

    logger.info("vendor_device_unregistered user_id=%s", db_user.id)

    return {"message": "Device unregistered successfully"}
