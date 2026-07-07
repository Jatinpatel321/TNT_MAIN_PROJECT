"""
Pydantic schemas for the Backup & Recovery module.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.modules.backup.models import BackupStatus, BackupType


# ── Backup Record Schemas ──────────────────────────────────────────────────

class BackupRecordOut(BaseModel):
    id: int
    filename: str
    backup_type: BackupType
    status: BackupStatus
    size_bytes: Optional[int] = None
    size_kb: Optional[float] = None
    size_mb: Optional[float] = None
    checksum_sha256: Optional[str] = None
    database_name: Optional[str] = None
    tables_count: Optional[int] = None
    rows_exported: Optional[int] = None
    duration_seconds: Optional[int] = None
    error_message: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_sizes(cls, obj: Any) -> "BackupRecordOut":
        data = BackupRecordOut.model_validate(obj)
        if obj.size_bytes:
            data.size_kb = round(obj.size_bytes / 1024, 1)
            data.size_mb = round(obj.size_bytes / (1024 * 1024), 2)
        return data


class BackupListResponse(BaseModel):
    backups: List[BackupRecordOut]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Restore Schemas ────────────────────────────────────────────────────────

class RestoreRequest(BaseModel):
    backup_id: int = Field(..., description="ID of the BackupRecord to restore")
    confirm_phrase: str = Field(..., description="Must be 'CONFIRM RESTORE' to proceed")


class RestoreResponse(BaseModel):
    message: str
    backup_id: int
    filename: str
    tables_restored: int
    duration_seconds: float


# ── Storage Schemas ────────────────────────────────────────────────────────

class StorageStats(BaseModel):
    total_backups: int
    total_size_bytes: int
    total_size_mb: float
    by_type: dict
    by_status: dict
    disk_free_bytes: Optional[int] = None
    disk_total_bytes: Optional[int] = None
    disk_free_mb: Optional[float] = None
    backup_dir: str
    oldest_backup: Optional[datetime] = None
    newest_backup: Optional[datetime] = None


# ── Scheduler Schemas ──────────────────────────────────────────────────────

class SchedulerJobInfo(BaseModel):
    job_id: str
    name: str
    next_run_time: Optional[datetime] = None
    trigger: str


class SchedulerStatus(BaseModel):
    running: bool
    jobs: List[SchedulerJobInfo]


# ── Integrity Verification ─────────────────────────────────────────────────

class VerifyResponse(BaseModel):
    backup_id: int
    filename: str
    stored_checksum: Optional[str]
    computed_checksum: Optional[str]
    integrity_ok: bool
    file_exists: bool
    message: str
