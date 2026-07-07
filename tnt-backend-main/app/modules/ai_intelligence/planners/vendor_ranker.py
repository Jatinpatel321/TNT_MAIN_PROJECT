from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.load_insights import get_load_label, is_express_pickup_eligible
from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderStatus
from app.modules.slots.model import Slot
from app.modules.users.model import User, UserRole


class VendorRanker:
    """AI-powered vendor ranking and load analytics"""

    def __init__(self, db: Session):
        self.db = db

    def get_vendor_rankings(self) -> List[Dict[str, Any]]:
        """Generate AI-powered vendor rankings"""

        vendors = self.db.query(User).filter(
            User.role == UserRole.VENDOR,
            User.is_approved == True
        ).all()

        rankings = []

        for vendor in vendors:
            rank_score = self._calculate_vendor_rank_score(vendor.id)
            load_indicator = self._calculate_live_load_indicator(vendor.id)
            express_pickup_eligible = self._calculate_express_pickup_eligibility(vendor.id)
            reasoning = self._generate_ranking_reasoning(vendor.id, rank_score, load_indicator)

            rankings.append({
                "vendor_id": vendor.id,
                "vendor_rank_score": rank_score,
                "live_load_indicator": load_indicator,
                "express_pickup_eligible": express_pickup_eligible,
                "reasoning": reasoning
            })

        # Sort by rank score descending
        rankings.sort(key=lambda x: x["vendor_rank_score"], reverse=True)

        return rankings

    def _calculate_vendor_rank_score(self, vendor_id: int) -> float:
        """Calculate comprehensive vendor rank score (0-100)"""

        thirty_days_ago = utcnow_naive() - timedelta(days=30)

        # Factor 1: Completion speed (30%)
        completion_speed = self._calculate_completion_speed(vendor_id, thirty_days_ago)

        # Factor 2: Success rate (25%)
        success_rate = self._calculate_success_rate(vendor_id, thirty_days_ago)

        # Factor 3: Customer satisfaction proxy (20%)
        # Using repeat orders as satisfaction proxy
        satisfaction_score = self._calculate_satisfaction_score(vendor_id, thirty_days_ago)

        # Factor 4: Operational efficiency (15%)
        efficiency_score = self._calculate_efficiency_score(vendor_id)

        # Factor 5: Recent performance (10%)
        recent_performance = self._calculate_recent_performance(vendor_id)

        # Weighted score calculation
        rank_score = (
            completion_speed * 0.30 +
            success_rate * 0.25 +
            satisfaction_score * 0.20 +
            efficiency_score * 0.15 +
            recent_performance * 0.10
        )

        return round(rank_score, 2)

    def _calculate_live_load_indicator(self, vendor_id: int) -> str:
        """Calculate current load level: LOW/MEDIUM/HIGH"""

        # Check current slot utilization
        current_slots = self.db.query(Slot).filter(Slot.vendor_id == vendor_id).all()

        if not current_slots:
            return "LOW"

        total_capacity = sum(slot.max_orders for slot in current_slots)
        current_orders = sum(slot.current_orders for slot in current_slots)

        return get_load_label(current_orders, total_capacity)

    def _calculate_express_pickup_eligibility(self, vendor_id: int) -> bool:
        current_slots = self.db.query(Slot).filter(Slot.vendor_id == vendor_id).all()
        if not current_slots:
            return False

        total_capacity = sum(slot.max_orders for slot in current_slots)
        current_orders = sum(slot.current_orders for slot in current_slots)
        return is_express_pickup_eligible(current_orders, total_capacity)

    def _calculate_completion_speed(self, vendor_id: int, since: datetime) -> float:
        """Calculate average completion speed score"""

        # This would require order timeline data
        # For now, use completion rate as proxy
        completed_orders = self.db.query(Order).filter(
            Order.vendor_id == vendor_id,
            Order.status == OrderStatus.COMPLETED,
            Order.created_at >= since
        ).count()

        total_orders = self.db.query(Order).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= since
        ).count()

        if total_orders == 0:
            return 50.0  # Neutral score

        completion_rate = completed_orders / total_orders
        speed_score = completion_rate * 100

        return speed_score

    def _calculate_success_rate(self, vendor_id: int, since: datetime) -> float:
        """Calculate order success rate"""

        successful_orders = self.db.query(Order).filter(
            Order.vendor_id == vendor_id,
            Order.status.in_([OrderStatus.COMPLETED, OrderStatus.CONFIRMED]),
            Order.created_at >= since
        ).count()

        total_orders = self.db.query(Order).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= since
        ).count()

        if total_orders == 0:
            return 50.0

        success_rate = successful_orders / total_orders * 100
        return success_rate

    def _calculate_satisfaction_score(self, vendor_id: int, since: datetime) -> float:
        """Calculate satisfaction score based on repeat orders"""

        # Count unique customers with multiple orders
        repeat_customers_query = self.db.query(
            Order.user_id,
            func.count(Order.id).label('order_count')
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= since
        ).group_by(Order.user_id)\
         .having(func.count(Order.id) > 1)\
         .subquery()

        total_customers = self.db.query(Order.user_id).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= since
        ).distinct().count()

        if total_customers == 0:
            return 50.0

        repeat_customers = self.db.query(repeat_customers_query).count()
        satisfaction_rate = repeat_customers / total_customers * 100

        return satisfaction_rate

    def _calculate_efficiency_score(self, vendor_id: int) -> float:
        """Calculate operational efficiency score"""

        # Based on average orders per slot utilization
        slots = self.db.query(Slot).filter(Slot.vendor_id == vendor_id).all()

        if not slots:
            return 50.0

        total_utilization = sum(
            slot.current_orders / max(slot.max_orders, 1)
            for slot in slots
        )

        avg_utilization = total_utilization / len(slots)
        efficiency_score = avg_utilization * 100

        return efficiency_score

    def _calculate_recent_performance(self, vendor_id: int) -> float:
        """Calculate recent 7-day performance"""

        seven_days_ago = utcnow_naive() - timedelta(days=7)

        recent_completion_rate = self._calculate_success_rate(vendor_id, seven_days_ago)

        return recent_completion_rate

    def _generate_ranking_reasoning(self, vendor_id: int, score: float, load: str) -> str:
        """Generate human-readable reasoning for ranking"""

        if score >= 80:
            base_reason = "Excellent performance across all metrics"
        elif score >= 60:
            base_reason = "Good overall performance"
        elif score >= 40:
            base_reason = "Average performance with room for improvement"
        else:
            base_reason = "Needs improvement in key areas"

        load_reason = f" with {load.lower()} current load" if load != "LOW" else ""

        return f"{base_reason}{load_reason}"
