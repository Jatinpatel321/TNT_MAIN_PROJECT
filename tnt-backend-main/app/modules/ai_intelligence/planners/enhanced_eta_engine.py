"""
Enhanced ETA Prediction Engine
===============================

Extends the existing ETAEngine with:
- Historical preparation times per menu item
- Menu complexity scoring
- Vendor workload analysis
- Slot occupancy with time-of-day awareness
- Delay prediction with confidence
- Preparation progress tracking

Integrates with existing ETA APIs without replacing them.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.menu.model import MenuItem
from app.modules.slots.model import Slot
from app.modules.vendors.profile_models import VendorProfile

logger = logging.getLogger("tnt.ai.eta")


class EnhancedETAEngine:
    """Advanced ETA prediction with ML-based factors."""

    def __init__(self, db: Session):
        self.db = db

    # ── Historical Preparation Times ──────────────────────────────────────

    def get_menu_item_prep_time(self, menu_item_id: int, vendor_id: int) -> Dict[str, Any]:
        """Get historical preparation time for a specific menu item.

        Returns:
            - avg_prep_time: Average preparation time in minutes
            - min_prep_time: Minimum observed time
            - max_prep_time: Maximum observed time
            - sample_size: Number of observations
            - confidence: Confidence score based on sample size
        """
        thirty_days_ago = utcnow_naive() - timedelta(days=30)

        # Get orders containing this menu item
        order_items = (
            self.db.query(OrderItem, Order)
            .join(Order, Order.id == OrderItem.order_id)
            .filter(
                OrderItem.menu_item_id == menu_item_id,
                Order.vendor_id == vendor_id,
                Order.created_at >= thirty_days_ago,
                Order.status.in_([OrderStatus.COMPLETED, OrderStatus.PICKED]),
                Order.eta_minutes.isnot(None),
            )
            .all()
        )

        if not order_items:
            return {
                "avg_prep_time": None,
                "min_prep_time": None,
                "max_prep_time": None,
                "sample_size": 0,
                "confidence": 0.0,
            }

        prep_times = [oi.Order.eta_minutes for oi in order_items]
        sample_size = len(prep_times)

        # Confidence increases with sample size (plateaus at 20 samples)
        confidence = min(1.0, sample_size / 20.0)

        return {
            "avg_prep_time": sum(prep_times) / sample_size,
            "min_prep_time": min(prep_times),
            "max_prep_time": max(prep_times),
            "sample_size": sample_size,
            "confidence": confidence,
        }

    def get_menu_complexity_score(self, menu_item_id: int) -> Dict[str, Any]:
        """Calculate menu item complexity score.

        Factors:
        - Base prep time from menu item
        - Historical variance (high variance = complex)
        - Category complexity (beverages < snacks < meals)
        - Quantity ordered (more items = more complex)

        Returns:
            - complexity_score: 0.0 (simple) to 1.0 (complex)
            - factors: Breakdown of complexity factors
        """
        menu_item = self.db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()

        if not menu_item:
            return {"complexity_score": 0.5, "factors": {}}

        factors = {}

        # Factor 1: Base prep time (0-0.3)
        base_prep = getattr(menu_item, 'prep_time', 10) or 10
        prep_factor = min(0.3, base_prep / 60.0)  # Normalize to 0-0.3
        factors["prep_time"] = prep_factor

        # Factor 2: Historical variance (0-0.3)
        prep_data = self.get_menu_item_prep_time(menu_item_id, menu_item.vendor_id)
        if prep_data["sample_size"] > 1:
            variance = prep_data["max_prep_time"] - prep_data["min_prep_time"]
            variance_factor = min(0.3, variance / 30.0)  # Normalize to 0-0.3
        else:
            variance_factor = 0.15  # Default medium variance
        factors["variance"] = variance_factor

        # Factor 3: Category complexity (0-0.2)
        category_complexity = {
            "beverages": 0.05,
            "snacks": 0.10,
            "south indian": 0.15,
            "chinese": 0.15,
            "italian": 0.18,
            "indian": 0.20,
            "print": 0.10,
            "xerox": 0.05,
            "binding": 0.15,
            "lamination": 0.10,
        }
        category = (menu_item.category or "food").lower()
        category_factor = category_complexity.get(category, 0.15)
        factors["category"] = category_factor

        # Factor 4: Item name complexity (0-0.2)
        # Longer names or special keywords indicate complexity
        name = menu_item.name or ""
        name_factor = 0.0
        if any(keyword in name.lower() for keyword in ["combo", "thali", "special", "deluxe"]):
            name_factor += 0.1
        if len(name.split()) > 3:
            name_factor += 0.1
        factors["name_complexity"] = name_factor

        complexity_score = sum(factors.values())

        return {
            "complexity_score": min(1.0, complexity_score),
            "factors": factors,
        }

    # ── Vendor Workload Analysis ──────────────────────────────────────────

    def get_vendor_workload(self, vendor_id: int) -> Dict[str, Any]:
        """Analyze current vendor workload.

        Returns:
            - active_orders: Number of active orders
            - avg_prep_time: Average prep time for vendor
            - completion_rate: Order completion rate (last 7 days)
            - workload_score: 0.0 (light) to 1.0 (overloaded)
            - estimated_capacity: Remaining capacity
        """
        # Active orders (not completed/cancelled)
        active_orders = (
            self.db.query(func.count(Order.id))
            .filter(
                Order.vendor_id == vendor_id,
                Order.status.in_([
                    OrderStatus.PLACED,
                    OrderStatus.CONFIRMED,
                    OrderStatus.PREPARING,
                ]),
            )
            .scalar() or 0
        )

        # Average prep time (last 30 days)
        thirty_days_ago = utcnow_naive() - timedelta(days=30)
        avg_prep_time = (
            self.db.query(func.avg(Order.eta_minutes))
            .filter(
                Order.vendor_id == vendor_id,
                Order.status == OrderStatus.COMPLETED,
                Order.created_at >= thirty_days_ago,
                Order.eta_minutes.isnot(None),
            )
            .scalar() or 15.0
        )

        # Completion rate (last 7 days)
        seven_days_ago = utcnow_naive() - timedelta(days=7)
        completed = (
            self.db.query(func.count(Order.id))
            .filter(
                Order.vendor_id == vendor_id,
                Order.status == OrderStatus.COMPLETED,
                Order.created_at >= seven_days_ago,
            )
            .scalar() or 0
        )

        total = (
            self.db.query(func.count(Order.id))
            .filter(
                Order.vendor_id == vendor_id,
                Order.created_at >= seven_days_ago,
            )
            .scalar() or 1
        )

        completion_rate = completed / total

        # Workload score (0.0-1.0)
        # Based on active orders and completion rate
        workload_score = min(1.0, (active_orders / 20.0) + (1.0 - completion_rate) * 0.5)

        return {
            "active_orders": active_orders,
            "avg_prep_time": float(avg_prep_time),
            "completion_rate": completion_rate,
            "workload_score": workload_score,
            "estimated_capacity": max(0, 20 - active_orders),
        }

    # ── Slot Occupancy Analysis ───────────────────────────────────────────

    def get_slot_occupancy(self, slot_id: int) -> Dict[str, Any]:
        """Analyze slot occupancy with time-of-day awareness.

        Returns:
            - current_orders: Current orders in slot
            - max_capacity: Maximum capacity
            - utilization: Utilization percentage
            - time_factor: Time-of-day multiplier
            - congestion_level: LOW, MEDIUM, HIGH
        """
        slot = self.db.query(Slot).filter(Slot.id == slot_id).first()

        if not slot:
            return {
                "current_orders": 0,
                "max_capacity": 0,
                "utilization": 0.0,
                "time_factor": 1.0,
                "congestion_level": "LOW",
            }

        current_orders = slot.current_orders or 0
        max_capacity = slot.max_orders or 1
        utilization = current_orders / max_capacity

        # Time-of-day factor
        # Peak hours (11-14, 18-20) have higher congestion
        now = utcnow_naive()
        current_hour = now.hour

        if (11 <= current_hour <= 14) or (18 <= current_hour <= 20):
            time_factor = 1.3  # 30% slower during peak
        elif 14 <= current_hour <= 17:
            time_factor = 1.1  # 10% slower during afternoon
        else:
            time_factor = 1.0  # Normal

        # Congestion level
        if utilization > 0.9:
            congestion_level = "HIGH"
        elif utilization > 0.6:
            congestion_level = "MEDIUM"
        else:
            congestion_level = "LOW"

        return {
            "current_orders": current_orders,
            "max_capacity": max_capacity,
            "utilization": utilization,
            "time_factor": time_factor,
            "congestion_level": congestion_level,
        }

    # ── Enhanced ETA Prediction ───────────────────────────────────────────

    def predict_eta_enhanced(
        self, order_id: int, menu_item_ids: list[int], vendor_id: int, slot_id: int
    ) -> Dict[str, Any]:
        """Enhanced ETA prediction with ML factors.

        Args:
            order_id: Order ID
            menu_item_ids: List of menu item IDs in the order
            vendor_id: Vendor ID
            slot_id: Slot ID

        Returns:
            - predicted_eta_minutes: Estimated preparation time
            - estimated_ready_at: ISO datetime when order will be ready
            - delay_risk_level: LOW, MEDIUM, HIGH
            - confidence: Prediction confidence (0.0-1.0)
            - factors: Breakdown of prediction factors
            - preparation_progress: Progress estimate (0-100%)
        """
        # Get base prep time from existing engine
        from app.modules.ai_intelligence.planners.eta_engine import ETAEngine

        base_engine = ETAEngine(self.db)
        base_prediction = base_engine.predict_eta(slot_id, vendor_id)

        # Get enhanced factors
        slot_occupancy = self.get_slot_occupancy(slot_id)
        vendor_workload = self.get_vendor_workload(vendor_id)

        # Calculate menu complexity
        max_complexity = 0.0
        total_complexity = 0.0
        for menu_item_id in menu_item_ids:
            complexity = self.get_menu_complexity_score(menu_item_id)
            total_complexity += complexity["complexity_score"]
            max_complexity = max(max_complexity, complexity["complexity_score"])

        avg_complexity = total_complexity / len(menu_item_ids) if menu_item_ids else 0.5

        # Enhanced ETA calculation
        base_eta = base_prediction["predicted_eta_minutes"]

        # Apply complexity factor (0.8 - 1.5)
        complexity_factor = 0.8 + (avg_complexity * 0.7)

        # Apply workload factor (0.9 - 1.4)
        workload_factor = 0.9 + (vendor_workload["workload_score"] * 0.5)

        # Apply slot occupancy factor (already in base, but enhance)
        occupancy_factor = slot_occupancy["time_factor"]

        # Calculate enhanced ETA
        enhanced_eta = int(
            base_eta * complexity_factor * workload_factor * occupancy_factor
        )

        # Ensure reasonable bounds
        enhanced_eta = max(5, min(enhanced_eta, 90))  # 5-90 minutes

        # Calculate confidence
        confidence_factors = []

        # Higher confidence with more historical data
        if vendor_workload["active_orders"] > 0:
            confidence_factors.append(0.2)

        if avg_complexity < 0.7:  # Not too complex
            confidence_factors.append(0.2)

        if slot_occupancy["utilization"] < 0.9:  # Not overloaded
            confidence_factors.append(0.2)

        if vendor_workload["completion_rate"] > 0.8:  # Reliable vendor
            confidence_factors.append(0.2)

        if len(menu_item_ids) <= 3:  # Reasonable order size
            confidence_factors.append(0.2)

        confidence = min(1.0, sum(confidence_factors))

        # Calculate delay risk
        delay_risk = self._calculate_delay_risk(
            slot_occupancy, vendor_workload, enhanced_eta, avg_complexity
        )

        # Calculate estimated ready time
        now = utcnow_naive()
        estimated_ready_at = now + timedelta(minutes=enhanced_eta)

        # Calculate preparation progress (for live updates)
        # This is a static estimate; actual progress tracked via order status
        preparation_progress = self._estimate_preparation_progress(
            enhanced_eta, base_eta
        )

        return {
            "predicted_eta_minutes": enhanced_eta,
            "estimated_ready_at": estimated_ready_at.isoformat(),
            "delay_risk_level": delay_risk,
            "confidence": round(confidence, 2),
            "factors": {
                "base_eta": base_eta,
                "complexity_factor": round(complexity_factor, 2),
                "workload_factor": round(workload_factor, 2),
                "occupancy_factor": round(occupancy_factor, 2),
                "avg_complexity": round(avg_complexity, 2),
                "vendor_workload": vendor_workload,
                "slot_occupancy": slot_occupancy,
            },
            "preparation_progress": preparation_progress,
        }

    def _calculate_delay_risk(
        self,
        slot_occupancy: Dict[str, Any],
        vendor_workload: Dict[str, Any],
        predicted_eta: int,
        complexity: float,
    ) -> str:
        """Calculate delay risk level with enhanced factors."""
        utilization = slot_occupancy["utilization"]
        workload_score = vendor_workload["workload_score"]

        # Risk score calculation
        risk_score = 0.0

        # Slot utilization (0-0.4)
        risk_score += min(0.4, utilization * 0.4)

        # Vendor workload (0-0.3)
        risk_score += min(0.3, workload_score * 0.3)

        # ETA length (0-0.2)
        if predicted_eta > 45:
            risk_score += 0.2
        elif predicted_eta > 30:
            risk_score += 0.1

        # Complexity (0-0.1)
        if complexity > 0.7:
            risk_score += 0.1

        # Determine risk level
        if risk_score >= 0.7:
            return "HIGH"
        elif risk_score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"

    def _estimate_preparation_progress(self, enhanced_eta: int, base_eta: int) -> Dict[str, Any]:
        """Estimate preparation progress for live updates.

        Returns progress milestones:
        - 0%: Order placed
        - 25%: Preparation started
        - 50%: Halfway through
        - 75%: Final preparation
        - 100%: Ready for pickup
        """
        # Calculate time milestones
        now = utcnow_naive()

        return {
            "total_minutes": enhanced_eta,
            "milestones": {
                "started_at": now + timedelta(minutes=0),
                "quarter_at": now + timedelta(minutes=int(enhanced_eta * 0.25)),
                "halfway_at": now + timedelta(minutes=int(enhanced_eta * 0.5)),
                "final_at": now + timedelta(minutes=int(enhanced_eta * 0.75)),
                "ready_at": now + timedelta(minutes=enhanced_eta),
            },
            "current_phase": "preparing",  # Will be updated by order status
        }

    # ── Delay Prediction ──────────────────────────────────────────────────

    def predict_delay_probability(self, order_id: int) -> Dict[str, Any]:
        """Predict probability of delay for an order.

        Returns:
            - delay_probability: 0.0-1.0
            - expected_delay_minutes: Expected delay if delayed
            - risk_factors: List of risk factors
            - recommendations: Suggestions to avoid delay
        """
        order = self.db.query(Order).filter(Order.id == order_id).first()

        if not order:
            return {
                "delay_probability": 0.0,
                "expected_delay_minutes": 0,
                "risk_factors": [],
                "recommendations": [],
            }

        slot_occupancy = self.get_slot_occupancy(order.slot_id)
        vendor_workload = self.get_vendor_workload(order.vendor_id)

        # Get menu items
        order_items = (
            self.db.query(OrderItem)
            .filter(OrderItem.order_id == order_id)
            .all()
        )

        menu_item_ids = [oi.menu_item_id for oi in order_items]
        avg_complexity = 0.0
        if menu_item_ids:
            complexities = [
                self.get_menu_complexity_score(mid)["complexity_score"]
                for mid in menu_item_ids
            ]
            avg_complexity = sum(complexities) / len(complexities)

        # Calculate delay probability
        delay_probability = 0.0
        risk_factors = []

        # Factor 1: Slot utilization (0-0.4)
        if slot_occupancy["utilization"] > 0.9:
            delay_probability += 0.4
            risk_factors.append("Slot nearly full")
        elif slot_occupancy["utilization"] > 0.7:
            delay_probability += 0.2
            risk_factors.append("Slot busy")

        # Factor 2: Vendor workload (0-0.3)
        if vendor_workload["workload_score"] > 0.8:
            delay_probability += 0.3
            risk_factors.append("Vendor overloaded")
        elif vendor_workload["workload_score"] > 0.6:
            delay_probability += 0.15
            risk_factors.append("Vendor busy")

        # Factor 3: Completion rate (0-0.2)
        if vendor_workload["completion_rate"] < 0.8:
            delay_probability += 0.2
            risk_factors.append("Low completion rate")

        # Factor 4: Menu complexity (0-0.1)
        if avg_complexity > 0.7:
            delay_probability += 0.1
            risk_factors.append("Complex menu items")

        delay_probability = min(1.0, delay_probability)

        # Expected delay
        expected_delay = 0
        if delay_probability > 0.5:
            expected_delay = int(
                (delay_probability - 0.5) * 20  # Up to 10 minutes
            )

        # Recommendations
        recommendations = []
        if slot_occupancy["utilization"] > 0.8:
            recommendations.append("Consider selecting a different slot")
        if vendor_workload["workload_score"] > 0.7:
            recommendations.append("Vendor is busy - expect longer wait time")
        if avg_complexity > 0.6:
            recommendations.append("Complex items may take longer to prepare")

        return {
            "delay_probability": round(delay_probability, 2),
            "expected_delay_minutes": expected_delay,
            "risk_factors": risk_factors,
            "recommendations": recommendations,
        }

    # ── Public API ────────────────────────────────────────────────────────

    def get_enhanced_eta(self, order_id: int) -> Dict[str, Any]:
        """Get enhanced ETA prediction for an order.

        This extends the existing ETA endpoint with additional ML factors.
        """
        order = self.db.query(Order).filter(Order.id == order_id).first()

        if not order:
            return self._default_response()

        # Get menu items
        order_items = (
            self.db.query(OrderItem)
            .filter(OrderItem.order_id == order_id)
            .all()
        )

        menu_item_ids = [oi.menu_item_id for oi in order_items]

        # Get enhanced prediction
        enhanced = self.predict_eta_enhanced(
            order_id, menu_item_ids, order.vendor_id, order.slot_id
        )

        # Get delay prediction
        delay_prediction = self.predict_delay_probability(order_id)

        # Combine results
        result = {
            "order_id": order_id,
            **enhanced,
            "delay_prediction": delay_prediction,
        }

        return result

    def _default_response(self) -> Dict[str, Any]:
        """Return default response when order not found."""
        now = utcnow_naive()
        return {
            "order_id": None,
            "predicted_eta_minutes": 15,
            "estimated_ready_at": (now + timedelta(minutes=15)).isoformat(),
            "delay_risk_level": "MEDIUM",
            "confidence": 0.5,
            "factors": {},
            "preparation_progress": {},
            "delay_prediction": {
                "delay_probability": 0.0,
                "expected_delay_minutes": 0,
                "risk_factors": [],
                "recommendations": [],
            },
        }