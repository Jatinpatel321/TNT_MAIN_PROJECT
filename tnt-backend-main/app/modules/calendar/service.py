"""Service layer for calendar events."""

from datetime import date, datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.calendar.model import CalendarEvent


def _to_naive_date(d: date) -> date:
    """Ensure we have a date, converting datetime if needed."""
    if isinstance(d, datetime):
        return d.date()
    return d


def list_events(
    db: Session,
    year: Optional[int] = None,
    month: Optional[int] = None,
    event_type: Optional[str] = None,
) -> List[CalendarEvent]:
    """List calendar events, optionally filtered by year/month/type."""
    query = db.query(CalendarEvent)

    if year and month:
        query = query.filter(
            CalendarEvent.event_date >= date(year, month, 1),
            CalendarEvent.event_date < date(year + (month // 12), (month % 12) + 1, 1),
        )
    elif year:
        query = query.filter(
            CalendarEvent.event_date >= date(year, 1, 1),
            CalendarEvent.event_date < date(year + 1, 1, 1),
        )

    if event_type:
        query = query.filter(CalendarEvent.event_type == event_type)

    return query.order_by(CalendarEvent.event_date.asc()).all()


def get_event(db: Session, event_id: int) -> Optional[CalendarEvent]:
    """Get a single event by ID."""
    return db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()


def get_event_for_date(db: Session, target_date: date) -> Optional[CalendarEvent]:
    """Get calendar event for a specific date, if one exists."""
    naive = _to_naive_date(target_date)
    return db.query(CalendarEvent).filter(
        CalendarEvent.event_date == naive
    ).first()


def create_event(db: Session, data: dict) -> CalendarEvent:
    """Create a new calendar event."""
    event_date = _to_naive_date(data["event_date"])

    # Check for duplicate on same date
    existing = db.query(CalendarEvent).filter(
        CalendarEvent.event_date == event_date
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"An event already exists for {event_date.isoformat()}: '{existing.label}'",
        )

    now = utcnow_naive()
    event = CalendarEvent(
        event_date=event_date,
        label=data["label"],
        event_type=data.get("event_type", "holiday"),
        affects_ordering=data.get("affects_ordering", True),
        description=data.get("description"),
        created_at=now.date(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def update_event(db: Session, event_id: int, data: dict) -> CalendarEvent:
    """Update a calendar event."""
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Calendar event not found")

    for key, value in data.items():
        if value is not None and hasattr(event, key):
            if key == "event_date":
                setattr(event, key, _to_naive_date(value))
            else:
                setattr(event, key, value)

    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event_id: int) -> None:
    """Delete a calendar event."""
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    db.delete(event)
    db.commit()


def get_ordering_blocked_dates(db: Session) -> List[date]:
    """Return all dates where affects_ordering is True (ordering is affected)."""
    rows = db.query(CalendarEvent.event_date).filter(
        CalendarEvent.affects_ordering == True
    ).all()
    return [row[0] for row in rows]


def check_date_ordering_impact(db: Session, target_date: date) -> dict:
    """Check if a specific date has any ordering-impacting events.

    Returns a dict with:
      - blocked: bool (ordering blocked / restricted)
      - event_type: str | None
      - label: str | None
      - description: str | None
    """
    naive = _to_naive_date(target_date)
    event = db.query(CalendarEvent).filter(
        CalendarEvent.event_date == naive,
        CalendarEvent.affects_ordering == True,
    ).first()

    if not event:
        return {"blocked": False, "event_type": None, "label": None, "description": None}

    return {
        "blocked": True,
        "event_type": event.event_type,
        "label": event.label,
        "description": event.description,
        "event_id": event.id,
    }
