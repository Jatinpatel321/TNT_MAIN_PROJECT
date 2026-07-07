"""
Prediction API Router
=====================

Endpoints for predictive behaviour learning:

GET /user/predictions/reorder - Suggested reorder with confidence
GET /user/predictions/insights - Comprehensive prediction insights
GET /user/predictions/accuracy - Prediction accuracy statistics
POST /user/predictions/resolve - Resolve prediction with actual order
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.recommendations.prediction_service import PredictionService

router = APIRouter(prefix="/user/predictions", tags=["Predictive Behaviour"])


@router.get("/reorder")
async def get_suggested_reorder(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get suggested reorder with prediction confidence.

    Returns:
        - suggested_items: Items to reorder
        - suggested_time: When to order
        - confidence: Prediction confidence (0.0-1.0)
        - reasoning: Why these suggestions
        - patterns: Learned patterns (weekly, daily, semester)
    """
    service = PredictionService(db)
    return service.get_suggested_reorder(user["id"])


@router.get("/insights")
async def get_prediction_insights(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get comprehensive prediction insights.

    Returns:
        - weekly_patterns: Day-of-week ordering habits
        - daily_patterns: Time-of-day ordering habits
        - semester_patterns: Academic calendar patterns
        - favourite_vendors: Top vendors with confidence
        - favourite_foods: Top food items with confidence
        - favourite_stationery: Top stationery services with confidence
        - prediction_accuracy: Historical prediction accuracy
        - next_order_prediction: Next order prediction
    """
    service = PredictionService(db)
    return service.get_prediction_insights(user["id"])


@router.get("/accuracy")
async def get_prediction_accuracy(
    days: int = Query(30, ge=1, le=90, description="Days to look back"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get prediction accuracy statistics.

    Returns:
        - total_predictions: Total predictions made
        - correct_predictions: How many were correct
        - accuracy: Overall accuracy percentage
        - by_type: Accuracy breakdown by prediction type
    """
    service = PredictionService(db)
    return service.get_prediction_accuracy(user["id"], days)


@router.post("/resolve")
async def resolve_prediction(
    prediction_id: int = Query(..., description="Prediction ID to resolve"),
    order_id: int = Query(..., description="Actual order ID"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Resolve a prediction with actual order outcome.

    This endpoint is called after an order is placed to update
    prediction accuracy and improve future predictions.
    """
    service = PredictionService(db)
    service.resolve_prediction(prediction_id, order_id)
    return {"resolved": True, "prediction_id": prediction_id, "order_id": order_id}
