import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.time_utils import utcnow_naive

security = HTTPBearer()
logger = logging.getLogger("tnt.security")

# 🔥 LOAD .env EXPLICITLY
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Read from SECRET_KEY (primary) or JWT_SECRET (legacy)
SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET")
if not SECRET_KEY:
    import sys
    if os.getenv("APP_ENV", "development") == "production":
        raise RuntimeError(
            "SECRET_KEY environment variable must be set in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    SECRET_KEY = "dev_only_insecure_secret_do_not_use_in_production"
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

_BLOCKED_USER_DETAIL = (
    "Your account is currently restricted. Contact admin."
)


def create_access_token(data: dict, expires_delta: int):
    to_encode = data.copy()
    expire = utcnow_naive() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        phone = payload.get("phone")
        role = payload.get("role")

        if user_id is None or role is None:
            try:
                from app.core import security_monitor
                from app.core.rate_limit import _client_ip
                security_monitor.record_jwt_failure(ip=_client_ip(request), token_preview=token[:15] if token else "", reason="Invalid token payload")
            except Exception:
                pass
            raise HTTPException(status_code=401, detail="Invalid token payload")

        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            try:
                from app.core import security_monitor
                from app.core.rate_limit import _client_ip
                security_monitor.record_jwt_failure(ip=_client_ip(request), token_preview=token[:15] if token else "", reason="Invalid token subject")
            except Exception:
                pass
            raise HTTPException(status_code=401, detail="Invalid token subject")

    except JWTError:
        try:
            from app.core import security_monitor
            from app.core.rate_limit import _client_ip
            security_monitor.record_jwt_failure(ip=_client_ip(request), token_preview=token[:15] if token else "", reason="JWTError")
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid token")

    # --- Active-user guard: re-check is_active on every request -----------
    # Import here to avoid a circular import at module load time.
    from app.modules.users.model import User

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        # Token references a user that no longer exists in the DB.
        logger.warning(
            "auth_user_not_found event=blocked_login_attempt "
            "user_id=%s phone=%s role=%s",
            user_id, phone, role,
        )
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        # Emit a structured monitoring event so alerting/dashboards can track
        # blocked access attempts in real time.
        logger.warning(
            "auth_blocked event=blocked_login_attempt "
            "user_id=%s phone=%s role=%s",
            user_id, phone, role,
        )
        try:
            from app.core import security_monitor
            from app.core.rate_limit import _client_ip
            security_monitor.record_api_abuse(ip=_client_ip(request), path=request.url.path, user_id=user_id, reason="Blocked user account access attempt")
        except Exception:
            pass
        raise HTTPException(status_code=403, detail=_BLOCKED_USER_DETAIL)

    return {
        "id": user_id,
        "phone": phone,
        "role": role,
        "is_active": user.is_active,
    }


def require_role(required_role: str):
    """
    Dependency factory that gates a route to a specific role.

    Also accepts 'admin' or 'super_admin' when either is required
    (since both are admin-level roles).

    The is_active check is inherited automatically because this delegates
    to get_current_user(), which performs the DB lookup on every request.
    """
    def role_checker(request: Request, user=Depends(get_current_user)):
        # Treat both admin and super_admin as valid for admin-level routes
        allowed = ["admin", "super_admin"] if required_role in ("admin", "super_admin") else [required_role]
        if user["role"] not in allowed:
            try:
                from app.core import security_monitor
                from app.core.rate_limit import _client_ip
                security_monitor.record_api_abuse(
                    ip=_client_ip(request),
                    path=request.url.path,
                    user_id=user["id"],
                    reason=f"Access denied: required {required_role}, got {user['role']}"
                )
            except Exception:
                pass
            raise HTTPException(status_code=403, detail="Access denied")
        return user
    return role_checker


def get_current_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Return the authenticated user's integer ID, enforcing the active guard."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            try:
                from app.core import security_monitor
                from app.core.rate_limit import _client_ip
                security_monitor.record_jwt_failure(ip=_client_ip(request), token_preview=token[:15] if token else "", reason="Invalid token payload")
            except Exception:
                pass
            raise HTTPException(status_code=401, detail="Invalid token payload")
        user_id = int(user_id)
    except JWTError:
        try:
            from app.core import security_monitor
            from app.core.rate_limit import _client_ip
            security_monitor.record_jwt_failure(ip=_client_ip(request), token_preview=token[:15] if token else "", reason="JWTError")
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid token")
    except (TypeError, ValueError):
        try:
            from app.core import security_monitor
            from app.core.rate_limit import _client_ip
            security_monitor.record_jwt_failure(ip=_client_ip(request), token_preview=token[:15] if token else "", reason="Invalid token subject")
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid token subject")

    from app.modules.users.model import User

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        logger.warning(
            "auth_blocked event=blocked_login_attempt user_id=%s", user_id
        )
        try:
            from app.core import security_monitor
            from app.core.rate_limit import _client_ip
            security_monitor.record_api_abuse(ip=_client_ip(request), path=request.url.path, user_id=user_id, reason="Blocked user account access attempt")
        except Exception:
            pass
        raise HTTPException(status_code=403, detail=_BLOCKED_USER_DETAIL)

    return user_id
