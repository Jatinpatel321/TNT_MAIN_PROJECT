"""Vendor dashboard WebSocket — real-time order queue for a single vendor.

Allows a vendor to connect once and receive ALL order events (new orders,
status changes, ETA updates, pickup confirmations) for their vendor
account in a single WebSocket connection.

Authentication
--------------
First text frame must be ``{"token": "<bearer jwt>"}``.
Server responds with ``{"authenticated": true, "user_id": ..., "vendor_id": ...}``.

Authorization
-------------
Only vendor-role users may connect. The server verifies the authenticated
user's role is "vendor" and uses their user_id as the vendor_id for
subscription.

Protocol
--------
Once authenticated, the server streams events:

  {"event": "status_change", "data": {...}}   — any of the vendor's orders changed
  {"event": "eta_update",     "data": {...}}
  {"event": "pickup_confirmed", "data": {...}}
  {"event": "new_order",      "data": {...}}  — brand-new order placed with this vendor
  {"event": "snapshot",       "data": [...]}  — full list of active orders on connect
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from app.database.session import SessionLocal
from app.modules.orders.model import Order, OrderStatus
from app.modules.orders.ws_manager import manager as ws_manager

logger = logging.getLogger("tnt.ws.vendor")

router = APIRouter(tags=["Vendor Dashboard (WebSocket)"])

_SECRET_KEY = ""
_ALGORITHM = "HS256"


def _init_crypto():
    global _SECRET_KEY, _ALGORITHM
    import os
    _SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or "dev_only_insecure_secret_do_not_use_in_production"
    _ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def _decode_token(token: str) -> Optional[dict]:
    if not _SECRET_KEY:
        _init_crypto()
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
        user_id = payload.get("sub")
        role = payload.get("role")
        if user_id is None or role is None:
            return None
        return {"id": int(user_id), "role": role}
    except (JWTError, ValueError, TypeError):
        try:
            from app.modules.vendors.auth_service import VENDOR_JWT_SECRET_KEY, VENDOR_JWT_ALGORITHM
            payload = jwt.decode(token, VENDOR_JWT_SECRET_KEY, algorithms=[VENDOR_JWT_ALGORITHM])
            vendor_id_str = payload.get("sub")
            role = payload.get("role")
            if not vendor_id_str:
                return None
            
            from app.modules.vendors.model import Vendor
            db = SessionLocal()
            try:
                vendor = db.query(Vendor).filter(Vendor.vendor_id == int(vendor_id_str)).first()
                if not vendor:
                    return None
                return {"id": vendor.owner_id, "role": "vendor"}
            finally:
                db.close()
        except Exception:
            return None


def _enrich_order(o: Order, db) -> dict:
    from app.modules.orders.model import OrderItem
    from app.modules.menu.model import MenuItem
    item_rows = db.query(OrderItem).filter(OrderItem.order_id == o.id).all()
    items = []
    for oi in item_rows:
        mi = db.query(MenuItem).filter(MenuItem.id == oi.menu_item_id).first()
        items.append({
            "menu_item_id": oi.menu_item_id,
            "name": mi.name if mi else "Unknown Item",
            "quantity": oi.quantity,
            "price_at_time": float(oi.price_at_time),
        })

    stationery_jobs = None
    if o.booking_type == "combined":
        from app.modules.stationery.job_model import StationeryJob
        sj_rows = (
            db.query(StationeryJob)
            .filter(StationeryJob.user_id == o.user_id, StationeryJob.vendor_id == o.vendor_id)
            .all()
        )
        stationery_jobs = [
            {
                "id": sj.id,
                "service_id": sj.service_id,
                "quantity": sj.quantity,
                "amount": float(sj.amount or 0),
                "status": sj.status.value if hasattr(sj.status, "value") else str(sj.status),
                "print_type": sj.print_type.value if hasattr(sj.print_type, "value") else sj.print_type,
                "paper_size": sj.paper_size.value if hasattr(sj.paper_size, "value") else sj.paper_size,
                "duplex": sj.duplex,
                "page_range": sj.page_range,
                "notes": sj.notes,
            }
            for sj in sj_rows
        ] or None

    return {
        "id": o.id,
        "user_id": o.user_id,
        "slot_id": o.slot_id,
        "vendor_id": o.vendor_id,
        "status": o.status.value if hasattr(o.status, "value") else str(o.status),
        "total_amount": float(o.total_amount),
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "eta_minutes": o.eta_minutes,
        "qr_code": o.qr_code is not None,
        "items": items,
        "group_id": o.group_id,
        "is_group": o.is_group,
        "booking_type": o.booking_type,
        "stationery_jobs": stationery_jobs,
    }


def _fetch_active_orders(vendor_id: int) -> list[dict]:
    """Return all non-terminal orders for this vendor as a list of dicts."""
    db = SessionLocal()
    try:
        orders = (
            db.query(Order)
            .filter(
                Order.vendor_id == vendor_id,
                Order.status.notin_([
                    OrderStatus.PICKED,
                    OrderStatus.COMPLETED,
                    OrderStatus.CANCELLED,
                ]),
            )
            .order_by(Order.created_at.desc())
            .limit(50)
            .all()
        )
        return [_enrich_order(o, db) for o in orders]
    finally:
        db.close()


@router.websocket("/ws/vendor/orders")
async def vendor_dashboard_ws(websocket: WebSocket) -> None:
    """Stream all order events for the authenticated vendor's dashboard."""
    user_ctx: Optional[dict] = None

    # We don't know vendor_id until authenticated — connect generically first
    await websocket.accept()

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

        # Verify vendor role
        role = (user_ctx.get("role") or "").lower()
        if role not in {"vendor", "admin", "super_admin"}:
            await websocket.send_text(json.dumps({"error": "Forbidden — vendor role required"}))
            await websocket.close(code=4003)
            return

        vendor_id = user_ctx["id"]

        await websocket.send_text(json.dumps({
            "authenticated": True,
            "user_id": vendor_id,
            "vendor_id": vendor_id,
        }))

        # ── Step 2: Register with vendor manager ──────────────────────────
        await ws_manager.connect_vendor(vendor_id, websocket)

        # ── Step 3: Send initial snapshot of active orders ────────────────
        active_orders = _fetch_active_orders(vendor_id)
        await ws_manager.send_json(websocket, {
            "event": "snapshot",
            "data": active_orders,
        })

        # ── Step 4: Subscribe to vendor Redis channel ─────────────────────
        await ws_manager.start_vendor_redis_listener(vendor_id)

        # ── Step 5: Keep connection alive ─────────────────────────────────
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
        if user_ctx:
            logger.info("vendor_ws_client_disconnect vendor_id=%s", user_ctx["id"])
    except Exception as exc:
        logger.exception("vendor_ws_error error=%s", exc)
        try:
            await websocket.send_text(json.dumps({"error": "Internal server error"}))
        except Exception:
            pass
    finally:
        if user_ctx:
            ws_manager.disconnect_vendor(user_ctx["id"], websocket)
