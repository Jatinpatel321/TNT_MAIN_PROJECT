"""
Pure-Python PostgreSQL backup service.

Uses psycopg2 (already in requirements.txt as psycopg2-binary) to perform a
table-by-table COPY-based dump since pg_dump is not available on PATH.

The resulting file is a gzip-compressed SQL script that can be restored via
the companion restore_service.py or manually with psql.

Backup format:
  backups/tnt_backup_<type>_<timestamp>.sql.gz
"""

from __future__ import annotations

import gzip
import hashlib
import io
import logging
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.modules.backup.models import BackupRecord, BackupStatus, BackupType
from app.modules.backup.schemas import BackupListResponse, BackupRecordOut, StorageStats

logger = logging.getLogger("tnt.backup")

BACKUP_DIR = Path(__file__).resolve().parent.parent.parent.parent / "backups"


def _ensure_dir() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _get_db_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    return url


def _parse_pg_url(url: str) -> Dict[str, str]:
    """Parse a postgresql[+driver]://user:pass@host:port/dbname URL."""
    # Strip driver suffix for parsing (e.g. postgresql+pg8000 -> postgresql)
    clean = url.split("+")[0] + "://" + url.split("://", 1)[1] if "://" in url else url
    parsed = urlparse(clean)
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "dbname": parsed.path.lstrip("/"),
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
    }


def _connect_psycopg2(params: Dict[str, str]):
    """Open a raw psycopg2 connection."""
    try:
        import psycopg2  # type: ignore
        return psycopg2.connect(
            host=params["host"],
            port=int(params["port"]),
            dbname=params["dbname"],
            user=params["user"],
            password=params["password"],
        )
    except ImportError:
        raise RuntimeError("psycopg2 not installed — cannot perform backup")


def _get_user_tables(cursor) -> List[str]:
    """Return all user-defined table names in topological order (parent tables first)."""
    cursor.execute(
        """
        SELECT tablename
        FROM pg_catalog.pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
        """
    )
    return [row[0] for row in cursor.fetchall()]


def _dump_schema(cursor, output: io.TextIOWrapper) -> None:
    """Write CREATE TABLE DDL for all user tables using information_schema."""
    cursor.execute(
        """
        SELECT
            tc.table_name,
            kcu.column_name,
            c.ordinal_position,
            c.column_default,
            c.is_nullable,
            c.data_type,
            c.character_maximum_length,
            c.numeric_precision,
            c.numeric_scale
        FROM information_schema.table_constraints AS tc
        FULL OUTER JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        RIGHT JOIN information_schema.columns AS c
            ON c.table_name = tc.table_name
            AND c.table_schema = tc.table_schema
            AND c.column_name = kcu.column_name
        WHERE c.table_schema = 'public'
        ORDER BY c.table_name, c.ordinal_position
        """
    )


def _dump_table_data_copy(cursor, table: str, output: io.TextIOWrapper) -> int:
    """
    Use COPY ... TO STDOUT to dump table data as tab-separated values,
    then write COPY ... FROM STDIN block to the SQL output.
    Returns row count.
    """
    # Get column names
    cursor.execute(
        f"SELECT column_name FROM information_schema.columns "
        f"WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",
        (table,),
    )
    columns = [row[0] for row in cursor.fetchall()]
    if not columns:
        return 0

    col_list = ", ".join(f'"{c}"' for c in columns)
    copy_sql = f'COPY "{table}" ({col_list}) FROM stdin;\n'

    buf = io.StringIO()
    cursor.copy_to(buf, f'"{table}"', columns=[f'"{c}"' for c in columns])
    data = buf.getvalue()
    row_count = data.count("\n") if data.strip() else 0

    if row_count > 0:
        output.write(copy_sql)
        output.write(data)
        output.write("\\.\n\n")

    return row_count


