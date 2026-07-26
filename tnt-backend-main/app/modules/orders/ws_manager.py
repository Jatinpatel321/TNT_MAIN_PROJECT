"""
WebSocket connection manager with Redis pub/sub integration.

Provides:
- Per-order connection tracking.
- Vendor-wide dashboard connection tracking.
- Redis pub/sub subscription so all server instances receive order events.
- Event → client forwarding with ordering guarantees.
- Graceful cleanup on disconnect.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger("tnt.ws.manager")

REDIS_CHANNEL_PREFIX = "order:events:"
VENDOR_CHANNEL_PREFIX = "vendor:events:"
GROUP_CHANNEL_PREFIX = "group:events:"


class OrderWSManager:
    """Tracks active WebSocket connections keyed by order_id.

    Each order_id channel subscribes to Redis pub/sub so that events
    published by any server process are forwarded to all connected clients.
    """

    def __init__(self) -> None:
        self._active: dict[int, list[WebSocket]] = {}
        self._redis_pubsub_tasks: dict[int, asyncio.Task] = {}
        # Vendor dashboard connections keyed by vendor_id
        self._vendor_connections: dict[int, list[WebSocket]] = {}
        self._vendor_redis_tasks: dict[int, asyncio.Task] = {}
        # Group cart connections keyed by group_id
        self._group_connections: dict[int, list[WebSocket]] = {}
        self._group_redis_tasks: dict[int, asyncio.Task] = {}
        # Reference to the server event loop, captured when a group client
        # connects, so synchronous request code can schedule broadcasts.
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def connect(self, order_id: int, ws: WebSocket) -> None:
        """Accept a WebSocket and register it."""
        if ws.client_state != WebSocketState.CONNECTED:
            await ws.accept()
        self._active.setdefault(order_id, []).append(ws)
        logger.info("ws_connect order_id=%s total=%s", order_id, len(self._active[order_id]))

    def disconnect(self, order_id: int, ws: WebSocket) -> None:
        """Remove a WebSocket from the tracking map."""
        conns = self._active.get(order_id, [])
        if ws in conns:
            conns.remove(ws)
        remaining = len(conns)
        logger.info("ws_disconnect order_id=%s remaining=%s", order_id, remaining)
        # If no more clients for this order, cancel the Redis listener task
        if remaining == 0 and order_id in self._redis_pubsub_tasks:
            self._redis_pubsub_tasks[order_id].cancel()
            del self._redis_pubsub_tasks[order_id]

    # ── Vendor Dashboard Connections ───────────────────────────────────────

    async def connect_vendor(self, vendor_id: int, ws: WebSocket) -> None:
        """Accept a WebSocket for a vendor dashboard connection."""
        if ws.client_state != WebSocketState.CONNECTED:
            await ws.accept()
        self._vendor_connections.setdefault(vendor_id, []).append(ws)
        logger.info("vendor_ws_connect vendor_id=%s total=%s", vendor_id, len(self._vendor_connections[vendor_id]))

    def disconnect_vendor(self, vendor_id: int, ws: WebSocket) -> None:
        """Remove a vendor dashboard WebSocket."""
        conns = self._vendor_connections.get(vendor_id, [])
        if ws in conns:
            conns.remove(ws)
        remaining = len(conns)
        logger.info("vendor_ws_disconnect vendor_id=%s remaining=%s", vendor_id, remaining)
        if remaining == 0 and vendor_id in self._vendor_redis_tasks:
            self._vendor_redis_tasks[vendor_id].cancel()
            del self._vendor_redis_tasks[vendor_id]

    async def broadcast_to_vendor(self, vendor_id: int, payload: dict) -> None:
        """Send *payload* to all dashboard connections for *vendor_id*."""
        for ws in list(self._vendor_connections.get(vendor_id, [])):
            await self.send_json(ws, payload)

    async def start_vendor_redis_listener(self, vendor_id: int) -> None:
        """Subscribe to the vendor-wide Redis channel and forward to all
        dashboard connections for this vendor."""
        if vendor_id in self._vendor_redis_tasks:
            return
        task = asyncio.create_task(self._vendor_redis_listener_loop(vendor_id))
        self._vendor_redis_tasks[vendor_id] = task

    async def _vendor_redis_listener_loop(self, vendor_id: int) -> None:
        """Background loop: subscribe to vendor channel, forward to clients."""
        try:
            from app.core.redis import redis_client

            pubsub = redis_client.pubsub()
            channel = f"{VENDOR_CHANNEL_PREFIX}{vendor_id}"
            await pubsub.subscribe(channel)
            logger.info("vendor_ws_redis_subscribed vendor_id=%s channel=%s", vendor_id, channel)

            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                    await self.broadcast_to_vendor(vendor_id, payload)
                except (json.JSONDecodeError, Exception) as exc:
                    logger.warning("vendor_ws_redis_parse_error vendor_id=%s error=%s", vendor_id, exc)

                if vendor_id not in self._vendor_connections or not self._vendor_connections[vendor_id]:
                    break

        except asyncio.CancelledError:
            logger.info("vendor_ws_redis_listener_cancelled vendor_id=%s", vendor_id)
        except Exception as exc:
            logger.exception("vendor_ws_redis_listener_error vendor_id=%s error=%s", vendor_id, exc)
        finally:
            if vendor_id in self._vendor_redis_tasks:
                del self._vendor_redis_tasks[vendor_id]

    # ── Group Cart Connections ─────────────────────────────────────────────

    async def connect_group(self, group_id: int, ws: WebSocket) -> None:
        """Accept a WebSocket for a group-cart connection."""
        if ws.client_state != WebSocketState.CONNECTED:
            await ws.accept()
        # Capture the running loop so sync request handlers can schedule
        # broadcasts onto it (see schedule_group_broadcast).
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        self._group_connections.setdefault(group_id, []).append(ws)
        logger.info("group_ws_connect group_id=%s total=%s", group_id, len(self._group_connections[group_id]))

    def schedule_group_broadcast(self, group_id: int, payload: dict) -> None:
        """Thread-safe, sync-callable: broadcast *payload* to a group's clients.

        Invoked from synchronous request handlers (which run in a threadpool).
        Delivers in-process so real-time works on a single instance regardless
        of the Redis client being sync or async.
        """
        if not self._group_connections.get(group_id):
            return
        loop = self._loop
        if loop is None or not loop.is_running():
            return
        try:
            asyncio.run_coroutine_threadsafe(self.broadcast_to_group(group_id, payload), loop)
        except Exception as exc:
            logger.warning("group_ws_schedule_broadcast_failed group_id=%s error=%s", group_id, exc)

    def disconnect_group(self, group_id: int, ws: WebSocket) -> None:
        """Remove a group-cart WebSocket."""
        conns = self._group_connections.get(group_id, [])
        if ws in conns:
            conns.remove(ws)
        remaining = len(conns)
        logger.info("group_ws_disconnect group_id=%s remaining=%s", group_id, remaining)
        if remaining == 0 and group_id in self._group_redis_tasks:
            self._group_redis_tasks[group_id].cancel()
            del self._group_redis_tasks[group_id]

    async def broadcast_to_group(self, group_id: int, payload: dict) -> None:
        """Send *payload* to all connections for *group_id*."""
        for ws in list(self._group_connections.get(group_id, [])):
            await self.send_json(ws, payload)

    async def start_group_redis_listener(self, group_id: int) -> None:
        """Subscribe to the group Redis channel and forward to all group members."""
        if group_id in self._group_redis_tasks:
            return
        task = asyncio.create_task(self._group_redis_listener_loop(group_id))
        self._group_redis_tasks[group_id] = task

    async def _group_redis_listener_loop(self, group_id: int) -> None:
        """Background loop: subscribe to group channel, forward to clients.

        Only runs when an *async* Redis client is configured. With a sync
        client (the default here) real-time is delivered in-process via
        ``schedule_group_broadcast`` instead, so this loop exits quietly.
        """
        try:
            import inspect

            from app.core.redis import redis_client

            pubsub = redis_client.pubsub()
            channel = f"{GROUP_CHANNEL_PREFIX}{group_id}"
            subscribe_result = pubsub.subscribe(channel)
            if not inspect.isawaitable(subscribe_result):
                # Sync Redis client — cross-process fan-out unavailable; rely on
                # in-process delivery. Exit without noise.
                logger.info("group_ws_redis_sync_client group_id=%s — using in-process delivery", group_id)
                return
            await subscribe_result
            logger.info("group_ws_redis_subscribed group_id=%s channel=%s", group_id, channel)

            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                    await self.broadcast_to_group(group_id, payload)
                except (json.JSONDecodeError, Exception) as exc:
                    logger.warning("group_ws_redis_parse_error group_id=%s error=%s", group_id, exc)

                if group_id not in self._group_connections or not self._group_connections[group_id]:
                    break

        except asyncio.CancelledError:
            logger.info("group_ws_redis_listener_cancelled group_id=%s", group_id)
        except Exception as exc:
            logger.exception("group_ws_redis_listener_error group_id=%s error=%s", group_id, exc)
        finally:
            if group_id in self._group_redis_tasks:
                del self._group_redis_tasks[group_id]

    # ── Common helpers ─────────────────────────────────────────────────────

    async def send_json(self, ws: WebSocket, payload: dict) -> None:
        """Send a JSON payload to a single client (best-effort)."""
        try:
            await ws.send_text(json.dumps(payload))
        except Exception as exc:
            logger.warning("ws_send_failed %s", exc)

    async def broadcast(self, order_id: int, payload: dict) -> None:
        """Push *payload* to every client tracking *order_id* (best-effort)."""
        for ws in list(self._active.get(order_id, [])):
            await self.send_json(ws, payload)

    async def start_redis_listener(self, order_id: int) -> None:
        """Start a background task that listens to Redis pub/sub for *order_id*
        and forwards events to all connected clients."""
        if order_id in self._redis_pubsub_tasks:
            return  # Already listening

        task = asyncio.create_task(self._redis_listener_loop(order_id))
        self._redis_pubsub_tasks[order_id] = task

    async def _redis_listener_loop(self, order_id: int) -> None:
        """Background loop: subscribe to Redis channel, forward to clients."""
        try:
            from app.core.redis import redis_client

            pubsub = redis_client.pubsub()
            channel = f"{REDIS_CHANNEL_PREFIX}{order_id}"
            await pubsub.subscribe(channel)
            logger.info("ws_redis_subscribed order_id=%s channel=%s", order_id, channel)

            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                    await self.broadcast(order_id, payload)
                except (json.JSONDecodeError, Exception) as exc:
                    logger.warning("ws_redis_message_parse_error order_id=%s error=%s", order_id, exc)

                # If no more clients, stop listening
                if order_id not in self._active or not self._active[order_id]:
                    break

        except asyncio.CancelledError:
            logger.info("ws_redis_listener_cancelled order_id=%s", order_id)
        except Exception as exc:
            logger.exception("ws_redis_listener_error order_id=%s error=%s", order_id, exc)
        finally:
            if order_id in self._redis_pubsub_tasks:
                del self._redis_pubsub_tasks[order_id]

    async def start_heartbeat(self, interval_seconds: int = 30) -> None:
        """Periodic ping loop to detect and clean up dead/zombie sockets."""
        from app.core.time_utils import utcnow_naive
        while True:
            await asyncio.sleep(interval_seconds)
            ping_frame = {"type": "ping", "timestamp": utcnow_naive().isoformat()}
            all_groups = [self._active, self._vendor_connections, self._group_connections]
            for group in all_groups:
                for key, ws_list in list(group.items()):
                    for ws in list(ws_list):
                        try:
                            if ws.client_state == WebSocketState.CONNECTED:
                                await self.send_json(ws, ping_frame)
                            else:
                                if ws in ws_list:
                                    ws_list.remove(ws)
                        except Exception:
                            if ws in ws_list:
                                ws_list.remove(ws)


# Global singleton
manager = OrderWSManager()
