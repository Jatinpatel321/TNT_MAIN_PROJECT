from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class ShadowLog(Base):
    """Stores shadow logging entries comparing ML model vs heuristic predictions.

    Used to evaluate model quality in production without altering user-facing outputs.
    """

    __tablename__ = "shadow_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    predicted_model = Column(Float, nullable=True)
    predicted_heuristic = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utcnow_naive, index=True)
