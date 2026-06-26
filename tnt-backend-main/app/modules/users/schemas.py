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
    enable_reorder_suggestions: bool = Field(
        default=True,
        description="Whether the AI engine should show reorder suggestions.",
    )
    enable_offpeak_reminders: bool = Field(
        default=True,
        description="Whether the app should remind user about off-peak discounts.",
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


class ProfileImageResponse(BaseModel):
    profile_image: str
