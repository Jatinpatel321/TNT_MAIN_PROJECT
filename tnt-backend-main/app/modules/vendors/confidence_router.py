"""
Forecast Confidence API Router
===============================

Endpoints for forecast confidence scoring:

GET /vendor/forecast/confidence - Get confidence score for forecast
GET /vendor/forecast/confidence/report - Get detailed confidence report
GET /vendor/forecast/confidence/summary - Get overall confidence summary
GET /vendor/forecast/confidence/history - Get prediction history
GET /vendor/forecast/confidence/levels - Get confidence level details
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.users.model import User
from app.modules.vendors.confidence_scoring_service import ConfidenceScoringService

router = APIRouter(prefix="/vendor/forecast/confidence", tags=["Vendor Forecast Confidence"])


def _get_vendor_id(user=Depends(get_current_user), db: Session = Depends(get_db)) -> int:
    """Resolve the authenticated user's vendor ID."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user.id


def _get_service(db: Session) -> ConfidenceScoringService:
    return ConfidenceScoringService(db)


@router.get("/{forecast_type}", summary="Get confidence score for forecast type")
def get_forecast_confidence(
    forecast_type: str,
    predicted_value: int = Query(..., description="Predicted value (orders, revenue, etc.)"),
    horizon_days: int = Query(7, ge=1, le=365, description="Forecast horizon in days"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get comprehensive confidence score for a prediction.
    
    Args:
        forecast_type: Type of forecast (short_term, daily, weekly, monthly)
        predicted_value: The predicted value
        horizon_days: Forecast horizon in days
        
    Returns:
        - confidence_percentage: Overall confidence (0-100)
        - confidence_level: high/medium/low
        - forecast_quality: excellent/good/fair/poor
        - historical_accuracy: Past prediction accuracy (0-100)
        - prediction_reliability: Consistency score (0-100)
        - risk_level: low/medium/high/critical
        - factors: Detailed factors affecting confidence
        - recommendations: AI-generated recommendations
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    
    # Get historical data (simplified - would come from forecasting service)
    historical_data = {
        "sample_size": 30,
        "patterns": [],
        "trend": "stable",
    }
    
    confidence_score = service.calculate_confidence(
        vendor_id=vendor_id,
        forecast_type=forecast_type,
        predicted_value=predicted_value,
        historical_data=historical_data,
        horizon_days=horizon_days,
    )
    
    return {
        "vendor_id": vendor_id,
        "forecast_type": forecast_type,
        "predicted_value": predicted_value,
        "confidence_percentage": confidence_score.confidence_percentage,
        "confidence_level": confidence_score.confidence_level.value,
        "forecast_quality": confidence_score.forecast_quality.value,
        "historical_accuracy": confidence_score.historical_accuracy,
        "prediction_reliability": confidence_score.prediction_reliability,
        "risk_level": confidence_score.risk_level.value,
        "factors": confidence_score.factors,
        "recommendations": confidence_score.recommendations,
    }


@router.get("/report/{forecast_type}", summary="Get detailed confidence report")
def get_confidence_report(
    forecast_type: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get detailed confidence report for a forecast type.
    
    Returns:
        - status: active/insufficient_data
        - total_predictions: Number of predictions made
        - average_accuracy: Average prediction accuracy
        - average_error_margin: Average error margin
        - accuracy_trend: improving/declining/stable
        - best_accuracy: Best accuracy achieved
        - worst_accuracy: Worst accuracy achieved
        - recent_predictions: List of recent predictions with actuals
        - insights: AI-generated insights
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_confidence_report(vendor_id, forecast_type)


@router.get("/summary", summary="Get overall confidence summary")
def get_confidence_summary(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get overall confidence summary across all forecast types.
    
    Returns:
        - overall_accuracy: Weighted average accuracy
        - total_predictions: Total predictions made
        - by_forecast_type: Breakdown by forecast type
        - overall_rating: excellent/good/fair/poor
        - recommendations: Overall recommendations
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_overall_confidence_summary(vendor_id)


@router.get("/levels", summary="Get confidence level details")
def get_confidence_levels(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get details for all confidence and risk levels.
    
    Returns:
        - confidence_levels: Details for high/medium/low
        - risk_levels: Details for low/medium/high/critical
    """
    service = _get_service(db)
    
    return {
        "confidence_levels": {
            "high": service.get_confidence_level_details(
                service.__class__.__module__.ConfidenceLevel.HIGH
            ),
            "medium": service.get_confidence_level_details(
                service.__class__.__module__.ConfidenceLevel.MEDIUM
            ),
            "low": service.get_confidence_level_details(
                service.__class__.__module__.ConfidenceLevel.LOW
            ),
        },
        "risk_levels": {
            "low": service.get_risk_level_details(
                service.__class__.__module__.RiskLevel.LOW
            ),
            "medium": service.get_risk_level_details(
                service.__class__.__module__.RiskLevel.MEDIUM
            ),
            "high": service.get_risk_level_details(
                service.__class__.__module__.RiskLevel.HIGH
            ),
            "critical": service.get_risk_level_details(
                service.__class__.__module__.RiskLevel.CRITICAL
            ),
        },
    }


@router.get("/history/{forecast_type}", summary="Get prediction history")
def get_prediction_history(
    forecast_type: str,
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get prediction history for a forecast type.
    
    Returns:
        - forecast_type: Type of forecast
        - total_records: Total records available
        - history: List of predictions with actuals
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    
    history = service._get_recent_history(vendor_id, forecast_type, limit=limit)
    
    return {
        "vendor_id": vendor_id,
        "forecast_type": forecast_type,
        "total_records": len(history),
        "history": [
            {
                "forecast_date": h.forecast_date.isoformat(),
                "predicted_value": h.predicted_value,
                "actual_value": h.actual_value,
                "confidence_score": h.confidence_score,
                "accuracy": h.accuracy,
                "error_margin": h.error_margin,
                "created_at": h.created_at.isoformat(),
            }
            for h in history
        ],
    }
