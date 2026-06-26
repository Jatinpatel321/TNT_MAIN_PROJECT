"""
Recommendation Ranking Router
==============================

Endpoints for advanced recommendation ranking:

GET /user/recommendations/ranked - Get ranked recommendations with scores
GET /user/recommendations/insights/{item_id} - Get detailed insights for an item
POST /user/recommendations/rank - Rank custom list of items
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.recommendations.ranking_service import RecommendationRankingService

router = APIRouter(prefix="/user/recommendations", tags=["Recommendation Ranking"])


class RankItemsRequest(BaseModel):
    items: list[dict[str, Any]]
    category: str = "recommended"


@router.get("/ranked")
async def get_ranked_recommendations(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get all recommendations with advanced ranking and scoring.

    Returns:
        - frequently_ordered: Ranked frequently ordered items
        - recommended_for_you: Ranked personalized recommendations
        - trending_near_you: Ranked trending items
        - because_you_ordered: Ranked association recommendations
        - All items include:
            - trending_score
            - popularity_score
            - affinity_score
            - recency_score
            - confidence
            - confidence_level
            - reason (human-readable)
    """
    from app.modules.recommendations.smart_engine import SmartRecommendationEngine

    engine = SmartRecommendationEngine(db)
    ranking_service = RecommendationRankingService(db)

    # Get base recommendations
    base_recs = engine.get_recommendations(user.id)

    # Rank each category
    ranked_recs = {
        "user_id": user.id,
        "frequently_ordered": ranking_service.rank_recommendations(
            user.id,
            base_recs.get("frequently_ordered", []),
            "frequently_ordered"
        ),
        "recommended_for_you": ranking_service.rank_recommendations(
            user.id,
            base_recs.get("recommended_for_you", []),
            "recommended"
        ),
        "trending_near_you": ranking_service.rank_recommendations(
            user.id,
            base_recs.get("trending_near_you", []),
            "trending"
        ),
        "because_you_ordered": ranking_service.rank_recommendations(
            user.id,
            base_recs.get("because_you_ordered", []),
            "because_you_ordered"
        ),
        "personalized_vendors": base_recs.get("personalized_vendors", []),
    }

    return ranked_recs


@router.get("/insights/{item_id}")
async def get_recommendation_insights(
    item_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get detailed insights for a specific recommendation.

    Returns:
        - scores: Complete score breakdown
        - reason: Human-readable reason
        - confidence: Overall confidence
        - insights: Additional insights
    """
    ranking_service = RecommendationRankingService(db)
    return ranking_service.get_recommendation_insights(user.id, item_id)


@router.post("/rank")
async def rank_custom_items(
    request: RankItemsRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Rank a custom list of recommendation items.

    Args:
        items: List of menu items to rank
        category: Recommendation category for reason generation

    Returns:
        Ranked and scored items with reasons
    """
    ranking_service = RecommendationRankingService(db)
    return ranking_service.rank_recommendations(
        user.id,
        request.items,
        request.category
    )