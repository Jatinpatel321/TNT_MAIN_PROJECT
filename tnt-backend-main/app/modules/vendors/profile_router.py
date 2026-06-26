"""Vendor Profile Module - API Router for profile, staff, and permissions."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.users.model import User
from app.modules.vendors.model import Vendor
from app.modules.vendors.profile_service import VendorProfileService

router = APIRouter(prefix="/vendors/profile", tags=["Vendor Profile"])


def _get_vendor(db: Session, user: dict) -> Vendor:
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    vendor = db.query(Vendor).filter(Vendor.owner_id == db_user.id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.get("/", summary="Get vendor profile")
def get_profile(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Get full vendor profile with business info, hours, holidays."""
    vendor = _get_vendor(db, user)
    service = VendorProfileService(db)
    return service.get_profile(vendor.vendor_id)


@router.put("/", summary="Update vendor profile")
def update_profile(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Update vendor profile fields."""
    vendor = _get_vendor(db, user)
    service = VendorProfileService(db)
    return service.update_profile(vendor.vendor_id, data)


@router.get("/staff", summary="Get staff members")
def get_staff(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Get all staff members for the vendor."""
    vendor = _get_vendor(db, user)
    service = VendorProfileService(db)
    staff = service.get_staff(vendor.vendor_id)
    return {"staff": staff, "total": len(staff)}


@router.post("/staff", summary="Add staff member")
def add_staff(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Add a new staff member with role-based permissions."""
    vendor = _get_vendor(db, user)
    service = VendorProfileService(db)
    try:
        return service.add_staff(vendor.vendor_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/staff/{staff_id}", summary="Update staff member")
def update_staff(
    staff_id: int,
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Update staff member details and permissions."""
    vendor = _get_vendor(db, user)
    service = VendorProfileService(db)

    # Check if we are updating permissions
    before_permissions = []
    if "permissions" in data:
        try:
            from app.modules.vendors.profile_models import VendorStaffPermission
            perms = db.query(VendorStaffPermission).filter(VendorStaffPermission.staff_id == staff_id).all()
            before_permissions = [p.permission for p in perms if p.is_granted]
        except Exception:
            pass

    try:
        res = service.update_staff(vendor.vendor_id, staff_id, data)
        # If permissions updated, write audit log
        if "permissions" in data:
            after_permissions = res.get("permissions", [])
            if set(before_permissions) != set(after_permissions):
                try:
                    from app.modules.auditlog.service import write as write_audit_log, AuditCategory
                    write_audit_log(
                        db=db,
                        action="vendor.staff_permissions_updated",
                        action_category=AuditCategory.VENDOR,
                        actor_id=user.get("id"),
                        actor_role=user.get("role"),
                        entity_type="VendorStaff",
                        entity_id=str(staff_id),
                        before_state={"permissions": before_permissions},
                        after_state={"permissions": after_permissions},
                    )
                    db.commit()
                except Exception:
                    pass
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/staff/{staff_id}", summary="Delete staff member")
def delete_staff(
    staff_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Remove a staff member."""
    vendor = _get_vendor(db, user)
    service = VendorProfileService(db)
    try:
        service.delete_staff(vendor.vendor_id, staff_id)
        return {"message": "Staff member removed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/permissions", summary="Get available permissions")
def get_permissions(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Get all available permissions grouped by module."""
    service = VendorProfileService(db)
    return service.get_permissions()