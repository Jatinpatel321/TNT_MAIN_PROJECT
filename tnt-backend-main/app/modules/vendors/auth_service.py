"""Vendor Authentication Service.

Provides:
- Vendor owner login (by vendor_id + password)
- Vendor staff login (by phone + password)
- Token refresh with rotating refresh tokens
- Profile management for vendors
- Staff CRUD for vendor owners

Token Structure
---------------
Access token (15 min expiry):
    {"sub": "<vendor_id>", "role": "vendor_owner", "type": "vendor_access", "staff_id": null}
    {"sub": "<vendor_id>", "role": "vendor_staff", "type": "vendor_access", "staff_id": <id>}

Refresh token (7 day expiry, single-use):
    {"sub": "<vendor_id>", "role": "vendor_owner|vendor_staff", "type": "vendor_refresh",
     "staff_id": <id|null>, "jti": "<uuid>"}
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from typing import Any, Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
import bcrypt as _bcrypt_lib
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.redis import redis_client
from app.core.time_utils import utcnow_naive
from app.modules.users.model import User
from app.modules.vendors.model import Vendor, VendorStaff, VendorStatus

logger = logging.getLogger("tnt.vendor.auth")

# ── Password hashing (direct bcrypt — compatible with bcrypt >= 4.0) ─────────

# ── Constants ────────────────────────────────────────────────────────────────
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7
VENDOR_JWT_SECRET_KEY = "tnt_vendor_secret_key_change_in_prod"  # TODO: move to env
VENDOR_JWT_ALGORITHM = "HS256"

vendor_security = HTTPBearer(auto_error=False)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _hash_password(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode("utf-8"), _bcrypt_lib.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt_lib.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _create_access_token(vendor_id: int, role: str, staff_id: int | None = None) -> str:
    expire = utcnow_naive() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(vendor_id),
        "role": role,
        "type": "vendor_access",
        "staff_id": staff_id,
        "exp": expire,
    }
    return jwt.encode(payload, VENDOR_JWT_SECRET_KEY, algorithm=VENDOR_JWT_ALGORITHM)


def _create_refresh_token(
    vendor_id: int, role: str, staff_id: int | None = None
) -> tuple[str, str]:
    """Return (refresh_token, jti). jti is stored in Redis for single-use rotation."""
    jti = str(uuid.uuid4())
    expire = utcnow_naive() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(vendor_id),
        "role": role,
        "type": "vendor_refresh",
        "staff_id": staff_id,
        "jti": jti,
        "exp": expire,
    }
    token = jwt.encode(payload, VENDOR_JWT_SECRET_KEY, algorithm=VENDOR_JWT_ALGORITHM)
    return token, jti


def _store_refresh_jti(jti: str, vendor_id: int) -> None:
    """Store refresh token JTI in Redis for single-use rotation."""
    key = f"vendor:refresh:{jti}"
    redis_client.setex(key, REFRESH_TOKEN_EXPIRE_DAYS * 86400, str(vendor_id))


def _consume_refresh_jti(jti: str) -> bool:
    """Consume (delete) a refresh JTI. Returns False if already consumed."""
    key = f"vendor:refresh:{jti}"
    deleted = redis_client.delete(key)
    return deleted > 0


def _build_vendor_response(vendor: Vendor) -> dict:
    owner = vendor.owner
    return {
        "vendor_id": vendor.vendor_id,
        "vendor_name": vendor.vendor_name,
        "category": vendor.category,
        "owner_id": vendor.owner_id,
        "owner_name": owner.name if owner else None,
        "owner_phone": owner.phone if owner else None,
        "status": vendor.status.value if hasattr(vendor.status, "value") else str(vendor.status),
        "created_at": vendor.created_at,
    }


# ── Auth Guard ───────────────────────────────────────────────────────────────


def get_current_vendor(
    credentials: HTTPAuthorizationCredentials = Depends(vendor_security),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Dependency that validates the vendor JWT and returns the vendor context.

    Returns dict with keys: vendor_id, role, staff_id
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, VENDOR_JWT_SECRET_KEY, algorithms=[VENDOR_JWT_ALGORITHM]
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    token_type = payload.get("type")
    if token_type != "vendor_access":
        raise HTTPException(status_code=401, detail="Invalid token type — use an access token")

    vendor_id = payload.get("sub")
    role = payload.get("role")
    staff_id = payload.get("staff_id")

    if vendor_id is None or role is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Verify vendor still exists and is active
    vendor = db.query(Vendor).filter(Vendor.vendor_id == int(vendor_id)).first()
    if vendor is None:
        raise HTTPException(status_code=401, detail="Vendor not found")
    if vendor.status != VendorStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Vendor account is not active")

    # If staff, verify staff still active
    if role == "vendor_staff" and staff_id is not None:
        staff = db.query(VendorStaff).filter(
            VendorStaff.id == staff_id,
            VendorStaff.vendor_id == int(vendor_id),
        ).first()
        if staff is None or not staff.is_active:
            raise HTTPException(status_code=403, detail="Staff account inactive")

    return {
        "vendor_id": int(vendor_id),
        "role": role,
        "staff_id": staff_id,
    }


def require_vendor_owner(
    vendor_ctx: dict = Depends(get_current_vendor),
) -> dict:
    """Dependency: only vendor owners may access the guarded endpoint."""
    if vendor_ctx["role"] != "vendor_owner":
        raise HTTPException(status_code=403, detail="Only vendor owners can perform this action")
    return vendor_ctx


# ── Registration ─────────────────────────────────────────────────────────────


def register_vendor(
    vendor_name: str,
    category: str,
    owner_phone: str,
    password: str,
    db: Session,
) -> dict:
    """Register a new vendor. Creates the Vendor record and links to a User.

    The User must already exist (phone registered). If not, this raises 400.
    The User's role is upgraded to VENDOR if it isn't already.
    """
    # Find the owner User
    user = db.query(User).filter(User.phone == owner_phone).first()
    if not user:
        raise HTTPException(
            status_code=400,
            detail="User not found. Register first via OTP login.",
        )

    # Check if user already owns a vendor
    existing = db.query(Vendor).filter(Vendor.owner_id == user.id).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"User already owns vendor #{existing.vendor_id} ({existing.vendor_name})",
        )

    # Upgrade user role to VENDOR
    if user.role and user.role.name != "VENDOR":
        from app.modules.users.model import UserRole
        user.role = UserRole.VENDOR

    vendor = Vendor(
        vendor_name=vendor_name,
        category=category,
        owner_id=user.id,
        password_hash=_hash_password(password),
        status=VendorStatus.PENDING,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    logger.info(
        "vendor_registered event=vendor_created vendor_id=%s owner_id=%s",
        vendor.vendor_id, user.id,
    )

    return _build_vendor_response(vendor)


# ── Login ─────────────────────────────────────────────────────────────────────


def login_as_vendor_owner(
    vendor_id: int,
    password: str,
    db: Session,
    request: Optional[Request] = None,
) -> dict:
    """Authenticate a vendor owner by vendor_id + password."""
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        try:
            from app.modules.auditlog.service import write as write_audit_log, AuditAction, AuditCategory
            write_audit_log(
                db=db,
                action=AuditAction.LOGIN_FAILED,
                action_category=AuditCategory.AUTH,
                entity_type="Vendor",
                metadata={"vendor_id": vendor_id},
                request=request
            )
            db.commit()
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid vendor ID or password")

    if not _verify_password(password, vendor.password_hash):
        try:
            from app.modules.auditlog.service import write as write_audit_log, AuditAction, AuditCategory
            write_audit_log(
                db=db,
                action=AuditAction.LOGIN_FAILED,
                action_category=AuditCategory.AUTH,
                entity_type="Vendor",
                actor_id=vendor.owner_id,
                metadata={"vendor_id": vendor_id},
                request=request
            )
            db.commit()
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid vendor ID or password")

    if vendor.status == VendorStatus.SUSPENDED:
        raise HTTPException(status_code=403, detail="Vendor account is suspended")
    if vendor.status == VendorStatus.INACTIVE:
        raise HTTPException(status_code=403, detail="Vendor account is inactive")

    access_token = _create_access_token(vendor.vendor_id, "vendor_owner")
    refresh_token, jti = _create_refresh_token(vendor.vendor_id, "vendor_owner")
    _store_refresh_jti(jti, vendor.vendor_id)

    try:
        from app.modules.auditlog.service import write as write_audit_log, AuditAction, AuditCategory
        write_audit_log(
            db=db,
            action=AuditAction.LOGIN_SUCCESS,
            action_category=AuditCategory.AUTH,
            actor_id=vendor.owner_id,
            actor_role="vendor_owner",
            entity_type="Vendor",
            entity_id=str(vendor.vendor_id),
            request=request
        )
        db.commit()
    except Exception:
        pass

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "vendor": _build_vendor_response(vendor),
    }


def login_as_vendor_staff(
    phone: str,
    password: str,
    db: Session,
    request: Optional[Request] = None,
) -> dict:
    """Authenticate a vendor staff member by phone + password."""
    staff = db.query(VendorStaff).filter(VendorStaff.phone == phone).first()
    if not staff:
        try:
            from app.modules.auditlog.service import write as write_audit_log, AuditAction, AuditCategory
            write_audit_log(
                db=db,
                action=AuditAction.LOGIN_FAILED,
                action_category=AuditCategory.AUTH,
                entity_type="VendorStaff",
                metadata={"phone": phone},
                request=request
            )
            db.commit()
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid staff phone or password")

    if not staff.password_hash or not _verify_password(password, staff.password_hash):
        try:
            from app.modules.auditlog.service import write as write_audit_log, AuditAction, AuditCategory
            write_audit_log(
                db=db,
                action=AuditAction.LOGIN_FAILED,
                action_category=AuditCategory.AUTH,
                entity_type="VendorStaff",
                metadata={"phone": phone, "vendor_id": staff.vendor_id},
                request=request
            )
            db.commit()
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid staff phone or password")

    if not staff.is_active:
        raise HTTPException(status_code=403, detail="Staff account is inactive")

    vendor = db.query(Vendor).filter(Vendor.vendor_id == staff.vendor_id).first()
    if not vendor or vendor.status != VendorStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Vendor is not active")

    access_token = _create_access_token(staff.vendor_id, "vendor_staff", staff.id)
    refresh_token, jti = _create_refresh_token(staff.vendor_id, "vendor_staff", staff.id)
    _store_refresh_jti(jti, staff.vendor_id)

    try:
        from app.modules.auditlog.service import write as write_audit_log, AuditAction, AuditCategory
        write_audit_log(
            db=db,
            action=AuditAction.LOGIN_SUCCESS,
            action_category=AuditCategory.AUTH,
            actor_role="vendor_staff",
            entity_type="VendorStaff",
            entity_id=str(staff.id),
            metadata={"vendor_id": staff.vendor_id},
            request=request
        )
        db.commit()
    except Exception:
        pass

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "vendor": _build_vendor_response(vendor),
    }


# ── Token Refresh ────────────────────────────────────────────────────────────


def refresh_vendor_token(refresh_token: str, db: Session) -> dict:
    """Refresh an access token using a single-use refresh token."""
    try:
        payload = jwt.decode(
            refresh_token, VENDOR_JWT_SECRET_KEY, algorithms=[VENDOR_JWT_ALGORITHM]
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if payload.get("type") != "vendor_refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Single-use check: consume JTI from Redis
    if not _consume_refresh_jti(jti):
        raise HTTPException(status_code=401, detail="Refresh token already used")

    vendor_id = int(payload["sub"])
    role = payload["role"]
    staff_id = payload.get("staff_id")

    # Verify vendor still active
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor or vendor.status != VendorStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Vendor is not active")

    # Issue new pair
    new_access = _create_access_token(vendor_id, role, staff_id)
    new_refresh, new_jti = _create_refresh_token(vendor_id, role, staff_id)
    _store_refresh_jti(new_jti, vendor_id)

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


# ── Profile ──────────────────────────────────────────────────────────────────


def get_vendor_profile(vendor_ctx: dict, db: Session) -> dict:
    """Return the vendor profile for the authenticated vendor."""
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_ctx["vendor_id"]).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return _build_vendor_response(vendor)


def update_vendor_profile(
    vendor_ctx: dict,
    db: Session,
    vendor_name: str | None = None,
    category: str | None = None,
) -> dict:
    """Update vendor profile fields. Only vendor_owner can edit."""
    if vendor_ctx["role"] != "vendor_owner":
        raise HTTPException(status_code=403, detail="Only vendor owner can update profile")

    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_ctx["vendor_id"]).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    if vendor_name is not None:
        vendor.vendor_name = vendor_name
    if category is not None:
        vendor.category = category

    db.commit()
    db.refresh(vendor)
    return _build_vendor_response(vendor)


# ── Staff CRUD (owner-only) ──────────────────────────────────────────────────


def list_staff(vendor_ctx: dict, db: Session) -> list[dict]:
    """List all staff members for the vendor."""
    staff_members = (
        db.query(VendorStaff)
        .filter(VendorStaff.vendor_id == vendor_ctx["vendor_id"])
        .order_by(VendorStaff.created_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "vendor_id": s.vendor_id,
            "name": s.name,
            "role": s.role,
            "phone": s.phone,
            "permissions": s.permissions,
            "is_active": s.is_active,
            "created_at": s.created_at,
        }
        for s in staff_members
    ]


def create_staff(
    vendor_ctx: dict,
    db: Session,
    name: str,
    role: str,
    phone: str,
    password: str,
    permissions: dict | None = None,
) -> dict:
    """Add a new staff member. Only vendor_owner can do this."""
    if vendor_ctx["role"] != "vendor_owner":
        raise HTTPException(status_code=403, detail="Only vendor owner can manage staff")

    # Check phone uniqueness
    existing = db.query(VendorStaff).filter(VendorStaff.phone == phone).first()
    if existing:
        raise HTTPException(status_code=409, detail="Staff with this phone already exists")

    staff = VendorStaff(
        vendor_id=vendor_ctx["vendor_id"],
        name=name,
        role=role,
        phone=phone,
        password_hash=_hash_password(password) if password else None,
        permissions=permissions or {},
        is_active=True,
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)

    return {
        "id": staff.id,
        "vendor_id": staff.vendor_id,
        "name": staff.name,
        "role": staff.role,
        "phone": staff.phone,
        "permissions": staff.permissions,
        "is_active": staff.is_active,
        "created_at": staff.created_at,
    }


def update_staff(
    vendor_ctx: dict,
    staff_id: int,
    db: Session,
    name: str | None = None,
    role: str | None = None,
    phone: str | None = None,
    is_active: bool | None = None,
    permissions: dict | None = None,
) -> dict:
    """Update a staff member's details."""
    if vendor_ctx["role"] != "vendor_owner":
        raise HTTPException(status_code=403, detail="Only vendor owner can manage staff")

    staff = (
        db.query(VendorStaff)
        .filter(
            VendorStaff.id == staff_id,
            VendorStaff.vendor_id == vendor_ctx["vendor_id"],
        )
        .first()
    )
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    if name is not None:
        staff.name = name
    if role is not None:
        staff.role = role
    if phone is not None:
        # Check uniqueness
        dup = (
            db.query(VendorStaff)
            .filter(VendorStaff.phone == phone, VendorStaff.id != staff_id)
            .first()
        )
        if dup:
            raise HTTPException(status_code=409, detail="Phone already in use by another staff member")
        staff.phone = phone
    if is_active is not None:
        staff.is_active = is_active
    if permissions is not None:
        staff.permissions = permissions

    db.commit()
    db.refresh(staff)

    return {
        "id": staff.id,
        "vendor_id": staff.vendor_id,
        "name": staff.name,
        "role": staff.role,
        "phone": staff.phone,
        "permissions": staff.permissions,
        "is_active": staff.is_active,
        "created_at": staff.created_at,
    }


def delete_staff(vendor_ctx: dict, staff_id: int, db: Session) -> None:
    """Remove a staff member."""
    if vendor_ctx["role"] != "vendor_owner":
        raise HTTPException(status_code=403, detail="Only vendor owner can manage staff")

    staff = (
        db.query(VendorStaff)
        .filter(
            VendorStaff.id == staff_id,
            VendorStaff.vendor_id == vendor_ctx["vendor_id"],
        )
        .first()
    )
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    db.delete(staff)
    db.commit()