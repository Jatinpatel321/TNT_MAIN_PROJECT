from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class OrderStatus(str, Enum):
    # Canonical states
    placed    = "placed"
    confirmed = "confirmed"
    preparing = "preparing"
    ready     = "ready"
    picked    = "picked"
    cancelled = "cancelled"
    # Legacy states — kept for backward-compat with existing DB rows
    pending          = "pending"
    ready_for_pickup = "ready_for_pickup"
    completed        = "completed"


class OrderItemResponse(BaseModel):
    menu_item_id: int
    name: str
    quantity: int
    price_at_time: float

    model_config = ConfigDict(from_attributes=True)


class StationeryJobSummary(BaseModel):
    id: int
    service_id: int
    quantity: int
    amount: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    slot_id: int
    vendor_id: int
    vendor_name: Optional[str] = None
    status: OrderStatus
    created_at: datetime
    total_amount: Optional[int] = None
    qr_code: Optional[str] = None
    items: Optional[list[OrderItemResponse]] = None
    eta_minutes: Optional[int] = None
    is_delayed: Optional[bool] = None
    booking_type: Optional[str] = "food"
    stationery_jobs: Optional[list[StationeryJobSummary]] = None
    fraud_flag: Optional[bool] = None
    fraud_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
