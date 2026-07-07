from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.stationery.job_model import JobStatus, StationeryJob
from app.modules.stationery.service_model import StationeryService


def mark_job_ready(job_id: int, vendor_id: int, db: Session):
    job = db.query(StationeryJob).filter(
        StationeryJob.id == job_id,
        StationeryJob.vendor_id == vendor_id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    service = db.query(StationeryService).filter(
        StationeryService.id == job.service_id
    ).first()

    job.amount = job.quantity * service.price_per_unit
    job.status = JobStatus.READY

    db.commit()
    return job
