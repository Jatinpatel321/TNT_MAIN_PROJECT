from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class SlotStatus(str, Enum):
    available = "available"
    limited = "limited"
    full = "full"
    blocked = "blocked"


class BookingStatus(str, Enum):
    confirmed = "confirmed"
    cancelled = "cancelled"


class BookingType(str, Enum):
    food = "food"
    stationery = "stationery"
    combined = "combined"


class SlotCreate(BaseModel):
    start_time: datetime
    end_time: datetime
    max_orders: int
    slot_duration_minutes: Optional[int] = None
    is_peak_hour: bool = False
    is_faculty_priority: bool = False
    auto_block_enabled: bool = False
    dynamic_capacity: Optional[int] = None
    capacity_notes: Optional[str] = None


class SlotUpdate(BaseModel):
    max_orders: Optional[int] = None
    status: Optional[SlotStatus] = None
    is_locked: Optional[bool] = None
    slot_duration_minutes: Optional[int] = None
    is_peak_hour: Optional[bool] = None
    is_faculty_priority: Optional[bool] = None
    auto_block_enabled: Optional[bool] = None
    dynamic_capacity: Optional[int] = None
    capacity_notes: Optional[str] = None


class SlotResponse(BaseModel):
    id: int
    vendor_id: int
    start_time: datetime
    end_time: datetime
    max_orders: int
    current_orders: int
    status: SlotStatus
    load_label: str = "LOW"
    express_pickup_eligible: bool = False
    is_locked: bool = False
    available_capacity: int = 0
    faculty_priority: bool = False
    queue_size: int = 0
    estimated_wait: int = 0
    is_ai_recommended: bool = False
    slot_duration_minutes: Optional[int] = None
    is_peak_hour: bool = False
    is_faculty_priority: bool = False
    auto_block_enabled: bool = False
    dynamic_capacity: Optional[int] = None
    capacity_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SlotBookingResponse(BaseModel):
    id: int
    slot_id: int
    user_id: int
    order_id: Optional[int] = None
    booking_type: BookingType = BookingType.food
    status: BookingStatus
    booked_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SlotBookRequest(BaseModel):
    order_id: Optional[int] = None


class SlotCancelResponse(BaseModel):
    message: str
    slot_id: int
    booking_id: int
    current_orders: int
    status: SlotStatus


class SlotLockResponse(BaseModel):
    message: str
    slot_id: int
    is_locked: bool


class SlotRecommendationResponse(BaseModel):
    recommended_slot: str
    estimated_wait: str
    reason: str


class SlotCapacityRuleCreate(BaseModel):
    rule_name: str
    day_of_week: Optional[int] = None
    start_hour: int
    end_hour: int
    base_capacity: int
    peak_capacity: Optional[int] = None


class SlotCapacityRuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    day_of_week: Optional[int] = None
    start_hour: Optional[int] = None
    end_hour: Optional[int] = None
    base_capacity: Optional[int] = None
    peak_capacity: Optional[int] = None
    is_active: Optional[bool] = None


class SlotCapacityRuleResponse(BaseModel):
    id: int
    vendor_id: int
    rule_name: str
    day_of_week: Optional[int]
    start_hour: int
    end_hour: int
    base_capacity: int
    peak_capacity: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SlotRuleCreate(BaseModel):
    rule_type: str
    rule_config: Dict[str, Any]
    is_enabled: bool = True
    priority: int = 0


class SlotRuleUpdate(BaseModel):
    rule_type: Optional[str] = None
    rule_config: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None
    priority: Optional[int] = None


class SlotRuleResponse(BaseModel):
    id: int
    vendor_id: int
    rule_type: str
    rule_config: Dict[str, Any]
    is_enabled: bool
    priority: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BulkSlotCreate(BaseModel):
    vendor_id: int
    start_date: datetime
    end_date: datetime
    interval_minutes: int = 60
    max_orders: int = 10
    slot_duration_minutes: Optional[int] = None
    is_peak_hour: bool = False
    is_faculty_priority: bool = False
    auto_block_enabled: bool = False


class SlotAnalyticsResponse(BaseModel):
    total_slots: int
    available_slots: int
    limited_slots: int
    full_slots: int
    blocked_slots: int
    total_bookings: int
    avg_utilization: float
    peak_hour_slots: int
    faculty_priority_slots: int


# ── Combined Booking Schemas ──────────────────────────────────────────────


class CombinedStationeryItem(BaseModel):
    service_id: int
    quantity: int
    file_url: Optional[str] = None


class CombinedFoodItem(BaseModel):
    menu_item_id: int
    quantity: int


class CombinedBookingRequest(BaseModel):
    """Payload for POST /slots/combined-booking.

    Books food items AND a stationery job against the SAME slot window.
    """
    slot_id: int
    food_items: List[CombinedFoodItem] = []
    stationery_items: List[CombinedStationeryItem] = []


class CombinedBookingResponse(BaseModel):
    """Response for a successful combined booking.

    Returns the order ID (which covers the food items) and the stationery
    job ID so the frontend can route to payment for both.
    """
    message: str
    order_id: int
    stationery_job_ids: List[int]
    slot_id: int
    booking_id: int
    total_amount: int
    status: str
