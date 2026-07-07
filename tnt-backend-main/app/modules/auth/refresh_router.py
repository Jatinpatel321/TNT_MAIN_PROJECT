"""JWT Refresh Token management.

Provides:
- ``POST /auth/refresh`` — exchange a valid refresh token for a new access token.
- ``POST /auth/logout`` — revoke a refresh token immediately.
- ``create_refresh_token()`` — used by the auth router after OTP verification.
- ``revoke_all_user_tokens()`` — called when an admin blocks a user.
"""
import json
import logging
import os
import secrets

from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.redis import redis_client
from app.core.security import create_access_token
from app.modules.users.model import User

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger("tnt.auth.refresh")

REFRESH_TTL_DAYS = int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "7"))
ACCESS_TTL_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or "dev_only_insecure_secret"
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def _refresh_key(token: str) -> str:
    return f"tnt:refresh_token:{token}"


def create_refresh_token(user_id: int, role: str, phone: str) -> str:
    """Generate a cryptographically random refresh token and store its payload in Redis."""
    token = secrets.token_urlsafe(64)
    payload = {"user_id": user_id, "role": role, "phone": phone}
    redis_client.setex(_refresh_key(token), REFRESH_TTL_DAYS * 86400, json.dumps(payload))
    return token


def revoke_refresh_token(token: str) -> None:
    """Delete a specific refresh token from Redis."""
    redis_client.delete(_refresh_key(token))


def revoke_all_user_tokens(user_id: int) -> None:
    """Scan and delete all refresh tokens belonging to a user (used on block action)."""
    pattern = "tnt:refresh_token:*"
    cursor = 0
    while True:
        cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
        for key in keys:
            raw = redis_client.get(key)
            if raw:
                try:
                    data = json.loads(raw)
                    if data.get("user_id") == user_id:
                        redis_client.delete(key)
                except Exception:
                    pass
        if cursor == 0:
            break


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/refresh", response_model=RefreshResponse)
def refresh_access_token(body: RefreshRequest, db: Session = Depends(get_db)):
    """
    Exchange a valid refresh token for a new access token.
    The refresh token is NOT rotated here (stateless rotation adds complexity);
    it remains valid until its TTL expires or it is explicitly revoked.
    """
    raw = redis_client.get(_refresh_key(body.refresh_token))
    if not raw:
        raise HTTPException(status_code=401, detail="Refresh token expired or invalid")

    try:
        payload = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=401, detail="Malformed refresh token payload")

    user_id = payload.get("user_id")
    role = payload.get("role")
    phone = payload.get("phone")

    # Re-check user is still active
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        revoke_refresh_token(body.refresh_token)
        raise HTTPException(status_code=403, detail="Account is inactive")

    access_token = create_access_token(
        {"sub": str(user_id), "phone": phone, "role": role},
        expires_delta=ACCESS_TTL_MINUTES,
    )
    return RefreshResponse(access_token=access_token)


@router.post("/logout")
def logout(body: RefreshRequest):
    """Revoke the provided refresh token immediately."""
    revoke_refresh_token(body.refresh_token)
    return {"message": "Logged out successfully"}