from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CalendarEventCreate(BaseModel):
    event_date: date
    label: str = Field(..., min_length=1, max_length=200)
    event_type: str = Field(default="holiday", pattern=r"^(holiday|exam_day)$")
    affects_ordering: bool = True
    description: Optional[str] = None


class CalendarEventUpdate(BaseModel):
    label: Optional[str] = None
    event_type: Optional[str] = None
    affects_ordering: Optional[bool] = None
    description: Optional[str] = None


class CalendarEventResponse(BaseModel):
    id: int
    event_date: date
    label: str
    event_type: str
    affects_ordering: bool
    description: Optional[str] = None
    created_at: Optional[date] = None

    class Config:
        from_attributes = True


class CalendarEventListResponse(BaseModel):
    events: List[CalendarEventResponse]
    total: int
