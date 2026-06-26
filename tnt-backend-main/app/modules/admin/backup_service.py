"""
Backup service — wraps scripts/backup_db.py for the admin API.

Produces .dump files (pg_dump custom format) in the project root's
``backups/`` directory.
"""
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("tnt.admin.backup")

BACKUP_DIR = Path(__file__).resolve().parent.parent.parent / "backups"


def _ensure_dir():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _get_db_url() -> str:
    """Read DATABASE_URL from the environment (already loaded by settings/config)."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return url


def _parse_pg_url(url: str) -> dict:
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "dbname": parsed.path.lstrip("/"),
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
    }


def run_backup() -> dict[str, Any]:
    """Execute pg_dump and save a .dump file. Return metadata."""
    _ensure_dir()
    db_url = _get_db_url()
    params = _parse_pg_url(db_url)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"tnt_backup_{timestamp}.dump"
    filepath = BACKUP_DIR / filename

    env = os.environ.copy()
    env["PGPASSWORD"] = params["password"]

    cmd = [
        "pg_dump",
        "--host", params["host"],
        "--port", params["port"],
        "--username", params["user"],
        "--dbname", params["dbname"],
        "--no-password",
        "--format", "custom",
        "--file", str(filepath),
    ]

    logger.info("starting backup → %s", filename)
    try:
        result = subprocess.run(
            cmd, env=env, check=True, capture_output=True, text=True, timeout=300
        )
    except subprocess.TimeoutExpired:
        logger.error("backup timed out after 300s")
        raise RuntimeError("Backup timed out")
    except subprocess.CalledProcessError as e:
        logger.error("pg_dump failed: %s", e.stderr)
        raise RuntimeError(f"pg_dump failed: {e.stderr}")

    size_kb = filepath.stat().st_size / 1024
    logger.info("backup complete %s (%.1f KB)", filename, size_kb)

    return {
        "filename": filename,
        "path": str(filepath),
        "size_bytes": filepath.stat().st_size,
        "size_kb": round(size_kb, 1),
        "size_mb": round(size_kb / 1024, 2),
        "created_at": timestamp,
        "database": params["dbname"],
    }


def list_backups() -> list[dict[str, Any]]:
    """Return metadata for every .dump file in the backups directory."""
    _ensure_dir()
    backups = []
    for f in sorted(BACKUP_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.suffix not in (".dump", ".sql", ".gz"):
            continue
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        backups.append({
            "filename": f.name,
            "size_bytes": f.stat().st_size,
            "size_kb": round(f.stat().st_size / 1024, 1),
            "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
            "created_at": mtime.isoformat(),
        })
    return backups
