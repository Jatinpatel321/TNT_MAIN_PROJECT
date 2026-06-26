from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class DemandPlanningResponse(BaseModel):
    expected_daily_orders: int
    slot_wise_demand_graph: Dict[str, int]
    popular_items: List[Dict[str, Any]]
    stationery_workload_score: float
    food_waste_risk_score: float


class CapacityRecommendationResponse(BaseModel):
    vendor_id: int
    recommended_capacity: int
    reasoning: str


class SlotRecommendation(BaseModel):
    slot_id: int
    score: float
    reasoning: str
    estimated_eta_minutes: int


class SlotRecommendationsResponse(BaseModel):
    recommendations: List[SlotRecommendation]
    best_slot_id: int


class PredictiveETAResponse(BaseModel):
    predicted_eta_minutes: int
    pickup_window_start: datetime
    pickup_window_end: datetime
    delay_risk_level: str  # LOW, MEDIUM, HIGH


class VendorRanking(BaseModel):
    vendor_id: int
    vendor_rank_score: float
    live_load_indicator: str  # LOW, MEDIUM, HIGH
    express_pickup_eligible: bool
    reasoning: str


class VendorRankingResponse(BaseModel):
    rankings: List[VendorRanking]


class PersonalizationResponse(BaseModel):
    recommended_for_you: List[Dict[str, Any]]
    smart_suggestions: List[Dict[str, Any]]
    active_preferences: Dict[str, Any] = {}


class ReorderSuggestion(BaseModel):
    item_id: int
    quantity: int
    slot_id: Optional[int]
    print_settings: Optional[Dict[str, Any]]


class ReorderSuggestionsResponse(BaseModel):
    suggestions: List[ReorderSuggestion]
    best_time_to_reorder: str


class AIAlert(BaseModel):
    type: str
    severity: str  # LOW, MEDIUM, HIGH
    explanation: str
    suggested_action: str


class ProactiveAlertsResponse(BaseModel):
    alerts: List[AIAlert]


class GroupCoordinationResponse(BaseModel):
    overlapping_windows: List[Dict[str, Any]]
    suggested_unified_slot: Optional[int]
    coordination_score: float


# ── New structured schemas for user-facing AI features ──────────────────────


class VendorRecommendationItem(BaseModel):
    vendor_id: int
    vendor_name: str
    vendor_type: str
    category: Optional[str] = None
    logo_url: Optional[str] = None
    rank_score: float
    live_load: str  # LOW, MEDIUM, HIGH
    express_pickup: bool
    reason: str


class VendorRecommendationsResponse(BaseModel):
    recommendations: List[VendorRecommendationItem]


class MenuSuggestionItem(BaseModel):
    item_id: int
    item_name: str
    vendor_id: int
    vendor_name: str
    price_paise: int
    image_url: Optional[str] = None
    is_available: bool
    reason: str
    confidence: float


class MenuSuggestionsResponse(BaseModel):
    personalized: List[MenuSuggestionItem]
    trending: List[MenuSuggestionItem]


class SmartReorderItem(BaseModel):
    item_id: int
    item_name: str
    vendor_id: int
    vendor_name: str
    price_paise: int
    image_url: Optional[str] = None
    order_count: int
    last_ordered_at: str
    suggested_quantity: int
    suggested_slot_id: Optional[int] = None
    suggested_slot_time: Optional[str] = None


class SmartReorderResponse(BaseModel):
    items: List[SmartReorderItem]
    best_reorder_time: str
    best_reorder_slot_id: Optional[int] = None


class PickupTimeSlot(BaseModel):
    slot_id: int
    vendor_id: int
    vendor_name: str
    start_time: str
    end_time: str
    eta_minutes: int
    congestion_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    delay_risk: str  # LOW, MEDIUM, HIGH
    score: float


class BestPickupTimeResponse(BaseModel):
    best_slot: Optional[PickupTimeSlot]
    alternative_slots: List[PickupTimeSlot]
    preferred_hour: int
    preferred_hour_source: str  # "history", "preference", "default"


class PeakHourPeriod(BaseModel):
    start_hour: int
    end_hour: int
    label: str
    severity: str  # LOW, MEDIUM, HIGH
    avg_wait_minutes: int
    order_volume: int


class PeakHourAlert(BaseModel):
    is_peak_now: bool
    current_period: Optional[PeakHourPeriod] = None
    peak_periods_today: List[PeakHourPeriod]
    off_peak_windows: List[Dict[str, Any]]
    suggested_action: str


class PopularNearbyVendor(BaseModel):
    vendor_id: int
    vendor_name: str
    vendor_type: str
    category: Optional[str] = None
    logo_url: Optional[str] = None
    order_count: int
    avg_rating: float
    live_load: str


class PopularNearbyResponse(BaseModel):
    food_vendors: List[PopularNearbyVendor]
    stationery_vendors: List[PopularNearbyVendor]
