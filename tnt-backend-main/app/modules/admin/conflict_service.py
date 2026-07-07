"""Conflict detection layer for admin dashboard.
Reads slot and booking data to surface anomalies — does not modify state.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List

from sqlalchemy import and_, func, text
from sqlalchemy.orm import Session

from app.modules.slots.model import Slot


def detect_overbooked_slots(db: Session) -> List[Dict]:
    """
    Return slots where current_orders > max_orders.
    These indicate a race condition that slipped through.
    """
    slots = (
        db.query(Slot)
        .filter(Slot.current_orders > Slot.max_orders)
        .order_by(Slot.start_time.asc())
        .all()
    )
    return [
        {
            "slot_id": s.id,
            "vendor_id": s.vendor_id,
            "start_time": s.start_time.isoformat(),
            "end_time": s.end_time.isoformat(),
            "max_orders": s.max_orders,
            "current_orders": s.current_orders,
            "overflow": s.current_orders - s.max_orders,
            "conflict_type": "overbooking",
            "severity": "critical",
        }
        for s in slots
    ]


def detect_duplicate_bookings(db: Session) -> List[Dict]:
    """
    Detect users with more than one confirmed booking in the same slot.
    """
    from app.modules.slots.model import SlotBooking, BookingStatus

    results = (
        db.query(
            SlotBooking.slot_id,
            SlotBooking.user_id,
            func.count(SlotBooking.id).label("booking_count"),
        )
        .filter(SlotBooking.status == BookingStatus.CONFIRMED)
        .group_by(SlotBooking.slot_id, SlotBooking.user_id)
        .having(func.count(SlotBooking.id) > 1)
        .order_by(func.count(SlotBooking.id).desc())
        .limit(100)
        .all()
    )

    return [
        {
            "slot_id": row.slot_id,
            "user_id": row.user_id,
            "booking_count": row.booking_count,
            "conflict_type": "duplicate_booking",
            "severity": "high",
        }
        for row in results
    ]


def detect_capacity_violations(db: Session) -> List[Dict]:
    """
    Detect slots approaching capacity (>= 90% full) in the next 2 hours.
    Useful for proactive admin intervention.
    """
    now = datetime.now(timezone.utc)
    two_hours = now + timedelta(hours=2)

    slots = (
        db.query(Slot)
        .filter(
            and_(
                Slot.start_time >= now,
                Slot.start_time <= two_hours,
                Slot.max_orders > 0,
            )
        )
        .all()
    )

    warnings = []
    for s in slots:
        fill_rate = s.current_orders / s.max_orders if s.max_orders else 0
        if fill_rate >= 0.9:
            warnings.append(
                {
                    "slot_id": s.id,
                    "vendor_id": s.vendor_id,
                    "start_time": s.start_time.isoformat(),
                    "fill_rate": round(fill_rate, 2),
                    "current_orders": s.current_orders,
                    "max_orders": s.max_orders,
                    "conflict_type": "capacity_warning",
                    "severity": "medium",
                }
            )
    return warnings


def get_conflict_summary(db: Session) -> Dict:
    overbooked = detect_overbooked_slots(db)
    duplicates = detect_duplicate_bookings(db)
    warnings = detect_capacity_violations(db)

    return {
        "overbooked_slots": overbooked,
        "duplicate_bookings": duplicates,
        "capacity_warnings": warnings,
        "totals": {
            "critical": len(overbooked),
            "high": len(duplicates),
            "medium": len(warnings),
        },
    }