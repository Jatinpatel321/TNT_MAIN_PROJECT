"""
Group AI Coordination Router
=============================

Endpoints for AI-powered group coordination:

GET /groups/{group_id}/ai/suggestions - Get comprehensive AI suggestions
GET /groups/{group_id}/ai/availability - Get member availability analysis
GET /groups/{group_id}/ai/pickup-slot - Get best pickup slot suggestion
GET /groups/{group_id}/ai/common-items - Get common menu item suggestions
GET /groups/{group_id}/ai/conflicts - Detect ordering conflicts
GET /groups/{group_id}/ai/synchronization - Get pickup synchronization
POST /groups/{group_id}/ai/save-suggestions - Save AI suggestions
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.group_cart.group_ai_service import GroupAIService

router = APIRouter(prefix="/groups", tags=["Group AI"])


@router.get("/{group_id}/ai/suggestions")
async def get_group_ai_suggestions(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get comprehensive AI suggestions for group coordination.

    Returns:
        - member_availability: Analysis of all members
        - optimal_ordering_time: Best time for group order
        - suggested_pickup_slot: Best slot recommendation
        - common_menu_items: Items liked by multiple members
        - ordering_conflicts: Detected conflicts
        - pickup_synchronization: Pickup timing analysis
        - overall_recommendations: Summary recommendations
    """
    service = GroupAIService(db)
    return service.get_group_ai_suggestions(group_id)


@router.get("/{group_id}/ai/availability")
async def get_member_availability(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get member availability analysis.

    Returns:
        - members: List with availability scores
        - optimal_ordering_time: Suggested time
        - availability_score: Overall score
        - conflicts: Scheduling conflicts
    """
    service = GroupAIService(db)
    return service.analyze_member_availability(group_id)


@router.get("/{group_id}/ai/pickup-slot")
async def get_pickup_slot_suggestion(
    group_id: int,
    vendor_id: int = Query(..., description="Vendor ID for slot suggestion"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get best pickup slot suggestion for the group.

    Args:
        vendor_id: Vendor ID to find slots for

    Returns:
        - suggested_slot_id
        - suggested_slot_time
        - alternatives
        - reasoning
        - confidence
    """
    service = GroupAIService(db)
    return service.suggest_best_pickup_slot(group_id, vendor_id)


@router.get("/{group_id}/ai/common-items")
async def get_common_menu_items(
    group_id: int,
    vendor_id: int = Query(..., description="Vendor ID"),
    limit: int = Query(10, ge=1, le=20, description="Max items to return"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get common menu items across group members.

    Args:
        vendor_id: Vendor ID
        limit: Maximum suggestions (default: 10)

    Returns:
        - suggested_items: Common items
        - member_preferences: Breakdown by member
        - conflicts: Preference conflicts
    """
    service = GroupAIService(db)
    return service.suggest_common_menu_items(group_id, vendor_id, limit)


@router.get("/{group_id}/ai/conflicts")
async def get_ordering_conflicts(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Detect ordering conflicts in the group.

    Returns:
        - conflicts: List of conflicts
        - severity: LOW, MEDIUM, HIGH
        - suggestions: Resolution suggestions
    """
    service = GroupAIService(db)
    return service.detect_ordering_conflicts(group_id)


@router.get("/{group_id}/ai/synchronization")
async def get_pickup_synchronization(
    group_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get pickup synchronization analysis.

    Returns:
        - synchronization_score: 0.0-1.0
        - estimated_pickup_time
        - pickup_windows: Per-item windows
        - synchronization_plan: Strategy recommendation
    """
    service = GroupAIService(db)
    return service.calculate_pickup_synchronization(group_id)


@router.post("/{group_id}/ai/save-suggestions")
async def save_ai_suggestions(
    group_id: int,
    suggestions: dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Save AI suggestions for tracking and analytics.

    Args:
        suggestions: AI suggestions to save

    Returns:
        - saved: Success status
        - group_id
    """
    service = GroupAIService(db)
    return service.save_ai_suggestions(group_id, suggestions)