from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.load_insights import get_load_label, is_express_pickup_eligible
from app.core.time_utils import utcnow_naive
from app.modules.notifications.model import Notification
from app.modules.notifications.service import notify_user
from app.modules.orders.item_service import add_items_to_order
from app.modules.orders.model import Order, OrderStatus
from app.modules.orders.service import create_order
from app.modules.users.model import User


def calculate_eta(order: Order, db: Session) -> datetime:
    """Calculate estimated time of arrival for order completion"""
    from app.modules.slots.model import Slot

    slot = db.query(Slot).filter(Slot.id == order.slot_id).first()
    if not slot:
        # Default ETA: 30 minutes from now
        return utcnow_naive() + timedelta(minutes=30)

    # Base ETA is slot end time
    base_eta = slot.end_time

    # Add preparation time based on order complexity
    from app.modules.orders.item_service import get_order_items
    items = get_order_items(order.id, db)

    # Simple heuristic: 2 minutes per item + 5 minutes base
    prep_time = len(items) * 2 + 5
    eta = base_eta + timedelta(minutes=prep_time)

    return eta


def detect_delay(order: Order, db: Session) -> bool:
    """Detect if order is delayed beyond ETA"""
    estimated_ready_at = getattr(order, "estimated_ready_at", None)
    if not estimated_ready_at:
        return False

    # Order is delayed if current time > ETA + 10 minutes buffer
    delay_threshold = estimated_ready_at + timedelta(minutes=10)
    return utcnow_naive() > delay_threshold


def create_reorder(original_order_id: int, user_id: int, db: Session):
    """Create a reorder from an existing completed order"""

    # Find original order (eligible if picked/completed)
    original_order = db.query(Order).filter(
        Order.id == original_order_id,
        Order.user_id == user_id,
        Order.status.in_([OrderStatus.PICKED, OrderStatus.COMPLETED])
    ).first()

    if not original_order:
        raise HTTPException(status_code=404, detail="Original order not found or not eligible for reorder")

    # Check if original order is recent (within 7 days)
    seven_days_ago = utcnow_naive() - timedelta(days=7)
    if original_order.created_at < seven_days_ago:
        raise HTTPException(status_code=400, detail="Order is too old for reorder")

    # Get original order items
    from app.modules.orders.item_service import get_order_items
    original_items = get_order_items(original_order_id, db)

    if not original_items:
        raise HTTPException(status_code=400, detail="No items found in original order")

    # Find available slot (same vendor, similar time)
    from app.modules.slots.model import Slot
    now = utcnow_naive()

    # Look for slots in next 2 hours from same vendor
    available_slots = db.query(Slot).filter(
        Slot.vendor_id == original_order.vendor_id,
        Slot.start_time > now,
        Slot.start_time < now + timedelta(hours=2),
        Slot.current_orders < Slot.max_orders
    ).order_by(Slot.start_time).limit(5).all()

    if not available_slots:
        raise HTTPException(status_code=400, detail="No available slots for reorder")

    # Use first available slot
    target_slot = available_slots[0]

    try:
        # Create new order
        new_order = create_order(user_id, target_slot.id, db)

        # Copy items from original order
        from app.modules.orders.item_schemas import OrderItemCreate
        reorder_items = [
            OrderItemCreate(
                menu_item_id=item.menu_item_id,
                quantity=item.quantity
            ) for item in original_items
        ]

        total_amount = add_items_to_order(new_order, reorder_items, db)
        new_order.total_amount = total_amount

        # Calculate ETA
        eta = calculate_eta(new_order, db)
        setattr(new_order, "estimated_ready_at", eta)

        db.commit()
        db.refresh(new_order)

        # Notify user
        user = db.query(User).filter(User.id == new_order.user_id).first()
        if user:
            notify_user(
                user_id=user.id,
                phone=user.phone,
                title="Reorder Placed",
                message=f"Your reorder #{new_order.id} has been placed successfully.",
                db=db
            )

        return {
            "order_id": new_order.id,
            "status": new_order.status.value,
            "total_amount": total_amount,
            "estimated_ready_at": eta.isoformat(),
            "slot_time": f"{target_slot.start_time.strftime('%I:%M %p')} - {target_slot.end_time.strftime('%I:%M %p')}",
            "pickup_load_label": get_load_label(target_slot.current_orders, target_slot.max_orders),
            "express_pickup_eligible": is_express_pickup_eligible(target_slot.current_orders, target_slot.max_orders),
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create reorder: {str(e)}")


def get_order_eta(order_id: int, user_id: int, db: Session):
    """Get ETA for an order"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == user_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Order was cancelled")

    # Calculate ETA if not set
    estimated_ready_at = getattr(order, "estimated_ready_at", None)
    if not estimated_ready_at:
        estimated_ready_at = calculate_eta(order, db)
        setattr(order, "estimated_ready_at", estimated_ready_at)

    # Check for delays and slot timing
    is_delayed = detect_delay(order, db)
    from app.modules.slots.model import Slot

    slot = db.query(Slot).filter(Slot.id == order.slot_id).first()
    now = utcnow_naive()

    slot_reminder_sent = False
    delay_alert_sent = False

    # ── Slot reminder (5–15 minutes before slot start) ───────────────────
    if slot and slot.start_time:
        minutes_to_start = (slot.start_time - now).total_seconds() / 60.0
        if 0 < minutes_to_start <= 15:
            existing = (
                db.query(Notification)
                .filter(
                    Notification.user_id == order.user_id,
                    Notification.title == "Slot Reminder",
                    Notification.message.like(f"%order #{order.id}%"),
                )
                .first()
            )
            if not existing:
                user = db.query(User).filter(User.id == order.user_id).first()
                if user:
                    notify_user(
                        user_id=user.id,
                        phone=user.phone,
                        title="Slot Reminder",
                        message=(
                            f"Reminder: your order #{order.id} pickup slot starts at "
                            f"{slot.start_time.strftime('%I:%M %p')}.") ,
                        db=db,
                    )
                    slot_reminder_sent = True

    # ── Delay alert (when order is running late) ─────────────────────────
    delay_minutes = 0.0
    if is_delayed:
        delay_minutes = max(0.0, (now - estimated_ready_at).total_seconds() / 60.0)
        existing_delay = (
            db.query(Notification)
            .filter(
                Notification.user_id == order.user_id,
                Notification.title == "Order Delayed",
                Notification.message.like(f"%order #{order.id}%"),
            )
            .first()
        )
        if not existing_delay:
            user = db.query(User).filter(User.id == order.user_id).first()
            if user:
                notify_user(
                    user_id=user.id,
                    phone=user.phone,
                    title="Order Delayed",
                    message=(
                        f"Your order #{order.id} is running about "
                        f"{delay_minutes:.0f} minutes late. We are sorry for the delay."),
                    db=db,
                )
                delay_alert_sent = True

    if slot_reminder_sent or delay_alert_sent:
        db.commit()

    return {
        "order_id": order.id,
        "status": order.status.value,
        "estimated_ready_at": estimated_ready_at.isoformat(),
        "is_delayed": is_delayed,
        "delay_minutes": delay_minutes if is_delayed else 0,
        "pickup_load_label": get_load_label(slot.current_orders, slot.max_orders) if slot else "LOW",
        "express_pickup_eligible": is_express_pickup_eligible(slot.current_orders, slot.max_orders) if slot else False,
    }
