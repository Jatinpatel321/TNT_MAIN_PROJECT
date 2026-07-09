from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class UserRole(str, Enum):
    student = "student"
    faculty = "faculty"
    vendor = "vendor"
    admin = "admin"
    super_admin = "super_admin"


class DietaryRestriction(str, Enum):
    vegetarian = "vegetarian"
    vegan = "vegan"
    gluten_free = "gluten_free"
    dairy_free = "dairy_free"
    nut_free = "nut_free"
    halal = "halal"
    jain = "jain"


class CuisinePreference(str, Enum):
    south_indian = "south_indian"
    north_indian = "north_indian"
    chinese = "chinese"
    fast_food = "fast_food"
    healthy = "healthy"
    snacks = "snacks"
    beverages = "beverages"


class DietaryPreference(str, Enum):
    """Single headline dietary identity shown on the profile."""
    vegetarian = "vegetarian"
    non_vegetarian = "non_vegetarian"
    vegan = "vegan"
    jain = "jain"
    other = "other"


class ResidenceType(str, Enum):
    hostel = "hostel"
    day_scholar = "day_scholar"


class UserPreferencesUpdate(BaseModel):
    """Structured dietary and meal preferences set explicitly by the user."""
    dietary_restrictions: Optional[List[DietaryRestriction]] = Field(
        default=None,
        description="One or more dietary restrictions/requirements.",
    )
    cuisine_preferences: Optional[List[CuisinePreference]] = Field(
        default=None,
        description="Preferred cuisine categories for recommendations.",
    )
    spice_level: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Preferred spice level (1 = mild, 5 = extra hot).",
    )
    preferred_pickup_hour: Optional[int] = Field(
        default=None,
        ge=0,
        le=23,
        description="Preferred hour of day for pickup (0-23).",
    )
    # Optional so an unsupplied field is ignored on merge, matching the
    # endpoint's documented "null fields are ignored" contract.
    enable_reorder_suggestions: Optional[bool] = Field(
        default=None,
        description="Whether the AI engine should show reorder suggestions.",
    )
    enable_offpeak_reminders: Optional[bool] = Field(
        default=None,
        description="Whether the app should remind user about off-peak discounts.",
    )
    enable_rush_alerts: Optional[bool] = Field(
        default=None,
        description="Whether the app should alert about vendor rush/peak load.",
    )
    enable_ai_recommendations: Optional[bool] = Field(
        default=None,
        description="Whether AI-personalized recommendations are shown.",
    )
    preferred_pickup_locations: Optional[List[str]] = Field(
        default=None,
        max_length=10,
        description="Free-form campus pickup spots the user prefers.",
    )
    favourite_categories: Optional[List[CuisinePreference]] = Field(
        default=None,
        description="Favourite food/stationery categories for the profile.",
    )
    dark_mode: Optional[bool] = Field(
        default=None,
        description="Persisted UI theme choice so it follows the account across devices.",
    )


class UserCreate(BaseModel):
    phone: str
    name: str
    role: UserRole
    university_id: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    phone: str
    name: Optional[str] = None
    full_name: Optional[str] = None
    role: UserRole
    vendor_type: Optional[str] = None
    university_id: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None
    email: Optional[str] = None
    campus: Optional[str] = None
    residence_type: Optional[str] = None
    dietary_preference: Optional[str] = None
    profile_image: Optional[str] = None
    is_active: bool = True
    is_approved: bool = False
    preferences: Optional[dict] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    university_id: Optional[str] = Field(None, min_length=1, max_length=30)
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    semester: Optional[int] = Field(None, ge=1, le=12)
    email: Optional[str] = Field(
        None,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    campus: Optional[str] = Field(None, min_length=1, max_length=100)
    residence_type: Optional[ResidenceType] = None
    dietary_preference: Optional[DietaryPreference] = None


class ProfileStatsResponse(BaseModel):
    """Aggregated account statistics for the profile dashboard."""
    total_orders: int
    food_orders: int
    stationery_orders: int
    group_orders: int
    total_spent: float  # rupees, successful payments only
    loyalty_points: float  # current redeemable balance
    rewards_earned: float  # lifetime points earned
    saved_via_offers: float  # rupees saved through vouchers + point redemptions
    member_since: Optional[datetime] = None


class ProfileImageResponse(BaseModel):
    profile_image: str


class FavoriteVendorResponse(BaseModel):
    vendor_id: int
    vendor_name: Optional[str] = None
    vendor_type: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FavoriteMenuItemResponse(BaseModel):
    menu_item_id: int
    name: Optional[str] = None
    vendor_id: Optional[int] = None
    price: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
