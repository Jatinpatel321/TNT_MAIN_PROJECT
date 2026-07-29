from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSON

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class DriftReport(Base):
    """Database model for storing data and prediction drift reports."""

    __tablename__ = "drift_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_type = Column(String(100), nullable=False, index=True)
    check_type = Column(String(50), nullable=False, index=True)  # 'data_drift' or 'prediction_drift'
    has_drift = Column(Boolean, nullable=False, default=False)
    report_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False, index=True)
