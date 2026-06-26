"""
app/modules/orders/order_service.py
====================================
Domain service layer for the Orders module (PROMPT 12).

All business logic that previously lived inline in orders/router.py lives here.
The router becomes a thin HTTP adapter: it resolves dependencies (auth, DB)
then delegates everything to this module.

Public surface:
  place_order          — student places a new order
  get_my_orders        — student fetches their orders
  get_vendor_orders    — vendor fetches incoming orders
  confirm_order        — vendor confirms a PLACED order
  mark_order_ready     — vendor marks order as READY for pickup
  cancel_order         — student (or admin) cancels an order
  get_order_timeline   — student views status history
  reorder              — student duplicates a past order
  get_order_eta        — student queries live ETA
  get_vendor_order_detail — vendor gets detailed view of a single order
  generate_order_qr    — student generates a QR code for pickup
  confirm_qr_pickup    — vendor scans QR to mark PICKED
  get_order_by_qr_code — vendor resolves an order from a QR code
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.load_insights import get_load_label, is_express_pickup_eligible
from app.core.observability import observability
from app.core.time_utils import utcnow_naive
from app.modules.notifications.model import NotificationType
from app.modules.notifications.service import notify_user
from sqlalchemy import func

from app.modules.orders.checkout_service import checkout_order_for_user
from app.modules.orders.history_model import OrderHistory
from app.modules.orders.model import Order, OrderStatus
from app.modules.orders.qr_service import (
    confirm_pickup,
    generate_qr_code,
    get_order_by_qr,
)
from app.modules.orders.reorder_service import create_reorder
from app.modules.orders.reorder_service import get_order_eta as _get_order_eta
from app.modules.orders.service import update_order_status
from app.modules.users.model import User
from app.core.db_transaction import transactional
from app.core.order_events import (
    publish_order_status_change,
    publish_eta_update,
    publish_pickup_confirmed,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _require_user(user: dict, db: Session) -> User:
    """Resolve the authenticated user dict → ORM User; raises 404 if missing."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


def _require_vendor(user: dict, db: Session) -> User:
    """Resolve vendor from auth context; raises 404 if missing."""
    vendor = db.query(User).filter(User.phone == user["phone"]).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


