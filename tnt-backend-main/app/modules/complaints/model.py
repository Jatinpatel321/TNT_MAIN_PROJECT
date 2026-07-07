import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class ComplaintCategory(enum.Enum):
    LATE_ORDER = "late_order"
    WRONG_ITEM = "wrong_item"
    QUALITY_ISSUE = "quality_issue"
    OTHER = "other"


class ComplaintStatus(enum.Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to_vendor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    category = Column(Enum(ComplaintCategory, values_callable=lambda x: [e.value for e in x]), nullable=False)
    status = Column(Enum(ComplaintStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=ComplaintStatus.OPEN)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)
