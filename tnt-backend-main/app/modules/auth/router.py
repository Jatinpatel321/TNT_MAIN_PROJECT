import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.observability import observability
from app.core.rate_limit import login_rate_limiter, otp_rate_limiter
from app.core.config import settings
from app.core.security import create_access_token, get_current_user, require_role
from app.modules.auth.otp_service import generate_otp, verify_otp
from app.modules.auth.refresh_router import create_refresh_token
from app.modules.auth.schemas import LoginRequest, VerifyOTPRequest
from app.modules.users.model import User, UserRole

router = APIRouter(prefix="/auth", tags=["Auth"])

logger = logging.getLogger("tnt.auth")


def _normalize_phone(raw: str) -> str:
    """
    Normalize an Indian phone number to +91XXXXXXXXXX format.

    Accepts:  '9727804515', '+919727804515', '919727804515', '+91 97278 04515'
    Returns:  '+919727804515'
    """
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 11 and digits.startswith("0"):
        return f"+91{digits[1:]}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    if len(digits) == 13 and digits.startswith("091"):
        return f"+91{digits[3:]}"
    # Unexpected format — prefix with + as best-effort
    return f"+{digits}"


def _lookup_user(db: Session, phone_normalized: str) -> Optional[User]:
    """
    Look up user by normalized phone (+91XXXXXXXXXX) or raw 10-digit form.
    The DB may have either format depending on how the user was created.
    """
    digits = re.sub(r"\D", "", phone_normalized)
    raw_10 = digits[-10:] if len(digits) >= 10 else digits
    candidates = (
        db.query(User)
        .filter(
            or_(
                User.phone == phone_normalized,
                User.phone == raw_10,
                User.phone == f"+91{raw_10}",
                User.phone == f"91{raw_10}",
            )
        )
        .all()
    )
    if not candidates:
        return None
    # Prefer admin role user if multiple matches exist
    for c in candidates:
        if c.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
            return c
    return candidates[0]


@router.post("/send-otp")
async def send_otp(
    body: LoginRequest,
    _rl: None = Depends(otp_rate_limiter),
):
    phone_normalized = _normalize_phone(body.phone)
    # Use the normalized phone for OTP storage so it matches verify-otp
    body.phone = phone_normalized

    # generate_otp handles Redis storage + SMS delivery internally.
    # The returned OTP value is intentionally unused here — it must never
    # be echoed back to the client.
    generate_otp(phone_normalized)

    return {"message": "OTP sent", "success": True, "phone": phone_normalized}


@router.post("/verify-otp")
def verify_otp_login(
    body: VerifyOTPRequest,
    db: Session = Depends(get_db),
    _rl: None = Depends(login_rate_limiter),
):
    phone_normalized = _normalize_phone(body.phone)
    body.phone = phone_normalized

    if not verify_otp(phone_normalized, body.otp):
        observability.record_otp_attempt(success=False)
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    observability.record_otp_attempt(success=True)

    user = _lookup_user(db, phone_normalized)

    # 🔥 AUTO-REGISTER IF NEW USER
    if not user:
        user = User(
            phone=phone_normalized,  # store consistently with +91
            role=UserRole.STUDENT,   # default role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(
            "auth_auto_register event=new_user phone=%s user_id=%s",
            phone_normalized, user.id,
        )
    else:
        # Migrate existing user's phone to normalized format if needed
        if user.phone != phone_normalized:
            logger.info(
                "auth_phone_migrate event=phone_normalized "
                "user_id=%s old=%s new=%s",
                user.id, user.phone, phone_normalized,
            )
            user.phone = phone_normalized
            db.commit()
            db.refresh(user)

    expires_minutes = settings.JWT_EXPIRY_MINUTES if hasattr(settings, "JWT_EXPIRY_MINUTES") else 1440
    token = create_access_token(
        data={
            "sub": str(user.id),
            "phone": user.phone,
            "role": user.role.value,
        },
        expires_delta=expires_minutes,
    )

    # Generate refresh token for session persistence
    refresh_token = create_refresh_token(user.id, user.role.value, user.phone)

    requires_2fa = (
        user.role.value in {"admin", "super_admin"}
        and getattr(user, "totp_enabled", False)
    )

    return {
        "success": True,
        "message": "Login successful",
        "data": {
            "access_token": token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "requires_2fa": requires_2fa,
            "user": {
                "id": user.id,
                "phone": user.phone,
                "name": user.name,
                "full_name": user.full_name,
                "role": user.role.value,
                "vendor_type": user.vendor_type,
                "university_id": user.university_id,
                "department": user.department,
                "semester": user.semester,
                "profile_image": user.profile_image,
                "is_active": user.is_active,
                "is_approved": user.is_approved,
            },
            "is_new_user": user.name is None,
        },
    }


# ── TOTP 2FA endpoints ────────────────────────────────────────────────────


@router.post("/admin/2fa/setup")
def setup_admin_2fa(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """Generate TOTP secret + QR code for admin 2FA setup."""
    from app.modules.auth.totp_service import generate_totp_secret, generate_qr_code_b64

    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if db_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled for this account")

    secret = generate_totp_secret()
    db_user.totp_secret = secret
    db.commit()

    qr_b64 = generate_qr_code_b64(secret, db_user.phone)
    return {
        "message": "Scan the QR code with your authenticator app, then call /auth/admin/2fa/confirm",
        "secret": secret,
        "qr_code_png_base64": qr_b64,
    }


@router.post("/admin/2fa/confirm")
def confirm_admin_2fa(
    code: str = Query(..., min_length=6, max_length=6, description="6-digit TOTP code from authenticator app"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """Confirm and activate 2FA by verifying the first TOTP code."""
    from app.modules.auth.totp_service import verify_totp

    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user or not db_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA setup not initiated — call /auth/admin/2fa/setup first")
    if db_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA already active")
    if not verify_totp(db_user.totp_secret, code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    db_user.totp_enabled = True
    db.commit()
    return {"message": "2FA successfully enabled for your admin account"}


@router.post("/admin/2fa/verify")
def verify_admin_2fa(
    totp_code: str = Query(..., min_length=6, max_length=6, description="6-digit TOTP code"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Verify a TOTP code after OTP login (for admins with 2FA enabled)."""
    from app.modules.auth.totp_service import verify_totp, is_admin_role

    if not is_admin_role(user.get("role", "")):
        raise HTTPException(status_code=403, detail="2FA verification is for admin accounts only")
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user or not db_user.totp_enabled or not db_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA not enabled on this account")
    if not verify_totp(db_user.totp_secret, totp_code):
        raise HTTPException(status_code=401, detail="Invalid authenticator code")
    return {"message": "2FA verified", "fully_authenticated": True}
