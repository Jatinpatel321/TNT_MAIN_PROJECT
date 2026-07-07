"""Pydantic schemas for conflict resolution module (pydantic v2)."""

from typing import List, Optional

from pydantic import BaseModel


class SlotConflict(BaseModel):
    slot_id: Optional[int] = None
    conflict_type: str = ""
    severity: str = ""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    vendor_id: Optional[int] = None
    max_orders: Optional[int] = None
    current_orders: Optional[int] = None
    overflow: Optional[int] = None
    fill_rate: Optional[float] = None
    user_id: Optional[int] = None
    booking_count: Optional[int] = None


class ConflictTotals(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0


class ConflictSummaryResponse(BaseModel):
    overbooked_slots: List[SlotConflict] = []
    duplicate_bookings: List[SlotConflict] = []
    capacity_warnings: List[SlotConflict] = []
    totals: ConflictTotals = ConflictTotals()