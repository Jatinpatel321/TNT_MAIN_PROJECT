"""
Enhanced ETA API Router
=======================

Extends existing ETA endpoints with ML-powered predictions:

GET /ai/enhanced-eta/{order_id} - Enhanced ETA with all factors
GET /ai/eta-factors/{order_id} - Detailed ETA factor breakdown
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.ai_intelligence.planners.enhanced_eta_engine import EnhancedETAEngine

router = APIRouter(prefix="/ai", tags=["Enhanced ETA"])


@router.get("/enhanced-eta/{order_id}")
async def get_enhanced_eta(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get enhanced ETA prediction with ML factors.

    Extends the existing /orders/{order_id}/eta endpoint with:
    - Historical preparation times per menu item
    - Menu complexity scoring
    - Vendor workload analysis
    - Slot occupancy with time-of-day awareness
    - Delay prediction with probability
    - Preparation progress milestones
    - Confidence score

    Returns:
        - order_id: Order ID
        - predicted_eta_minutes: Estimated preparation time
        - estimated_ready_at: ISO datetime when order will be ready
        - delay_risk_level: LOW, MEDIUM, HIGH
        - confidence: Prediction confidence (0.0-1.0)
        - factors: Breakdown of prediction factors
        - preparation_progress: Progress milestones
        - delay_prediction: Delay probability and risk factors
    """
    engine = EnhancedETAEngine(db)
    return engine.get_enhanced_eta(order_id)


@router.get("/eta-factors/{order_id}")
async def get_eta_factors(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get detailed ETA factor breakdown for transparency.

    Returns:
        - menu_items: Per-item complexity and prep time
        - vendor_workload: Vendor capacity and efficiency
        - slot_occupancy: Current slot utilization
        - time_factors: Time-of-day adjustments
        - delay_risks: Identified risk factors
    """
    from app.modules.orders.model import Order, OrderItem
    from app.modules.ai_intelligence.planners.eta_engine import ETAEngine

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return {"error": "Order not found"}

    engine = EnhancedETAEngine(db)
    base_engine = ETAEngine(db)

    # Get base prediction
    base_prediction = base_engine.predict_eta(order.slot_id, order.vendor_id)

    # Get menu item details
    order_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    menu_details = []
    for oi in order_items:
        prep_time = engine.get_menu_item_prep_time(oi.menu_item_id, order.vendor_id)
        complexity = engine.get_menu_complexity_score(oi.menu_item_id)
        menu_item = db.query(OrderItem).filter(OrderItem.id == oi.id).first()
        menu_details.append({
            "menu_item_id": oi.menu_item_id,
            "quantity": oi.quantity,
            "prep_time": prep_time,
            "complexity": complexity,
        })

    # Get vendor and slot analysis
    vendor_workload = engine.get_vendor_workload(order.vendor_id)
    slot_occupancy = engine.get_slot_occupancy(order.slot_id)

    return {
        "order_id": order_id,
        "base_prediction": base_prediction,
        "menu_items": menu_details,
        "vendor_workload": vendor_workload,
        "slot_occupancy": slot_occupancy,
        "time_factors": {
            "current_hour": utcnow_naive().hour,
            "peak_hours": ["11:00-14:00", "18:00-20:00"],
            "time_multiplier": slot_occupancy["time_factor"],
        },
    }