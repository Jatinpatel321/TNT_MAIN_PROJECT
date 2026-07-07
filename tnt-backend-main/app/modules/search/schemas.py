from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SearchItemResult(BaseModel):
    """A single item (menu item or stationery service) in search results."""
    id: int
    vendor_id: int
    name: str
    description: str | None = None
    price: int  # paise
    item_type: str  # "food" | "stationery"
    is_available: bool
    image_url: str | None = None
    unit: str | None = None  # stationery only
    vendor_name: str | None = None
    vendor_rating: float = 4.5
    vendor_category: str | None = None


class SearchVendorResult(BaseModel):
    """A vendor in search results."""
    id: int
    name: str | None
    vendor_type: str
    description: str | None = None
    rating: float = 4.5
    category: str | None = None
    location: str | None = None
    logo_url: str | None = None
    is_open: bool = True
    live_load_label: str = "LOW"
    express_pickup_eligible: bool = False
    matched_items: list[SearchItemResult] = []


class SearchResponse(BaseModel):
    vendors: list[SearchVendorResult]
    items: list[SearchItemResult]
    total_vendors: int
    total_items: int
