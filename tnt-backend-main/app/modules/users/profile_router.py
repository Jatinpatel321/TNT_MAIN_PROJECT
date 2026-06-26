import os
import uuid

from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.users.model import User
from app.modules.users.schemas import (
    ProfileImageResponse,
    ProfileUpdateRequest,
    UserResponse,
)

router = APIRouter(prefix="/profile", tags=["Profile"])


class DeviceTokenRequest(BaseModel):
    device_token: str
    push_enabled: bool = True


@router.post("/device-token", summary="Register FCM device token")
def register_device_token(
    payload: DeviceTokenRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.device_token = payload.device_token
    db_user.push_enabled = payload.push_enabled
    db.commit()
    return {"message": "Device token registered"}

UPLOAD_DIR = "uploads/profile"
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _get_current_db_user(user: dict, db: Session) -> User:
    db_user = db.query(User).filter(User.id == user["id"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if db_user.phone != user["phone"]:
        raise HTTPException(status_code=403, detail="Cannot access other user's profile")
    return db_user


@router.get("/me", response_model=UserResponse)
def get_profile(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Return the full profile of the currently authenticated user."""
    db_user = _get_current_db_user(user, db)
    return db_user


@router.put("/update", response_model=UserResponse)
def update_profile(
    body: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Update profile fields for the currently authenticated user.

    Only supplied (non-null) fields are updated; null fields are ignored.
    """
    db_user = _get_current_db_user(user, db)
    update_data = body.model_dump(exclude_none=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/upload-image", response_model=ProfileImageResponse)
def upload_profile_image(
    file: UploadFile,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Upload or replace the authenticated user's profile image.

    Accepts JPEG, PNG, or WebP up to 5 MB.
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image format. Allowed: {', '.join(sorted(ALLOWED_TYPES))}",
        )

    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB)")

    db_user = _get_current_db_user(user, db)

    # Remove old image file if it exists on disk
    if db_user.profile_image:
        old_path = db_user.profile_image.lstrip("/")
        if os.path.exists(old_path):
            os.remove(old_path)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(content)

    db_user.profile_image = f"/{UPLOAD_DIR}/{filename}"
    db.commit()
    db.refresh(db_user)

    return ProfileImageResponse(profile_image=db_user.profile_image)
