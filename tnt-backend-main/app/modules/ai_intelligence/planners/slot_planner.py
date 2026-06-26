from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order
from app.modules.slots.model import Slot


class SlotPlanner:
    """AI-powered slot and capacity intelligence"""

    def __init__(self, db: Session):
        self.db = db

    def get_capacity_recommendation(self, vendor_id: int) -> Dict[str, Any]:
        """Calculate AI capacity recommendation for vendor"""

        # Get last 7 days average orders per slot
        seven_days_ago = utcnow_naive() - timedelta(days=7)

        avg_orders_per_slot = self._calculate_avg_orders_per_slot(vendor_id, seven_days_ago)

        # Calculate vendor speed factor (based on completion rate)
        speed_factor = self._calculate_vendor_speed_factor(vendor_id, seven_days_ago)

        # AI recommendation formula
        recommended_capacity = int(avg_orders_per_slot * speed_factor)

        # Ensure reasonable bounds
        recommended_capacity = max(5, min(recommended_capacity, 50))

        reasoning = f"Based on {avg_orders_per_slot:.1f} avg orders/slot and {speed_factor:.2f} speed factor"

        return {
            "vendor_id": vendor_id,
            "recommended_capacity": recommended_capacity,
            "reasoning": reasoning
        }

    def get_slot_adjustment_signals(self, vendor_id: int) -> List[Dict[str, Any]]:
        """Generate signals for dynamic slot adjustments"""

        signals = []

        # Check for peak hours
        peak_signals = self._detect_peak_hours(vendor_id)
        signals.extend(peak_signals)

        # Check for underutilized slots
        underutilized_signals = self._detect_underutilized_slots(vendor_id)
        signals.extend(underutilized_signals)

        # Check for slot duration optimization
        duration_signals = self._optimize_slot_duration(vendor_id)
        signals.extend(duration_signals)

        return signals

    def _calculate_avg_orders_per_slot(self, vendor_id: int, since: datetime) -> float:
        """Calculate average orders per slot over time period"""

        result = self.db.query(
            func.avg(Slot.current_orders).label('avg_orders')
        ).filter(
            Slot.vendor_id == vendor_id,
            Slot.id.in_(
                self.db.query(Order.slot_id).filter(Order.created_at >= since)
            )
        ).first()

        return result.avg_orders or 0.0

    def _calculate_vendor_speed_factor(self, vendor_id: int, since: datetime) -> float:
        """Calculate vendor speed factor based on completion patterns"""

        # Simple speed factor based on order completion rate
        total_orders = self.db.query(Order).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= since
        ).count()

        completed_orders = self.db.query(Order).filter(
            Order.vendor_id == vendor_id,
            Order.status == "completed",
            Order.created_at >= since
        ).count()

        if total_orders == 0:
            return 1.0

        completion_rate = completed_orders / total_orders

        # Speed factor: higher completion rate = higher speed factor
        speed_factor = 0.8 + (completion_rate * 0.4)  # Range: 0.8 - 1.2

        return round(speed_factor, 2)

    def _detect_peak_hours(self, vendor_id: int) -> List[Dict[str, Any]]:
        """Detect peak hours and suggest special slots"""

        signals = []
        current_hour = utcnow_naive().hour

        # Check if current hour is typically busy
        busy_hours = self._get_busy_hours(vendor_id)

        if current_hour in busy_hours:
            signals.append({
                "type": "peak_hour_detected",
                "severity": "medium",
                "message": f"Peak hour detected at {current_hour}:00. Consider special handling.",
                "suggested_action": "Add extra capacity or shorter slot duration"
            })

        return signals

    def _detect_underutilized_slots(self, vendor_id: int) -> List[Dict[str, Any]]:
        """Detect slots with low utilization"""

        signals = []

        slots = self.db.query(Slot).filter(Slot.vendor_id == vendor_id).all()

        for slot in slots:
            utilization = (slot.current_orders / max(slot.max_orders, 1)) * 100

            if utilization < 30:  # Less than 30% utilization
                signals.append({
                    "type": "underutilized_slot",
                    "severity": "low",
                    "slot_id": slot.id,
                    "message": f"Slot {slot.id} has only {utilization:.1f}% utilization",
                    "suggested_action": "Consider merging with adjacent slots or reducing capacity"
                })

        return signals

    def _optimize_slot_duration(self, vendor_id: int) -> List[Dict[str, Any]]:
        """Suggest optimal slot durations based on patterns"""

        signals = []

        # Analyze completion times vs slot duration
        avg_completion_time = self._calculate_avg_completion_time(vendor_id)

        if avg_completion_time:
            optimal_duration = avg_completion_time + 5  # 5 min buffer

            signals.append({
                "type": "slot_duration_optimization",
                "severity": "info",
                "message": f"Average completion time: {avg_completion_time} min",
                "suggested_action": f"Consider {optimal_duration} min slot duration"
            })

        return signals

    def _get_busy_hours(self, vendor_id: int) -> List[int]:
        """Get hours that are typically busy"""

        seven_days_ago = utcnow_naive() - timedelta(days=7)

        busy_hours_query = self.db.query(
            func.extract('hour', Order.created_at).label('hour'),
            func.count(Order.id).label('count')
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= seven_days_ago
        ).group_by(func.extract('hour', Order.created_at))\
         .order_by(func.count(Order.id).desc())\
         .limit(3).all()

        return [int(row.hour) for row in busy_hours_query]

    def _calculate_avg_completion_time(self, vendor_id: int) -> float:
        """Calculate average time from order to completion"""
        completed_orders = self.db.query(Order).filter(
            Order.vendor_id == vendor_id,
            Order.status == "completed",
            Order.pickup_confirmed_at.isnot(None),
            Order.created_at.isnot(None),
        ).all()

        completion_minutes: list[float] = []
        for order in completed_orders:
            delta_minutes = (order.pickup_confirmed_at - order.created_at).total_seconds() / 60
            if delta_minutes > 0:
                completion_minutes.append(delta_minutes)

        if not completion_minutes:
            return 15.0

        return round(sum(completion_minutes) / len(completion_minutes), 1)
