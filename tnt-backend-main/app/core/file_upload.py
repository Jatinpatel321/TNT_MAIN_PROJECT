import os
import uuid

from fastapi import HTTPException, UploadFile

UPLOAD_DIR = "uploads/menu"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
# Extension fallback used when python-magic is not installed
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _detect_mime(file_bytes: bytes) -> str:
    """Detect MIME type from file content, not header. Falls back to 'unknown'."""
    try:
        import magic
        return magic.from_buffer(file_bytes[:2048], mime=True)
    except ImportError:
        return "unknown"


def _extension_allowed(filename: str) -> bool:
    ext = os.path.splitext(filename)[-1].lower()
    return ext in ALLOWED_EXTENSIONS


def save_menu_image(file: UploadFile) -> str:
    # Read file content first for size and MIME checks
    file_bytes = file.file.read()

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds maximum size of 5 MB")

    detected_mime = _detect_mime(file_bytes)
    if detected_mime == "unknown":
        # python-magic not available — fall back to extension check
        if not _extension_allowed(file.filename or ""):
            raise HTTPException(
                status_code=415,
                detail="Unsupported file type. Only JPEG, PNG, WebP, and GIF are allowed.",
            )
    elif detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type detected: {detected_mime}. Only images are accepted.",
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "upload")[-1].lower() or ".bin"
    filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)

    return f"/uploads/menu/{filename}"
