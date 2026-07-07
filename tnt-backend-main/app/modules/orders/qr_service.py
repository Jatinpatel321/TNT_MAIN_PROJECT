import hashlib
import hmac
import os
import secrets

from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderStatus

_QR_SIGNING_KEY = os.getenv("QR_SIGNING_KEY", "dev_qr_key_change_in_production").encode()


def _sign_qr_token(order_id: int, raw_token: str) -> str:
    """Return HMAC-signed QR token: <raw_token>.<signature>"""
    sig = hmac.new(
        _QR_SIGNING_KEY,
        f"{order_id}:{raw_token}".encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    return f"{raw_token}.{sig}"


def _verify_qr_token(order_id: int, qr_code: str) -> bool:
    """Verify that qr_code was signed for this order_id."""
    parts = qr_code.rsplit(".", 1)
    if len(parts) != 2:
        return False
    raw_token, provided_sig = parts
    expected_sig = hmac.new(
        _QR_SIGNING_KEY,
        f"{order_id}:{raw_token}".encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    return hmac.compare_digest(expected_sig, provided_sig)


def generate_qr_code(order_id: int, db: Session) -> str:
    """Generate a signed QR code for an order."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise ValueError("Order not found")

    # Accept both canonical READY and legacy READY_FOR_PICKUP
    if order.status not in (OrderStatus.READY, OrderStatus.READY_FOR_PICKUP):
        raise ValueError("Order is not ready for pickup")

    if order.qr_code and "." in order.qr_code:
        return order.qr_code  # Return existing QR if already generated

    raw_token = secrets.token_urlsafe(16)
    signed_token = _sign_qr_token(order_id, raw_token)
    order.qr_code = signed_token
    db.commit()
    return signed_token


def confirm_pickup(qr_code: str, vendor_id: int, db: Session) -> bool:
    """Confirm pickup using QR code with HMAC verification."""
    order = db.query(Order).filter(Order.qr_code == qr_code).first()
    if not order:
        return False

    # Verify HMAC signature
    if not _verify_qr_token(order.id, qr_code):
        return False

    if order.vendor_id != vendor_id:
        return False  # Only the assigned vendor can confirm

    # Accept both canonical READY and legacy READY_FOR_PICKUP
    if order.status not in (OrderStatus.READY, OrderStatus.READY_FOR_PICKUP):
        return False

    from app.modules.orders.service import update_order_status
    try:
        update_order_status(order, OrderStatus.PICKED, "vendor", db)
        order.pickup_confirmed_at = utcnow_naive()
        order.pickup_confirmed_by = vendor_id
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False


def get_order_by_qr(qr_code: str, db: Session) -> Order:
    """Get order details by QR code for vendor verification."""
    return db.query(Order).filter(Order.qr_code == qr_code).first()


# ── Group pickup: a single QR that covers every member's order ──────────────

import re

_GROUP_QR_RE = re.compile(r"^GRP-(\d+)-")


def _sign_group_qr_token(group_id: int, prefix: str) -> str:
    """Return HMAC-signed group QR token: <prefix>.<signature>."""
    sig = hmac.new(
        _QR_SIGNING_KEY,
        f"group:{group_id}:{prefix}".encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    return f"{prefix}.{sig}"


def _verify_group_qr_token(qr_code: str) -> int | None:
    """Verify a group QR token and return its group_id, or None if invalid."""
    parts = qr_code.rsplit(".", 1)
    if len(parts) != 2:
        return None
    prefix, provided_sig = parts
    match = _GROUP_QR_RE.match(prefix)
    if not match:
        return None
    group_id = int(match.group(1))
    expected_sig = hmac.new(
        _QR_SIGNING_KEY,
        f"group:{group_id}:{prefix}".encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    if not hmac.compare_digest(expected_sig, provided_sig):
        return None
    return group_id


def generate_group_qr_code(group_id: int, db: Session) -> str:
    """Generate (once) a signed pickup QR for an entire group order.

    Stored on ``groups.qr_code`` and reused on subsequent calls so the whole
    group presents one stable code.
    """
    from app.modules.group_cart.model import Group, GroupStatus

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise ValueError("Group not found")
    if group.status not in (GroupStatus.ORDERED, GroupStatus.COMPLETED):
        raise ValueError("Group order has not been placed yet")

    if group.qr_code and "." in group.qr_code:
        return group.qr_code  # Reuse existing group QR

    prefix = f"GRP-{group_id}-{secrets.token_urlsafe(12)}"
    signed_token = _sign_group_qr_token(group_id, prefix)
    group.qr_code = signed_token
    db.commit()
    return signed_token


def confirm_group_pickup(qr_code: str, vendor_id: int, db: Session) -> dict:
    """Confirm pickup for an entire group in a single scan.

    Verifies the group QR's HMAC, then transitions every one of the group's
    READY orders (for this vendor) to PICKED. Orders not yet ready are reported
    as skipped so the vendor knows the group isn't fully collectable yet.
    """
    group_id = _verify_group_qr_token(qr_code)
    if group_id is None:
        return {"success": False, "detail": "Invalid group QR code"}

    orders = (
        db.query(Order)
        .filter(Order.group_id == group_id, Order.vendor_id == vendor_id)
        .all()
    )
    if not orders:
        return {"success": False, "detail": "No orders for this group at your stall"}

    from app.modules.orders.service import update_order_status

    picked, skipped = [], []
    for order in orders:
        if order.status in (OrderStatus.READY, OrderStatus.READY_FOR_PICKUP):
            try:
                update_order_status(order, OrderStatus.PICKED, "vendor", db)
                order.pickup_confirmed_at = utcnow_naive()
                order.pickup_confirmed_by = vendor_id
                picked.append(order.id)
            except Exception:
                skipped.append({"order_id": order.id, "reason": "transition_failed"})
        elif order.status == OrderStatus.PICKED:
            skipped.append({"order_id": order.id, "reason": "already_picked"})
        else:
            skipped.append({
                "order_id": order.id,
                "reason": "not_ready",
                "status": order.status.value if hasattr(order.status, "value") else str(order.status),
            })

    if picked:
        db.commit()

        # Mark the group COMPLETED once every order is picked up.
        remaining = (
            db.query(Order)
            .filter(
                Order.group_id == group_id,
                Order.status.notin_([OrderStatus.PICKED, OrderStatus.COMPLETED, OrderStatus.CANCELLED]),
            )
            .count()
        )
        if remaining == 0:
            from app.modules.group_cart.model import Group, GroupStatus
            group = db.query(Group).filter(Group.id == group_id).first()
            if group and group.status != GroupStatus.COMPLETED:
                group.status = GroupStatus.COMPLETED
                db.commit()
            try:
                from app.core.group_events import publish_group_event
                publish_group_event(group_id, "group_picked_up", {"picked_order_ids": picked})
            except Exception:
                pass
    else:
        db.rollback()

    return {
        "success": bool(picked),
        "group_id": group_id,
        "picked_order_ids": picked,
        "picked_count": len(picked),
        "skipped": skipped,
        "total_orders": len(orders),
    }