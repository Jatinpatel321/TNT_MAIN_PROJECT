from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreateRequest(BaseModel):
    quality_rating: int = Field(ge=1, le=5)
    time_rating: int = Field(ge=1, le=5)
    behavior_rating: int = Field(ge=1, le=5)
    overall_rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = None


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    user_id: int
    vendor_id: int
    overall_rating: int | None
    quality_rating: int
    time_rating: int
    behavior_rating: int
    comment: str | None
    created_at: str


class VendorReviewCreateRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: str | None = None
    review_text: str | None = None
    is_anonymous: bool = False
    order_id: int | None = None


class VendorReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor_id: int
    user_id: int
    order_id: int | None
    rating: int
    title: str | None
    review_text: str | None
    is_anonymous: bool
    reviewer_name: str | None
    created_at: str


class VendorFeedbackSummaryResponse(BaseModel):
    vendor_id: int
    total_reviews: int
    avg_quality_rating: float
    avg_time_rating: float
    avg_behavior_rating: float
    avg_overall_rating: float
    rating_distribution: dict[int, int]
