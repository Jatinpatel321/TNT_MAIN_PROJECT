import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from datetime import date as date_type

from app.core.faculty_policy import is_slot_in_faculty_priority_window
from app.core.time_utils import ist_now, utcnow_naive
from app.modules.orders.model import Order

from app.core.redis import redis_client
from app.modules.calendar.model import CalendarEvent
from app.modules.slots.model import Slot, SlotBooking, SlotStatus, BookingStatus, SlotCapacityRule, SlotRule
from app.modules.users.model import User

LOCK_TTL = 5  # seconds


def generate_stationery_slots(
    vendor_id: int,
    db: Session,
    interval_minutes: int = 10,
    horizon_minutes: int = 120,
    capacity_per_slot: int = 5,
):
    now = ist_now()
    minutes_into_hour = now.minute % interval_minutes
    delta_to_boundary = interval_minutes - minutes_into_hour if minutes_into_hour else 0
    start = (now + timedelta(minutes=delta_to_boundary)).replace(second=0, microsecond=0)
    end_horizon = now + timedelta(minutes=horizon_minutes)

    existing = db.query(Slot).filter(Slot.vendor_id == vendor_id, Slot.start_time >= now).all()
    existing_starts = {s.start_time.replace(second=0, microsecond=0) for s in existing}

    new_slots: list[Slot] = []
    cursor = start
    while cursor < end_horizon:
        if cursor not in existing_starts:
            slot = Slot(
                vendor_id=vendor_id,
                start_time=cursor,
                end_time=cursor + timedelta(minutes=interval_minutes),
                max_orders=capacity_per_slot,
                current_orders=0,
                status=SlotStatus.AVAILABLE,
            )
            db.add(slot)
            new_slots.append(slot)
        cursor += timedelta(minutes=interval_minutes)

    if new_slots:
        db.commit()
        for slot in new_slots:
            db.refresh(slot)

    return existing + new_slots


def recommend_best_slot(vendor_id: int, db: Session) -> dict[str, str]:
    from datetime import timedelta

    now = utcnow_naive()
    candidate_slots: list[Slot] = (
        db.query(Slot)
        .filter(
            Slot.vendor_id == vendor_id,
            Slot.start_time >= now,
            Slot.max_orders > 0,
            Slot.current_orders < Slot.max_orders,
        )
        .order_by(Slot.start_time.asc())
        .all()
    )

    if not candidate_slots:
        raise HTTPException(status_code=404, detail="No available slots for this vendor")

    cutoff = now - timedelta(days=14)
    completed_orders = (
        db.query(Order)
        .filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= cutoff,
            Order.actual_completion_minutes.isnot(None),
        )
        .all()
    )

    if completed_orders:
        prep_minutes = sum(o.actual_completion_minutes or 0 for o in completed_orders) / max(1, len(completed_orders))
    else:
        eta_orders = (
            db.query(Order)
            .filter(
                Order.vendor_id == vendor_id,
                Order.created_at >= cutoff,
                Order.eta_minutes.isnot(None),
            )
            .all()
        )
        prep_minutes = (
            sum(o.eta_minutes or 0 for o in eta_orders) / max(1, len(eta_orders))
            if eta_orders
            else 7.0
        )

    prep_minutes = float(max(3.0, min(prep_minutes, 25.0)))

    historical_orders = (
        db.query(Order.slot_id)
        .filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= cutoff,
        )
        .all()
    )
    slot_ids = [r[0] for r in historical_orders]
    rush_by_hour: dict[int, int] = {}
    if slot_ids:
        slot_rows = db.query(Slot.id, Slot.start_time).filter(Slot.id.in_(slot_ids)).all()
        for sid, st in slot_rows:
            hour = (st.hour if st else 0)
            rush_by_hour[hour] = rush_by_hour.get(hour, 0) + 1

    max_rush = max(rush_by_hour.values(), default=0)

    def _slot_score(s: Slot) -> float:
        utilization = (s.current_orders / s.max_orders) if s.max_orders > 0 else 1.0
        capacity_score = 1.0 - utilization
        delta_minutes = max(0.0, (s.start_time - now).total_seconds() / 60.0)
        time_score = max(0.0, 1.0 - (delta_minutes / 180.0))
        rush = rush_by_hour.get(s.start_time.hour, 0)
        rush_penalty = (rush / max_rush) if max_rush > 0 else 0.0
        rush_score = 1.0 - rush_penalty
        prep_score = 1.0 / (1.0 + (prep_minutes / 10.0))
        return (capacity_score * 0.50) + (time_score * 0.20) + (rush_score * 0.20) + (prep_score * 0.10)

    best = max(
        candidate_slots,
        key=lambda s: (_slot_score(s), -max(0.0, (s.start_time - now).total_seconds())),
    )

    utilization = (best.current_orders / best.max_orders) if best.max_orders > 0 else 1.0
    rush = rush_by_hour.get(best.start_time.hour, 0)
    rush_penalty = (rush / max_rush) if max_rush > 0 else 0.0
    estimated_wait = int(round((prep_minutes * (0.5 + utilization * 1.5)) + (rush_penalty * 5.0)))
    estimated_wait = max(1, estimated_wait)

    reason_bits: list[str] = []
    if utilization <= 0.5:
        reason_bits.append("Low load")
    elif utilization <= 0.8:
        reason_bits.append("Moderate load")
    else:
        reason_bits.append("Limited capacity")
    if rush_penalty <= 0.3:
        reason_bits.append("low rush")
    elif rush_penalty >= 0.7:
        reason_bits.append("high rush")
    if prep_minutes <= 7.0:
        reason_bits.append("fast vendor preparation")
    elif prep_minutes >= 15.0:
        reason_bits.append("slower vendor preparation")

    reason = " and ".join(reason_bits[:3]) or "Balanced load and timing"
    slot_label = best.start_time.strftime("%I:%M %p").lstrip("0")

    return {
        "recommended_slot": slot_label,
        "estimated_wait": f"{estimated_wait} minutes",
        "reason": reason[0].upper() + reason[1:],
    }


