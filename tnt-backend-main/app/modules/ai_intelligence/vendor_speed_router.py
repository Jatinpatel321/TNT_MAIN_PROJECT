"""
Vendor Speed API Router
=======================

Endpoints for dynamic vendor speed adjustment:

GET /ai/vendor-speed/{vendor_id} - Get vendor speed metrics
GET /ai/vendor-speed/batch - Get batch vendor speeds
GET /ai/vendor-speed/waiting-time/{vendor_id} - Get predicted waiting time
GET /ai/vendor-speed/suggested-delay/{vendor_id} - Get suggested ordering delay
POST /ai/vendor-speed/update-eta/{order_id} - Update ETA with vendor speed
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.ai_intelligence.vendor_speed_service import VendorSpeedService

router = APIRouter(prefix="/ai", tags=["Vendor Speed"])


@router.get("/vendor-speed/{vendor_id}")
async def get_vendor_speed(
    vendor_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get comprehensive vendor speed metrics.

    Returns:
        - vendor_id
        - speed_score: 0.0-1.0
        - speed_label: FAST, NORMAL, BUSY, VERY_BUSY
        - predicted_waiting_time
        - suggested_delay
        - measurements: All raw measurements
        - factors: Scoring factors
        - recommendations
    """
    service = VendorSpeedService(db)
    return service.get_vendor_speed_metrics(vendor_id)


@router.get("/vendor-speed/batch")
async def get_batch_vendor_speeds(
    vendor_ids: str = Query(..., description="Comma-separated vendor IDs"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get speed metrics for multiple vendors.

    Args:
        vendor_ids: Comma-separated list of vendor IDs

    Returns:
        List of vendor speed metrics
    """
    ids = [int(vid.strip()) for vid in vendor_ids.split(",") if vid.strip()]
    service = VendorSpeedService(db)
    return service.get_batch_vendor_speeds(ids)


@router.get("/vendor-speed/waiting-time/{vendor_id}")
async def get_waiting_time(
    vendor_id: int,
    order_size: int = Query(1, ge=1, le=20, description="Number of items in order"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get predicted waiting time for a new order.

    Args:
        vendor_id: Vendor ID
        order_size: Number of items (default: 1)

    Returns:
        - base_wait_time
        - queue_wait_time
        - total_wait_time
        - confidence
    """
    service = VendorSpeedService(db)
    return service.calculate_predicted_waiting_time(vendor_id, order_size)


@router.get("/vendor-speed/suggested-delay/{vendor_id}")
async def get_suggested_delay(
    vendor_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get suggested ordering delay to avoid congestion.

    Returns:
        - should_delay: Whether to delay ordering
        - suggested_delay_minutes
        - optimal_order_time
        - reason
    """
    service = VendorSpeedService(db)
    return service.calculate_suggested_delay(vendor_id)


@router.post("/vendor-speed/update-eta/{order_id}")
async def update_eta_with_speed(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Update ETA for an order based on current vendor speed.

    This dynamically adjusts ETA based on real-time vendor performance.

    Returns:
        - order_id
        - original_eta
        - updated_eta
        - speed_label
        - adjustment_factor
    """
    service = VendorSpeedService(db)
    return service.update_eta_with_vendor_speed(order_id)