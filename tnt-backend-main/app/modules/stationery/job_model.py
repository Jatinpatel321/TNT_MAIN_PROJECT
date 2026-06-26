import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class JobStatus(enum.Enum):
    SUBMITTED = "submitted"
    IN_PROGRESS = "in_progress"
    READY = "ready"
    COLLECTED = "collected"


class StationeryJob(Base):
    __tablename__ = "stationery_jobs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("stationery_services.id"), nullable=False)

    quantity = Column(Integer, nullable=False)
    file_url = Column(String, nullable=True)
    amount = Column(Integer, nullable=False, default=0)
    is_paid = Column(Boolean, nullable=False, default=False)
    razorpay_order_id = Column(String, nullable=True)
    razorpay_payment_id = Column(String, nullable=True)
    razorpay_signature = Column(String, nullable=True)

    status = Column(Enum(JobStatus, values_callable=lambda x: [e.value for e in x]), default=JobStatus.SUBMITTED)
    created_at = Column(DateTime, default=utcnow_naive)