def _require_own_order(order_id: int, db_user: User, db: Session) -> Order:
    """Fetch *order_id*, asserting it belongs to *db_user*; raises 404 otherwise."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or order.user_id != db_user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def _require_vendor_order(order_id: int, vendor: User, db: Session) -> Order:
    """Fetch *order_id* scoped to *vendor*; 404 on miss (security masking)."""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.vendor_id == vendor.id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# ──────────────────────────────────────────────────────────────────────────────
# Student-facing operations
# ──────────────────────────────────────────────────────────────────────────────

def place_order(
    user: dict,
    slot_id: int,
    items: list,
    idempotency_key: str | None,
    db: Session,
) -> dict:
    """Place a new order for *user* into *slot_id* with *items*."""
    from app.core.redis import redis_client

    db_user = _require_user(user, db)

    # Idempotency guard — prevents duplicate orders from network retries
    idempotency_cache_key = None
    if idempotency_key:
        idempotency_cache_key = f"idempotency:order:{user['phone']}:{idempotency_key}"
        if redis_client.exists(idempotency_cache_key):
            raise HTTPException(status_code=409, detail="Duplicate request")

    order, slot, total_amount, eta_minutes = checkout_order_for_user(db_user, slot_id, items, db)

    if idempotency_cache_key:
        redis_client.setex(idempotency_cache_key, 3600, str(order.id))

    notify_user(
        user_id=db_user.id,
        phone=db_user.phone,
        title="Order Placed",
        message=f"Your order #{order.id} has been placed successfully. ETA: {eta_minutes} minutes.",
        db=db,
        send_sms_flag=False,
        notification_type=NotificationType.ORDER_PLACED,
        reference_id=order.id,
    )
    # Commit the notification created above (checkout_order_for_user already
    # committed the order itself via @transactional; this is a second, smaller
    # commit just for the notification row).
    db.commit()

    return {
        "order_id": order.id,
        "status": order.status,
        "total_amount": total_amount,
        "eta_minutes": eta_minutes,
        "pickup_load_label": get_load_label(slot.current_orders, slot.max_orders),
        "express_pickup_eligible": is_express_pickup_eligible(slot.current_orders, slot.max_orders),
    }


def get_my_orders(user: dict, db: Session) -> list[dict]:
    """Return all orders belonging to the authenticated student, enriched with items, vendor name, ETA, and delay status."""
    from app.modules.menu.model import MenuItem
    from app.modules.orders.model import OrderItem
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    orders = (
        db.query(Order)
        .filter(Order.user_id == db_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    result = []
    for order in orders:
        vendor = db.query(User).filter(User.id == order.vendor_id).first()
        vendor_name = vendor.name if vendor else f"Vendor #{order.vendor_id}"
        order_items_rows = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        items = []
        for oi in order_items_rows:
            mi = db.query(MenuItem).filter(MenuItem.id == oi.menu_item_id).first()
            items.append({
                "menu_item_id": oi.menu_item_id,
                "name": mi.name if mi else "Unknown Item",
                "quantity": oi.quantity,
                "price_at_time": oi.price_at_time,
                "line_total": float(oi.price_at_time) * oi.quantity,
            })

        is_delayed = False
        if order.eta_minutes and order.status not in {OrderStatus.PICKED, OrderStatus.COMPLETED, OrderStatus.CANCELLED}:
            from app.core.time_utils import utcnow_naive
            from datetime import timedelta
            eta_time = order.created_at + timedelta(minutes=order.eta_minutes) if order.created_at else None
            if eta_time and utcnow_naive() > eta_time:
                is_delayed = True

        # Fetch stationery jobs for combined orders
        stationery_jobs = None
        if order.booking_type == "combined":
            from app.modules.stationery.job_model import StationeryJob
            sj_rows = (
                db.query(StationeryJob)
                .filter(
                    StationeryJob.user_id == order.user_id,
                    StationeryJob.vendor_id == order.vendor_id,
                )
                .all()
            )
            stationery_jobs = [
                {
                    "id": sj.id,
                    "service_id": sj.service_id,
                    "quantity": sj.quantity,
                    "amount": sj.amount or 0,
                    "status": sj.status.value if hasattr(sj.status, "value") else str(sj.status),
                }
                for sj in sj_rows
            ]

        result.append({
            "id": order.id,
            "user_id": order.user_id,
            "slot_id": order.slot_id,
            "vendor_id": order.vendor_id,
            "vendor_name": vendor_name,
            "status": order.status.value if hasattr(order.status, "value") else str(order.status),
            "created_at": order.created_at,
            "total_amount": order.total_amount,
            "qr_code": order.qr_code,
            "items": items,
            "eta_minutes": order.eta_minutes,
            "is_delayed": is_delayed,
            "booking_type": order.booking_type or "food",
            "stationery_jobs": stationery_jobs,
        })
    return result


@transactional
def cancel_order(user: dict, order_id: int, db: Session) -> dict:
    """Cancel *order_id* on behalf of the authenticated student."""
    db_user = _require_user(user, db)
    order = _require_own_order(order_id, db_user, db)

    update_order_status(order, OrderStatus.CANCELLED, "student", db)

    notify_user(
        user_id=db_user.id,
        phone=db_user.phone,
        title="Order Cancelled",
        message=f"Your order #{order.id} has been cancelled.",
        db=db,
        send_sms_flag=True,
        notification_type=NotificationType.ORDER_CANCELLED,
        reference_id=order.id,
    )
    return {"message": "Order cancelled"}


def get_order_timeline(user: dict, order_id: int, db: Session) -> list[OrderHistory]:
    """Return the status-history timeline for *order_id* (student view)."""
    db_user = _require_user(user, db)
    _require_own_order(order_id, db_user, db)  # ownership check

    return (
        db.query(OrderHistory)
        .filter(OrderHistory.order_id == order_id)
        .order_by(OrderHistory.changed_at)
        .all()
    )


def reorder(user: dict, order_id: int, db: Session) -> dict:
    """Duplicate a past order as a new placement."""
    db_user = _require_user(user, db)
    return create_reorder(order_id, db_user.id, db)


def get_order_eta(user: dict, order_id: int, db: Session) -> dict:
    """Return a live ETA estimate for *order_id*."""
    db_user = _require_user(user, db)
    return _get_order_eta(order_id, db_user.id, db)


def generate_order_qr(order_id: int, db: Session) -> dict:
    """Generate (or return cached) QR code for student pickup."""
    try:
        qr_code = generate_qr_code(order_id, db)
        return {"qr_code": qr_code}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ──────────────────────────────────────────────────────────────────────────────
# Vendor-facing operations
# ──────────────────────────────────────────────────────────────────────────────

def get_vendor_orders(user: dict, db: Session) -> list[Order]:
    """Return all orders assigned to the authenticated vendor."""
    vendor = db.query(User).filter(User.phone == user["phone"]).first()
    return (
        db.query(Order)
        .filter(Order.vendor_id == vendor.id)
        .order_by(Order.created_at.desc())
        .all()
    )


@transactional
def confirm_order(user: dict, order_id: int, db: Session) -> dict:
    """Vendor confirms a PLACED order → CONFIRMED."""
    vendor = _require_vendor(user, db)
    order = _require_vendor_order(order_id, vendor, db)

    # Record latency from order placement to vendor confirmation.
    if order.created_at is not None:
        latency_ms = (utcnow_naive() - order.created_at).total_seconds() * 1000
        observability.record_vendor_confirmation(latency_ms)

    update_order_status(order, OrderStatus.CONFIRMED, "vendor", db)

    student = db.query(User).filter(User.id == order.user_id).first()
    notify_user(
        user_id=student.id,
        phone=student.phone,
        title="Order Confirmed",
        message=f"Your order #{order.id} has been confirmed.",
        db=db,
        send_sms_flag=False,
        notification_type=NotificationType.ORDER_ACCEPTED,
        reference_id=order.id,
    )
    return {"message": "Order confirmed"}


@transactional
def mark_order_preparing(user: dict, order_id: int, db: Session) -> dict:
    """Vendor marks a CONFIRMED order as PREPARING."""
    vendor = _require_vendor(user, db)
    order = _require_vendor_order(order_id, vendor, db)

    update_order_status(order, OrderStatus.PREPARING, "vendor", db)

    student = db.query(User).filter(User.id == order.user_id).first()
    notify_user(
        user_id=student.id,
        phone=student.phone,
        title="Order Preparing",
        message=f"Your order #{order.id} is being prepared.",
        db=db,
        send_sms_flag=False,
        notification_type=NotificationType.ORDER_PREPARING,
        reference_id=order.id,
    )
    return {"message": "Order marked as preparing"}


@transactional
def mark_order_ready(user: dict, order_id: int, db: Session) -> dict:
    """Vendor marks a PREPARING order as READY for pickup."""
    vendor = _require_vendor(user, db)
    order = _require_vendor_order(order_id, vendor, db)

    update_order_status(order, OrderStatus.READY, "vendor", db)

    student = db.query(User).filter(User.id == order.user_id).first()
    notify_user(
        user_id=student.id,
        phone=student.phone,
        title="Order Ready",
        message=f"Your order #{order.id} is ready for pickup!",
        db=db,
        send_sms_flag=True,
        notification_type=NotificationType.ORDER_READY,
        reference_id=order.id,
    )
    return {"message": "Order marked as ready"}


def get_vendor_order_detail(user: dict, order_id: int, db: Session) -> dict:
    """Return detailed view of a single order for the vendor."""
    from app.modules.orders.details_service import get_vendor_order_details

    vendor = _require_vendor(user, db)
    if not vendor.is_approved:
        raise HTTPException(status_code=403, detail="Vendor not approved")
    return get_vendor_order_details(order_id, vendor.id, db)


@transactional
def confirm_qr_pickup(user: dict, qr_code: str, db: Session) -> dict:
    """Vendor scans QR → marks order as PICKED."""
    vendor = _require_vendor(user, db)
    success = confirm_pickup(qr_code, vendor.id, db)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid QR code or pickup not allowed")
    return {"message": "Pickup confirmed successfully"}


def get_order_by_qr_code(user: dict, qr_code: str, db: Session) -> dict:
    """Resolve and return order details from a QR code (vendor view)."""
    vendor = _require_vendor(user, db)
    order = get_order_by_qr(qr_code, db)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.vendor_id != vendor.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return {
        "order_id": order.id,
        "user_id": order.user_id,
        "status": order.status.value,
        "created_at": order.created_at.isoformat(),
    }


def get_vendor_analytics(user: dict, db: Session) -> dict:
    """Return order analytics for the authenticated vendor.

    Metrics returned
    ----------------
    total_orders        — all-time order count
    pending_orders      — orders awaiting confirmation (PLACED)
    confirmed_orders    — orders currently in CONFIRMED state
    ready_orders        — orders currently in READY state
    completed_orders    — terminal orders (PICKED + COMPLETED)
    cancelled_orders    — terminal cancelled orders
    total_revenue_paise — sum of total_amount for non-cancelled orders
    completion_rate_pct — completed / (completed + cancelled) * 100
    avg_confirmation_ms — avg latency from placement to confirmation
    peak_hour           — hour of day (0-23) with the most orders placed
    busiest_day         — weekday name with the most orders placed
    recent_orders       — last 10 orders (id, status, amount, created_at)
    """
    from app.modules.orders.history_model import OrderHistory
    from app.core.time_utils import utcnow_naive

    vendor = _require_vendor(user, db)

    orders = (
        db.query(Order)
        .filter(Order.vendor_id == vendor.id)
        .all()
    )

    total = len(orders)
    state_counts = {
        "PLACED": 0, "PENDING": 0,
        "CONFIRMED": 0,
        "PREPARING": 0,
        "READY": 0, "READY_FOR_PICKUP": 0,
        "PICKED": 0, "COMPLETED": 0,
        "CANCELLED": 0,
    }
    total_revenue = 0
    hour_counter: dict[int, int] = {}
    day_counter: dict[str, int] = {}
    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for o in orders:
        status_val = o.status.value.upper() if hasattr(o.status, "value") else str(o.status).upper()
        if status_val in state_counts:
            state_counts[status_val] += 1

        if status_val not in {"CANCELLED"}:
            total_revenue += int(o.total_amount or 0)

        if o.created_at:
            h = o.created_at.hour
            hour_counter[h] = hour_counter.get(h, 0) + 1
            day_name = DAYS[o.created_at.weekday()]
            day_counter[day_name] = day_counter.get(day_name, 0) + 1

    completed = state_counts["PICKED"] + state_counts["COMPLETED"]
    cancelled = state_counts["CANCELLED"]
    pending = state_counts["PLACED"] + state_counts["PENDING"]
    preparing = state_counts["CONFIRMED"] + state_counts["PREPARING"]
    ready = state_counts["READY"] + state_counts["READY_FOR_PICKUP"]
    denominator = completed + cancelled
    completion_rate = round(completed / denominator * 100, 1) if denominator else 0.0

    # Average confirmation latency from OrderHistory records
    confirm_histories = (
        db.query(OrderHistory)
        .join(Order, Order.id == OrderHistory.order_id)
        .filter(
            Order.vendor_id == vendor.id,
            OrderHistory.status == OrderStatus.CONFIRMED,
        )
        .all()
    )
    total_latency_ms = 0.0
    latency_count = 0
    for h in confirm_histories:
        parent = db.query(Order).filter(Order.id == h.order_id).first()
        if parent and parent.created_at and h.changed_at:
            diff_ms = (h.changed_at - parent.created_at).total_seconds() * 1000
            total_latency_ms += diff_ms
            latency_count += 1
    avg_confirmation_ms = round(total_latency_ms / latency_count, 1) if latency_count else None

    peak_hour = max(hour_counter, key=hour_counter.get) if hour_counter else None
    busiest_day = max(day_counter, key=day_counter.get) if day_counter else None

    recent = sorted(orders, key=lambda o: o.created_at or utcnow_naive(), reverse=True)[:10]
    recent_orders = [
        {
            "order_id": o.id,
            "status": o.status.value if hasattr(o.status, "value") else str(o.status),
            "total_amount": o.total_amount,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in recent
    ]

    return {
        "vendor_id": vendor.id,
        "total_orders": total,
        "pending_orders": pending,
        "confirmed_orders": state_counts["CONFIRMED"],
        "preparing_orders": preparing,
        "ready_orders": ready,
        "completed_orders": completed,
        "cancelled_orders": cancelled,
        "total_revenue_paise": total_revenue,
        "completion_rate_pct": completion_rate,
        "avg_confirmation_ms": avg_confirmation_ms,
        "peak_hour": peak_hour,
        "busiest_day": busiest_day,
        "recent_orders": recent_orders,
    }
