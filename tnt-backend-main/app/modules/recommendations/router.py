"""
Recommendations router
======================

GET /recommendations/{user_id}

Returns:
    recommended_items  – best overall picks (association + trending + personal)
    trending_items     – campus-wide hot sellers (last 7 days)
    popular_items      – popular items over last 30 days
    top_recommended    – alias for recommended_items (backward compat)
    personalized_items – tailored to this user's order history (backward compat)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.recommendations.engine import RecommendationEngine
from app.modules.recommendations.ranking_service import RecommendationRankingService

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("/offers/personalized")
def get_personalized_offers(
    limit: int = 10,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """AI-personalized promotional offers for the authenticated user.

    Ranks real, currently-valid vendor offers by SVD affinity, then layers
    loyalty, favourite-vendor preference, time-of-day/rush, and discount depth.
    """
    service = RecommendationRankingService(db)
    return service.get_personalized_offers(user["id"], limit=limit)


@router.get("/{user_id}")
def get_recommendations(
    user_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """
    AI-powered recommendation endpoint.

    **Returns three primary lists:**
    - `recommended_items` – personalised top picks
    - `trending_items` – campus-wide hot sellers (7 days)
    - `popular_items` – popular items (30 days)

    **Examples:**
    - User buys Burger  → recommends Fries + Cold Coffee
    - User buys Dosa    → recommends Filter Coffee
    - User buys Pasta   → recommends Garlic Bread
    """
    engine = RecommendationEngine(db)
    return engine.recommend(user_id)
