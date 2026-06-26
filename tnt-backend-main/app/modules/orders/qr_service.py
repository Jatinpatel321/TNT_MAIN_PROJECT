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

    if order.qr_code:
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

    order.status = OrderStatus.PICKED
    order.pickup_confirmed_at = utcnow_naive()
    order.pickup_confirmed_by = vendor_id
    db.commit()
    return True


def get_order_by_qr(qr_code: str, db: Session) -> Order:
    """Get order details by QR code for vendor verification."""
    return db.query(Order).filter(Order.qr_code == qr_code).first()