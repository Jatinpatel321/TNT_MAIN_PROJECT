import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.rate_limit import check_rate_limit, payment_rate_limiter
from app.core.security import get_current_user
from app.modules.notifications.model import Notification
from app.modules.orders.model import Order, OrderStatus
from app.modules.payments import payment_service
from app.modules.payments.model import Payment, PaymentStatus

router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
    dependencies=[Depends(payment_rate_limiter)],
)


class MockPaymentRequest(BaseModel):
    order_id: int
    method: str = "UPI"   # "UPI" | "CARD" | "WALLET"
    amount: float | None = None  # optional override (paise); uses order total if omitted


@router.post("/mock")
def mock_payment(
    payload: MockPaymentRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Dev-only mock payment gateway.  Always succeeds.
    Accepts method = 'UPI' | 'CARD' | 'WALLET'.
    Updates Payment → SUCCESS and Order → CONFIRMED, then emits a Notification.
    """
    # Per-user rate limit: 10 payment attempts per 5 minutes per user
    check_rate_limit(
        key=f"payment:user:{user['id']}",
        limit=10,
        window_seconds=300,
    )

    method = (payload.method or "UPI").upper()
    if method not in {"UPI", "CARD", "WALLET"}:
        raise HTTPException(status_code=400, detail="method must be UPI, CARD or WALLET")

    order = db.query(Order).filter(Order.id == payload.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not your order")

    payment = (
        db.query(Payment)
        .filter(Payment.order_id == payload.order_id)
        .order_by(Payment.id.desc())
        .first()
    )

    amount_paise = int(payload.amount) if payload.amount else (order.total_amount or 0)
    mock_payment_id = f"mock_pay_{uuid.uuid4().hex[:16]}"

    if payment:
        payment.status = PaymentStatus.SUCCESS
        payment.razorpay_payment_id = mock_payment_id
    else:
        payment = Payment(
            order_id=payload.order_id,
            amount=amount_paise,
            status=PaymentStatus.SUCCESS,
            razorpay_payment_id=mock_payment_id,
            idempotency_key=f"mock_{payload.order_id}_{uuid.uuid4().hex[:8]}",
        )
        db.add(payment)

    order.status = OrderStatus.CONFIRMED

    notification = Notification(
        user_id=user["id"],
        title="Payment Successful 🎉",
        message=f"₹{amount_paise / 100:.2f} paid via {method}. Order #{payload.order_id} is confirmed!",
        is_read=False,
    )
    db.add(notification)
    db.commit()
    db.refresh(payment)

    return {
        "payment_id": payment.id,
        "order_id": payload.order_id,
        "status": "SUCCESS",
        "method": method,
        "amount": amount_paise,
        "amount_display": f"₹{amount_paise / 100:.2f}",
        "mock_payment_id": mock_payment_id,
        "message": f"Payment of ₹{amount_paise / 100:.2f} via {method} was successful.",
    }


@router.post("/razorpay/initiate/{order_id}")
def initiate(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
):
    """Initiate a Razorpay payment.

    Send a ``X-Idempotency-Key: <uuid>`` header to make this endpoint safe
    to retry.  Repeated calls with the same key return the existing payment
    record without creating a second Razorpay order.
    """
    # Per-user rate limit: 10 payment initiations per 5 minutes per user
    check_rate_limit(
        key=f"payment:initiate:user:{user['id']}",
        limit=10,
        window_seconds=300,
    )
    return payment_service.initiate(order_id, user, x_idempotency_key, db)


@router.post("/razorpay/verify/{payment_id}")
def verify(
    payment_id: int,
    razorpay_payment_id: str,
    razorpay_signature: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return payment_service.verify(payment_id, razorpay_payment_id, razorpay_signature, user, db)


@router.post("/razorpay/refund/{payment_id}")
def refund(
    payment_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return payment_service.refund(payment_id, user, db)
