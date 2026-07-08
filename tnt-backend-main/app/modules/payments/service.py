import hashlib
import hmac
import os

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.db_transaction import transactional
from app.core.observability import observability
from app.core.razorpay_client import client
from app.core.time_utils import utcnow_naive
from app.modules.ledger.model import LedgerSource, LedgerType
from app.modules.ledger.service import add_ledger_entry
from app.modules.notifications.service import notify_user
from app.modules.orders.model import Order, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.users.model import User


def _payment_owner_id(payment: Payment, db: Session) -> int | None:
    """Return the user_id that owns *payment* regardless of payment type."""
    if payment.order_id is not None:
        order = db.query(Order).filter(Order.id == payment.order_id).first()
        return order.user_id if order else None
    if payment.stationery_job_id is not None:
        from app.modules.stationery.job_model import StationeryJob
        job = db.query(StationeryJob).filter(StationeryJob.id == payment.stationery_job_id).first()
        return job.user_id if job else None
    return None


@transactional
def initiate_payment(
    order_id: int,
    user: dict,
    db: Session,
    idempotency_key: str | None = None,
):
    """Initiate a Razorpay payment for *order_id*.

    If *idempotency_key* is supplied and a ``Payment`` row for this
    (order_id, idempotency_key) pair already exists, that existing record is
    returned immediately — no second Razorpay order is created.  This makes
    the endpoint safe to retry: the frontend must generate one UUID per
    payment *attempt* and send it in the ``X-Idempotency-Key`` header.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    role = (user.get("role") or "").lower()
    is_admin = role in {"admin", "super_admin"}
    if not is_admin and order.user_id != user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized to initiate payment for this order")

    # ── Idempotency fast-path ─────────────────────────────────────────────
    if idempotency_key:
        existing = (
            db.query(Payment)
            .filter(
                Payment.order_id == order_id,
                Payment.idempotency_key == idempotency_key,
            )
            .first()
        )
        if existing:
            return {
                "payment_id": existing.id,
                "razorpay_order_id": existing.razorpay_order_id,
                "amount": float(existing.amount),
                "key": os.getenv("RAZORPAY_KEY_ID"),
                "idempotent": True,
            }
    # ─────────────────────────────────────────────────────────────────────

    from decimal import Decimal
    from app.core.money import to_paise

    amount = Decimal(str(order.total_amount or 0))  # rupees
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Order amount is invalid")

    razorpay_order = client.order.create({
        "amount": to_paise(amount),  # Razorpay transacts in paise
        "currency": "INR",
        "payment_capture": 1,
    })

    payment = Payment(
        order_id=order_id,
        amount=amount,  # stored in rupees
        razorpay_order_id=razorpay_order["id"],
        status=PaymentStatus.INITIATED,
        idempotency_key=idempotency_key,  # None when no key supplied
    )

    db.add(payment)
    db.flush()   # assign server-side id without committing; decorator commits
    db.refresh(payment)

    return {
        "payment_id": payment.id,
        "razorpay_order_id": razorpay_order["id"],
        "amount": float(amount),
        "key": os.getenv("RAZORPAY_KEY_ID"),
        "idempotent": False,
    }


def finalize_payment(payment: Payment, order: Order, db: Session) -> None:
    """
    Unified payment-success finalizer.

    Called by BOTH the manual ``verify_payment()`` path and the Razorpay
    webhook handler so that every successful payment produces identical
    side-effects regardless of which code path processed it:

    * payment.status  → SUCCESS
    * order.status    → CONFIRMED
    * Ledger CREDIT entry created
    * Student notified

    The caller is responsible for ``db.commit()`` after this function returns
    so that all mutations land in a single transaction.
    """
    payment.status = PaymentStatus.SUCCESS
    order.status = OrderStatus.CONFIRMED

    add_ledger_entry(
        order_id=payment.order_id,
        payment_id=payment.id,
        amount=payment.amount,
        entry_type=LedgerType.CREDIT,
        source=LedgerSource.PAYMENT,
        description="Payment received",
        db=db,
    )

    # Notify the student — best-effort; failure must not break finalization.
    student = db.query(User).filter(User.id == order.user_id).first()
    if student:
        notify_user(
            user_id=student.id,
            phone=student.phone,
            title="Payment Successful",
            message=f"Your payment for order #{order.id} was successful.",
            db=db,
        )

    # Publish payment confirmation to WebSocket channel
    try:
        from app.core.order_events import publish_order_event
        publish_order_event(
            order_id=order.id,
            event="payment_confirmed",
            data={
                "order_id": order.id,
                "vendor_id": order.vendor_id,
                "amount": float(payment.amount or 0),  # rupees
                "timestamp": utcnow_naive().isoformat(),
                "description": f"Order #{order.id} payment confirmed",
                "payment_method": "online",
                "is_online": True,
                "type": "online_payment",
                "fee": round((float(payment.amount or 0)) * 0.02, 2),
                "net_amount": round((float(payment.amount or 0)) * 0.98, 2),
            }
        )
    except Exception as e:
        observability.record_exception(e)



@transactional
def verify_payment(
    payment_id: int,
    razorpay_payment_id: str,
    razorpay_signature: str,
    db: Session,
    user: dict,
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    order = db.query(Order).filter(Order.id == payment.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    role = (user.get("role") or "").lower()
    is_admin = role in {"admin", "super_admin"}
    if not is_admin and order.user_id != user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized to verify this payment")

    body = f"{payment.razorpay_order_id}|{razorpay_payment_id}"
    secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not secret:
        # Server misconfiguration must surface clearly, not as a TypeError 500.
        raise HTTPException(
            status_code=503,
            detail="Payment verification unavailable: gateway secret not configured",
        )

    expected_signature = hmac.new(
        bytes(secret, "utf-8"),
        bytes(body, "utf-8"),
        hashlib.sha256
    ).hexdigest()

    if expected_signature != razorpay_signature:
        payment.status = PaymentStatus.FAILED
        observability.record_payment_failure()
        # Raise HTTPException — decorator commits the FAILED status before propagating.
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # Store Razorpay identifiers then delegate all success-path side-effects.
    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature = razorpay_signature

    finalize_payment(payment, order, db)
    return {"message": "Payment verified successfully"}  # decorator commits



@transactional
def refund_payment(payment_id: int, user: dict, db):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # ── Resolve the owning entity (order or stationery job) ──────────────
    owner_user_id = _payment_owner_id(payment, db)
    if owner_user_id is None:
        raise HTTPException(status_code=404, detail="Payment source not found")

    role = (user.get("role") or "").lower()
    is_admin = role in {"admin", "super_admin"}
    if not is_admin and owner_user_id != user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized to refund this payment")

    if payment.status != PaymentStatus.SUCCESS:
        raise HTTPException(
            status_code=400,
            detail="Only successful payments can be refunded"
        )

    # 🔁 Razorpay refund
    from app.core.money import to_paise
    refund = client.payment.refund(
        payment.razorpay_payment_id,
        {
            "amount": to_paise(payment.amount)  # Razorpay refunds in paise
        }
    )

    payment.status = PaymentStatus.REFUNDED
    payment.razorpay_refund_id = refund["id"]
    payment.refunded_at = utcnow_naive()

    # Auto refund ETA — estimate when the money actually reaches the customer.
    from app.modules.ai_intelligence.planners.refund_eta_engine import RefundETAEngine
    from app.modules.payments.model import RefundStatus
    _eta = RefundETAEngine(db).estimate_refund_completion(payment, from_time=payment.refunded_at)
    payment.refund_status = RefundStatus.PROCESSING.value
    payment.estimated_refund_at = _eta["estimated_completion_at"]

    # Cancel the linked entity and notify owner
    if payment.order_id is not None:
        order = db.query(Order).filter(Order.id == payment.order_id).first()
        if order:
            from app.modules.orders.service import update_order_status
            try:
                update_order_status(order, OrderStatus.CANCELLED, "system", db, note="Refund issued")
            except Exception:
                order.status = OrderStatus.CANCELLED

        add_ledger_entry(
            order_id=payment.order_id,
            payment_id=payment.id,
            amount=payment.amount,
            entry_type=LedgerType.DEBIT,
            source=LedgerSource.REFUND,
            description="Refund issued",
            db=db
        )

        if order:
            refund_user = db.query(User).filter(User.id == order.user_id).first()
        else:
            refund_user = None

    else:
        # Stationery job refund
        from app.modules.stationery.job_model import StationeryJob, JobStatus
        job = db.query(StationeryJob).filter(
            StationeryJob.id == payment.stationery_job_id
        ).first()
        if job:
            job.is_paid = False
            # Revert to READY so vendor knows refund was issued
            if job.status == JobStatus.READY:
                job.status = JobStatus.SUBMITTED

        add_ledger_entry(
            order_id=None,
            payment_id=payment.id,
            amount=payment.amount,
            entry_type=LedgerType.DEBIT,
            source=LedgerSource.REFUND,
            description="Stationery job refund issued",
            db=db
        )

        refund_user = db.query(User).filter(User.id == owner_user_id).first()

    # decorator commits all of the above atomically

    if refund_user:
        notify_user(
            user_id=refund_user.id,
            phone=refund_user.phone,
            title="Refund Processed",
            message="Your refund has been processed successfully.",
            db=db
        )

    try:
        from app.modules.auditlog.service import write as write_audit_log, AuditAction, AuditCategory
        write_audit_log(
            db=db,
            action=AuditAction.REFUND_ISSUED,
            action_category=AuditCategory.PAYMENT,
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            entity_type="Payment",
            entity_id=str(payment.id),
            before_state={"status": "SUCCESS"},
            after_state={"status": "REFUNDED", "razorpay_refund_id": refund["id"]},
        )
    except Exception:
        pass

    return {
        "message": "Refund initiated successfully",
        "refund_id": refund["id"],
        "refund_status": payment.refund_status,
        "estimated_refund_at": payment.estimated_refund_at.isoformat() if payment.estimated_refund_at else None,
    }


def get_refund_status(order_id: int, user: dict, db: Session) -> dict:
    """Return live refund status + ETA for the latest refunded payment of *order_id*.

    Auto-advances the refund to COMPLETED once the estimated window elapses.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    role = (user.get("role") or "").lower()
    is_admin = role in {"admin", "super_admin"}
    if not is_admin and order.user_id != user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized to view this refund")

    payment = (
        db.query(Payment)
        .filter(
            Payment.order_id == order_id,
            Payment.status == PaymentStatus.REFUNDED,
        )
        .order_by(Payment.id.desc())
        .first()
    )
    if not payment:
        return {"order_id": order_id, "has_refund": False}

    from app.modules.ai_intelligence.planners.refund_eta_engine import RefundETAEngine
    engine = RefundETAEngine(db)
    prog = engine.progress(payment)  # may mutate payment.refund_status
    db.commit()

    return {
        "order_id": order_id,
        "has_refund": True,
        "payment_id": payment.id,
        "amount": float(payment.amount),
        "refund_status": prog["refund_status"],
        "progress_percent": prog["progress_percent"],
        "message": prog["message"],
        "refunded_at": payment.refunded_at.isoformat() if payment.refunded_at else None,
        "estimated_refund_at": payment.estimated_refund_at.isoformat() if payment.estimated_refund_at else None,
        "razorpay_refund_id": payment.razorpay_refund_id,
    }
