from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.group_cart import group_service
from app.modules.group_cart.model import PaymentSplitType

router = APIRouter(prefix="/groups", tags=["Group Cart"])


# ── Pydantic schemas ──────────────────────────────────────────────────

class CreateGroupRequest(BaseModel):
    name: str


class InviteMemberRequest(BaseModel):
    phone: str


class AddCartItemRequest(BaseModel):
    menu_item_id: int
    quantity: int


class LockSlotRequest(BaseModel):
    slot_id: int
    duration_minutes: Optional[int] = 30


class SetPaymentSplitRequest(BaseModel):
    split_type: PaymentSplitType
    amount: Optional[float] = None
    percentage: Optional[float] = None


class GroupCheckoutRequest(BaseModel):
    payment_method: str = "UPI"


class GroupResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    status: str
    created_at: datetime
    members: List[Any]
    cart_items: List[Any]
    slot_lock: Optional[Any]

    model_config = ConfigDict(from_attributes=True)


class GroupMemberResponse(BaseModel):
    id: int
    user_id: int
    role: str
    joined_at: str
    user: dict


class GroupCartItemResponse(BaseModel):
    id: int
    menu_item_id: int
    owner_id: int
    quantity: int
    price_at_time: float
    menu_item: dict
    owner: dict


# ── Routes ───────────────────────────────────────────────────────────────

@router.post("/")
def create_group(
    request: CreateGroupRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new group cart."""
    return group_service.create_group(request.name, current_user, db)


@router.get("/my-groups")
def get_my_groups(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all groups where user is a member."""
    return group_service.get_my_groups(current_user, db)


@router.get("/{group_id}")
def get_group(
    group_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get group details."""
    return group_service.get_group_detail(group_id, current_user, db)


@router.post("/{group_id}/invite")
def invite_member(
    group_id: int,
    request: InviteMemberRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Invite a member to the group."""
    return group_service.invite_member(group_id, request.phone, current_user, db)


@router.post("/{group_id}/cart")
def add_cart_item(
    group_id: int,
    request: AddCartItemRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add item to group cart."""
    return group_service.add_cart_item(group_id, request.menu_item_id, request.quantity, current_user, db)


@router.post("/{group_id}/slot/lock")
def lock_slot(
    group_id: int,
    request: LockSlotRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lock a slot for the group."""
    return group_service.lock_slot(group_id, request.slot_id, request.duration_minutes, current_user, db)


@router.post("/{group_id}/order")
def place_group_order(
    group_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    """Place order for the entire group."""
    return group_service.place_group_order(group_id, current_user, db)


@router.post("/{group_id}/checkout", summary="Checkout group cart")
def checkout_group(
    group_id: int,
    payload: GroupCheckoutRequest | None = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Place orders for all members in the group cart.

    - Validates that a slot has been locked for the group.
    - Creates individual orders for each member based on their cart items.
    - Applies payment split (equal / custom / unified).
    - Initiates Razorpay payment for each member's share.
    - Sends notifications to all group members.
    - Transitions group status to ORDERED.
    """
    result = group_service.place_group_order(group_id, current_user, db)
    return {
        "message": "Group order placed successfully",
        "group_id": group_id,
        "orders": result.get("orders", []),
        "payment_reconciliation": result.get("payment_reconciliation", {}),
        "total_amount": result.get("total_amount", 0),
    }


@router.get("/{group_id}/payment-splits")
def get_payment_splits(
    group_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get payment split configuration."""
    return group_service.get_payment_splits(group_id, current_user, db)


@router.post("/{group_id}/payment-split")
def set_payment_split(
    group_id: int,
    request: SetPaymentSplitRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set payment split for current user."""
    return group_service.set_payment_split(
        group_id, request.split_type, request.amount, request.percentage, current_user, db
    )


@router.delete("/{group_id}/cart/{item_id}")
def remove_cart_item(
    group_id: int,
    item_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove item from group cart (only owner can remove their items)."""
    return group_service.remove_cart_item(group_id, item_id, current_user, db)