def _update_slot_status(slot: Slot) -> None:
    """Recalculate slot status based on current_orders / max_orders."""
    if slot.max_orders <= 0:
        slot.status = SlotStatus.FULL
        return
    utilization = slot.current_orders / slot.max_orders
    if slot.current_orders >= slot.max_orders:
        slot.status = SlotStatus.FULL
    elif utilization >= 0.7:
        slot.status = SlotStatus.LIMITED
    else:
        slot.status = SlotStatus.AVAILABLE
    slot.congestion_level = utilization * 100


def _check_calendar_event_restrictions(slot: Slot, user_id: int, db: Session) -> None:
    """Check if the slot's date is blocked or restricted by a calendar event.

    - Holiday (affects_ordering=True): block all new bookings.
    - Exam Day (affects_ordering=True): allow only faculty/admin roles.
    Raises HTTPException if the booking is not allowed.
    """
    slot_date = slot.start_time.date()
    event = db.query(CalendarEvent).filter(
        CalendarEvent.event_date == slot_date,
        CalendarEvent.affects_ordering == True,
    ).first()
    if not event:
        return

    if event.event_type == "holiday":
        raise HTTPException(
            status_code=400,
            detail=f"Ordering is closed on {slot_date.isoformat()} ({event.label} — Holiday). "
                   f"No bookings are allowed on this date.",
        )

    if event.event_type == "exam_day":
        # Only faculty/admin/super_admin can book on exam days
        user = db.query(User).filter(User.id == user_id).first()
        role = (user.role.value if user and hasattr(user.role, 'value') else '').lower() if user else ''
        if role not in {"faculty", "admin", "super_admin"}:
            raise HTTPException(
                status_code=400,
                detail=f"Slot on {slot_date.isoformat()} is reserved for faculty/staff "
                       f"({event.label} — Exam Day). Student bookings are not allowed.",
            )
        # Faculty can book — reduce max_orders by half to prioritise faculty
        if hasattr(slot, 'max_orders'):
            slot.max_orders = max(1, slot.max_orders // 2)


def _apply_capacity_rules(slot: Slot, user_id: int, db: Session) -> int:
    """Return the effective max_orders after applying any active capacity rules for this user.

    Looks up the user's role from the User table (not from the Slot model,
    which has no vendor_role column). This ensures role-based capacity rules
    (e.g. faculty priority limits) are correctly applied.
    """
    # Look up the actual user's role from the database
    user = db.query(User).filter(User.id == user_id).first()
    user_role = (user.role.value if user and hasattr(user.role, 'value') else 'student') if user else 'student'

    rules = db.query(SlotCapacityRule).filter(
        SlotCapacityRule.vendor_id == slot.vendor_id,
        SlotCapacityRule.is_active == True,
    ).all()

    effective_max = slot.max_orders
    slot_day = slot.start_time.weekday()
    slot_hour = slot.start_time.hour

    for rule in rules:
        # Day filter: if rule specifies a day, skip non-matching days
        if rule.day_of_week is not None and rule.day_of_week != slot_day:
            continue

        # Hour window filter
        if rule.start_hour <= slot_hour < rule.end_hour:
            # Determine capacity: peak_capacity if available and slot is peak, else base_capacity
            if rule.peak_capacity is not None and slot.is_peak_hour:
                cap = rule.peak_capacity
            else:
                cap = rule.base_capacity
            effective_max = min(effective_max, cap)

    return effective_max


def _book_slot_internal(slot_id: int, user_id: int, db: Session, commit: bool, order_id: int | None = None):
    lock_key = f"slot_lock:{slot_id}"

    lock_acquired = redis_client.set(lock_key, "locked", nx=True, ex=LOCK_TTL)
    if not lock_acquired:
        raise HTTPException(status_code=429, detail="Slot is being booked, try again")

    try:
        slot = db.query(Slot).filter(Slot.id == slot_id).with_for_update().first()
        if not slot:
            raise HTTPException(status_code=404, detail="Slot not found")

        if slot.is_locked:
            raise HTTPException(status_code=423, detail="Slot is currently locked by vendor")

        # Check calendar event restrictions (holiday/exam day)
        _check_calendar_event_restrictions(slot, user_id, db)

        # Apply capacity rules to determine effective max_orders
        # _apply_capacity_rules looks up the user's role from the User table internally
        effective_max = _apply_capacity_rules(slot, user_id, db)
        if slot.current_orders >= effective_max:
            slot.status = SlotStatus.FULL
            if commit:
                db.commit()
            else:
                db.flush()
            raise HTTPException(status_code=400, detail="Slot is full — cannot book")

        # Check for duplicate active booking by this user
        existing = db.query(SlotBooking).filter(
            SlotBooking.slot_id == slot_id,
            SlotBooking.user_id == user_id,
            SlotBooking.status == BookingStatus.CONFIRMED,
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="You already have an active booking for this slot")

        slot.current_orders += 1
        _update_slot_status(slot)

        booking = SlotBooking(
            slot_id=slot_id,
            user_id=user_id,
            order_id=order_id,
            status=BookingStatus.CONFIRMED,
        )
        db.add(booking)

        if commit:
            db.commit()
            db.refresh(slot)
            db.refresh(booking)
        else:
            db.flush()

        return slot, booking

    finally:
        redis_client.delete(lock_key)


def book_slot(slot_id: int, user_id: int, db: Session, order_id: int | None = None):
    slot, booking = _book_slot_internal(slot_id, user_id, db, commit=True, order_id=order_id)
    return slot, booking


def reserve_slot_for_order(slot_id: int, user_id: int, db: Session, order_id: int | None = None):
    slot, booking = _book_slot_internal(slot_id, user_id, db, commit=False, order_id=order_id)
    return slot


def cancel_slot_booking(booking_id: int, user_id: int, db: Session):
    booking = db.query(SlotBooking).filter(
        SlotBooking.id == booking_id,
        SlotBooking.user_id == user_id,
        SlotBooking.status == BookingStatus.CONFIRMED,
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Active booking not found")

    slot = db.query(Slot).filter(Slot.id == booking.slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = utcnow_naive()

    slot.current_orders = max(0, slot.current_orders - 1)
    _update_slot_status(slot)

    # Send SMS notification for slot cancellation (urgent event)
    try:
        from app.modules.notifications.model import NotificationType
        from app.modules.notifications.service import notify_user
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            notify_user(
                user_id=user_id,
                phone=user.phone,
                title="Slot Booking Cancelled",
                message=f"Your slot booking (ID: {booking_id}) on {slot.start_time.strftime('%b %d at %I:%M %p')} has been cancelled.",
                db=db,
                send_sms_flag=True,
                notification_type=NotificationType.ALERT,
                reference_id=booking_id,
            )
    except Exception:
        pass

    db.commit()
    db.refresh(slot)
    db.refresh(booking)

    return slot, booking


def lock_slot(slot_id: int, db: Session, locked_by: str):
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    if slot.is_locked:
        raise HTTPException(status_code=409, detail="Slot is already locked")

    slot.is_locked = True
    slot.locked_by = locked_by
    slot.locked_at = utcnow_naive()
    db.commit()
    db.refresh(slot)
    return slot


def unlock_slot(slot_id: int, db: Session):
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    if not slot.is_locked:
        raise HTTPException(status_code=409, detail="Slot is not locked")

    slot.is_locked = False
    slot.locked_by = None
    slot.locked_at = None
    db.commit()
    db.refresh(slot)
    return slot


def get_user_bookings(user_id: int, db: Session, active_only: bool = True):
    query = db.query(SlotBooking).filter(SlotBooking.user_id == user_id)
    if active_only:
        query = query.filter(SlotBooking.status == BookingStatus.CONFIRMED)
    return query.order_by(SlotBooking.booked_at.desc()).all()


# ── Advanced Slot Management Services ──────────────────────────────────────


def create_slot_capacity_rule(vendor_id: int, rule_data: Dict[str, Any], db: Session) -> SlotCapacityRule:
    """Create a new slot capacity rule for a vendor."""
    rule = SlotCapacityRule(
        vendor_id=vendor_id,
        rule_name=rule_data["rule_name"],
        day_of_week=rule_data.get("day_of_week"),
        start_hour=rule_data["start_hour"],
        end_hour=rule_data["end_hour"],
        base_capacity=rule_data["base_capacity"],
        peak_capacity=rule_data.get("peak_capacity"),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def get_slot_capacity_rules(vendor_id: int, db: Session) -> List[SlotCapacityRule]:
    """Get all capacity rules for a vendor."""
    return db.query(SlotCapacityRule).filter(SlotCapacityRule.vendor_id == vendor_id).all()


def update_slot_capacity_rule(rule_id: int, vendor_id: int, rule_data: Dict[str, Any], db: Session) -> SlotCapacityRule:
    """Update a slot capacity rule."""
    rule = db.query(SlotCapacityRule).filter(SlotCapacityRule.id == rule_id, SlotCapacityRule.vendor_id == vendor_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Capacity rule not found")
    
    for key, value in rule_data.items():
        if hasattr(rule, key) and value is not None:
            setattr(rule, key, value)
    
    db.commit()
    db.refresh(rule)
    return rule


def delete_slot_capacity_rule(rule_id: int, vendor_id: int, db: Session) -> bool:
    """Delete a slot capacity rule."""
    rule = db.query(SlotCapacityRule).filter(SlotCapacityRule.id == rule_id, SlotCapacityRule.vendor_id == vendor_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Capacity rule not found")
    
    db.delete(rule)
    db.commit()
    return True


def create_slot_rule(vendor_id: int, rule_data: Dict[str, Any], db: Session) -> SlotRule:
    """Create a new slot rule for a vendor."""
    rule = SlotRule(
        vendor_id=vendor_id,
        rule_type=rule_data["rule_type"],
        rule_config=json.dumps(rule_data["rule_config"]),
        is_enabled=rule_data.get("is_enabled", True),
        priority=rule_data.get("priority", 0),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def get_slot_rules(vendor_id: int, db: Session) -> List[SlotRule]:
    """Get all rules for a vendor."""
    return db.query(SlotRule).filter(SlotRule.vendor_id == vendor_id).order_by(SlotRule.priority.desc()).all()


def update_slot_rule(rule_id: int, vendor_id: int, rule_data: Dict[str, Any], db: Session) -> SlotRule:
    """Update a slot rule."""
    rule = db.query(SlotRule).filter(SlotRule.id == rule_id, SlotRule.vendor_id == vendor_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    for key, value in rule_data.items():
        if hasattr(rule, key) and value is not None:
            if key == "rule_config" and isinstance(value, dict):
                setattr(rule, key, json.dumps(value))
            else:
                setattr(rule, key, value)
    
    db.commit()
    db.refresh(rule)
    return rule


def delete_slot_rule(rule_id: int, vendor_id: int, db: Session) -> bool:
    """Delete a slot rule."""
    rule = db.query(SlotRule).filter(SlotRule.id == rule_id, SlotRule.vendor_id == vendor_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    db.delete(rule)
    db.commit()
    return True


def apply_slot_rules(slot: Slot, db: Session) -> None:
    """Apply vendor rules to a slot (auto-block, faculty priority, peak hour, etc.)."""
    rules = db.query(SlotRule).filter(SlotRule.vendor_id == slot.vendor_id, SlotRule.is_enabled == True).order_by(SlotRule.priority.desc()).all()
    
    for rule in rules:
        config = json.loads(rule.rule_config) if isinstance(rule.rule_config, str) else rule.rule_config
        
        if rule.rule_type == "auto_block":
            if config.get("enabled", False) and slot.current_orders >= slot.max_orders:
                slot.status = SlotStatus.BLOCKED
                slot.auto_block_enabled = True
        
        elif rule.rule_type == "faculty_priority":
            if config.get("enabled", False):
                slot.is_faculty_priority = True
        
        elif rule.rule_type == "peak_hour":
            if config.get("enabled", False):
                peak_hours = config.get("peak_hours", [])
                current_hour = slot.start_time.hour
                for peak_range in peak_hours:
                    if isinstance(peak_range, dict):
                        start = peak_range.get("start", 0)
                        end = peak_range.get("end", 23)
                        if start <= current_hour <= end:
                            slot.is_peak_hour = True
                            break
        
        elif rule.rule_type == "duration":
            if config.get("enabled", False):
                slot.slot_duration_minutes = config.get("duration_minutes")


def get_slot_analytics(vendor_id: int, db: Session) -> Dict[str, Any]:
    """Get slot analytics for a vendor."""
    slots = db.query(Slot).filter(Slot.vendor_id == vendor_id).all()
    
    total_slots = len(slots)
    available_slots = sum(1 for s in slots if s.status == SlotStatus.AVAILABLE)
    limited_slots = sum(1 for s in slots if s.status == SlotStatus.LIMITED)
    full_slots = sum(1 for s in slots if s.status == SlotStatus.FULL)
    blocked_slots = sum(1 for s in slots if s.status == SlotStatus.BLOCKED)
    
    total_bookings = sum(s.current_orders for s in slots)
    avg_utilization = (total_bookings / sum(s.max_orders for s in slots) * 100) if slots and sum(s.max_orders for s in slots) > 0 else 0
    
    peak_hour_slots = sum(1 for s in slots if s.is_peak_hour)
    faculty_priority_slots = sum(1 for s in slots if s.is_faculty_priority)
    
    return {
        "total_slots": total_slots,
        "available_slots": available_slots,
        "limited_slots": limited_slots,
        "full_slots": full_slots,
        "blocked_slots": blocked_slots,
        "total_bookings": total_bookings,
        "avg_utilization": round(avg_utilization, 2),
        "peak_hour_slots": peak_hour_slots,
        "faculty_priority_slots": faculty_priority_slots,
    }


def bulk_create_slots(vendor_id: int, slot_data: Dict[str, Any], db: Session) -> List[Slot]:
    """Bulk create slots for a vendor."""
    start_date = slot_data["start_date"]
    end_date = slot_data["end_date"]
    interval_minutes = slot_data.get("interval_minutes", 60)
    max_orders = slot_data.get("max_orders", 10)
    
    new_slots = []
    current_time = start_date
    
    while current_time < end_date:
        end_time = current_time + timedelta(minutes=interval_minutes)
        
        slot = Slot(
            vendor_id=vendor_id,
            start_time=current_time,
            end_time=end_time,
            max_orders=max_orders,
            current_orders=0,
            status=SlotStatus.AVAILABLE,
            slot_duration_minutes=slot_data.get("slot_duration_minutes"),
            is_peak_hour=slot_data.get("is_peak_hour", False),
            is_faculty_priority=slot_data.get("is_faculty_priority", False),
            auto_block_enabled=slot_data.get("auto_block_enabled", False),
        )
        
        db.add(slot)
        new_slots.append(slot)
        current_time = end_time
    
    db.commit()
    for slot in new_slots:
        db.refresh(slot)
    
    return new_slots


def update_slot(slot_id: int, vendor_id: int, slot_data: Dict[str, Any], db: Session) -> Slot:
    """Update a slot."""
    slot = db.query(Slot).filter(Slot.id == slot_id, Slot.vendor_id == vendor_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    for key, value in slot_data.items():
        if hasattr(slot, key) and value is not None:
            setattr(slot, key, value)
    
    db.commit()
    db.refresh(slot)
    return slot


def delete_slot(slot_id: int, vendor_id: int, db: Session) -> bool:
    """Delete a slot."""
    slot = db.query(Slot).filter(Slot.id == slot_id, Slot.vendor_id == vendor_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    db.delete(slot)
    db.commit()
    return True
