"""Vendor Authentication Router.

Prefix: /vendor

Endpoints
---------
POST /vendor/register       — Register a new vendor (requires existing User)
POST /vendor/login           — Login as vendor owner or staff
POST /vendor/refresh         — Rotate refresh token
GET  /vendor/profile         — Get own vendor profile
PUT  /vendor/profile         — Update vendor profile (owner only)
GET  /vendor/staff           — List staff members (owner only)
POST /vendor/staff           — Create staff member (owner only)
PUT  /vendor/staff/{id}      — Update staff member (owner only)
DELETE /vendor/staff/{id}    — Delete staff member (owner only)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db

from app.modules.vendors.auth_schemas import (
    VendorLoginRequest,
    VendorLoginResponse,
    VendorProfileResponse,
    VendorProfileUpdate,
    VendorStaffCreate,
    VendorStaffResponse,
    VendorStaffUpdate,
    VendorTokenRefreshRequest,
    VendorTokenRefreshResponse,
)
from app.modules.vendors.auth_service import (
    create_staff,
    delete_staff,
    get_current_vendor,
    get_vendor_profile,
    list_staff,
    login_as_vendor_owner,
    login_as_vendor_staff,
    refresh_vendor_token,
    register_vendor,
    require_vendor_owner,
    update_staff,
    update_vendor_profile,
)

router = APIRouter(prefix="/vendor", tags=["Vendor Auth"])


# ─── Registration & Auth ────────────────────────────────────────────────────


@router.post("/register")
def register(
    vendor_name: str,
    category: str,
    owner_phone: str,
    password: str,
    db: Session = Depends(get_db),
):
    """Register a new vendor business.

    The owner_phone must belong to an existing User (created via OTP login).
    The User's role is upgraded to VENDOR automatically.
    Returns the new vendor profile with PENDING status.
    """
    result = register_vendor(
        vendor_name=vendor_name,
        category=category,
        owner_phone=owner_phone,
        password=password,
        db=db,
    )
    return {"success": True, "vendor": result}


@router.post("/login", response_model=VendorLoginResponse)
def login(
    body: VendorLoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticate as vendor owner or staff.

    To login as an **owner**: provide ``vendor_id`` + ``password``.
    To login as **staff**: provide ``staff_phone`` + ``password``.
    """
    if body.staff_phone:
        return login_as_vendor_staff(
            phone=body.staff_phone,
            password=body.password,
            db=db,
        )
    return login_as_vendor_owner(
        vendor_id=body.vendor_id,
        password=body.password,
        db=db,
    )


@router.post("/refresh", response_model=VendorTokenRefreshResponse)
def refresh(
    body: VendorTokenRefreshRequest,
    db: Session = Depends(get_db),
):
    """Exchange a refresh token for a new access + refresh pair.

    Refresh tokens are single-use (rotated). If a token is used twice,
    the second request is rejected.
    """
    result = refresh_vendor_token(
        refresh_token=body.refresh_token,
        db=db,
    )

    return VendorTokenRefreshResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type=result["token_type"],
    )


# ─── Profile ─────────────────────────────────────────────────────────────────


@router.get("/profile", response_model=VendorProfileResponse)
def profile(
    db: Session = Depends(get_db),
    vendor_ctx: dict = Depends(get_current_vendor),
):
    """Get the authenticated vendor's profile."""
    return get_vendor_profile(vendor_ctx, db)


@router.put("/profile", response_model=VendorProfileResponse)
def update_profile(
    body: VendorProfileUpdate,
    db: Session = Depends(get_db),
    vendor_ctx: dict = Depends(require_vendor_owner),
):
    """Update vendor profile (owner only)."""
    return update_vendor_profile(
        vendor_ctx=vendor_ctx,
        db=db,
        vendor_name=body.vendor_name,
        category=body.category,
    )


# ─── Staff Management (owner only) ───────────────────────────────────────────


@router.get("/staff", response_model=list[VendorStaffResponse])
def list_staff_endpoint(
    db: Session = Depends(get_db),
    vendor_ctx: dict = Depends(require_vendor_owner),
):
    """List all staff members for this vendor."""
    return list_staff(vendor_ctx, db)


@router.post("/staff", response_model=VendorStaffResponse)
def create_staff_endpoint(
    body: VendorStaffCreate,
    db: Session = Depends(get_db),
    vendor_ctx: dict = Depends(require_vendor_owner),
):
    """Add a new staff member (owner only)."""
    return create_staff(
        vendor_ctx=vendor_ctx,
        db=db,
        name=body.name,
        role=body.role,
        phone=body.phone,
        password=body.password,
        permissions=body.permissions,
    )


@router.put("/staff/{staff_id}", response_model=VendorStaffResponse)
def update_staff_endpoint(
    staff_id: int,
    body: VendorStaffUpdate,
    db: Session = Depends(get_db),
    vendor_ctx: dict = Depends(require_vendor_owner),
):
    """Update a staff member (owner only)."""
    return update_staff(
        vendor_ctx=vendor_ctx,
        staff_id=staff_id,
        db=db,
        name=body.name,
        role=body.role,
        phone=body.phone,
        is_active=body.is_active,
        permissions=body.permissions,
    )


@router.delete("/staff/{staff_id}")
def delete_staff_endpoint(
    staff_id: int,
    db: Session = Depends(get_db),
    vendor_ctx: dict = Depends(require_vendor_owner),
):
    """Remove a staff member (owner only)."""
    delete_staff(vendor_ctx, staff_id, db)
    return {"message": "Staff member removed"}
