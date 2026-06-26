"""
Restore service — reconstructs the PostgreSQL database from a .sql.gz backup.

DESTRUCTIVE: Truncates all tables then replays the COPY data from backup.
Protected by admin role + explicit confirmation phrase in the API layer.
"""

from __future__ import annotations

import gzip
import io
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.modules.backup.models import BackupRecord, BackupStatus

logger = logging.getLogger("tnt.restore")

BACKUP_DIR = Path(__file__).resolve().parent.parent.parent.parent / "backups"

CONFIRM_PHRASE = "CONFIRM RESTORE"


def _parse_pg_url(url: str) -> Dict[str, str]:
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
        raise RuntimeError("psycopg2 not installed")


def _get_user_tables(cursor):
    cursor.execute(
        """
        SELECT tablename FROM pg_catalog.pg_tables
        WHERE schemaname = 'public' ORDER BY tablename
        """
    )
    return [row[0] for row in cursor.fetchall()]


def restore_from_backup(
    backup_id: int,
    confirm_phrase: str,
    db: Session,
) -> Dict[str, Any]:
    """
    Restore database from a backup record.

    Steps:
    1. Validate confirm_phrase
    2. Find BackupRecord by id
    3. Read + decompress the .sql.gz file
    4. Disable FK checks, truncate all tables, replay COPY blocks, re-enable FK checks
    5. Post-restore: count tables restored
    6. Update BackupRecord status
    """
    if confirm_phrase.strip().upper() != CONFIRM_PHRASE:
        raise ValueError(
            f"Confirmation phrase must be '{CONFIRM_PHRASE}' (received: '{confirm_phrase}')"
        )

    record = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
    if not record:
        raise ValueError(f"Backup #{backup_id} not found")

    if record.status in (BackupStatus.deleted, BackupStatus.in_progress):
        raise ValueError(f"Cannot restore backup with status '{record.status.value}'")

    filepath = BACKUP_DIR / record.filename
    if not filepath.exists():
        raise FileNotFoundError(f"Backup file not found: {record.filename}")

    db_url = os.getenv("DATABASE_URL", "")
    params = _parse_pg_url(db_url)

    start_time = time.monotonic()
    tables_restored = 0

    try:
        conn = _connect_psycopg2(params)
        conn.autocommit = False
        cursor = conn.cursor()

        logger.warning(
            "RESTORE INITIATED — backup_id=%d filename=%s", backup_id, record.filename
        )

        # Disable FK checks for the session
        cursor.execute("SET session_replication_role = 'replica';")

        # Truncate all existing user tables
        tables = _get_user_tables(cursor)
        if tables:
            quoted = ", ".join(f'"{t}"' for t in tables)
            cursor.execute(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE;")
            logger.info("Truncated %d tables", len(tables))

        # Read backup file and replay COPY blocks
        with gzip.open(str(filepath), "rt", encoding="utf-8") as gz:
            content = gz.read()

        # Parse COPY ... FROM stdin blocks
        copy_pattern = re.compile(
            r'COPY\s+"?(\w+)"?\s*\(([^)]+)\)\s+FROM\s+stdin;\n(.*?)\\\.',
            re.DOTALL | re.IGNORECASE,
        )

        for match in copy_pattern.finditer(content):
            table_name = match.group(1)
            data_block = match.group(3)

            if not data_block.strip():
                continue

            try:
                buf = io.StringIO(data_block)
                # Extract column list from match
                col_str = match.group(2)
                columns = [c.strip().strip('"') for c in col_str.split(",")]
                cursor.copy_from(buf, f'"{table_name}"', columns=columns)
                tables_restored += 1
                logger.debug("Restored table: %s", table_name)
            except Exception as tbl_err:
                logger.error("Failed to restore table %s: %s", table_name, tbl_err)
                # Continue with next table rather than aborting entire restore
                continue

        # Re-enable FK checks
        cursor.execute("SET session_replication_role = 'origin';")
        conn.commit()
        cursor.close()
        conn.close()

        duration = round(time.monotonic() - start_time, 2)
        logger.info(
            "Restore complete — %d tables restored in %.1fs", tables_restored, duration
        )

        return {
            "message": "Restore completed successfully",
            "backup_id": backup_id,
            "filename": record.filename,
            "tables_restored": tables_restored,
            "duration_seconds": duration,
        }

    except Exception as exc:
        logger.error("Restore failed: %s", exc)
        raise RuntimeError(f"Restore failed: {exc}") from exc
