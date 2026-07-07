"""Real-time order status tracking via WebSocket — event-driven.

Uses Redis pub/sub so events published by the order service (from any
server instance) are forwarded to all connected clients in real time,
replacing the old DB-polling approach.

Authentication
--------------
First text frame must be ``{"token": "<bearer jwt>"}``.
Server responds with ``{"authenticated": true, "user_id": ...}``.

Authorization
-------------
- Admin/vendor/super_admin: any order.
- Student/faculty: own orders only.

Protocol
--------
Once authenticated, the server streams events:

  {"event": "status_change", "data": {...}}
  {"event": "eta_update",     "data": {...}}
  {"event": "pickup_confirmed", "data": {...}}
  {"event": "terminal", "data": {...}}
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from app.database.session import SessionLocal
from app.modules.orders.model import Order, OrderStatus
from app.modules.orders.ws_manager import manager as ws_manager

logger = logging.getLogger("tnt.ws")

router = APIRouter(tags=["Order Tracking (WebSocket)"])

_TERMINAL_STATES = {
    OrderStatus.PICKED,
    OrderStatus.COMPLETED,
    OrderStatus.CANCELLED,
}

_SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or "dev_only_insecure_secret_do_not_use_in_production"
_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def _decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
        user_id = payload.get("sub")
        role = payload.get("role")
        if user_id is None or role is None:
            return None
        return {"id": int(user_id), "role": role}
    except (JWTError, ValueError, TypeError):
        return None


def _get_order_snapshot(order_id: int) -> Optional[dict]:
    """Return a minimal status snapshot for *order_id* from the DB."""
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return None
        return {
            "order_id": order.id,
            "user_id": order.user_id,
            "status": order.status.value if hasattr(order.status, "value") else str(order.status),
            "vendor_id": order.vendor_id,
            "total_amount": order.total_amount,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "eta_minutes": order.eta_minutes,
        }
    finally:
        db.close()


def _is_terminal(status_value: str) -> bool:
    terminal_values = {s.value for s in _TERMINAL_STATES}
    return status_value.lower() in terminal_values


@router.websocket("/ws/orders/{order_id}")
async def order_status_ws(order_id: int, websocket: WebSocket) -> None:
    """Stream real-time order status updates via Redis pub/sub push model."""
    await ws_manager.connect(order_id, websocket)
    user_ctx: Optional[dict] = None

    try:
        # ── Step 1: Authenticate ──────────────────────────────────────────
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
            auth_frame = json.loads(raw)
        except asyncio.TimeoutError:
            await websocket.send_text(json.dumps({"error": "Authentication timeout"}))
            await websocket.close(code=4001)
            return
        except (json.JSONDecodeError, Exception):
            await websocket.send_text(json.dumps({"error": "Invalid auth frame"}))
            await websocket.close(code=4001)
            return

        token = auth_frame.get("token", "")
        user_ctx = _decode_token(token)
        if user_ctx is None:
            await websocket.send_text(json.dumps({"error": "Unauthorized"}))
            await websocket.close(code=4001)
            return

        await websocket.send_text(json.dumps({
            "authenticated": True,
            "user_id": user_ctx["id"],
        }))

        # ── Step 2: Authorize ─────────────────────────────────────────────
        snapshot = _get_order_snapshot(order_id)
        if snapshot is None:
            await websocket.send_text(json.dumps({"error": "Order not found"}))
            await websocket.close(code=4004)
            return

        role = (user_ctx.get("role") or "").lower()
        is_privileged = role in {"vendor", "admin", "super_admin"}

        if not is_privileged:
            # Non-privileged users may only watch their own orders
            if snapshot.get("user_id") != user_ctx["id"]:
                await websocket.send_text(json.dumps({"error": "Forbidden — you do not own this order"}))
                await websocket.close(code=4003)
                return
        else:
            # Privileged users (vendor/admin) may watch any order, but vendors
            # are scoped to their own vendor orders.
            if role == "vendor" and snapshot.get("vendor_id") != user_ctx["id"]:
                await websocket.send_text(json.dumps({"error": "Forbidden — this order is not assigned to you"}))
                await websocket.close(code=4003)
                return

        # ── Step 3: Send initial snapshot ─────────────────────────────────
        await ws_manager.send_json(websocket, {"event": "status", "data": snapshot})

        # If terminal, close immediately
        if _is_terminal(snapshot["status"]):
            await ws_manager.send_json(websocket, {"event": "terminal", "data": snapshot})
            await websocket.close(code=1000)
            return

        # ── Step 4: Subscribe to Redis pub/sub for live events ────────────
        await ws_manager.start_redis_listener(order_id)

        # ── Step 5: Keep connection alive until client disconnects ────────
        # The Redis listener task forwards events to this connection.
        # We just wait for the client to disconnect.
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Client may send ping frames; respond with pong
                frame = json.loads(raw)
                if frame.get("type") == "ping":
                    await ws_manager.send_json(websocket, {"type": "pong"})
            except asyncio.TimeoutError:
                # Send a heartbeat ping; if it fails, client is gone
                try:
                    await ws_manager.send_json(websocket, {"type": "ping"})
                except Exception:
                    break
            except (json.JSONDecodeError, Exception):
                break

    except WebSocketDisconnect:
        logger.info("ws_client_disconnect order_id=%s", order_id)
    except Exception as exc:
        logger.exception("ws_error order_id=%s error=%s", order_id, exc)
        try:
            await websocket.send_text(json.dumps({"error": "Internal server error"}))
        except Exception:
            pass
    finally:
        ws_manager.disconnect(order_id, websocket)
