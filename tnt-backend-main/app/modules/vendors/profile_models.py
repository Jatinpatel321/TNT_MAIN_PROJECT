"""Vendor Profile Module - Business info, hours, holidays, cover images, pickup instructions."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Boolean, Text, JSON

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class VendorProfile(Base):
    """Extended vendor profile with business details."""
    __tablename__ = "vendor_profiles"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.vendor_id"), nullable=False, unique=True)

    # Business Info
    business_name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=True)  # food, stationery
    description = Column(Text, nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Branding
    logo_url = Column(String(500), nullable=True)
    cover_image = Column(String(500), nullable=True)

    # Business Hours (JSON: {"monday": {"open": "09:00", "close": "21:00"}, ...})
    business_hours = Column(JSON, default=dict)

    # Pickup Instructions
    pickup_instructions = Column(Text, nullable=True)

    # Holiday Settings (JSON: [{"date": "2024-12-25", "reason": "Christmas"}, ...])
    holidays = Column(JSON, default=list)

    # Settings
    is_open = Column(Boolean, default=True)
    max_pickup_distance_km = Column(Float, nullable=True)
    prep_time_minutes = Column(Integer, default=15)

    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class VendorStaffPermission(Base):
    """Granular permissions for staff members."""
    __tablename__ = "vendor_staff_permissions"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("vendor_staff.id"), nullable=False)
    permission = Column(String(100), nullable=False)  # e.g. "orders.view", "menu.edit", "slots.manage"
    is_granted = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow_naive)