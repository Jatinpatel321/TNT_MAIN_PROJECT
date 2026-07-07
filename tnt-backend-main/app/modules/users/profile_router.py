import os
import uuid

from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.menu.model import MenuItem
from app.modules.users.favorites_model import UserFavoriteMenuItem, UserFavoriteVendor
from app.modules.users.model import User, UserRole
from app.modules.users.schemas import (
    FavoriteMenuItemResponse,
    FavoriteVendorResponse,
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


# ── Favourite vendors ───────────────────────────────────────────────────────

@router.get("/favorites/vendors", response_model=list[FavoriteVendorResponse])
def list_favorite_vendors(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """List the authenticated user's favourite vendors (stalls)."""
    db_user = _get_current_db_user(user, db)
    rows = (
        db.query(UserFavoriteVendor, User)
        .join(User, User.id == UserFavoriteVendor.vendor_id)
        .filter(UserFavoriteVendor.user_id == db_user.id)
        .order_by(UserFavoriteVendor.created_at.desc())
        .all()
    )
    return [
        FavoriteVendorResponse(
            vendor_id=vendor.id,
            vendor_name=vendor.full_name or vendor.name,
            vendor_type=vendor.vendor_type,
            created_at=fav.created_at,
        )
        for fav, vendor in rows
    ]


@router.post("/favorites/vendors/{vendor_id}", response_model=FavoriteVendorResponse)
def add_favorite_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Mark a vendor as favourite. Idempotent — adding twice is a no-op."""
    db_user = _get_current_db_user(user, db)
    vendor = db.query(User).filter(User.id == vendor_id, User.role == UserRole.VENDOR).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    existing = (
        db.query(UserFavoriteVendor)
        .filter(UserFavoriteVendor.user_id == db_user.id, UserFavoriteVendor.vendor_id == vendor_id)
        .first()
    )
    if not existing:
        existing = UserFavoriteVendor(user_id=db_user.id, vendor_id=vendor_id)
        db.add(existing)
        db.commit()
        db.refresh(existing)

    return FavoriteVendorResponse(
        vendor_id=vendor.id,
        vendor_name=vendor.full_name or vendor.name,
        vendor_type=vendor.vendor_type,
        created_at=existing.created_at,
    )


@router.delete("/favorites/vendors/{vendor_id}")
def remove_favorite_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Remove a vendor from favourites."""
    db_user = _get_current_db_user(user, db)
    existing = (
        db.query(UserFavoriteVendor)
        .filter(UserFavoriteVendor.user_id == db_user.id, UserFavoriteVendor.vendor_id == vendor_id)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()
    return {"message": "Removed from favourites"}


# ── Favourite menu items ─────────────────────────────────────────────────────

@router.get("/favorites/menu-items", response_model=list[FavoriteMenuItemResponse])
def list_favorite_menu_items(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """List the authenticated user's favourite menu items."""
    db_user = _get_current_db_user(user, db)
    rows = (
        db.query(UserFavoriteMenuItem, MenuItem)
        .join(MenuItem, MenuItem.id == UserFavoriteMenuItem.menu_item_id)
        .filter(UserFavoriteMenuItem.user_id == db_user.id)
        .order_by(UserFavoriteMenuItem.created_at.desc())
        .all()
    )
    return [
        FavoriteMenuItemResponse(
            menu_item_id=item.id,
            name=item.name,
            vendor_id=item.vendor_id,
            price=item.price,
            created_at=fav.created_at,
        )
        for fav, item in rows
    ]


@router.post("/favorites/menu-items/{menu_item_id}", response_model=FavoriteMenuItemResponse)
def add_favorite_menu_item(
    menu_item_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Mark a menu item as favourite. Idempotent — adding twice is a no-op."""
    db_user = _get_current_db_user(user, db)
    item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    existing = (
        db.query(UserFavoriteMenuItem)
        .filter(UserFavoriteMenuItem.user_id == db_user.id, UserFavoriteMenuItem.menu_item_id == menu_item_id)
        .first()
    )
    if not existing:
        existing = UserFavoriteMenuItem(user_id=db_user.id, menu_item_id=menu_item_id)
        db.add(existing)
        db.commit()
        db.refresh(existing)

    return FavoriteMenuItemResponse(
        menu_item_id=item.id,
        name=item.name,
        vendor_id=item.vendor_id,
        price=item.price,
        created_at=existing.created_at,
    )


@router.delete("/favorites/menu-items/{menu_item_id}")
def remove_favorite_menu_item(
    menu_item_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Remove a menu item from favourites."""
    db_user = _get_current_db_user(user, db)
    existing = (
        db.query(UserFavoriteMenuItem)
        .filter(UserFavoriteMenuItem.user_id == db_user.id, UserFavoriteMenuItem.menu_item_id == menu_item_id)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()
    return {"message": "Removed from favourites"}
