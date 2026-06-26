"""Business Hours Enforcement - API Router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.users.model import User
from app.modules.vendors.business_hours_service import (
    get_vendor_business_hours,
    update_vendor_business_hours,
    check_business_hours,
)

router = APIRouter(prefix="/vendors/business-hours", tags=["Vendor Business Hours"])


@router.get("/", summary="Get business hours configuration")
def api_get_business_hours(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get current business hours, holidays, and open status for the vendor."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    return get_vendor_business_hours(db_user.id, db)


@router.put("/", summary="Update business hours configuration")
def api_update_business_hours(
    data: dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Update business hours, holidays, and/or open/closed toggle.

    Body example:
    {
        "business_hours": {
            "monday": {"open": "09:00", "close": "21:00"},
            "tuesday": {"open": "09:00", "close": "21:00"},
            ...
        },
        "holidays": [{"date": "2024-12-25", "reason": "Christmas"}],
        "is_open": true
    }
    """
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        result = update_vendor_business_hours(
            vendor_id=db_user.id,
            business_hours=data.get("business_hours"),
            holidays=data.get("holidays"),
            is_open=data.get("is_open"),
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status", summary="Check if vendor is currently open")
def api_check_business_hours(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Check if the vendor is currently open based on configured hours and holidays."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    is_open, message = check_business_hours(db_user.id, db)
    return {
        "is_open": is_open,
        "message": message,
    }
