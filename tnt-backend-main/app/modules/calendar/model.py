from sqlalchemy import Boolean, Column, Date, Integer, String, Text

from app.database.base import Base


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    event_date = Column(Date, nullable=False, index=True)
    label = Column(String(200), nullable=False)
    event_type = Column(String(20), nullable=False, default="holiday")  # holiday | exam_day
    affects_ordering = Column(Boolean, nullable=False, default=True)
    description = Column(Text, nullable=True)
    created_at = Column(Date, nullable=False)  # stores naive date of creation
