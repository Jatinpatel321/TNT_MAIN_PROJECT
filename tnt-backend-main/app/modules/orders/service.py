"""
Order status transition service — single source of truth for status changes.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.history_model import OrderHistory
from app.modules.orders.model import Order, OrderStatus

logger = logging.getLogger("tnt.orders.service")


def create_order(user_id: int, slot_id: int, db: Session) -> Order:
    """Create a placed order for a user in a slot."""
    from app.modules.slots.model import Slot

    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise ValueError("Slot not found")

    order = Order(
        user_id=user_id,
        slot_id=slot_id,
        vendor_id=slot.vendor_id,
        status=OrderStatus.PLACED,
        total_amount=0,
    )
    db.add(order)
    db.flush()
    return order

def update_order_status(
    order: Order,
    new_status: OrderStatus,
    changed_by: str,
    db: Session,
    note: Optional[str] = None,
) -> None:
    """Transition *order* to *new_status* and record the change in history.

    Args:
        order: The order to update.
        new_status: Target status.
        changed_by: Who triggered the change ("student", "vendor", "system").
        db: Database session.
        note: Optional human-readable note attached to the history entry.
    """
    previous_status = order.status

    # Validate state transitions
    allowed_transitions = _ALLOWED_TRANSITIONS.get(previous_status, set())
    if new_status not in allowed_transitions and new_status != previous_status:
        logger.warning(
            "order_invalid_transition order_id=%s from=%s to=%s",
            order.id, previous_status, new_status,
        )
        raise ValueError(
            f"Cannot transition from {previous_status} to {new_status}"
        )

    order.status = new_status

    # Record history
    history = OrderHistory(
        order_id=order.id,
        status=new_status,
        changed_by=changed_by,
        note=note,
        changed_at=utcnow_naive(),
    )
    db.add(history)

    # Publish event to Redis pub/sub for real-time WebSocket delivery
    _publish_status_event(order, previous_status, new_status)


def _publish_status_event(
    order: Order,
    previous_status: OrderStatus,
    new_status: OrderStatus,
) -> None:
    """Publish a status change event to Redis pub/sub."""
    try:
        from app.core.order_events import publish_order_status_change

        prev_val = previous_status.value if hasattr(previous_status, "value") else str(previous_status)
        new_val = new_status.value if hasattr(new_status, "value") else str(new_status)

        publish_order_status_change(
            order_id=order.id,
            previous_status=prev_val,
            new_status=new_val,
            vendor_id=order.vendor_id,
            user_id=order.user_id,
            eta_minutes=order.eta_minutes,
        )
    except Exception as exc:
        logger.exception("order_event_publish_error order_id=%s error=%s", order.id, exc)


# ── Valid state transitions ──────────────────────────────────────────────────

_ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PLACED: {
        OrderStatus.CONFIRMED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.PENDING: {  # legacy compat
        OrderStatus.CONFIRMED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.CONFIRMED: {
        OrderStatus.PREPARING,
        OrderStatus.CANCELLED,
    },
    OrderStatus.PREPARING: {
        OrderStatus.READY,
        OrderStatus.CANCELLED,
    },
    OrderStatus.READY: {
        OrderStatus.PICKED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.READY_FOR_PICKUP: {  # legacy compat
        OrderStatus.PICKED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.PICKED: set(),
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}
