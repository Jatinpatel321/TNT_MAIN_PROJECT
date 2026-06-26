"""
app/modules/group_cart/group_service.py
=========================================
Domain service layer for the Group Cart module (PROMPT 12).

Wraps ``GroupCartService`` (the low-level stateful class) behind a clean,
function-based API so that routers stay thin HTTP adapters.

All DB queries that previously lived inline in ``group_cart/router.py`` live
here, giving tests a single import target and keeping routers free of SQLAlchemy.

Public surface:
  create_group         — create a new group cart
  get_my_groups        — list groups the user belongs to
  get_group_detail     — fetch a single group's full details
  invite_member        — owner invites a user by phone
  add_cart_item        — member adds a menu item to the shared cart
  remove_cart_item     — member removes their own cart item
  lock_slot            — owner locks a slot for the group
  place_group_order    — owner triggers order placement for all members
  get_payment_splits   — fetch current split configuration for a group
  set_payment_split    — member configures their payment split
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.group_cart.model import Group, GroupCartItem, GroupMember, PaymentSplitType
from app.modules.group_cart.service import GroupCartService


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _svc(db: Session) -> GroupCartService:
    """Return a configured ``GroupCartService`` instance."""
    return GroupCartService(db)


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def create_group(name: str, user: dict, db: Session) -> dict:
    """Create a new group cart owned by *user*."""
    svc = _svc(db)
    group = svc.create_group(name, user["id"])
    return svc.get_group(group.id, user["id"])


def get_my_groups(user: dict, db: Session) -> list[Group]:
    """Return all groups where the authenticated user is a member."""
    return (
        db.query(Group)
        .join(GroupMember)
        .filter(GroupMember.user_id == user["id"])
        .all()
    )


def get_group_detail(group_id: int, user: dict, db: Session) -> dict:
    """Return full details for *group_id* (membership, cart items, slot lock)."""
    return _svc(db).get_group(group_id, user["id"])


def invite_member(group_id: int, phone: str, user: dict, db: Session) -> dict:
    """Invite a user (identified by *phone*) into *group_id*."""
    member = _svc(db).invite_member(group_id, user["id"], phone)
    return {"message": "Member invited successfully", "member_id": member.id}


def add_cart_item(
    group_id: int,
    menu_item_id: int,
    quantity: int,
    user: dict,
    db: Session,
) -> dict:
    """Add *menu_item_id* × *quantity* to the group cart."""
    cart_item = _svc(db).add_cart_item(group_id, user["id"], menu_item_id, quantity)
    return {"message": "Item added to cart", "cart_item_id": cart_item.id}


def remove_cart_item(group_id: int, item_id: int, user: dict, db: Session) -> dict:
    """Remove *item_id* from the group cart.

    Raises 404 if the item doesn't exist in this group, 403 if the requesting
    user is not the item owner.
    """
    item = (
        db.query(GroupCartItem)
        .filter(GroupCartItem.id == item_id, GroupCartItem.group_id == group_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    if item.owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="Can only remove your own items")

    db.delete(item)
    db.commit()
    return {"message": "Item removed from cart"}


def lock_slot(
    group_id: int,
    slot_id: int,
    duration_minutes: int,
    user: dict,
    db: Session,
) -> dict:
    """Lock *slot_id* for *group_id* for up to *duration_minutes* minutes."""
    lock = _svc(db).lock_slot(group_id, user["id"], slot_id, duration_minutes)
    return {"message": "Slot locked successfully", "lock_id": lock.id}


def place_group_order(group_id: int, user: dict, db: Session) -> dict:
    """Place orders for all group members and return the consolidated result."""
    return _svc(db).place_group_order(group_id, user["id"])


def get_payment_splits(group_id: int, user: dict, db: Session):
    """Return the current payment-split configuration for the group."""
    return _svc(db).get_payment_splits(group_id, user["id"])


def set_payment_split(
    group_id: int,
    split_type: PaymentSplitType,
    amount: Optional[float],
    percentage: Optional[float],
    user: dict,
    db: Session,
) -> dict:
    """Configure the authenticated user's payment split for *group_id*."""
    split = _svc(db).set_payment_split(
        group_id, user["id"], split_type, amount, percentage
    )
    return {"message": "Payment split updated", "split_id": split.id}
