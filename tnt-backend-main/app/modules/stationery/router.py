import re
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.file_upload_stationery import save_stationery_file
from app.core.security import get_current_user, require_role
from app.modules.notifications.service import notify_user
from app.modules.stationery.job_model import JobStatus, PaperSize, PrintType, StationeryJob
from app.modules.stationery.service_model import StationeryService
from app.modules.users.model import User

router = APIRouter(prefix="/stationery", tags=["Stationery"])

PAGE_RANGE_PATTERN = re.compile(r"^[0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*$")


@router.get("/jobs")
def list_jobs(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """Admin: list all stationery print jobs with student/vendor/service context."""
    jobs = db.query(StationeryJob).order_by(StationeryJob.created_at.desc()).all()
    result = []
    for job in jobs:
        student = db.query(User).filter(User.id == job.user_id).first()
        vendor = db.query(User).filter(User.id == job.vendor_id).first()
        service = db.query(StationeryService).filter(StationeryService.id == job.service_id).first()
        result.append({
            "id": job.id,
            "user_id": job.user_id,
            "user_name": (student.full_name or student.name) if student else None,
            "vendor_id": job.vendor_id,
            "vendor_name": (vendor.full_name or vendor.name) if vendor else None,
            "service_name": service.name if service else None,
            "file_url": job.file_url,
            "quantity": job.quantity,
            "print_type": job.print_type.value if hasattr(job.print_type, "value") else job.print_type,
            "paper_size": job.paper_size.value if hasattr(job.paper_size, "value") else job.paper_size,
            "duplex": job.duplex,
            "page_range": job.page_range,
            "notes": job.notes,
            "status": job.status.value if hasattr(job.status, "value") else job.status,
            "payment_status": "paid" if job.is_paid else "unpaid",
            "total_amount": float(job.amount or 0),
            "submitted_at": job.created_at.isoformat() if job.created_at else None,
        })
    return result


@router.get("/services")
def list_services(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """List stationery services.

    Admins see every vendor's services; a stationery vendor sees only their own.
    """
    query = db.query(StationeryService)
    if (user.get("role") or "").lower() == "vendor":
        query = query.filter(StationeryService.vendor_id == user["id"])

    services = query.order_by(StationeryService.created_at.desc()).all()

    vendor_ids = {s.vendor_id for s in services}
    vendors = (
        db.query(User).filter(User.id.in_(vendor_ids)).all() if vendor_ids else []
    )
    vendor_names = {v.id: (v.full_name or v.name) for v in vendors}

    return [
        {
            "id": s.id,
            "vendor_id": s.vendor_id,
            "vendor_name": vendor_names.get(s.vendor_id),
            "name": s.name,
            "service_type": s.service_type,
            "description": s.description,
            "price_per_page": s.price_per_page,
            "price_per_unit": s.price_per_unit,
            "unit": s.unit,
            "max_capacity": s.max_capacity,
            "current_load": s.current_load,
            "is_available": s.is_available,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in services
    ]


@router.post("/services")
def add_service(
    name: str = Form(...),
    price_per_unit: float = Form(...),
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
    print_type: Literal["bw", "color"] = Form("bw"),
    paper_size: Literal["A4", "A3"] = Form("A4"),
    duplex: bool = Form(False),
    page_range: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
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

    page_range = page_range.strip() if page_range else None
    if page_range and not PAGE_RANGE_PATTERN.match(page_range):
        raise HTTPException(
            status_code=400,
            detail="page_range must look like '1-5' or '1,3,5-8'",
        )
    notes = notes.strip() if notes else None
    if notes and len(notes) > 1000:
        raise HTTPException(status_code=400, detail="notes must be at most 1000 characters")

    file_url = save_stationery_file(file)

    job = StationeryJob(
        user_id=student.id,
        vendor_id=service.vendor_id,
        service_id=service.id,
        quantity=quantity,
        file_url=file_url,
        print_type=PrintType(print_type),
        paper_size=PaperSize(paper_size),
        duplex=duplex,
        page_range=page_range,
        notes=notes,
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
