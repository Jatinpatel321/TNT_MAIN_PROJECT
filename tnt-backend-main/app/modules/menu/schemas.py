from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class MenuItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    price: int = Field(..., gt=0)
    category: str = Field(default="food", pattern="^(food|stationery)$")
    prep_time_minutes: Optional[int] = Field(None, ge=0)
    available_quantity: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = None


class MenuItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[int] = Field(None, gt=0)
    is_available: Optional[bool] = None
    prep_time_minutes: Optional[int] = Field(None, ge=0)
    available_quantity: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = None


class MenuItemResponse(BaseModel):
    id: int
    vendor_id: int
    name: str
    description: Optional[str]
    price: int
    image_url: Optional[str]
    is_available: bool
    prep_time_minutes: Optional[int]
    available_quantity: Optional[int]
    category: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class InventoryCreate(BaseModel):
    menu_item_id: int
    current_stock: int = Field(..., ge=0)
    low_stock_threshold: int = Field(default=10, ge=0)
    auto_disable: bool = True


class InventoryUpdate(BaseModel):
    current_stock: Optional[int] = Field(None, ge=0)
    low_stock_threshold: Optional[int] = Field(None, ge=0)
    auto_disable: Optional[bool] = None


class InventoryResponse(BaseModel):
    id: int
    menu_item_id: int
    current_stock: int
    low_stock_threshold: int
    last_restocked_at: Optional[datetime]
    auto_disable: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    menu_item: Optional[MenuItemResponse] = None

    class Config:
        from_attributes = True


class StationeryServiceCreate(BaseModel):
    service_type: str = Field(..., pattern="^(xerox|color_print|bw_print)$")
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    price_per_page: int = Field(..., gt=0)
    max_capacity: Optional[int] = Field(None, ge=0)
    is_available: bool = True


class StationeryServiceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    price_per_page: Optional[int] = Field(None, gt=0)
    max_capacity: Optional[int] = Field(None, ge=0)
    current_load: Optional[int] = Field(None, ge=0)
    is_available: Optional[bool] = None


class StationeryServiceResponse(BaseModel):
    id: int
    vendor_id: int
    service_type: str
    name: str
    description: Optional[str]
    price_per_page: int
    max_capacity: Optional[int]
    current_load: int
    is_available: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int