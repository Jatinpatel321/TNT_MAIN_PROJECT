"""Vendor auth schemas — login, token refresh, profile management."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Auth ─────────────────────────────────────────────────────────────────────


class VendorLoginRequest(BaseModel):
    """Login with vendor_id + password for vendor-owner flow."""

    vendor_id: int = Field(..., description="Vendor ID")
    password: str = Field(..., min_length=4, description="Password")
    staff_phone: Optional[str] = Field(
        None, description="Staff phone — use for staff login instead of vendor_id"
    )


class VendorLoginResponse(BaseModel):
    """Successful login response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    vendor: "VendorProfileResponse"


class VendorTokenRefreshRequest(BaseModel):
    refresh_token: str


class VendorTokenRefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── Vendor Profile ───────────────────────────────────────────────────────────


class VendorProfileResponse(BaseModel):
    vendor_id: int
    vendor_name: str
    category: Optional[str] = None
    owner_id: int
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class VendorProfileUpdate(BaseModel):
    vendor_name: Optional[str] = Field(None, min_length=1, max_length=150)
    category: Optional[str] = None


# ── Vendor Staff ─────────────────────────────────────────────────────────────


class VendorStaffCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="staff", pattern="^(manager|staff)$")
    phone: str = Field(..., min_length=10)
    password: str = Field(..., min_length=4)
    permissions: Optional[dict] = None


class VendorStaffResponse(BaseModel):
    id: int
    vendor_id: int
    name: str
    role: str
    phone: str
    permissions: Optional[dict] = None
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class VendorStaffUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = Field(None, pattern="^(manager|staff)$")
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    permissions: Optional[dict] = None
