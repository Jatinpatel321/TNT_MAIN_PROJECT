from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Text
from app.database.base import Base


class RetrainingLog(Base):
    __tablename__ = "ml_retraining_logs"

    id = Column(Integer, primary_key=True, index=True)
    model_type = Column(String(100), nullable=False, index=True)
    triggered_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    status = Column(String(50), nullable=False)  # "success", "failed", "insufficient_data"
    version_id = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
