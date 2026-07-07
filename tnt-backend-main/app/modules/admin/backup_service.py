"""
Backup service (admin module) — compatibility shim.

The full backup implementation has moved to app.modules.backup.backup_service.
This module re-exports run_backup() and list_backups() for backward-compat
with the legacy admin router routes (/admin/backup and /admin/backups).
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("tnt.admin.backup")

# Re-export the real implementation
from app.modules.backup.backup_service import (  # noqa: F401
    run_backup,
    list_backups as _list_backups,
    BACKUP_DIR,
)
from app.modules.backup.models import BackupType


def run_backup_legacy() -> dict[str, Any]:
    """
    Legacy shim used by the old /admin/backup route.
    Calls the new pure-Python backup implementation.
    """
    return run_backup(backup_type=BackupType.manual, db=None)


def list_backups() -> list[dict[str, Any]]:
    """
    Legacy shim: returns backup metadata from the filesystem
    (no DB session required, for backward compat).
    """
    from datetime import datetime, timezone

    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    backups = []
    for f in sorted(Path(BACKUP_DIR).iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.suffix not in (".dump", ".sql", ".gz"):
            continue
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        backups.append(
            {
                "filename": f.name,
                "size_bytes": f.stat().st_size,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                "created_at": mtime.isoformat(),
            }
        )
    return backups
