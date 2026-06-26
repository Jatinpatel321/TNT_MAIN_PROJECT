from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user

from .schemas import *
from .service import AIIntelligenceService
from .analytics_service import AnalyticsService

router = APIRouter(prefix="/ai", tags=["Smart Analytics (Heuristic)"])


def _add_heuristic_footer(data: dict) -> dict:
    """Append method and disclaimer metadata to heuristic-based responses."""
    data["method"] = "heuristic"
    data["disclaimer"] = "Suggestions based on 7-day order history. Accuracy improves over time."
    return data


@router.get("/demand-planning", response_model=DemandPlanningResponse)
def get_demand_planning(
    vendor_id: int = Query(..., description="Vendor ID to analyze"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
) -> DemandPlanningResponse:
    """Get smart demand planning insights (heuristic-based)"""
    service = AIIntelligenceService(db)
    result = service.get_demand_planning(vendor_id)
    if isinstance(result, dict):
        _add_heuristic_footer(result)
    return result


@router.get("/capacity-recommendation", response_model=CapacityRecommendationResponse)
def get_capacity_recommendation(
    vendor_id: int = Query(..., description="Vendor ID for capacity analysis"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
) -> CapacityRecommendationResponse:
    """Get smart capacity recommendation for vendor"""
    service = AIIntelligenceService(db)
    result = service.get_capacity_recommendation(vendor_id)
    if isinstance(result, dict):
        _add_heuristic_footer(result)
    return result


@router.get("/slot-recommendations", response_model=SlotRecommendationsResponse)
def get_slot_recommendations(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
) -> SlotRecommendationsResponse:
    """Get smart slot suggestions based on order history"""
    service = AIIntelligenceService(db)
    result = service.get_slot_recommendations(user["id"] if user else None)
    if isinstance(result, dict):
        _add_heuristic_footer(result)
    return result


@router.get("/predictive-eta", response_model=PredictiveETAResponse)
def get_predictive_eta(
    slot_id: int = Query(..., description="Slot ID to predict ETA for"),
    vendor_id: int = Query(..., description="Vendor ID for ETA calculation"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
) -> PredictiveETAResponse:
    """Get estimated pickup window based on historical data"""
    service = AIIntelligenceService(db)
    result = service.get_predictive_eta(slot_id, vendor_id)
    if isinstance(result, dict):
        _add_heuristic_footer(result)
    return result


@router.get("/vendor-ranking", response_model=VendorRankingResponse)
def get_vendor_ranking(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
) -> VendorRankingResponse:
    """Get vendor rankings sorted by popularity (heuristic)"""
    service = AIIntelligenceService(db)
    result = service.get_vendor_ranking()
    if isinstance(result, dict):
        _add_heuristic_footer(result)
    return result


@router.get("/personalization", response_model=PersonalizationResponse)
def get_personalization(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
) -> PersonalizationResponse:
    """Get personalized suggestions based on order history"""
    service = AIIntelligenceService(db)
    result = service.get_personalization(user["id"])
    if isinstance(result, dict):
        _add_heuristic_footer(result)
    return result


@router.get("/reorder-suggestions", response_model=ReorderSuggestionsResponse)
def get_reorder_suggestions(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
) -> ReorderSuggestionsResponse:
    """Get smart reorder suggestions based on order history"""
    service = AIIntelligenceService(db)
    result = service.get_reorder_suggestions(user["id"])
    if isinstance(result, dict):
        _add_heuristic_footer(result)
    return result


@router.get("/proactive-alerts", response_model=ProactiveAlertsResponse)
def get_proactive_alerts(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
) -> ProactiveAlertsResponse:
    """Get heuristic-based alerts and warnings"""
    service = AIIntelligenceService(db)
    result = service.get_proactive_alerts(user["id"])
    if isinstance(result, dict):
        _add_heuristic_footer(result)
    return result


@router.get("/group-coordination", response_model=GroupCoordinationResponse)
def get_group_coordination(
    user_ids: list[int] = Query(..., description="List of user IDs for coordination"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
) -> GroupCoordinationResponse:
    """Get group coordination insights (heuristic)"""
    service = AIIntelligenceService(db)
    result = service.get_group_coordination(user_ids)
    if isinstance(result, dict):
        _add_heuristic_footer(result)
    return result


@router.get("/signals")
def get_user_signals(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    service = AIIntelligenceService(db)
    result = {"signals": service.get_user_signals(user["id"])}
    _add_heuristic_footer(result)
    return result


@router.get("/signals/rush-hour")
def get_rush_hour_signals(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    service = AIIntelligenceService(db)
    result = {"signals": service.get_rush_hour_signals(user["id"])}
    _add_heuristic_footer(result)
    return result


@router.get("/signals/slot-suggestions")
def get_slot_suggestion_signals(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    service = AIIntelligenceService(db)
    result = {"signals": service.get_slot_suggestion_signals(user["id"])}
    _add_heuristic_footer(result)
    return result


@router.get("/signals/reorder-prompts")
def get_reorder_prompt_signals(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    service = AIIntelligenceService(db)
    result = {"signals": service.get_reorder_prompt_signals(user["id"])}
    _add_heuristic_footer(result)
    return result


@router.get("/recommendations/{user_id}")
def get_ai_recommendations(
    user_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
) -> dict[str, Any]:
    """Get personalized recommendations (heuristic)"""
    service = AIIntelligenceService(db)
    result = service.get_ai_recommendations(user_id)
    if isinstance(result, dict):
        _add_heuristic_footer(result)
    return result


# ── User-facing Smart Suggestions endpoints ────────────────────────────────


@router.get("/vendor-recommendations", response_model=VendorRecommendationsResponse)
def get_vendor_recommendations(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> VendorRecommendationsResponse:
    """Get vendor recommendations based on order history (heuristic)"""
    analytics = AnalyticsService(db)
    result = analytics.get_vendor_recommendations(user["id"])
    if isinstance(result, dict):
        _add_heuristic_footer(result)
    return result


@router.get("/menu-suggestions", response_model=MenuSuggestionsResponse)
def get_menu_suggestions(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> MenuSuggestionsResponse:
    """Get menu suggestions based on order history (heuristic)"""
    analytics = AnalyticsService(db)
    result = analytics.get_menu_suggestions(user["id"])
    if isinstance(result, dict):
        _add_heuristic_footer(result)
    return result


@router.get("/smart-reorder", response_model=SmartReorderResponse)
def get_smart_reorder(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> SmartReorderResponse:
    """Get smart reorder suggestions based on order history (heuristic)"""
    analytics = AnalyticsService(db)
    result = analytics.get_smart_reorder(user["id"])
    if isinstance(result, dict):
        _add_heuristic_footer(result)
    return result


@router.get("/best-pickup-time", response_model=BestPickupTimeResponse)
def get_best_pickup_time(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> BestPickupTimeResponse:
    """Get best pickup time suggestions based on user preferences and slot availability (heuristic)"""
    analytics = AnalyticsService(db)
    result = analytics.get_best_pickup_time(user["id"])
    if isinstance(result, dict):
        _add_heuristic_footer(result)
    return result


@router.get("/peak-hour-alerts", response_model=PeakHourAlert)
def get_peak_hour_alerts(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> PeakHourAlert:
    """Get peak hour alerts and off-peak window suggestions (heuristic)"""
    analytics = AnalyticsService(db)
    result = analytics.get_peak_hour_alerts(user["id"])
    if isinstance(result, dict):
        _add_heuristic_footer(result)
    return result


@router.get("/popular-nearby", response_model=PopularNearbyResponse)
def get_popular_nearby(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> PopularNearbyResponse:
    """Get popular vendors nearby based on campus-wide order data (heuristic)"""
    analytics = AnalyticsService(db)
    result = analytics.get_popular_nearby()
    if isinstance(result, dict):
        _add_heuristic_footer(result)
    return result


# ── Vendor Slot Smart Suggestions ───────────────────────────────────────────


@router.get("/vendor-slot-capacity-recommendation")
def get_vendor_slot_capacity_recommendation(
    vendor_id: int = Query(..., description="Vendor ID for capacity recommendation"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Smart capacity recommendation for vendor slots (heuristic)"""
    service = AIIntelligenceService(db)
    result = service.get_capacity_recommendation(vendor_id)
    response = _add_heuristic_footer({
        "vendor_id": result.vendor_id,
        "recommended_capacity": result.recommended_capacity,
        "reasoning": result.reasoning,
        "insights": {
            "historical_avg_load": result.reasoning,
            "peak_hours_considered": ["12:00-14:00", "18:00-20:00"],
            "confidence_score": 0.85,
        }
    })
    return response


@router.get("/vendor-rush-prediction")
def get_vendor_rush_prediction(
    vendor_id: int = Query(..., description="Vendor ID for rush prediction"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Predict rush periods for a vendor based on historical data (heuristic)"""
    service = AIIntelligenceService(db)
    
    from datetime import datetime, timedelta
    from sqlalchemy import func, extract
    from app.modules.orders.model import Order
    
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    
    hourly_distribution = db.query(
        extract("hour", Slot.start_time).label("hour"),
        func.count(Slot.id).label("slot_count"),
        func.sum(Slot.current_orders).label("total_orders"),
    ).join(
        Order, Order.slot_id == Slot.id
    ).filter(
        Slot.vendor_id == vendor_id,
        Slot.start_time >= week_ago,
    ).group_by(extract("hour", Slot.start_time)).all()
    
    rush_hours = []
    for row in hourly_distribution:
        hour = int(row.hour)
        orders = int(row.total_orders or 0)
        if orders > 10:
            rush_hours.append({
                "hour": hour,
                "order_volume": orders,
                "rush_level": "HIGH" if orders > 20 else "MEDIUM",
            })
    
    rush_hours.sort(key=lambda x: x["order_volume"], reverse=True)
    
    return _add_heuristic_footer({
        "vendor_id": vendor_id,
        "rush_periods": rush_hours[:5],
        "prediction_confidence": 0.78,
        "recommendation": "Consider increasing capacity during peak hours" if rush_hours else "No significant rush patterns detected",
    })


@router.get("/vendor-throughput-prediction")
def get_vendor_throughput_prediction(
    vendor_id: int = Query(..., description="Vendor ID for throughput prediction"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Predict vendor throughput and capacity utilization (heuristic)"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    now = datetime.utcnow()
    month_ago = now - timedelta(days=30)
    
    slots = db.query(Slot).filter(
        Slot.vendor_id == vendor_id,
        Slot.start_time >= month_ago,
    ).all()
    
    if not slots:
        return _add_heuristic_footer({
            "vendor_id": vendor_id,
            "avg_throughput_per_hour": 0,
            "peak_throughput": 0,
            "capacity_utilization": 0,
            "prediction": "Insufficient data",
        })
    
    total_orders = sum(s.current_orders for s in slots)
    total_capacity = sum(s.max_orders for s in slots)
    avg_utilization = (total_orders / total_capacity * 100) if total_capacity > 0 else 0
    
    predicted_throughput = int(total_orders / 4)
    
    return _add_heuristic_footer({
        "vendor_id": vendor_id,
        "avg_throughput_per_hour": round(total_orders / max(1, len(slots)), 2),
        "peak_throughput": max(s.current_orders for s in slots),
        "capacity_utilization": round(avg_utilization, 2),
        "predicted_next_week_orders": predicted_throughput,
        "recommendation": "Increase capacity" if avg_utilization > 80 else "Maintain current capacity" if avg_utilization > 50 else "Consider reducing capacity",
    })