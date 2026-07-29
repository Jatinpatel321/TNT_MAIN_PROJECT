from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.ml.features import is_rush_hour
from app.modules.ai_intelligence.ml_bridge import predict_with_fallback
from app.modules.orders.model import Order
from app.modules.slots.model import Slot

# Hard safety constant: never recommend a slot at or above this occupancy
_MAX_SAFE_OCCUPANCY = 0.90


class SlotPlanner:
    """AI-powered slot and capacity intelligence"""

    def __init__(self, db: Session):
        self.db = db

    def get_capacity_recommendation(self, vendor_id: int) -> Dict[str, Any]:
        """Calculate AI capacity recommendation for vendor, via ML or heuristic fallback."""

        # Get last 7 days average orders per slot
        seven_days_ago = utcnow_naive() - timedelta(days=7)

        avg_orders_per_slot = self._calculate_avg_orders_per_slot(vendor_id, seven_days_ago)
        speed_factor = self._calculate_vendor_speed_factor(vendor_id, seven_days_ago)

        # Heuristic: original formula — avg_orders_per_slot * speed_factor, clamped 5–50
        def heuristic_fn() -> int:
            return max(5, min(int(avg_orders_per_slot * speed_factor), 50))

        # Build features matching extract_slot_features columns:
        # ["occupancy", "hour", "weekday", "rush_hour", "avg_completion_minutes", "max_capacity"]
        # For the capacity recommendation we represent the vendor's aggregated slot state
        slots = self.db.query(Slot).filter(Slot.vendor_id == vendor_id).all()
        if slots:
            total_cap = sum(s.max_orders for s in slots)
            total_orders = sum(s.current_orders for s in slots)
            agg_occupancy = total_orders / max(total_cap, 1)
            max_cap = total_cap / max(len(slots), 1)
        else:
            agg_occupancy = 0.0
            max_cap = 10.0

        now = utcnow_naive()
        avg_completion = self._calculate_avg_completion_time(vendor_id)
        features = {
            "occupancy": agg_occupancy,
            "hour": float(now.hour),
            "weekday": float(now.weekday()),
            "rush_hour": float(1 if is_rush_hour(now) else 0),
            "avg_completion_minutes": float(avg_completion),
            "max_capacity": float(max_cap),
        }

        raw_result, source = predict_with_fallback(
            "slot_recommendation", features, heuristic_fn
        )

        # Model predicts occupancy (0–1 range) — convert to a capacity number
        if source == "model":
            predicted_occupancy = max(0.0, min(float(raw_result), 1.0))
            # Recommended capacity: if model predicts lower occupancy, suggest higher cap
            total_current_orders = sum(s.current_orders for s in slots) if slots else 0
            if predicted_occupancy > 0:
                recommended_capacity = int(total_current_orders / predicted_occupancy)
            else:
                recommended_capacity = heuristic_fn()
        else:
            recommended_capacity = int(raw_result)

        # Ensure reasonable bounds regardless of source
        recommended_capacity = max(5, min(recommended_capacity, 50))

        reasoning = (
            f"Based on {avg_orders_per_slot:.1f} avg orders/slot and "
            f"{speed_factor:.2f} speed factor [source: {source}]"
        )

        return {
            "vendor_id": vendor_id,
            "recommended_capacity": recommended_capacity,
            "reasoning": reasoning,
            "source": source,
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

    def get_available_slots_ranked(self, vendor_id: int) -> List[Dict[str, Any]]:
        """Return available slots for vendor ranked by ML recommendation score.

        HARD SAFETY RULE: Slots at > 90% capacity are ALWAYS excluded from
        recommendations, regardless of model output.
        """
        slots = self.db.query(Slot).filter(Slot.vendor_id == vendor_id).all()
        scored = []
        for slot in slots:
            occupancy = slot.current_orders / max(slot.max_orders, 1)

            # ── Hard safety rule — enforced BEFORE and AFTER bridge call ──
            if occupancy >= _MAX_SAFE_OCCUPANCY:
                continue

            avg_completion = self._calculate_avg_completion_time(vendor_id)
            features = {
                "occupancy": occupancy,
                "hour": float(slot.start_time.hour),
                "weekday": float(slot.start_time.weekday()),
                "rush_hour": float(1 if is_rush_hour(slot.start_time) else 0),
                "avg_completion_minutes": float(avg_completion),
                "max_capacity": float(slot.max_orders),
            }

            # Heuristic: lower occupancy is better → invert for ranking score
            def heuristic_fn(occ=occupancy) -> float:
                return 1.0 - occ

            score, source = predict_with_fallback(
                "slot_recommendation", features, heuristic_fn
            )
            rec_score = float(score)

            # ── Post-bridge safety re-check ──
            # (model output might encode high occupancy as high score — clamp)
            if occupancy >= _MAX_SAFE_OCCUPANCY:
                continue

            scored.append({
                "slot_id": slot.id,
                "occupancy_pct": int(occupancy * 100),
                "recommendation_score": round(rec_score, 3),
                "source": source,
            })

        scored.sort(key=lambda s: s["recommendation_score"], reverse=True)
        return scored

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

        # func.avg returns decimal.Decimal on Postgres; coerce to float so
        # downstream arithmetic (avg * speed_factor) doesn't raise TypeError.
        return float(result.avg_orders) if result.avg_orders is not None else 0.0

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
