"""Vendor Image Upload Module - API endpoints for logo and cover image uploads."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.modules.vendors.auth_service import get_current_vendor
from app.modules.vendors.model import Vendor
from app.modules.vendors.profile_service import VendorProfileService

router = APIRouter()

# Configuration
UPLOAD_DIR = Path("uploads/vendors")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
LOGO_MAX_DIMENSIONS = (512, 512)
COVER_MAX_DIMENSIONS = (1200, 630)


def ensure_upload_dir():
    """Ensure upload directory exists."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def validate_image_file(file: UploadFile) -> None:
    """Validate uploaded image file."""
    # Check file extension
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Check content type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Must be an image."
        )


@router.post("/upload/logo")
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor),
) -> dict[str, Any]:
    """Upload vendor logo."""
    try:
        ensure_upload_dir()
        validate_image_file(file)

        # Read file content
        content = await file.read()
        
        # Check file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="File size too large. Max 5MB allowed."
            )

        # Generate unique filename
        file_ext = Path(file.filename or "").suffix.lower()
        unique_filename = f"logo_{vendor.vendor_id}_{uuid.uuid4().hex}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename

        # Save file
        with open(file_path, "wb") as f:
            f.write(content)

        # Update vendor profile
        service = VendorProfileService(db)
        profile = service._get_or_create_profile(vendor.vendor_id)
        profile.logo_url = f"/uploads/vendors/{unique_filename}"
        db.flush()

        return {
            "url": profile.logo_url,
            "filename": unique_filename,
            "size": len(content),
            "content_type": file.content_type,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/upload/cover")
async def upload_cover_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor),
) -> dict[str, Any]:
    """Upload vendor cover image."""
    try:
        ensure_upload_dir()
        validate_image_file(file)

        # Read file content
        content = await file.read()
        
        # Check file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="File size too large. Max 5MB allowed."
            )

        # Generate unique filename
        file_ext = Path(file.filename or "").suffix.lower()
        unique_filename = f"cover_{vendor.vendor_id}_{uuid.uuid4().hex}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename

        # Save file
        with open(file_path, "wb") as f:
            f.write(content)

        # Update vendor profile
        service = VendorProfileService(db)
        profile = service._get_or_create_profile(vendor.vendor_id)
        profile.cover_image = f"/uploads/vendors/{unique_filename}"
        db.flush()

        return {
            "url": profile.cover_image,
            "filename": unique_filename,
            "size": len(content),
            "content_type": file.content_type,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.delete("/upload/{image_type}")
async def delete_image(
    image_type: str,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor),
) -> dict[str, str]:
    """Delete vendor image (logo or cover)."""
    if image_type not in ["logo", "cover"]:
        raise HTTPException(status_code=400, detail="Invalid image type")

    try:
        service = VendorProfileService(db)
        profile = service._get_or_create_profile(vendor.vendor_id)

        # Get current image URL
        image_url = profile.logo_url if image_type == "logo" else profile.cover_image
        
        if image_url:
            # Delete file from filesystem
            file_path = Path("." + image_url)
            if file_path.exists():
                file_path.unlink()

            # Update profile
            if image_type == "logo":
                profile.logo_url = None
            else:
                profile.cover_image = None
            
            db.flush()

        return {"message": "Image deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")