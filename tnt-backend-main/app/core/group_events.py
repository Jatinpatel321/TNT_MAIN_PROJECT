"""
Group cart event bus — Redis pub/sub for real-time group-cart updates.

Mirrors ``app.core.order_events`` but keyed by ``group_id`` so that every
member viewing a shared group cart receives changes (item added/removed,
member joined, slot locked, split finalized, order placed) in real time —
replacing the previous client-side polling.

Flow
----
1. A group changes in ``GroupCartService`` (e.g. add_cart_item).
2. The service calls ``publish_group_event()``.
3. The event is published to Redis channel ``group:events:{group_id}``.
4. Every WebSocket server instance subscribed to that channel forwards the
   event to all connected group members (see ``/ws/groups/{group_id}``).
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("tnt.group_events")

GROUP_CHANNEL_PREFIX = "group:events:"


def _publish(channel: str, payload: dict) -> bool:
    """Low-level publish helper."""
    try:
        from app.core.redis import redis_client
        from app.core.money import json_default

        redis_client.publish(channel, json.dumps(payload, default=json_default))
        return True
    except Exception as exc:
        logger.exception("group_redis_publish_failed channel=%s error=%s", channel, exc)
        return False


def publish_group_event(group_id: int, event: str, data: dict[str, Any]) -> bool:
    """Publish a group-cart event to Redis pub/sub.

    Args:
        group_id: The group that changed.
        event: Event type (e.g. "group_updated", "order_placed", "split_finalized").
        data: Payload delivered to subscribers.

    Returns:
        True if published successfully, False otherwise.
    """
    payload = {
        "group_id": group_id,
        "event": event,
        "data": data,
    }
    # Redis publish — for cross-process fan-out (multi-instance deployments).
    ok = _publish(f"{GROUP_CHANNEL_PREFIX}{group_id}", payload)

    # In-process delivery — guarantees real-time works on a single instance
    # (the common deployment) without relying on an async Redis client.
    try:
        from app.modules.orders.ws_manager import manager
        manager.schedule_group_broadcast(group_id, payload)
    except Exception as exc:
        logger.warning("group_inprocess_broadcast_failed group_id=%s error=%s", group_id, exc)

    if ok:
        logger.info("group_event_published group_id=%s event=%s", group_id, event)
    return ok
