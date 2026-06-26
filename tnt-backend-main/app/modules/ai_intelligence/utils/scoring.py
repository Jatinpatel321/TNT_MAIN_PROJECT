from typing import Any, Dict

from app.core.time_utils import utcnow_naive
from app.modules.slots.model import Slot


class SlotScoring:
    """AI-powered slot scoring utilities"""

    @staticmethod
    def calculate_slot_score(slot: Slot, vendor_speed_score: float, historical_completion_rate: float) -> float:
        """Calculate comprehensive slot score (0-100)"""

        # Factor 1: Capacity remaining (35%)
        capacity_remaining = max(0, slot.max_orders - slot.current_orders)
        max_capacity = slot.max_orders or 1
        capacity_score = (capacity_remaining / max_capacity) * 35

        # Factor 2: Vendor speed score (25%)
        speed_score = vendor_speed_score * 0.25

        # Factor 3: Historical completion rate (20%)
        completion_score = historical_completion_rate * 0.20

        # Factor 4: Rush factor penalty (20%)
        rush_factor = SlotScoring._calculate_rush_factor(slot)
        rush_penalty = rush_factor * 0.20

        # Total score
        total_score = capacity_score + speed_score + completion_score - rush_penalty

        return max(0, min(100, total_score))

    @staticmethod
    def _calculate_rush_factor(slot: Slot) -> float:
        """Calculate rush factor based on slot timing"""

        # Extract hour from slot start time
        slot_hour = slot.start_time.hour

        # Peak hours: 12-14 (lunch), 19-21 (dinner)
        if 12 <= slot_hour <= 14 or 19 <= slot_hour <= 21:
            return 0.3  # 30% rush penalty
        elif 11 <= slot_hour <= 15 or 18 <= slot_hour <= 22:
            return 0.1  # 10% mild rush penalty
        else:
            return 0.0  # No rush penalty


class CongestionScoring:
    """Congestion analysis utilities"""

    @staticmethod
    def analyze_congestion_level(slot: Slot) -> Dict[str, Any]:
        """Analyze congestion level for a slot"""

        if slot.max_orders == 0:
            return {"level": "LOW", "percentage": 0}

        utilization = slot.current_orders / slot.max_orders

        if utilization >= 0.9:
            level = "CRITICAL"
        elif utilization >= 0.75:
            level = "HIGH"
        elif utilization >= 0.5:
            level = "MEDIUM"
        else:
            level = "LOW"

        return {
            "level": level,
            "percentage": int(utilization * 100)
        }


class VendorScoring:
    """Vendor performance scoring utilities"""

    @staticmethod
    def calculate_vendor_speed_score(vendor_id: int, db) -> float:
        """Calculate vendor speed score based on completion times"""

        from datetime import datetime, timedelta

        from sqlalchemy import func

        from app.modules.orders.model import Order, OrderStatus

        thirty_days_ago = utcnow_naive() - timedelta(days=30)

        # Average completion time vs ETA
        avg_completion_vs_eta = db.query(
            func.avg(Order.eta_minutes - Order.actual_completion_minutes)
        ).filter(
            Order.vendor_id == vendor_id,
            Order.status == OrderStatus.COMPLETED,
            Order.created_at >= thirty_days_ago,
            Order.eta_minutes.isnot(None),
            Order.actual_completion_minutes.isnot(None)
        ).scalar()

        if avg_completion_vs_eta is None:
            return 50.0  # Neutral score

        # Convert to score: faster than ETA = higher score
        if avg_completion_vs_eta <= -5:  # 5+ minutes faster
            return 90.0
        elif avg_completion_vs_eta <= 0:  # On time or slightly fast
            return 75.0
        elif avg_completion_vs_eta <= 10:  # Slightly late
            return 60.0
        else:  # Significantly late
            return 30.0

    @staticmethod
    def calculate_historical_completion_rate(vendor_id: int, db) -> float:
        """Calculate historical completion rate"""

        from datetime import datetime, timedelta

        from app.modules.orders.model import Order, OrderStatus

        thirty_days_ago = utcnow_naive() - timedelta(days=30)

        completed_orders = db.query(Order).filter(
            Order.vendor_id == vendor_id,
            Order.status == OrderStatus.COMPLETED,
            Order.created_at >= thirty_days_ago
        ).count()

        total_orders = db.query(Order).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= thirty_days_ago
        ).count()

        if total_orders == 0:
            return 0.5  # 50% default

        return completed_orders / total_orders
