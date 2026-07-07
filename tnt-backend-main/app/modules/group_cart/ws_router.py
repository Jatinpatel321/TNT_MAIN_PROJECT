"""Real-time group-cart updates via WebSocket — event-driven.

Uses Redis pub/sub (``group:events:{group_id}``) so changes published by
``GroupCartService`` on any server instance reach every connected group
member in real time, replacing the previous client-side polling.

Authentication
--------------
First text frame must be ``{"token": "<bearer jwt>"}``.
Server responds with ``{"authenticated": true, "user_id": ...}``.

Authorization
-------------
Only members of the group may connect.

Protocol
--------
Once authenticated, the server streams events published by the service:

  {"event": "group_updated", "data": {"title": ..., "message": ...}}
  {"event": "order_placed",  "data": {...}}
  {"event": "split_finalized", "data": {...}}
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
from app.modules.group_cart.model import Group, GroupMember
from app.modules.orders.ws_manager import manager as ws_manager

logger = logging.getLogger("tnt.ws.group")

router = APIRouter(tags=["Group Cart (WebSocket)"])

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


def _group_membership_snapshot(group_id: int, user_id: int) -> Optional[dict]:
    """Return a minimal snapshot if *user_id* is a member of *group_id*, else None."""
    db = SessionLocal()
    try:
        group = db.query(Group).filter(Group.id == group_id).first()
        if not group:
            return None
        member = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        ).first()
        if not member:
            return None
        return {
            "group_id": group.id,
            "name": group.name,
            "status": group.status.value if hasattr(group.status, "value") else str(group.status),
        }
    finally:
        db.close()


@router.websocket("/ws/groups/{group_id}")
async def group_cart_ws(group_id: int, websocket: WebSocket) -> None:
    """Stream real-time group-cart updates via Redis pub/sub push model."""
    await ws_manager.connect_group(group_id, websocket)
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

        # ── Step 2: Authorize (membership) ────────────────────────────────
        snapshot = _group_membership_snapshot(group_id, user_ctx["id"])
        if snapshot is None:
            await websocket.send_text(json.dumps({"error": "Forbidden — you are not a member of this group"}))
            await websocket.close(code=4003)
            return

        # ── Step 3: Send initial snapshot ─────────────────────────────────
        await ws_manager.send_json(websocket, {"event": "connected", "data": snapshot})

        # ── Step 4: Subscribe to Redis pub/sub for live events ────────────
        await ws_manager.start_group_redis_listener(group_id)

        # ── Step 5: Keep connection alive until client disconnects ────────
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                frame = json.loads(raw)
                if frame.get("type") == "ping":
                    await ws_manager.send_json(websocket, {"type": "pong"})
            except asyncio.TimeoutError:
                try:
                    await ws_manager.send_json(websocket, {"type": "ping"})
                except Exception:
                    break
            except (json.JSONDecodeError, Exception):
                break

    except WebSocketDisconnect:
        logger.info("group_ws_client_disconnect group_id=%s", group_id)
    except Exception as exc:
        logger.exception("group_ws_error group_id=%s error=%s", group_id, exc)
        try:
            await websocket.send_text(json.dumps({"error": "Internal server error"}))
        except Exception:
            pass
    finally:
        ws_manager.disconnect_group(group_id, websocket)
