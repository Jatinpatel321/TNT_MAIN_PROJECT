"""
AI Inventory Planning API Router
=================================

Predictions and suggestions for inventory planning.

Endpoints:
GET /vendor/inventory/ai/plan - Generate complete inventory plan
GET /vendor/inventory/ai/items-finishing - Items likely to finish
GET /vendor/inventory/ai/items-restock - Items to restock
GET /vendor/inventory/ai/demand - Expected demand predictions
GET /vendor/inventory/ai/wastage - Expected wastage predictions
GET /vendor/inventory/ai/restock-suggestions - Restock suggestions
GET /vendor/inventory/ai/waste-suggestions - Waste reduction suggestions
GET /vendor/inventory/ai/purchase-plan - Smart purchase plan
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.users.model import User
from app.modules.vendors.ai_inventory_planning_service import AIInventoryPlanningService

router = APIRouter(prefix="/vendors/inventory/ai", tags=["Vendor AI Inventory"])


def _resolve_vendor(user: dict, db: Session) -> int:
    """Get vendor user ID from authenticated user."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user.id


def _get_service(db: Session) -> AIInventoryPlanningService:
    return AIInventoryPlanningService(db)


@router.get("/plan", summary="Generate complete inventory plan")
def get_inventory_plan(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Generate complete AI inventory plan with predictions and suggestions.
    
    Returns:
        - items_likely_to_finish: Items with stock-out risk
        - items_to_restock: Items needing restock
        - expected_demand: Predicted demand per item
        - expected_wastage: Predicted wastage per item
        - restock_suggestions: Actionable restock suggestions
        - waste_reduction_suggestions: Waste reduction tips
        - smart_purchase_plan: Optimized purchase quantities
        - summary: Summary statistics
        - insights: AI-generated insights
    """
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    plan = service.generate_inventory_plan(vendor_id)
    
    return {
        "vendor_id": vendor_id,
        "generated_at": plan.generated_at,
        "items_likely_to_finish": plan.items_likely_to_finish,
        "items_to_restock": plan.items_to_restock,
        "expected_demand": plan.expected_demand,
        "expected_wastage": plan.expected_wastage,
        "restock_suggestions": plan.restock_suggestions,
        "waste_reduction_suggestions": plan.waste_reduction_suggestions,
        "smart_purchase_plan": plan.smart_purchase_plan,
        "summary": plan.summary,
        "insights": plan.insights,
    }


@router.get("/items-finishing", summary="Items likely to finish soon")
def get_items_finishing(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get items likely to run out of stock soon.
    
    Returns:
        - total_items: Number of items at risk
        - items: List of items with stock-out details
        - insights: AI insights
    """
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    return service.get_items_likely_to_finish(vendor_id)


@router.get("/items-restock", summary="Items to restock")
def get_items_restock(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get items that need restocking with priority.
    
    Returns:
        - total_items: Number of items needing restock
        - items: List of items with restock details
        - priority_breakdown: Count by priority level
    """
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    return service.get_items_to_restock(vendor_id)


@router.get("/demand", summary="Expected demand predictions")
def get_demand(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get expected demand predictions for inventory items.
    
    Returns:
        - total_daily_demand: Total expected daily demand
        - total_weekly_demand: Total expected weekly demand
        - items: Per-item demand breakdown
    """
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    return service.get_expected_demand(vendor_id)


@router.get("/wastage", summary="Expected wastage predictions")
def get_wastage(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get expected wastage predictions.
    
    Returns:
        - total_predicted_wastage: Total predicted waste
        - high_risk_items: Items with high waste risk
        - items: Per-item wastage breakdown
    """
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    return service.get_expected_wastage(vendor_id)


@router.get("/restock-suggestions", summary="Restock suggestions")
def get_restock_suggestions(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get actionable restock suggestions.
    
    Returns:
        - total_suggestions: Number of suggestions
        - suggestions: List of restock suggestions
        - insights: AI insights
    """
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    return service.get_restock_suggestions(vendor_id)


@router.get("/waste-suggestions", summary="Waste reduction suggestions")
def get_waste_suggestions(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get waste reduction suggestions.
    
    Returns:
        - total_suggestions: Number of suggestions
        - suggestions: List of waste reduction suggestions
        - insights: AI insights
    """
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    return service.get_waste_reduction_suggestions(vendor_id)


@router.get("/purchase-plan", summary="Smart purchase plan")
def get_purchase_plan(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get smart purchase plan with optimized quantities.
    
    Returns:
        - total_items: Number of items in plan
        - plan: Purchase plan by priority
        - total_estimated_cost: Estimated total cost
        - summary: Summary statistics
        - insights: AI insights
    """
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    return service.get_smart_purchase_plan(vendor_id)
