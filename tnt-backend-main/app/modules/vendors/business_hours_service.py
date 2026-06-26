"""Business Hours Enforcement Service.

Enables server-side validation of vendor business hours and holiday settings
at order placement time. Reads from VendorProfile.business_hours JSON column.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.time_utils import ist_now
from app.modules.vendors.model import Vendor
from app.modules.vendors.profile_models import VendorProfile

WEEKDAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def get_vendor_business_hours(vendor_id: int, db: Session) -> dict[str, Any]:
    """Return the business hours configuration for a vendor.

    Args:
        vendor_id: The users.id of the vendor (User.id with role=VENDOR).
        db: Database session.

    Returns:
        Dict with business_hours, holidays, is_open, and whether currently open.
    """
    # Map from users.id to Vendor model
    vendor = db.query(Vendor).filter(Vendor.owner_id == vendor_id).first()
    if not vendor:
        return {
            "business_hours": {},
            "holidays": [],
            "is_open": True,
            "currently_open": True,
            "message": "No vendor profile found - defaulting to open",
        }

    profile = db.query(VendorProfile).filter(VendorProfile.vendor_id == vendor.vendor_id).first()
    if not profile:
        return {
            "business_hours": {},
            "holidays": [],
            "is_open": True,
            "currently_open": True,
            "message": "No vendor profile found - defaulting to open",
        }

    business_hours = profile.business_hours or {}
    holidays = profile.holidays or []
    is_open_flag = profile.is_open if profile.is_open is not None else True

    currently_open, message = check_business_hours(vendor_id, db)

    return {
        "business_hours": business_hours,
        "holidays": holidays,
        "is_open": is_open_flag,
        "currently_open": currently_open,
        "message": message,
        "profile_id": profile.id,
    }


def update_vendor_business_hours(
    vendor_id: int,
    business_hours: dict | None = None,
    holidays: list | None = None,
    is_open: bool | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    """Update business hours configuration for a vendor.

    Args:
        vendor_id: The users.id of the vendor.
        business_hours: JSON dict with day schedules.
        holidays: List of holiday date entries.
        is_open: Master open/closed toggle.
        db: Database session.

    Returns:
        Updated business hours config.
    """
    vendor = db.query(Vendor).filter(Vendor.owner_id == vendor_id).first()
    if not vendor:
        raise ValueError("Vendor not found")

    profile = db.query(VendorProfile).filter(VendorProfile.vendor_id == vendor.vendor_id).first()
    if not profile:
        raise ValueError("Vendor profile not found")

    if business_hours is not None:
        profile.business_hours = business_hours
    if holidays is not None:
        profile.holidays = holidays
    if is_open is not None:
        profile.is_open = is_open

    db.commit()
    db.refresh(profile)

    return get_vendor_business_hours(vendor_id, db)


def check_business_hours(vendor_id: int, db: Session) -> tuple[bool, str]:
    """Check if the vendor is currently open for business.

    Checks three conditions:
      1. Master is_open toggle on VendorProfile
      2. Whether today is a configured holiday
      3. Whether current IST time falls within today's business hours

    Args:
        vendor_id: The users.id of the vendor.
        db: Database session.

    Returns:
        Tuple of (is_open: bool, reason: str).
    """
    vendor = db.query(Vendor).filter(Vendor.owner_id == vendor_id).first()
    if not vendor:
        return True, "No vendor profile configured - defaulting to open"

    profile = db.query(VendorProfile).filter(VendorProfile.vendor_id == vendor.vendor_id).first()
    if not profile:
        return True, "No vendor profile configured - defaulting to open"

    # 1. Master toggle
    if hasattr(profile, 'is_open') and profile.is_open is False:
        return False, "Vendor is currently closed"

    # 2. Holiday check
    now = ist_now()
    holidays = profile.holidays or []
    today_str = now.date().isoformat()
    for holiday in holidays:
        if isinstance(holiday, dict):
            if holiday.get("date") == today_str:
                reason = holiday.get("reason", "Holiday")
                return False, f"Vendor is closed today: {reason}"
        elif isinstance(holiday, str) and holiday == today_str:
            return False, "Vendor is closed today (holiday)"

    # 3. Business hours check
    business_hours = profile.business_hours or {}
    if not business_hours:
        return True, "No business hours configured - defaulting to open"

    today_name = WEEKDAY_NAMES[now.weekday()]

    current_minutes = now.hour * 60 + now.minute

    def parse_window(day_key: str) -> tuple[int, int, str, str] | None:
        hours = business_hours.get(day_key, {})
        open_time = hours.get("open") if isinstance(hours, dict) else None
        close_time = hours.get("close") if isinstance(hours, dict) else None
        if not open_time or not close_time:
            return None
        try:
            open_hour, open_min = (int(x) for x in open_time.split(":"))
            close_hour, close_min = (int(x) for x in close_time.split(":"))
        except (ValueError, AttributeError):
            return None
        return open_hour * 60 + open_min, close_hour * 60 + close_min, open_time, close_time

    today_window = parse_window(today_name)
    if today_window:
        open_minutes, close_minutes, open_time_str, close_time_str = today_window
        if close_minutes <= open_minutes:
            is_inside_window = current_minutes >= open_minutes or current_minutes < close_minutes
        else:
            is_inside_window = open_minutes <= current_minutes < close_minutes

        if is_inside_window:
            return True, "Vendor is currently open"
        if current_minutes < open_minutes:
            previous_name = WEEKDAY_NAMES[(now.weekday() - 1) % 7]
            previous_window = parse_window(previous_name)
            if previous_window:
                prev_open, prev_close, _prev_open_str, _prev_close_str = previous_window
                if prev_close <= prev_open and current_minutes < prev_close:
                    return True, "Vendor is currently open"
            return False, f"Vendor opens at {open_time_str} today"
        return False, f"Vendor closed at {close_time_str} today"

    previous_name = WEEKDAY_NAMES[(now.weekday() - 1) % 7]
    previous_window = parse_window(previous_name)
    if previous_window:
        prev_open, prev_close, _prev_open_str, prev_close_str = previous_window
        if prev_close <= prev_open and current_minutes < prev_close:
            return True, "Vendor is currently open"
        if not today_window and current_minutes < prev_close:
            return False, f"Vendor closed at {prev_close_str} today"

    if today_name not in business_hours:
        return False, f"Vendor is closed on {today_name.capitalize()}"
    return False, f"Business hours incomplete for {today_name.capitalize()}"