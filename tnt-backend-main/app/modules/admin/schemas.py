"""Pydantic schemas for admin module (pydantic v2)."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class AdminUserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: Optional[str] = None
    full_name: Optional[str] = None
    phone: str = ""
    role: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None


class AdminUserDetailResponse(AdminUserSummary):
    preferences: Optional[Dict[str, Any]] = None
    order_count: Optional[int] = None
    last_active_at: Optional[datetime] = None


class AdminUserListResponse(BaseModel):
    users: List[AdminUserSummary] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    role_summary: Dict[str, int] = {}


class AdminUserStatusUpdate(BaseModel):
    is_active: bool = True


class AdminUserRoleUpdate(BaseModel):
    role: str


# ── Vendor management ──────────────────────────────────────────────────────

VENDOR_TYPES = {"food", "stationery", "mixed"}


class VendorOperatingHours(BaseModel):
    """Per-day open/close windows, e.g. {"open": "09:00", "close": "21:00"}."""
    open: Optional[str] = None
    close: Optional[str] = None
    closed: bool = False


class VendorSlotDefaults(BaseModel):
    slot_duration_minutes: Optional[int] = None
    default_capacity: Optional[int] = None
    opening_time: Optional[str] = None  # HH:MM
    closing_time: Optional[str] = None  # HH:MM


class AdminVendorCreate(BaseModel):
    phone: str
    name: str
    vendor_type: str = "food"          # food | stationery | mixed
    is_approved: bool = True
    stall: Optional[str] = None
    location: Optional[str] = None
    business_name: Optional[str] = None
    description: Optional[str] = None
    email: Optional[str] = None
    operating_hours: Optional[Dict[str, Any]] = None   # {"monday": {...}, ...}
    slot_defaults: Optional[Dict[str, Any]] = None


class AdminVendorUpdate(BaseModel):
    name: Optional[str] = None
    vendor_type: Optional[str] = None
    is_approved: Optional[bool] = None
    is_active: Optional[bool] = None
    stall: Optional[str] = None
    location: Optional[str] = None
    business_name: Optional[str] = None
    description: Optional[str] = None
    email: Optional[str] = None
    operating_hours: Optional[Dict[str, Any]] = None
    slot_defaults: Optional[Dict[str, Any]] = None