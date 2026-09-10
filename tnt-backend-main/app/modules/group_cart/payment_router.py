"""
Group Payment Split Router
===========================

Endpoints for group split payments:

GET /groups/{group_id}/payments/summary - Get payment summary
GET /groups/{group_id}/payments/status - Get payment status
GET /groups/{group_id}/payments/contributions - Get contribution summary
GET /groups/{group_id}/payments/outstanding - Get outstanding payments
POST /groups/{group_id}/payments/calculate - Calculate payment split
POST /groups/{group_id}/payments/record - Record a payment
POST /groups/{group_id}/payments/remind - Send payment reminder
POST /groups/{group_id}/payments/razorpay-order - Create Razorpay order
POST /groups/{group_id}/payments/verify - Verify Razorpay payment
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.group_cart.group_service import require_group_member
from app.modules.group_cart.model import PaymentSplitType
from app.modules.group_cart.payment_service import GroupPaymentService

router = APIRouter(prefix="/groups", tags=["Group Payments"])


class CalculateSplitRequest(BaseModel):
    split_type: PaymentSplitType
    total_amount: float
    custom_splits: dict[int, float] | None = None


class RecordPaymentRequest(BaseModel):
    amount: float
    payment_method: str
    razorpay_payment_id: str | None = None
    user_id: int | None = None


class CreateRazorpayOrderRequest(BaseModel):
    amount: float
    user_id: int | None = None


class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_signature: str
    razorpay_order_id: str | None = None
    user_id: int | None = None


def _resolve_payer_id(requested_user_id: int | None, current_user: dict) -> int:
    """Ensure callers only record or verify payments for themselves unless admin."""
    current_id = current_user.get("id")
    if requested_user_id is not None and requested_user_id != current_id:
        role = (current_user.get("role") or "").lower()
        if role not in {"admin", "super_admin"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to act on behalf of another user",
            )
        return requested_user_id
    return current_id


@router.get("/{group_id}/payments/summary")
async def get_payment_summary(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get comprehensive payment summary for the group.

    Returns:
        - payment_status: Overall payment status
        - contribution_summary: Detailed contributions
        - outstanding_payments: Unpaid members
    """
    require_group_member(group_id, user, db)
    service = GroupPaymentService(db)
    return service.get_group_payment_summary(group_id)


@router.get("/{group_id}/payments/status")
async def get_payment_status(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get payment status for all group members.

    Returns:
        - total_amount: Total order amount
        - total_paid: Total amount paid
        - total_pending: Total amount pending
        - payment_percentage: Overall completion
        - members: Per-member status
        - unpaid_members: List of unpaid members
    """
    require_group_member(group_id, user, db)
    service = GroupPaymentService(db)
    return service.get_payment_status(group_id)


@router.get("/{group_id}/payments/contributions")
async def get_contribution_summary(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get detailed contribution summary.

    Returns:
        - contributions: Per-member contributions
        - payment_methods: Breakdown by method
        - timeline: Payment timeline
        - statistics: Payment statistics
    """
    require_group_member(group_id, user, db)
    service = GroupPaymentService(db)
    return service.get_contribution_summary(group_id)


@router.get("/{group_id}/payments/outstanding")
async def get_outstanding_payments(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get list of outstanding (unpaid) payments.

    Returns:
        - outstanding: List of unpaid members
        - total_outstanding: Total amount outstanding
        - suggested_actions: Actions for owner
    """
    require_group_member(group_id, user, db)
    service = GroupPaymentService(db)
    return service.get_outstanding_payments(group_id)


@router.post("/{group_id}/payments/calculate")
async def calculate_payment_split(
    group_id: int,
    request: CalculateSplitRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Calculate payment split for group members.

    Args:
        split_type: EQUAL, CUSTOM, or PERCENTAGE
        total_amount: Total order amount
        custom_splits: Custom amounts (for CUSTOM type)

    Returns:
        - splits: List of payment splits
        - total_amount: Total amount
        - split_type: Type of split
    """
    require_group_member(group_id, user, db)
    service = GroupPaymentService(db)
    res = service.calculate_split(
        group_id=group_id,
        split_type=request.split_type,
        total_amount=request.total_amount,
        custom_splits=request.custom_splits,
    )
    if "error" in res:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res["error"])
    return res


@router.post("/{group_id}/payments/record")
async def record_payment(
    group_id: int,
    request: RecordPaymentRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Record a payment from a group member.

    Args:
        amount: Payment amount
        payment_method: Payment method
        razorpay_payment_id: Razorpay payment ID (optional)
        user_id: Target user ID (optional, admin only)

    Returns:
        - payment_record: Payment details
        - status: Payment status
    """
    require_group_member(group_id, user, db)
    payer_id = _resolve_payer_id(request.user_id, user)
    service = GroupPaymentService(db)
    res = service.record_payment(
        group_id=group_id,
        user_id=payer_id,
        amount=request.amount,
        payment_method=request.payment_method,
        razorpay_payment_id=request.razorpay_payment_id,
    )
    if "error" in res:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res["error"])
    return res


@router.post("/{group_id}/payments/remind")
async def send_payment_reminder(
    group_id: int,
    user_id: int | None = Query(None, description="Specific user ID (optional)"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    """Send payment reminder to unpaid members.

    Args:
        user_id: Specific user ID (optional, if not provided sends to all unpaid)

    Returns:
        - sent: Success status
        - reminder_count: Number of reminders sent
    """
    require_group_member(group_id, current_user, db)
    service = GroupPaymentService(db)

    if user_id:
        return service.send_payment_reminder(group_id, user_id)
    else:
        return service.send_bulk_reminders(group_id)


@router.post("/{group_id}/payments/razorpay-order")
async def create_razorpay_order(
    group_id: int,
    request: CreateRazorpayOrderRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Create Razorpay order for individual member payment.

    Args:
        amount: Payment amount
        user_id: Target user ID (optional, admin only)

    Returns:
        - razorpay_order_id: Razorpay order ID
        - amount: Amount in paise
        - currency: Currency code
        - receipt: Receipt ID
    """
    require_group_member(group_id, user, db)
    payer_id = _resolve_payer_id(request.user_id, user)
    service = GroupPaymentService(db)
    res = service.create_razorpay_order_for_member(
        group_id=group_id,
        user_id=payer_id,
        amount=request.amount,
    )
    if "error" in res:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=res["error"])
    return res


@router.post("/{group_id}/payments/verify")
async def verify_razorpay_payment(
    group_id: int,
    request: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Verify Razorpay payment and update records.

    Args:
        razorpay_payment_id: Razorpay payment ID
        razorpay_signature: Razorpay signature
        razorpay_order_id: Optional Razorpay order ID
        user_id: Target user ID (optional, admin only)

    Returns:
        - verified: Success status
        - payment: Payment details
    """
    require_group_member(group_id, user, db)
    payer_id = _resolve_payer_id(request.user_id, user)
    service = GroupPaymentService(db)
    res = service.verify_razorpay_payment(
        group_id=group_id,
        user_id=payer_id,
        razorpay_payment_id=request.razorpay_payment_id,
        razorpay_signature=request.razorpay_signature,
        razorpay_order_id=request.razorpay_order_id,
    )
    if not res.get("verified"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res.get("error", "Payment verification failed"),
        )
    return res