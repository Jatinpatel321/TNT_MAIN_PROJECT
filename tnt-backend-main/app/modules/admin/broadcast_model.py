from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, default="info")  # info | warning | critical
    audience = Column(String(50), nullable=False, default="all")   # all | faculty | vendor_customers
    vendor_id = Column(Integer, nullable=True)                     # for vendor_customers filter
    sent_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)
