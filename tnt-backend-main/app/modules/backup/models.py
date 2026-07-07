"""
BackupRecord SQLAlchemy model.

Stores metadata for every backup operation (manual, daily, weekly) in the
``backup_records`` table so the history is fully queryable and survives
filesystem changes.
"""

import enum

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    func,
)

from app.database.base import Base


class BackupType(str, enum.Enum):
    manual = "manual"
    daily = "daily"
    weekly = "weekly"


class BackupStatus(str, enum.Enum):
    success = "success"
    failed = "failed"
    in_progress = "in_progress"
    deleted = "deleted"


class BackupRecord(Base):
    """Persistent metadata record for a single backup operation."""

    __tablename__ = "backup_records"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, nullable=False, index=True)
    backup_type = Column(
        String(20),
        nullable=False,
        default=BackupType.manual,
    )
    status = Column(
        String(20),
        nullable=False,
        default=BackupStatus.in_progress,
    )
    size_bytes = Column(BigInteger, nullable=True)
    checksum_sha256 = Column(String(64), nullable=True)
    database_name = Column(String(128), nullable=True)
    tables_count = Column(Integer, nullable=True)
    rows_exported = Column(BigInteger, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