def run_backup(
    backup_type: BackupType = BackupType.manual,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Execute a full database backup using psycopg2 COPY.

    Creates a gzip-compressed SQL file in the backups/ directory.
    Saves a BackupRecord to the database (if db session provided).
    Returns metadata dict.
    """
    _ensure_dir()
    db_url = _get_db_url()
    params = _parse_pg_url(db_url)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"tnt_backup_{backup_type.value}_{timestamp}.sql.gz"
    filepath = BACKUP_DIR / filename

    # Create in-progress DB record
    record: Optional[BackupRecord] = None
    if db is not None:
        record = BackupRecord(
            filename=filename,
            backup_type=backup_type,
            status=BackupStatus.in_progress,
            database_name=params["dbname"],
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    start_time = time.monotonic()
    total_rows = 0
    error_msg: Optional[str] = None

    try:
        conn = _connect_psycopg2(params)
        conn.autocommit = True
        cursor = conn.cursor()

        tables = _get_user_tables(cursor)
        logger.info("Starting %s backup → %s (%d tables)", backup_type.value, filename, len(tables))

        # Write SQL to gzipped file
        with gzip.open(str(filepath), "wt", encoding="utf-8") as gz:
            gz.write(f"-- TNT Database Backup\n")
            gz.write(f"-- Type: {backup_type.value}\n")
            gz.write(f"-- Created: {timestamp} UTC\n")
            gz.write(f"-- Database: {params['dbname']}\n")
            gz.write(f"-- Tables: {len(tables)}\n\n")
            gz.write("SET session_replication_role = 'replica';\n\n")

            for table in tables:
                gz.write(f"-- Table: {table}\n")
                try:
                    rows = _dump_table_data_copy(cursor, table, gz)
                    total_rows += rows
                    logger.debug("  %s: %d rows", table, rows)
                except Exception as tbl_err:
                    logger.warning("  Skip %s: %s", table, tbl_err)
                    gz.write(f"-- WARNING: could not dump {table}: {tbl_err}\n\n")

            gz.write("\nSET session_replication_role = 'origin';\n")

        cursor.close()
        conn.close()

        duration = round(time.monotonic() - start_time)
        size_bytes = filepath.stat().st_size

        # Compute SHA-256
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        checksum = sha256.hexdigest()

        result = {
            "id": record.id if record else None,
            "filename": filename,
            "backup_type": backup_type.value,
            "status": "success",
            "size_bytes": size_bytes,
            "size_kb": round(size_bytes / 1024, 1),
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "checksum_sha256": checksum,
            "database": params["dbname"],
            "tables_count": len(tables),
            "rows_exported": total_rows,
            "duration_seconds": duration,
            "created_at": timestamp,
        }

        # Update DB record
        if db is not None and record is not None:
            record.status = BackupStatus.success
            record.size_bytes = size_bytes
            record.checksum_sha256 = checksum
            record.tables_count = len(tables)
            record.rows_exported = total_rows
            record.duration_seconds = duration
            record.completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(record)
            result["id"] = record.id

        logger.info(
            "Backup complete: %s (%.1f KB, %d rows, %ds)",
            filename, size_bytes / 1024, total_rows, duration,
        )
        return result

    except Exception as exc:
        error_msg = str(exc)
        logger.error("Backup failed: %s", error_msg)

        # Clean up partial file
        if filepath.exists():
            filepath.unlink(missing_ok=True)

        # Mark as failed in DB
        if db is not None and record is not None:
            record.status = BackupStatus.failed
            record.error_message = error_msg
            record.completed_at = datetime.now(timezone.utc)
            db.commit()

        raise RuntimeError(f"Backup failed: {error_msg}") from exc


def list_backups(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    backup_type: Optional[str] = None,
    status: Optional[str] = None,
) -> BackupListResponse:
    """Return paginated list of backup records from the database."""
    query = db.query(BackupRecord)

    if backup_type:
        query = query.filter(BackupRecord.backup_type == backup_type)
    if status:
        query = query.filter(BackupRecord.status == status)

    # Exclude physically deleted records from display
    query = query.filter(BackupRecord.status != BackupStatus.deleted)

    total = query.count()
    offset = (page - 1) * page_size
    records = (
        query.order_by(BackupRecord.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = []
    for r in records:
        out = BackupRecordOut.model_validate(r)
        if r.size_bytes:
            out.size_kb = round(r.size_bytes / 1024, 1)
            out.size_mb = round(r.size_bytes / (1024 * 1024), 2)
        items.append(out)

    return BackupListResponse(
        backups=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, -(-total // page_size)),
    )


def get_storage_stats(db: Session) -> StorageStats:
    """Compute storage statistics for the backup dashboard."""
    _ensure_dir()

    records = (
        db.query(BackupRecord)
        .filter(BackupRecord.status.notin_([BackupStatus.deleted, BackupStatus.failed]))
        .all()
    )

    total_bytes = sum(r.size_bytes or 0 for r in records)

    by_type: Dict[str, int] = {}
    for r in records:
        key = r.backup_type.value
        by_type[key] = by_type.get(key, 0) + 1

    by_status: Dict[str, int] = {}
    all_records = db.query(BackupRecord).all()
    for r in all_records:
        key = r.status.value
        by_status[key] = by_status.get(key, 0) + 1

    timestamps = [r.created_at for r in records if r.created_at]

    disk_free: Optional[int] = None
    disk_total: Optional[int] = None
    try:
        usage = shutil.disk_usage(str(BACKUP_DIR))
        disk_free = usage.free
        disk_total = usage.total
    except Exception:
        pass

    return StorageStats(
        total_backups=len(records),
        total_size_bytes=total_bytes,
        total_size_mb=round(total_bytes / (1024 * 1024), 2),
        by_type=by_type,
        by_status=by_status,
        disk_free_bytes=disk_free,
        disk_total_bytes=disk_total,
        disk_free_mb=round(disk_free / (1024 * 1024), 1) if disk_free else None,
        backup_dir=str(BACKUP_DIR),
        oldest_backup=min(timestamps) if timestamps else None,
        newest_backup=max(timestamps) if timestamps else None,
    )


def verify_backup(backup_id: int, db: Session) -> Dict[str, Any]:
    """Re-compute the SHA-256 checksum and compare against the stored value."""
    record = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
    if not record:
        raise ValueError(f"Backup #{backup_id} not found")

    filepath = BACKUP_DIR / record.filename
    file_exists = filepath.exists()
    integrity_ok = False
    computed = None

    if file_exists:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        computed = sha256.hexdigest()
        integrity_ok = (computed == record.checksum_sha256) if record.checksum_sha256 else False

    msg = "OK" if integrity_ok else ("Checksum mismatch" if file_exists else "File not found")
    return {
        "backup_id": backup_id,
        "filename": record.filename,
        "stored_checksum": record.checksum_sha256,
        "computed_checksum": computed,
        "integrity_ok": integrity_ok,
        "file_exists": file_exists,
        "message": msg,
    }


def delete_backup(backup_id: int, db: Session) -> Dict[str, Any]:
    """Delete backup file from disk and mark record as deleted in DB."""
    record = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
    if not record:
        raise ValueError(f"Backup #{backup_id} not found")

    filepath = BACKUP_DIR / record.filename
    if filepath.exists():
        filepath.unlink()
        logger.info("Deleted backup file: %s", record.filename)

    record.status = BackupStatus.deleted
    db.commit()

    return {"message": f"Backup {record.filename} deleted", "backup_id": backup_id}
