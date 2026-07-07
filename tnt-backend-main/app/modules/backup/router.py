"""
Backup & Recovery API router.

All endpoints require the ``admin`` role.

Routes:
  POST   /admin/backup/run            Trigger manual backup
  GET    /admin/backups               List backups (paginated + filtered)
  GET    /admin/backups/{id}          Single backup detail
  DELETE /admin/backups/{id}          Delete backup file + record
  POST   /admin/backup/restore        Trigger restore (destructive)
  GET    /admin/backup/storage        Storage stats
  GET    /admin/backup/scheduler      Scheduler status & next run times
  GET    /admin/backup/verify/{id}    Re-verify backup checksum
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.database.session import get_db
from app.modules.backup import backup_service, restore_service
from app.modules.backup.backup_scheduler import get_scheduler_status
from app.modules.backup.models import BackupType
from app.modules.backup.schemas import (
    BackupListResponse,
    BackupRecordOut,
    RestoreRequest,
    RestoreResponse,
    SchedulerStatus,
    StorageStats,
    VerifyResponse,
)

router = APIRouter(prefix="/admin/backup", tags=["Backup & Recovery"])

# ── Manual Backup ──────────────────────────────────────────────────────────


@router.post("/run", summary="Trigger a manual database backup")
def trigger_manual_backup(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """
    Runs a full pure-Python COPY-based PostgreSQL backup.
    File saved as ``backups/tnt_backup_manual_<timestamp>.sql.gz``.
    """
    try:
        result = backup_service.run_backup(backup_type=BackupType.manual, db=db)
        return {"message": "Backup completed successfully", "backup": result}
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Legacy endpoint compatibility (existing admin UI uses POST /admin/backup) ──


@router.post("", summary="Trigger a backup (legacy alias)", include_in_schema=False)
def trigger_backup_legacy(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    return trigger_manual_backup(db=db, user=user)


# ── List Backups ───────────────────────────────────────────────────────────


@router.get("s", response_model=BackupListResponse, summary="List all backup records")
def list_backups(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    backup_type: Optional[str] = Query(None, description="Filter by type: manual, daily, weekly"),
    status: Optional[str] = Query(None, description="Filter by status: success, failed"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """Return paginated backup history from the database."""
    return backup_service.list_backups(
        db=db, page=page, page_size=page_size, backup_type=backup_type, status=status
    )


# ── Single Backup Detail ───────────────────────────────────────────────────


@router.get("s/{backup_id}", response_model=BackupRecordOut, summary="Get backup detail")
def get_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    from app.modules.backup.models import BackupRecord

    record = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Backup #{backup_id} not found")

    out = BackupRecordOut.model_validate(record)
    if record.size_bytes:
        out.size_kb = round(record.size_bytes / 1024, 1)
        out.size_mb = round(record.size_bytes / (1024 * 1024), 2)
    return out


# ── Delete Backup ──────────────────────────────────────────────────────────


@router.delete("s/{backup_id}", summary="Delete backup file and record")
def delete_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    try:
        return backup_service.delete_backup(backup_id=backup_id, db=db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Restore ────────────────────────────────────────────────────────────────


@router.post("/restore", response_model=RestoreResponse, summary="Restore database from backup")
def restore_backup(
    payload: RestoreRequest,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """
    **DESTRUCTIVE** — Truncates all tables and restores from the selected backup.

    The ``confirm_phrase`` field must be exactly ``CONFIRM RESTORE``.
    """
    try:
        result = restore_service.restore_from_backup(
            backup_id=payload.backup_id,
            confirm_phrase=payload.confirm_phrase,
            db=db,
        )
        return RestoreResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Storage Stats ──────────────────────────────────────────────────────────


@router.get("/storage", response_model=StorageStats, summary="Get backup storage statistics")
def get_storage_stats(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """Returns total backup count, storage used, disk space, and breakdown by type/status."""
    return backup_service.get_storage_stats(db=db)


# ── Scheduler Status ───────────────────────────────────────────────────────


@router.get("/scheduler", summary="Get scheduler status and next run times")
def get_scheduler(
    user=Depends(require_role("admin")),
):
    """Returns whether the scheduler is running and next run times for daily/weekly jobs."""
    return get_scheduler_status()


# ── Integrity Verification ─────────────────────────────────────────────────


@router.get("/verify/{backup_id}", response_model=VerifyResponse, summary="Verify backup integrity")
def verify_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """
    Re-computes the SHA-256 checksum of the backup file and compares it
    against the stored value. Returns integrity status.
    """
    try:
        result = backup_service.verify_backup(backup_id=backup_id, db=db)
        return VerifyResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
