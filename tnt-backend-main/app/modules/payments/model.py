import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class PaymentStatus(enum.Enum):
    INITIATED = "initiated"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    # Exactly one of order_id / stationery_job_id must be set.
    # Both are nullable at the DB level so that either flow can create a
    # Payment row; application logic enforces that at least one is present.
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    stationery_job_id = Column(
        Integer, ForeignKey("stationery_jobs.id"), nullable=True, index=True
    )

    amount = Column(Integer, nullable=False)  # paise
    status = Column(Enum(PaymentStatus, values_callable=lambda x: [e.value for e in x]), default=PaymentStatus.INITIATED)

    # Caller-supplied UUID that makes the initiate endpoint idempotent.
    # A (order_id, idempotency_key) pair is globally unique; a second request
    # with the same pair returns the already-created payment without hitting
    # Razorpay again.
    idempotency_key = Column(String, nullable=True, index=True)

    razorpay_order_id = Column(String, nullable=True)
    razorpay_payment_id = Column(String, nullable=True)
    razorpay_signature = Column(String, nullable=True)

    razorpay_refund_id = Column(String, nullable=True)
    refunded_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=utcnow_naive)

    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "idempotency_key",
            name="uq_payment_order_idempotency",
        ),
    )
