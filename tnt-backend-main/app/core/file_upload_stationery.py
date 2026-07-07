import os
import uuid

from fastapi import HTTPException, UploadFile

UPLOAD_DIR = "uploads/stationery"


def save_stationery_file(file: UploadFile) -> str:
    if file.content_type not in ["application/pdf"]:
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    filename = f"{uuid.uuid4()}.pdf"
    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as f:
        f.write(file.file.read())

    return f"/uploads/stationery/{filename}"
