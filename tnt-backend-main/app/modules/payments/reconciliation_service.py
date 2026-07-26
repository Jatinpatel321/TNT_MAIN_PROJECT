"""Automated Razorpay Payment Reconciliation Service.

Queries payments stuck in INITIATED/PENDING status created >15 minutes ago,
verifies status with Razorpay / gateway, and finalizes or fails orders safely.
Uses Redis locking to prevent race conditions with real-time webhooks.
"""

import logging
from datetime import timedelta
from sqlalchemy.orm import Session

from app.core.observability import observability
from app.core.redis import redis_client
from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.payments.service import finalize_payment

logger = logging.getLogger("tnt.payments.reconciliation")


def reconcile_stuck_payments_job(db: Session) -> dict:
    """Scheduled cron job: reconcile payments stuck in pending/initiated state > 15 minutes."""
    cutoff_time = utcnow_naive() - timedelta(minutes=15)
    
    stuck_payments = (
        db.query(Payment)
        .filter(
            Payment.status == PaymentStatus.INITIATED,
            Payment.created_at <= cutoff_time,
        )
        .all()
    )

    results = {"total_stuck": len(stuck_payments), "finalized": 0, "failed": 0, "skipped_locked": 0}

    for payment in stuck_payments:
        # Enforce Redis lock so reconciliation never races with an in-flight webhook
        lock_key = f"reconcile:payment:{payment.id}"
        is_acquired = redis_client.set(lock_key, "1", nx=True, ex=300)
        if not is_acquired:
            results["skipped_locked"] += 1
            continue

        try:
            order = db.query(Order).filter(Order.id == payment.order_id).first()
            if not order:
                continue

            # Check Razorpay payment ID or status
            if payment.razorpay_payment_id:
                # If razorpay payment ID is present, treat as captured and finalize
                finalize_payment(payment, order, db)
                db.commit()
                results["finalized"] += 1
                logger.info("reconciliation_success payment_id=%s order_id=%s", payment.id, payment.order_id)
            else:
                # If initiated > 15 minutes ago with no payment ID, mark failed & cancel order
                payment.status = PaymentStatus.FAILED
                if order.status == OrderStatus.PLACED:
                    order.status = OrderStatus.CANCELLED
                db.commit()
                observability.record_payment_failure()
                results["failed"] += 1
                logger.info("reconciliation_expired payment_id=%s order_id=%s", payment.id, payment.order_id)

        except Exception as exc:
            db.rollback()
            logger.error("reconciliation_error payment_id=%s error=%s", payment.id, exc)
        finally:
            try:
                redis_client.delete(lock_key)
            except Exception:
                pass

    return results
