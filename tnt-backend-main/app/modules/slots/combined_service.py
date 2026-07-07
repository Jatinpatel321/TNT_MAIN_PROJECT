"""Combined booking service — books food items AND a stationery job against the SAME slot window.

This module implements the core business logic for the ``POST /slots/combined-booking``
endpoint.  It reuses existing slot capacity logic, order creation, and stationery
job creation while validating capacity for both sub-orders before committing anything.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.db_transaction import transactional
from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderStatus
from app.modules.orders.service import create_order, update_order_status
from app.modules.slots.model import Slot, SlotBooking, BookingType, BookingStatus
from app.modules.slots.service import _book_slot_internal, _apply_capacity_rules
from app.modules.stationery.job_model import StationeryJob, JobStatus
from app.modules.stationery.service_model import StationeryService
from app.modules.users.model import User
from app.modules.menu.model import MenuItem


def _calculate_food_total(user_id: int, food_items: list[dict], db: Session) -> tuple[int, list[dict]]:
    """Validate food items, calculate total, and return enriched items.

    Returns:
        Tuple of (total_amount_paise, enriched_items_list)
    """
    total = 0
    enriched = []
    for item in food_items:
        menu_item_id = item["menu_item_id"]
        quantity = item["quantity"]
        menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
        if not menu_item:
            raise HTTPException(status_code=404, detail=f"Menu item {menu_item_id} not found")
        if not menu_item.is_available:
            raise HTTPException(status_code=400, detail=f"Menu item '{menu_item.name}' is not available")
        if menu_item.available_quantity is not None and menu_item.available_quantity < quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for '{menu_item.name}'")

        line_total = int(menu_item.price) * quantity
        total += line_total
        enriched.append({
            "menu_item_id": menu_item_id,
            "name": menu_item.name,
            "quantity": quantity,
            "price_at_time": float(menu_item.price),
            "line_total": line_total,
        })
    return total, enriched


def _calculate_stationery_total(
    vendor_id: int,
    stationery_items: list[dict],
    db: Session,
) -> tuple[list[StationeryJob], int]:
    """Validate stationery items, create (uncommitted) StationeryJob rows, return total.

    The jobs are added to the session but NOT committed — the caller's
    ``@transactional`` decorator will commit everything atomically.
    """
    jobs: list[StationeryJob] = []
    total = 0
    for item in stationery_items:
        service_id = item["service_id"]
        quantity = item["quantity"]
        service = db.query(StationeryService).filter(
            StationeryService.id == service_id,
            StationeryService.is_available == True,
        ).first()
        if not service:
            raise HTTPException(status_code=404, detail=f"Stationery service {service_id} not found or unavailable")

        # Use price_per_unit if available, else price_per_page * quantity heuristic
        unit_price = service.price_per_unit or service.price_per_page or 0
        line_total = int(unit_price) * quantity
        total += line_total

        job = StationeryJob(
            user_id=0,  # placeholder — set after we resolve the user
            vendor_id=vendor_id,
            service_id=service.id,
            quantity=quantity,
            file_url=item.get("file_url"),
            amount=line_total,
            is_paid=False,
            status=JobStatus.SUBMITTED,
        )
        jobs.append(job)
    return jobs, total


@transactional
def create_combined_booking(
    user_id: int,
    slot_id: int,
    food_items: list[dict],
    stationery_items: list[dict],
    db: Session,
) -> dict:
    """Execute a combined booking — validates capacity, creates order + stationery jobs.

    Steps:
    1. Validate slot exists, is not locked, has capacity (accounting for rules).
    2. Validate both food items and stationery items in a single transaction.
    3. Reserve the slot (increments ``current_orders``).
    4. Create the Order (with booking_type='combined').
    5. Create StationeryJob rows and link them to the Order.
    6. Update slot booking with booking_type='combined'.
    7. All-or-nothing commit.

    Returns a dict matching ``CombinedBookingResponse``.
    """
    # ── 1. Validate slot ─────────────────────────────────────────────────
    slot = db.query(Slot).filter(Slot.id == slot_id).with_for_update().first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot.is_locked:
        raise HTTPException(status_code=423, detail="Slot is currently locked by vendor")

    effective_max = _apply_capacity_rules(slot, user_id, db)
    if slot.current_orders >= effective_max:
        raise HTTPException(status_code=400, detail="Slot is full — cannot book")

    # ── 2. Validate no duplicate booking for this user/slot ──────────────
    existing = db.query(SlotBooking).filter(
        SlotBooking.slot_id == slot_id,
        SlotBooking.user_id == user_id,
        SlotBooking.status == BookingStatus.CONFIRMED,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="You already have an active booking for this slot")

    # ── 3. Validate food items ───────────────────────────────────────────
    vendor_id = slot.vendor_id
    vendor = db.query(User).filter(User.id == vendor_id).first()
    if not vendor or not vendor.is_active or not vendor.is_approved:
        raise HTTPException(status_code=400, detail="Vendor is not available")

    food_total, enriched_food = _calculate_food_total(user_id, food_items, db)

    # ── 4. Validate and create stationery jobs ───────────────────────────
    stationery_jobs, stationery_total = _calculate_stationery_total(vendor_id, stationery_items, db)

    total_amount = food_total + stationery_total

    # ── 5. Reserve the slot (uses existing Redis-based slot lock) ─────────
    slot, booking = _book_slot_internal(slot_id, user_id, db, commit=False, order_id=None)

    # ── 6. Create the Order with combined flag ───────────────────────────
    order = create_order(user_id=user_id, slot_id=slot_id, db=db)
    order.total_amount = total_amount
    order.booking_type = "combined"

    # Link stationery jobs to the order and set user_id
    stationery_job_ids: list[int] = []
    for idx, job in enumerate(stationery_jobs):
        job.user_id = user_id
        db.add(job)
        db.flush()  # get job.id
        stationery_job_ids.append(job.id)

        # Link first stationery job via order.stationery_job_id for backward compat
        if idx == 0:
            order.stationery_job_id = job.id

    # ── 7. Create OrderItem rows for food items ──────────────────────────
    from app.modules.orders.model import OrderItem
    for fi in enriched_food:
        oi = OrderItem(
            order_id=order.id,
            menu_item_id=fi["menu_item_id"],
            quantity=fi["quantity"],
            price_at_time=fi["price_at_time"],
        )
        db.add(oi)

    # ── 8. Update the SlotBooking with booking_type = combined ───────────
    booking.booking_type = BookingType.COMBINED
    booking.order_id = order.id

    # Set ETA
    congestion_factor = slot.congestion_level if hasattr(slot, "congestion_level") else 0
    order.eta_minutes = 15 + int(congestion_factor / 10)

    # ── 9. Notify ────────────────────────────────────────────────────────
    from app.modules.notifications.model import NotificationType
    from app.modules.notifications.service import notify_user
    notify_user(
        user_id=user_id,
        phone=vendor.phone,  # notification to vendor
        title="New Combined Order",
        message=f"Combined order #{order.id} (food + stationery) placed.",
        db=db,
        notification_type=NotificationType.ORDER_PLACED,
        reference_id=order.id,
    )

    # Note: @transactional decorator commits here

    db.flush()
    db.refresh(order)

    return {
        "message": "Combined booking successful",
        "order_id": order.id,
        "stationery_job_ids": stationery_job_ids,
        "slot_id": slot.id,
        "booking_id": booking.id,
        "total_amount": total_amount,
        "status": order.status.value if hasattr(order.status, "value") else str(order.status),
    }
