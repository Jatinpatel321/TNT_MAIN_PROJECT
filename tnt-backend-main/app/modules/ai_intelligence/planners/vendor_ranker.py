from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.load_insights import get_load_label, is_express_pickup_eligible
from app.core.time_utils import utcnow_naive
from app.modules.ai_intelligence.ml_bridge import predict_with_fallback
from app.modules.orders.model import Order, OrderStatus
from app.modules.slots.model import Slot
from app.modules.users.model import User, UserRole

try:
    from app.modules.feedback.model import VendorReview as _VendorReview  # noqa: F401
    _HAS_VENDOR_REVIEW = True
except ImportError:
    _HAS_VENDOR_REVIEW = False


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
            rank_score, source = self._calculate_vendor_rank_score(vendor.id)
            load_indicator = self._calculate_live_load_indicator(vendor.id)

            # Policy-driven hard rule: express pickup eligibility is computed
            # from live capacity data, NOT delegated to the ML model.
            express_pickup_eligible = self._calculate_express_pickup_eligibility(vendor.id)
            reasoning = self._generate_ranking_reasoning(vendor.id, rank_score, load_indicator)

            rankings.append({
                "vendor_id": vendor.id,
                "vendor_rank_score": rank_score,
                "live_load_indicator": load_indicator,
                "express_pickup_eligible": express_pickup_eligible,
                "reasoning": reasoning,
                "source": source,
            })

        # Sort by rank score descending and assign rank index
        rankings.sort(key=lambda x: x["vendor_rank_score"], reverse=True)
        for idx, r in enumerate(rankings, start=1):
            r["rank"] = idx

        return rankings

    def _calculate_vendor_rank_score(self, vendor_id: int) -> tuple[float, str]:
        """Calculate comprehensive vendor rank score (0-100), via ML or heuristic fallback.

        Returns (score, source) where source is "model" or "heuristic".
        """
        thirty_days_ago = utcnow_naive() - timedelta(days=30)

        # Gather raw metrics needed by both heuristic and feature vector
        total_orders = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= thirty_days_ago,
        ).scalar() or 0

        completed = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.status.in_([OrderStatus.COMPLETED]),
            Order.created_at >= thirty_days_ago,
        ).scalar() or 0

        cancelled = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.status == OrderStatus.CANCELLED,
            Order.created_at >= thirty_days_ago,
        ).scalar() or 0

        repeat_customers = self.db.query(
            Order.user_id, func.count(Order.id)
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= thirty_days_ago,
        ).group_by(Order.user_id).having(func.count(Order.id) > 1).count()

        unique_customers = self.db.query(Order.user_id).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= thirty_days_ago,
        ).distinct().count()

        avg_rating = 0.0
        if _HAS_VENDOR_REVIEW:
            try:
                from app.modules.feedback.model import VendorReview
                avg_rating = self.db.query(func.avg(VendorReview.rating)).filter(
                    VendorReview.vendor_id == vendor_id
                ).scalar() or 0.0
            except Exception:
                avg_rating = 0.0

        completion_rate = completed / max(total_orders, 1)
        repeat_rate = repeat_customers / max(unique_customers, 1)

        # Build feature dict matching extract_vendor_ranking_features columns:
        # ["completion_rate", "avg_rating", "repeat_customer_rate",
        #  "cancellations", "refunds", "total_orders"]
        features = {
            "completion_rate": completion_rate,
            "avg_rating": float(avg_rating),
            "repeat_customer_rate": repeat_rate,
            "cancellations": float(cancelled),
            "refunds": float(cancelled),   # refunds proxied by cancellations (same in training)
            "total_orders": float(total_orders),
        }

        # Heuristic: original weighted scoring formula, unchanged in behaviour
        def heuristic_fn() -> float:
            speed_score = self._calculate_completion_speed(vendor_id, thirty_days_ago)
            success_score = self._calculate_success_rate(vendor_id, thirty_days_ago)
            satisfaction_score = self._calculate_satisfaction_score(vendor_id, thirty_days_ago)
            efficiency_score = self._calculate_efficiency_score(vendor_id)
            recent_score = self._calculate_recent_performance(vendor_id)
            return round(
                speed_score * 0.30 +
                success_score * 0.25 +
                satisfaction_score * 0.20 +
                efficiency_score * 0.15 +
                recent_score * 0.10,
                2,
            )

        raw_score, source = predict_with_fallback(
            "vendor_ranking", features, heuristic_fn
        )

        # Model output is in [0, 1] (completion_rate range) — scale to 0–100
        if source == "model":
            rank_score = round(float(raw_score) * 100, 2)
        else:
            rank_score = float(raw_score)

        # Clamp to valid range
        rank_score = max(0.0, min(rank_score, 100.0))

        return rank_score, source

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
