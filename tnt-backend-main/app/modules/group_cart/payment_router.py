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

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.group_cart.model import PaymentSplitType
from app.modules.group_cart.payment_service import GroupPaymentService

router = APIRouter(prefix="/groups", tags=["Group Payments"])


class CalculateSplitRequest(BaseModel):
    split_type: PaymentSplitType
    total_amount: float
    custom_splits: dict[int, float] | None = None


class RecordPaymentRequest(BaseModel):
    user_id: int
    amount: float
    payment_method: str
    razorpay_payment_id: str | None = None


class CreateRazorpayOrderRequest(BaseModel):
    user_id: int
    amount: float


class VerifyPaymentRequest(BaseModel):
    user_id: int
    razorpay_payment_id: str
    razorpay_signature: str


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
    service = GroupPaymentService(db)
    return service.calculate_split(
        group_id=group_id,
        split_type=request.split_type,
        total_amount=request.total_amount,
        custom_splits=request.custom_splits,
    )


@router.post("/{group_id}/payments/record")
async def record_payment(
    group_id: int,
    request: RecordPaymentRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Record a payment from a group member.

    Args:
        user_id: User ID making payment
        amount: Payment amount
        payment_method: Payment method
        razorpay_payment_id: Razorpay payment ID (optional)

    Returns:
        - payment_record: Payment details
        - status: Payment status
    """
    service = GroupPaymentService(db)
    return service.record_payment(
        group_id=group_id,
        user_id=request.user_id,
        amount=request.amount,
        payment_method=request.payment_method,
        razorpay_payment_id=request.razorpay_payment_id,
    )


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
        user_id: User ID
        amount: Payment amount

    Returns:
        - razorpay_order_id: Razorpay order ID
        - amount: Amount in paise
        - currency: Currency code
        - receipt: Receipt ID
    """
    service = GroupPaymentService(db)
    return service.create_razorpay_order_for_member(
        group_id=group_id,
        user_id=request.user_id,
        amount=request.amount,
    )


@router.post("/{group_id}/payments/verify")
async def verify_razorpay_payment(
    group_id: int,
    request: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Verify Razorpay payment and update records.

    Args:
        user_id: User ID
        razorpay_payment_id: Razorpay payment ID
        razorpay_signature: Razorpay signature

    Returns:
        - verified: Success status
        - payment_status: Payment status
    """
    service = GroupPaymentService(db)
    return service.verify_razorpay_payment(
        group_id=group_id,
        user_id=request.user_id,
        razorpay_payment_id=request.razorpay_payment_id,
        razorpay_signature=request.razorpay_signature,
    )