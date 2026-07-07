from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderStatus
from app.modules.slots.model import Slot


class ETAEngine:
    """AI-powered predictive ETA and pickup window calculation"""

    def __init__(self, db: Session):
        self.db = db

    def predict_eta(self, slot_id: int, vendor_id: int) -> Dict[str, Any]:
        """Predict ETA and pickup window for a slot"""

        # Get slot details
        slot = self.db.query(Slot).filter(Slot.id == slot_id).first()
        if not slot:
            return self._default_eta_response()

        # Calculate base prep time
        base_prep_time = self._calculate_base_prep_time(vendor_id)

        # Calculate queue depth factor
        queue_factor = self._calculate_queue_depth_factor(slot)

        # Calculate vendor efficiency factor
        efficiency_factor = self._calculate_vendor_efficiency_factor(vendor_id)

        # AI prediction formula
        predicted_eta = int(base_prep_time * queue_factor * efficiency_factor)

        # Ensure reasonable bounds
        predicted_eta = max(5, min(predicted_eta, 60))  # 5-60 minutes

        # Calculate pickup window
        _raw_start = slot.start_time
        if isinstance(_raw_start, datetime):
            slot_start = _raw_start
        else:
            slot_start = datetime.combine(datetime.today(), _raw_start)
        pickup_window_start = slot_start
        pickup_window_end = slot_start + timedelta(minutes=predicted_eta)

        # Calculate delay risk level
        delay_risk = self._calculate_delay_risk_level(slot, predicted_eta)

        return {
            "predicted_eta_minutes": predicted_eta,
            "pickup_window_start": pickup_window_start,
            "pickup_window_end": pickup_window_end,
            "delay_risk_level": delay_risk
        }

    def _calculate_base_prep_time(self, vendor_id: int) -> float:
        """Calculate base preparation time based on vendor history"""

        thirty_days_ago = utcnow_naive() - timedelta(days=30)

        # Average completion time for vendor
        avg_completion_time = self.db.query(
            func.avg(Order.eta_minutes)
        ).filter(
            Order.vendor_id == vendor_id,
            Order.status == OrderStatus.COMPLETED,
            Order.created_at >= thirty_days_ago,
            Order.eta_minutes.isnot(None)
        ).scalar()

        return avg_completion_time or 15.0  # Default 15 minutes

    def _calculate_queue_depth_factor(self, slot: Slot) -> float:
        """Calculate factor based on current queue depth"""

        if slot.max_orders == 0:
            return 1.0

        utilization = slot.current_orders / slot.max_orders

        # Queue factor increases with utilization
        if utilization < 0.5:
            return 1.0
        elif utilization < 0.8:
            return 1.2
        else:
            return 1.5

    def _calculate_vendor_efficiency_factor(self, vendor_id: int) -> float:
        """Calculate vendor efficiency factor"""

        seven_days_ago = utcnow_naive() - timedelta(days=7)

        # Completion rate in last 7 days
        completed_orders = self.db.query(Order).filter(
            Order.vendor_id == vendor_id,
            Order.status == OrderStatus.COMPLETED,
            Order.created_at >= seven_days_ago
        ).count()

        total_orders = self.db.query(Order).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= seven_days_ago
        ).count()

        if total_orders == 0:
            return 1.0

        completion_rate = completed_orders / total_orders

        # Efficiency factor: higher completion rate = lower factor (faster)
        efficiency_factor = 2.0 - completion_rate  # Range: 1.0 - 2.0

        return efficiency_factor

    def _calculate_delay_risk_level(self, slot: Slot, predicted_eta: int) -> str:
        """Calculate delay risk level: LOW, MEDIUM, HIGH"""

        if slot.max_orders == 0:
            return "LOW"

        utilization = slot.current_orders / slot.max_orders

        # High risk if heavily utilized and long ETA
        if utilization > 0.9 and predicted_eta > 30:
            return "HIGH"
        elif utilization > 0.7 or predicted_eta > 25:
            return "MEDIUM"
        else:
            return "LOW"

    def _default_eta_response(self) -> Dict[str, Any]:
        """Return default ETA response when slot not found"""

        now = utcnow_naive()
        return {
            "predicted_eta_minutes": 15,
            "pickup_window_start": now,
            "pickup_window_end": now + timedelta(minutes=15),
            "delay_risk_level": "MEDIUM"
        }
