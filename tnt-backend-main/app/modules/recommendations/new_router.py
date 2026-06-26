"""
New Recommendation API Router
=============================

Three new endpoints for the upgraded recommendation engine:

    GET /user/recommendations
    GET /user/personalized-vendors
    GET /user/personalized-menu

All leverage:
    - User behaviour learning (vendor visits, menu clicks, search)
    - Preference snapshots (favourite vendors, items, categories, timings)
    - Time-of-day awareness
    - Redis caching
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.recommendations.smart_engine import SmartRecommendationEngine

router = APIRouter(prefix="/user", tags=["Personalized Recommendations"])


@router.get("/recommendations")
async def get_user_recommendations(
    limit: int = Query(20, ge=1, le=50, description="Number of recommendations"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get personalised recommendations for the current user.

    Returns five curated lists:
        - **frequently_ordered** — items the user orders most often
        - **recommended_for_you** — hybrid preference + association picks
        - **trending_near_you** — campus-wide trending, time-of-day boosted
        - **because_you_ordered** — collaborative "users who bought X also bought Y"
        - **personalized_vendors** — top vendor picks for this user

    Results are cached in Redis for 5 minutes.
    """
    engine = SmartRecommendationEngine(db)
    return await engine.get_recommendations(user["id"], limit)


@router.get("/personalized-vendors")
async def get_user_personalized_vendors(
    limit: int = Query(10, ge=1, le=20, description="Number of vendors"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get personalised vendor recommendations for the current user.

    Vendors are scored based on:
        - Order frequency
        - Current load (LOW → higher score)
        - Average rating
        - Preference snapshot

    Results are cached in Redis for 10 minutes.
    """
    engine = SmartRecommendationEngine(db)
    return await engine.get_personalized_vendors(user["id"], limit)


@router.post("/interactions")
async def record_user_interaction(
    event_type: str = Query(..., description="Event type: page_view, item_click, search, order_placed, category_view, favourite"),
    vendor_id: Optional[int] = Query(None, description="Vendor ID if applicable"),
    menu_item_id: Optional[int] = Query(None, description="Menu item ID if applicable"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Record a user interaction event for behaviour learning.

    This endpoint should be called from the frontend whenever a user:
        - Views a vendor page (page_view)
        - Clicks a menu item (item_click)
        - Performs a search (search)
        - Views a category (category_view)
        - Favourites a vendor (favourite)

    Events are stored in user_behaviour table and used to
    improve recommendations over time.
    """
    engine = SmartRecommendationEngine(db)
    return engine.record_interaction(
        user_id=user["id"],
        event_type=event_type,
        vendor_id=vendor_id,
        menu_item_id=menu_item_id,
    )


@router.get("/personalized-menu")
async def get_user_personalized_menu(
    vendor_id: Optional[int] = Query(None, description="Filter by vendor ID"),
    limit: int = Query(10, ge=1, le=30, description="Number of items"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get personalised menu items for the current user.

    Items are ranked by:
        - Whether user has ordered them before
        - Preference for the vendor
        - Current availability

    Optionally filter by vendor_id to see personalised items within
    a specific vendor's menu.

    Results are cached in Redis for 5 minutes.
    """
    engine = SmartRecommendationEngine(db)
    return await engine.get_personalized_menu(user["id"], vendor_id, limit)
