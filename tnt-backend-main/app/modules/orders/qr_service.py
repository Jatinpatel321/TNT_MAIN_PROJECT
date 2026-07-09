import hashlib
import hmac
import os
import secrets
import time

from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderStatus

_QR_SIGNING_KEY = os.getenv("QR_SIGNING_KEY", "dev_qr_key_change_in_production").encode()

# Rotating QR codes expire after this many minutes. A pickup QR is short-lived
# so that a screenshot shared/leaked earlier cannot be replayed at the counter —
# the vendor's scan of a stale token fails signature+expiry verification and the
# student must present the live, in-app rotating code.
QR_EXPIRY_MINUTES = int(os.getenv("QR_EXPIRY_MINUTES", "15"))


def _sign(order_id: int, raw_token: str, expires_at: int) -> str:
    """Return the 16-char HMAC signature binding order_id, token and expiry."""
    return hmac.new(
        _QR_SIGNING_KEY,
        f"{order_id}:{raw_token}:{expires_at}".encode(),
        hashlib.sha256,
    ).hexdigest()[:16]


def _sign_qr_token(order_id: int, raw_token: str, expires_at: int) -> str:
    """Return HMAC-signed, expiring QR token: <raw_token>.<expires_at>.<signature>."""
    sig = _sign(order_id, raw_token, expires_at)
    return f"{raw_token}.{expires_at}.{sig}"


def _parse_expiry(qr_code: str) -> int | None:
    """Extract the expiry epoch-seconds from a v2 token, or None if absent/legacy."""
    parts = qr_code.split(".")
    if len(parts) != 3:
        return None
    try:
        return int(parts[1])
    except (ValueError, TypeError):
        return None


def _verify_qr_token(order_id: int, qr_code: str, *, check_expiry: bool = True) -> bool:
    """Verify that *qr_code* was signed for *order_id* and has not expired.

    Supports two formats for backward compatibility:
      • v2 (current): ``<raw>.<expires_at>.<sig>`` — signed and expiring.
      • v1 (legacy):  ``<raw>.<sig>``            — signed, non-expiring.
    """
    parts = qr_code.split(".")

    if len(parts) == 3:
        raw_token, expires_str, provided_sig = parts
        try:
            expires_at = int(expires_str)
        except (ValueError, TypeError):
            return False
        expected_sig = _sign(order_id, raw_token, expires_at)
        if not hmac.compare_digest(expected_sig, provided_sig):
            return False
        if check_expiry and time.time() > expires_at:
            return False
        return True

    if len(parts) == 2:
        # Legacy non-expiring token.
        raw_token, provided_sig = parts
        expected_sig = hmac.new(
            _QR_SIGNING_KEY,
            f"{order_id}:{raw_token}".encode(),
            hashlib.sha256,
        ).hexdigest()[:16]
        return hmac.compare_digest(expected_sig, provided_sig)

    return False


def _is_live(order_id: int, qr_code: str | None) -> bool:
    """True if *qr_code* is a currently-valid (signed, unexpired) token."""
    return bool(qr_code) and "." in qr_code and _verify_qr_token(order_id, qr_code)


def _mint_token(order_id: int) -> str:
    raw_token = secrets.token_urlsafe(16)
    expires_at = int(time.time()) + QR_EXPIRY_MINUTES * 60
    return _sign_qr_token(order_id, raw_token, expires_at)


def generate_qr_code(order_id: int, db: Session, *, force: bool = False) -> str:
    """Generate (or reuse) a signed, expiring QR code for an order.

    Returns the existing token while it is still live; mints a fresh rotating
    token once the previous one has expired, or immediately when *force* is set
    (used by the explicit refresh endpoint).
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise ValueError("Order not found")

    # Accept both canonical READY and legacy READY_FOR_PICKUP
    if order.status not in (OrderStatus.READY, OrderStatus.READY_FOR_PICKUP):
        raise ValueError("Order is not ready for pickup")

    if not force and _is_live(order_id, order.qr_code):
        return order.qr_code  # Reuse the current live token

    order.qr_code = _mint_token(order_id)
    db.commit()
    return order.qr_code


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
        # Push a dedicated pickup event to the user's order channel and the
        # vendor-wide channel so the user app, vendor app and admin dashboard
        # all reflect the collection the instant the QR is scanned.
        try:
            from app.core.order_events import publish_pickup_confirmed
            publish_pickup_confirmed(order.id, vendor_id)
        except Exception:
            pass
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