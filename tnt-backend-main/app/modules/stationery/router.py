from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.file_upload_stationery import save_stationery_file
from app.core.security import get_current_user, require_role
from app.modules.notifications.service import notify_user
from app.modules.stationery.job_model import JobStatus, StationeryJob
from app.modules.stationery.service_model import StationeryService
from app.modules.users.model import User

router = APIRouter(prefix="/stationery", tags=["Stationery"])


@router.post("/services")
def add_service(
    name: str = Form(...),
    price_per_unit: int = Form(...),
    unit: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor"))
):
    vendor = db.query(User).filter(User.id == user["id"]).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if (vendor.vendor_type or "food").lower() != "stationery":
        raise HTTPException(status_code=403, detail="Only stationery vendors can manage stationery services")

    service = StationeryService(
        vendor_id=vendor.id,
        name=name,
        price_per_unit=price_per_unit,
        unit=unit
    )

    db.add(service)
    db.commit()
    db.refresh(service)

    return service



@router.post("/jobs")
def submit_job(
    service_id: int = Form(...),
    quantity: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    student = db.query(User).filter(User.id == user["id"]).first()
    if not student:
        raise HTTPException(status_code=404, detail="User not found")

    service = db.query(StationeryService).filter(
        StationeryService.id == service_id,
        StationeryService.is_available == True
    ).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found or unavailable")

    file_url = save_stationery_file(file)

    job = StationeryJob(
        user_id=student.id,
        vendor_id=service.vendor_id,
        service_id=service.id,
        quantity=quantity,
        file_url=file_url
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    vendor = db.query(User).filter(User.id == service.vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    notify_user(
        user_id=vendor.id,
        phone=vendor.phone,
        title="New Stationery Job",
        message="A new stationery job has been submitted.",
        db=db
    )

    return job



@router.post("/jobs/{job_id}/status")
def update_job_status(
    job_id: int,
    status: JobStatus,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor"))
):
    vendor = db.query(User).filter(User.id == user["id"]).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if (vendor.vendor_type or "food").lower() != "stationery":
        raise HTTPException(status_code=403, detail="Only stationery vendors can update stationery jobs")

    job = db.query(StationeryJob).filter(
        StationeryJob.id == job_id,
        StationeryJob.vendor_id == vendor.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = status
    db.commit()

    if status == JobStatus.READY:
        student = db.query(User).filter(User.id == job.user_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        notify_user(
            user_id=student.id,
            phone=student.phone,
            title="Job Ready",
            message="Your stationery job is ready for payment and pickup.",
            db=db
        )

    return {"message": "Job status updated"}
