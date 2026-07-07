import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class PaymentStatus(enum.Enum):
    INITIATED = "initiated"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class RefundStatus(enum.Enum):
    """Lifecycle of a refund after it has been initiated with the gateway."""
    PENDING = "pending"        # refund requested, not yet acknowledged
    PROCESSING = "processing"  # gateway is processing (money in transit)
    COMPLETED = "completed"    # funds settled back to the customer


class RefundRequestStatus(enum.Enum):
    """Admin approval lifecycle for a customer-initiated refund request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RefundRequest(Base):
    """Customer-initiated refund request that an admin approves or rejects.

    Approval executes the actual gateway refund via the existing refund flow;
    the status transitions form the refund timeline.
    """
    __tablename__ = "refund_requests"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)  # rupees
    reason = Column(String, nullable=True)
    status = Column(
        Enum(RefundRequestStatus, values_callable=lambda x: [e.value for e in x]),
        default=RefundRequestStatus.PENDING,
        nullable=False,
    )
    decision_note = Column(String, nullable=True)
    decided_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    requested_at = Column(DateTime, default=utcnow_naive)
    decided_at = Column(DateTime, nullable=True)


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

    amount = Column(Numeric(10, 2), nullable=False)  # rupees
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

    # Auto refund ETA — set when a refund is initiated. ``refund_status`` holds a
    # RefundStatus value; ``estimated_refund_at`` is the AI-estimated completion
    # time surfaced to the user for progress tracking.
    refund_status = Column(String, nullable=True)
    estimated_refund_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=utcnow_naive)

    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "idempotency_key",
            name="uq_payment_order_idempotency",
        ),
    )
