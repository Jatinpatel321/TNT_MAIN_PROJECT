"""
app/modules/payments/payment_service.py
========================================
Domain service layer for the Payments module (PROMPT 12).

This module is the single callable boundary for all HTTP-initiated payment
operations.  It delegates the heavy lifting to the lower-level functions in
``payments/service.py`` (Razorpay integration, ledger entries, notifications)
while providing a stable, test-friendly API that the router can call in one
line.

Public surface:
  initiate   — create a Razorpay order and a Payment row
  verify     — validate Razorpay signature and finalise the payment
  refund     — issue a Razorpay refund and update ledger / order status
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.payments.service import (
    initiate_payment,
    refund_payment,
    verify_payment,
)


def initiate(
    order_id: int,
    user: dict,
    idempotency_key: str | None,
    db: Session,
) -> dict:
    """Create a Razorpay order and a corresponding ``Payment`` row.

    Idempotent when *idempotency_key* is provided — a second call with the
    same key returns the existing payment record without hitting Razorpay again.
    """
    return initiate_payment(order_id, user=user, db=db, idempotency_key=idempotency_key)


def verify(
    payment_id: int,
    razorpay_payment_id: str,
    razorpay_signature: str,
    user: dict,
    db: Session,
) -> dict:
    """Verify the Razorpay signature and mark the payment as SUCCESS.

    Also transitions the linked order to CONFIRMED and creates a ledger entry.
    """
    return verify_payment(
        payment_id,
        razorpay_payment_id,
        razorpay_signature,
        db,
        user=user,
    )


def refund(
    payment_id: int,
    user: dict,
    db: Session,
) -> dict:
    """Initiate a Razorpay refund and update the payment / order state.

    Only the payment owner (or an admin) may request a refund.
    Only payments in SUCCESS status can be refunded.
    """
    return refund_payment(payment_id, user, db)
