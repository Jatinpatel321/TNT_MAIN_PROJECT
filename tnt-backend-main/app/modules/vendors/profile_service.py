"""Vendor Profile Module - Business logic for profile, staff, and permissions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.vendors.model import Vendor, VendorStaff
from app.modules.vendors.profile_models import VendorProfile, VendorStaffPermission


# ── Permission Constants ──────────────────────────────────────────────────

PERMISSIONS = {
    "orders": ["orders.view", "orders.accept", "orders.prepare", "orders.ready", "orders.complete"],
    "menu": ["menu.view", "menu.edit", "menu.toggle_availability"],
    "slots": ["slots.view", "slots.manage"],
    "analytics": ["analytics.view"],
    "profile": ["profile.view", "profile.edit"],
    "staff": ["staff.view", "staff.manage"],
    "promotions": ["promotions.view", "promotions.manage"],
    "settlements": ["settlements.view"],
}

OWNER_PERMISSIONS = [p for group in PERMISSIONS.values() for p in group]

STAFF_DEFAULT_PERMISSIONS = [
    "orders.view", "orders.accept", "orders.prepare", "orders.ready", "orders.complete",
    "menu.view",
    "slots.view",
    "profile.view",
]

MANAGER_PERMISSIONS = [
    "orders.view", "orders.accept", "orders.prepare", "orders.ready", "orders.complete",
    "menu.view", "menu.edit", "menu.toggle_availability",
    "slots.view", "slots.manage",
    "analytics.view",
    "profile.view", "profile.edit",
    "staff.view",
    "promotions.view",
]


class VendorProfileService:
    """Service for vendor profile, staff management, and permissions."""

    def __init__(self, db: Session):
        self.db = db

    def _get_vendor(self, vendor_id: int) -> Vendor:
        vendor = self.db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
        if not vendor:
            raise ValueError("Vendor not found")
        return vendor

    def _get_or_create_profile(self, vendor_id: int) -> VendorProfile:
        profile = self.db.query(VendorProfile).filter(
            VendorProfile.vendor_id == vendor_id
        ).first()
        if not profile:
            vendor = self._get_vendor(vendor_id)
            profile = VendorProfile(
                vendor_id=vendor_id,
                business_name=vendor.vendor_name,
                category=vendor.category,
            )
            self.db.add(profile)
            self.db.flush()
        return profile

    # ── Profile ────────────────────────────────────────────────────────────

    def get_profile(self, vendor_id: int) -> Dict[str, Any]:
        """Get full vendor profile with business info, hours, holidays."""
        vendor = self._get_vendor(vendor_id)
        profile = self._get_or_create_profile(vendor_id)

        return {
            "vendor_id": vendor.vendor_id,
            "business_name": profile.business_name,
            "category": profile.category or vendor.category,
            "description": profile.description,
            "phone": profile.phone or vendor.owner.phone if vendor.owner else None,
            "email": profile.email,
            "location": profile.location,
            "latitude": profile.latitude,
            "longitude": profile.longitude,
            "logo_url": profile.logo_url,
            "cover_image": profile.cover_image,
            "business_hours": profile.business_hours or {},
            "pickup_instructions": profile.pickup_instructions,
            "holidays": profile.holidays or [],
            "is_open": profile.is_open,
            "max_pickup_distance_km": profile.max_pickup_distance_km,
            "prep_time_minutes": profile.prep_time_minutes,
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.updated_at.isoformat(),
        }

    def update_profile(self, vendor_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update vendor profile fields."""
        profile = self._get_or_create_profile(vendor_id)

        updatable_fields = [
            "business_name", "description", "phone", "email", "location",
            "latitude", "longitude", "logo_url", "cover_image",
            "business_hours", "pickup_instructions", "holidays",
            "is_open", "max_pickup_distance_km", "prep_time_minutes",
        ]

        for field in updatable_fields:
            if field in data:
                setattr(profile, field, data[field])

        self.db.flush()
        return self.get_profile(vendor_id)

    # ── Staff Management ───────────────────────────────────────────────────

    def get_staff(self, vendor_id: int) -> List[Dict[str, Any]]:
        """Get all staff members for a vendor."""
        vendor = self._get_vendor(vendor_id)
        staff = self.db.query(VendorStaff).filter(
            VendorStaff.vendor_id == vendor_id
        ).all()

        result = []
        for member in staff:
            permissions = self.db.query(VendorStaffPermission).filter(
                VendorStaffPermission.staff_id == member.id
            ).all()
            result.append({
                "id": member.id,
                "name": member.name,
                "role": member.role,
                "phone": member.phone,
                "is_active": member.is_active,
                "permissions": [p.permission for p in permissions if p.is_granted],
                "created_at": member.created_at.isoformat(),
            })
        return result

    def add_staff(self, vendor_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new staff member."""
        vendor = self._get_vendor(vendor_id)

        role = data.get("role", "staff")
        if role not in ("manager", "staff"):
            raise ValueError("Role must be 'manager' or 'staff'")

        staff = VendorStaff(
            vendor_id=vendor_id,
            name=data["name"],
            role=role,
            phone=data["phone"],
            password_hash=data.get("password_hash"),
        )
        self.db.add(staff)
        self.db.flush()

        # Assign default permissions based on role
        if role == "manager":
            default_perms = MANAGER_PERMISSIONS
        else:
            default_perms = STAFF_DEFAULT_PERMISSIONS

        for perm in default_perms:
            sp = VendorStaffPermission(
                staff_id=staff.id,
                permission=perm,
                is_granted=True,
            )
            self.db.add(sp)

        self.db.flush()
        return {
            "id": staff.id,
            "name": staff.name,
            "role": staff.role,
            "phone": staff.phone,
            "is_active": staff.is_active,
            "permissions": default_perms,
        }

    def update_staff(self, vendor_id: int, staff_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update staff member details and permissions."""
        staff = self.db.query(VendorStaff).filter(
            VendorStaff.id == staff_id,
            VendorStaff.vendor_id == vendor_id,
        ).first()
        if not staff:
            raise ValueError("Staff member not found")

        if "name" in data:
            staff.name = data["name"]
        if "role" in data:
            staff.role = data["role"]
        if "phone" in data:
            staff.phone = data["phone"]
        if "is_active" in data:
            staff.is_active = data["is_active"]

        # Update permissions if provided
        if "permissions" in data:
            # Remove existing permissions
            self.db.query(VendorStaffPermission).filter(
                VendorStaffPermission.staff_id == staff_id
            ).delete()

            # Add new permissions
            for perm in data["permissions"]:
                sp = VendorStaffPermission(
                    staff_id=staff_id,
                    permission=perm,
                    is_granted=True,
                )
                self.db.add(sp)

        self.db.flush()

        # Return updated staff
        permissions = self.db.query(VendorStaffPermission).filter(
            VendorStaffPermission.staff_id == staff_id
        ).all()

        return {
            "id": staff.id,
            "name": staff.name,
            "role": staff.role,
            "phone": staff.phone,
            "is_active": staff.is_active,
            "permissions": [p.permission for p in permissions if p.is_granted],
        }

    def delete_staff(self, vendor_id: int, staff_id: int) -> None:
        """Remove a staff member."""
        staff = self.db.query(VendorStaff).filter(
            VendorStaff.id == staff_id,
            VendorStaff.vendor_id == vendor_id,
        ).first()
        if not staff:
            raise ValueError("Staff member not found")

        # Delete permissions first
        self.db.query(VendorStaffPermission).filter(
            VendorStaffPermission.staff_id == staff_id
        ).delete()

        self.db.delete(staff)
        self.db.flush()

    # ── Permissions ───────────────────────────────────────────────────────

    def get_permissions(self) -> Dict[str, Any]:
        """Get all available permissions grouped by module."""
        return {
            "groups": PERMISSIONS,
            "owner_permissions": OWNER_PERMISSIONS,
            "staff_defaults": STAFF_DEFAULT_PERMISSIONS,
            "manager_defaults": MANAGER_PERMISSIONS,
        }

    def check_permission(self, vendor_id: int, staff_id: int, permission: str) -> bool:
        """Check if a staff member has a specific permission."""
        staff = self.db.query(VendorStaff).filter(
            VendorStaff.id == staff_id,
            VendorStaff.vendor_id == vendor_id,
        ).first()
        if not staff:
            return False

        # Owner has all permissions
        if staff.role == "owner":
            return True

        perm = self.db.query(VendorStaffPermission).filter(
            VendorStaffPermission.staff_id == staff_id,
            VendorStaffPermission.permission == permission,
            VendorStaffPermission.is_granted == True,
        ).first()

        return perm is not None