from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.db_transaction import transactional
from app.core.deps import get_db
from app.core.observability import observability
from app.core.razorpay_webhook import verify_webhook_signature
from app.core.redis import redis_client
from app.modules.orders.model import Order, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.payments.service import finalize_payment

router = APIRouter(prefix="/webhooks/razorpay", tags=["Razorpay Webhooks"])


@router.post("/")
@transactional
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    body = await request.body()

    verify_webhook_signature(body, x_razorpay_signature)

    payload = await request.json()
    event = payload.get("event")
    entity = payload["payload"]["payment"]["entity"]

    razorpay_payment_id = entity.get("id")
    idempotency_key = f"webhook:razorpay:{event}:{razorpay_payment_id}"

    is_first = redis_client.set(idempotency_key, "1", nx=True, ex=3600)
    if not is_first:
        return {"status": "duplicate_ignored"}

    payment = (
        db.query(Payment)
        .filter(Payment.razorpay_payment_id == razorpay_payment_id)
        .first()
    )

    if not payment:
        return {"status": "ignored"}

    order = db.query(Order).filter(Order.id == payment.order_id).first()

    # ✅ PAYMENT SUCCESS — delegate to the shared finalizer so ledger,
    # order status, and notification are identical to the manual verify path.
    if event == "payment.captured":
        finalize_payment(payment, order, db)

    # ❌ PAYMENT FAILED
    elif event == "payment.failed":
        payment.status = PaymentStatus.FAILED
        order.status = OrderStatus.CANCELLED
        observability.record_payment_failure()

    # 🔁 REFUND PROCESSED
    elif event == "refund.processed":
        payment.status = PaymentStatus.REFUNDED
        order.status = OrderStatus.CANCELLED

    return {"status": "ok"}  # decorator commits
