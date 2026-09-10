"""Secure file upload helper for stationery printing documents.

Enforces:
1. Strict PDF magic-byte validation (b"%PDF-") independently of client MIME header.
2. Hard streaming byte limit (25 MB max) to prevent memory exhaustion and disk fill attacks.
3. Private storage in `secure_uploads/stationery` outside public static file trees.
4. Clean rollback of partial files on validation or limit failure.
"""

from __future__ import annotations

import os
import uuid
from fastapi import HTTPException, UploadFile, status

# Private directory outside public static mounts
SECURE_UPLOAD_DIR = os.path.join(os.getcwd(), "secure_uploads", "stationery")
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
CHUNK_SIZE = 64 * 1024  # 64 KB chunks
PDF_MAGIC_BYTES = b"%PDF"


def save_stationery_file(file: UploadFile) -> str:
    """Save customer stationery PDF securely with size and content verification.

    Returns an internal document retrieval path scoped to authorized routes:
      f"/stationery/jobs/document/{filename}"
    """
    if file.content_type and file.content_type.lower() not in ["application/pdf", "application/x-pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents are allowed",
        )

    os.makedirs(SECURE_UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4()}.pdf"
    file_path = os.path.join(SECURE_UPLOAD_DIR, filename)

    total_bytes = 0
    first_chunk = True

    try:
        with open(file_path, "wb") as f:
            while True:
                chunk = file.file.read(CHUNK_SIZE)
                if not chunk:
                    break

                # Validate magic bytes on first chunk
                if first_chunk:
                    first_chunk = False
                    if not chunk.startswith(PDF_MAGIC_BYTES):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid file: content does not match genuine PDF format",
                        )

                total_bytes += len(chunk)
                if total_bytes > MAX_FILE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File size exceeds maximum allowable limit of 25MB",
                    )

                f.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file uploaded",
            )

    except Exception:
        # Clean up partial file on failure
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        raise

    return f"/stationery/jobs/document/{filename}"
