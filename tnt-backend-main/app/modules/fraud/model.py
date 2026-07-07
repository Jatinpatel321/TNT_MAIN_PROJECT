from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, index=True)  # "low", "medium", "high", "critical"
    score = Column(Float, nullable=False, default=0.0)
    description = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="pending", index=True)  # "pending", "resolved", "false_positive"
    resolution_notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utcnow_naive, index=True)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    user = relationship("User", foreign_keys=[user_id])
    vendor = relationship("User", foreign_keys=[vendor_id])
    order = relationship("Order", foreign_keys=[order_id])
