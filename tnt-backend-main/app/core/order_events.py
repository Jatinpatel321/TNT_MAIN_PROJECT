"""
Order event bus — Redis pub/sub for cross-process real-time order updates.

Provides both per-order and vendor-wide channels so that:
- Students receive events for their specific order (via /ws/orders/{id}).
- Vendors receive events for ALL their orders on a single dashboard
  connection (via /ws/vendor/orders).

Flow
----
1. An order status changes in any service (e.g., confirm_order).
2. The service calls ``publish_order_event()``.
3. The event is published to Redis channel ``order:events:{order_id}``.
4. All WebSocket server instances subscribed to that channel receive
   the event and forward it to connected clients.
5. The same event is also published to ``vendor:events:{vendor_id}``
   so the vendor dashboard receives it in real time.

This replaces the DB-polling approach with an event-driven push model.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger("tnt.order_events")

REDIS_CHANNEL_PREFIX = "order:events:"
VENDOR_CHANNEL_PREFIX = "vendor:events:"


def _publish(channel: str, payload: dict) -> bool:
    """Low-level publish helper."""
    try:
        from app.core.redis import redis_client

        data = json.dumps(payload)
        redis_client.publish(channel, data)
        return True
    except Exception as exc:
        logger.exception("redis_publish_failed channel=%s error=%s", channel, exc)
        return False


def publish_order_event(order_id: int, event: str, data: dict[str, Any]) -> bool:
    """Publish an order event to Redis pub/sub.

    Args:
        order_id: The order that changed.
        event: Event type (e.g. "status_change", "eta_update", "pickup_confirmed").
        data: Payload to send to subscribers.

    Returns:
        True if published successfully, False otherwise.
    """
    payload = {
        "order_id": order_id,
        "event": event,
        "data": data,
    }
    channel = f"{REDIS_CHANNEL_PREFIX}{order_id}"
    ok = _publish(channel, payload)

    # Also publish to the vendor-wide channel so the vendor dashboard
    # receives all events for all their orders in one connection.
    if data.get("vendor_id"):
        vendor_channel = f"{VENDOR_CHANNEL_PREFIX}{data['vendor_id']}"
        _publish(vendor_channel, payload)

    if ok:
        logger.info("order_event_published order_id=%s event=%s", order_id, event)
    return ok


def publish_order_status_change(
    order_id: int,
    previous_status: str,
    new_status: str,
    vendor_id: int,
    user_id: int,
    eta_minutes: Optional[int] = None,
) -> bool:
    """Convenience wrapper for publishing a status change event."""
    return publish_order_event(order_id, "status_change", {
        "order_id": order_id,
        "previous_status": previous_status,
        "new_status": new_status,
        "vendor_id": vendor_id,
        "user_id": user_id,
        "eta_minutes": eta_minutes,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
    })


def publish_eta_update(order_id: int, eta_minutes: int, is_delayed: bool = False, vendor_id: int = 0) -> bool:
    """Publish an ETA update event."""
    return publish_order_event(order_id, "eta_update", {
        "order_id": order_id,
        "eta_minutes": eta_minutes,
        "is_delayed": is_delayed,
        "vendor_id": vendor_id,
    })


def publish_pickup_confirmed(order_id: int, vendor_id: int) -> bool:
    """Publish a pickup-confirmed event."""
    return publish_order_event(order_id, "pickup_confirmed", {
        "order_id": order_id,
        "vendor_id": vendor_id,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
    })
