"""Stationery printer monitoring + print cost matrix models."""

from __future__ import annotations

import enum

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint,
)

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class PrinterStatus(enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class Printer(Base):
    """A physical printer at a stationery stall, with live telemetry.

    Telemetry (queue_depth, ink_level_pct, paper_count, status) is updated by a
    printer agent or the admin; health is derived on read from these fields.
    """
    __tablename__ = "printers"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # null = campus-wide
    name = Column(String(120), nullable=False)
    location = Column(String(200), nullable=True)
    model = Column(String(120), nullable=True)

    status = Column(
        Enum(PrinterStatus, values_callable=lambda x: [e.value for e in x]),
        default=PrinterStatus.ONLINE, nullable=False,
    )
    queue_depth = Column(Integer, default=0, nullable=False)          # jobs waiting
    ink_level_pct = Column(Integer, default=100, nullable=False)      # 0-100
    paper_count = Column(Integer, default=0, nullable=False)          # sheets remaining
    capacity_pages_per_hour = Column(Integer, default=600, nullable=False)

    last_seen_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class PrintCostMatrix(Base):
    """Per-vendor (or global) price overrides for print jobs.

    A NULL vendor_id row is the campus-wide default for that
    (print_type, paper_size, duplex) combination.
    """
    __tablename__ = "print_cost_matrix"
    __table_args__ = (
        UniqueConstraint("vendor_id", "print_type", "paper_size", "duplex", name="uq_print_cost_combo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    print_type = Column(String(20), nullable=False)   # bw | color
    paper_size = Column(String(20), nullable=False)   # A4 | A3
    duplex = Column(Boolean, default=False, nullable=False)
    price_per_page_paise = Column(Integer, nullable=False)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)
