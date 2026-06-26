"""CRUD endpoints for calendar events (admin-only)."""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import require_role
from app.modules.calendar.schemas import (
    CalendarEventCreate,
    CalendarEventListResponse,
    CalendarEventResponse,
    CalendarEventUpdate,
)
from app.modules.calendar.service import (
    list_events,
    get_event,
    create_event,
    update_event,
    delete_event,
    check_date_ordering_impact,
)

router = APIRouter(prefix="/admin/calendar-events", tags=["Calendar"])


@router.get("/", response_model=CalendarEventListResponse)
def list_calendar_events(
    year: Optional[int] = Query(None, description="Filter by year"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter by month (1-12)"),
    event_type: Optional[str] = Query(None, description="Filter by type: holiday | exam_day"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """List all calendar events, with optional year/month/type filters."""
    events = list_events(db, year=year, month=month, event_type=event_type)
    return CalendarEventListResponse(
        events=[CalendarEventResponse.model_validate(e) for e in events],
        total=len(events),
    )


@router.get("/check-date", response_model=dict)
def check_date(
    event_date: date = Query(..., description="Date to check (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """Check if a specific date has ordering-impacting events."""
    return check_date_ordering_impact(db, event_date)


@router.get("/{event_id}", response_model=CalendarEventResponse)
def get_calendar_event(
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """Get a single calendar event by ID."""
    event = get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    return CalendarEventResponse.model_validate(event)


@router.post("/", response_model=CalendarEventResponse, status_code=201)
def create_calendar_event(
    payload: CalendarEventCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """Create a new calendar event (holiday or exam day)."""
    event = create_event(db, payload.model_dump())
    return CalendarEventResponse.model_validate(event)


@router.put("/{event_id}", response_model=CalendarEventResponse)
def update_calendar_event(
    event_id: int,
    payload: CalendarEventUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """Update a calendar event."""
    event = update_event(db, event_id, payload.model_dump(exclude_unset=True))
    return CalendarEventResponse.model_validate(event)


@router.delete("/{event_id}")
def delete_calendar_event(
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """Delete a calendar event."""
    delete_event(db, event_id)
    return {"message": "Calendar event deleted", "event_id": event_id}
