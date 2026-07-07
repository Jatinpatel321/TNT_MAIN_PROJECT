"""
Vendor Speed Adjustment Service
================================

Dynamically measures and calculates vendor speed metrics:

Measures:
- Average preparation time
- Current queue depth
- Order completion rate
- Current workload

Calculates:
- Vendor speed score (0.0-1.0)
- Predicted waiting time
- Suggested ordering delay

Updates ETA automatically based on real-time vendor performance.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.slots.model import Slot
from app.modules.vendors.profile_models import VendorProfile

logger = logging.getLogger("tnt.ai.vendor_speed")


class VendorSpeedService:
    """Service for measuring and calculating vendor speed metrics."""

    def __init__(self, db: Session):
        self.db = db

    # ── Measurement Methods ───────────────────────────────────────────────

    def measure_avg_preparation_time(self, vendor_id: int, days: int = 30) -> Dict[str, Any]:
        """Measure average preparation time for a vendor.

        Args:
            vendor_id: Vendor ID
            days: Number of days to look back (default: 30)

        Returns:
            - avg_prep_time: Average preparation time in minutes
            - min_prep_time: Minimum observed time
            - max_prep_time: Maximum observed time
            - median_prep_time: Median preparation time
            - sample_size: Number of orders analyzed
            - std_deviation: Standard deviation
            - confidence: Confidence score (0.0-1.0)
        """
        since = utcnow_naive() - timedelta(days=days)

        # Get completed orders with ETA
        orders = (
            self.db.query(Order.eta_minutes)
            .filter(
                Order.vendor_id == vendor_id,
                Order.status == OrderStatus.COMPLETED,
                Order.created_at >= since,
                Order.eta_minutes.isnot(None),
                Order.eta_minutes > 0,
            )
            .all()
        )

        if not orders:
            return {
                "avg_prep_time": 15.0,
                "min_prep_time": 10.0,
                "max_prep_time": 20.0,
                "median_prep_time": 15.0,
                "sample_size": 0,
                "std_deviation": 0.0,
                "confidence": 0.0,
            }

        prep_times = [o.eta_minutes for o in orders]
        sample_size = len(prep_times)
        avg_time = sum(prep_times) / sample_size
        min_time = min(prep_times)
        max_time = max(prep_times)

        # Calculate median
        sorted_times = sorted(prep_times)
        mid = sample_size // 2
        median_time = sorted_times[mid] if sample_size % 2 == 1 else (sorted_times[mid - 1] + sorted_times[mid]) / 2

        # Calculate standard deviation
        variance = sum((t - avg_time) ** 2 for t in prep_times) / sample_size
        std_dev = variance ** 0.5

        # Confidence increases with sample size (plateaus at 30)
        confidence = min(1.0, sample_size / 30.0)

        return {
            "avg_prep_time": round(avg_time, 1),
            "min_prep_time": round(min_time, 1),
            "max_prep_time": round(max_time, 1),
            "median_prep_time": round(median_time, 1),
            "sample_size": sample_size,
            "std_deviation": round(std_dev, 1),
            "confidence": round(confidence, 2),
        }

    def measure_current_queue(self, vendor_id: int) -> Dict[str, Any]:
        """Measure current queue depth for a vendor.

        Args:
            vendor_id: Vendor ID

        Returns:
            - active_orders: Number of active orders
            - pending_orders: Orders waiting to be prepared
            - preparing_orders: Orders currently being prepared
            - confirmed_orders: Orders confirmed but not started
            - queue_depth: Total orders in queue
            - avg_items_per_order: Average number of items per order
        """
        # Get active orders (not completed/cancelled)
        active_orders = (
            self.db.query(Order)
            .filter(
                Order.vendor_id == vendor_id,
                Order.status.in_([
                    OrderStatus.PLACED,
                    OrderStatus.CONFIRMED,
                    OrderStatus.PREPARING,
                ]),
            )
            .all()
        )

        queue_depth = len(active_orders)
        pending = sum(1 for o in active_orders if o.status == OrderStatus.PLACED)
        confirmed = sum(1 for o in active_orders if o.status == OrderStatus.CONFIRMED)
        preparing = sum(1 for o in active_orders if o.status == OrderStatus.PREPARING)

        # Calculate average items per order
        total_items = 0
        for order in active_orders:
            items = self.db.query(func.count(OrderItem.id)).filter(OrderItem.order_id == order.id).scalar() or 0
            total_items += items

        avg_items = total_items / queue_depth if queue_depth > 0 else 0.0

        return {
            "active_orders": queue_depth,
            "pending_orders": pending,
            "preparing_orders": preparing,
            "confirmed_orders": confirmed,
            "queue_depth": queue_depth,
            "avg_items_per_order": round(avg_items, 1),
        }

    def measure_completion_rate(self, vendor_id: int, days: int = 7) -> Dict[str, Any]:
        """Measure order completion rate for a vendor.

        Args:
            vendor_id: Vendor ID
            days: Number of days to look back (default: 7)

        Returns:
            - total_orders: Total orders in period
            - completed_orders: Successfully completed orders
            - cancelled_orders: Cancelled orders
            - completion_rate: Percentage (0.0-1.0)
            - cancellation_rate: Percentage (0.0-1.0)
            - avg_completion_time: Average time to complete
        """
        since = utcnow_naive() - timedelta(days=days)

        # Total orders
        total_orders = (
            self.db.query(func.count(Order.id))
            .filter(
                Order.vendor_id == vendor_id,
                Order.created_at >= since,
            )
            .scalar() or 0
        )

        # Completed orders
        completed_orders = (
            self.db.query(func.count(Order.id))
            .filter(
                Order.vendor_id == vendor_id,
                Order.status == OrderStatus.COMPLETED,
                Order.created_at >= since,
            )
            .scalar() or 0
        )

        # Cancelled orders
        cancelled_orders = (
            self.db.query(func.count(Order.id))
            .filter(
                Order.vendor_id == vendor_id,
                Order.status == OrderStatus.CANCELLED,
                Order.created_at >= since,
            )
            .scalar() or 0
        )

        completion_rate = completed_orders / total_orders if total_orders > 0 else 0.0
        cancellation_rate = cancelled_orders / total_orders if total_orders > 0 else 0.0

        # Average completion time
        avg_completion_time = (
            self.db.query(func.avg(Order.eta_minutes))
            .filter(
                Order.vendor_id == vendor_id,
                Order.status == OrderStatus.COMPLETED,
                Order.created_at >= since,
                Order.eta_minutes.isnot(None),
            )
            .scalar() or 15.0
        )

        return {
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "cancelled_orders": cancelled_orders,
            "completion_rate": round(completion_rate, 2),
            "cancellation_rate": round(cancellation_rate, 2),
            "avg_completion_time": round(float(avg_completion_time), 1),
        }

    def measure_current_workload(self, vendor_id: int) -> Dict[str, Any]:
        """Measure current workload for a vendor.

        Args:
            vendor_id: Vendor ID

        Returns:
            - active_orders: Current active orders
            - max_capacity: Estimated max capacity
            - utilization: Current utilization (0.0-1.0)
            - estimated_capacity: Remaining capacity
            - workload_level: LOW, MEDIUM, HIGH, CRITICAL
        """
        queue = self.measure_current_queue(vendor_id)
        completion = self.measure_completion_rate(vendor_id)

        active_orders = queue["active_orders"]
        max_capacity = 20  # Default max capacity
        utilization = active_orders / max_capacity

        # Estimate capacity based on completion rate
        # If completion rate is high, vendor can handle more
        if completion["completion_rate"] > 0.9:
            max_capacity = 25
        elif completion["completion_rate"] > 0.8:
            max_capacity = 20
        else:
            max_capacity = 15

        estimated_capacity = max(0, max_capacity - active_orders)

        # Workload level
        if utilization >= 0.95:
            workload_level = "CRITICAL"
        elif utilization >= 0.8:
            workload_level = "HIGH"
        elif utilization >= 0.5:
            workload_level = "MEDIUM"
        else:
            workload_level = "LOW"

        return {
            "active_orders": active_orders,
            "max_capacity": max_capacity,
            "utilization": round(utilization, 2),
            "estimated_capacity": estimated_capacity,
            "workload_level": workload_level,
        }

    # ── Calculation Methods ───────────────────────────────────────────────

    def calculate_vendor_speed_score(self, vendor_id: int) -> Dict[str, Any]:
        """Calculate overall vendor speed score.

        Speed Score (0.0-1.0) based on:
        - Average prep time (lower is faster) - 30%
        - Completion rate (higher is better) - 30%
        - Current queue (lower is faster) - 20%
        - Workload level - 20%

        Returns:
            - speed_score: 0.0 (slow) to 1.0 (fast)
            - speed_label: FAST, NORMAL, BUSY, VERY_BUSY
            - factors: Breakdown of scoring factors
            - recommendations: Suggestions for improvement
        """
        prep_time = self.measure_avg_preparation_time(vendor_id)
        completion = self.measure_completion_rate(vendor_id)
        queue = self.measure_current_queue(vendor_id)
        workload = self.measure_current_workload(vendor_id)

        # Factor 1: Prep time score (0-1, lower time = higher score)
        # Assume 10 min = 1.0, 30 min = 0.0
        avg_prep = prep_time["avg_prep_time"]
        prep_score = max(0.0, min(1.0, (30 - avg_prep) / 20.0))

        # Factor 2: Completion rate (0-1)
        completion_score = completion["completion_rate"]

        # Factor 3: Queue score (0-1, lower queue = higher score)
        # Assume 0 orders = 1.0, 20 orders = 0.0
        queue_score = max(0.0, min(1.0, (20 - queue["queue_depth"]) / 20.0))

        # Factor 4: Workload score (0-1)
        workload_scores = {
            "LOW": 1.0,
            "MEDIUM": 0.7,
            "HIGH": 0.4,
            "CRITICAL": 0.1,
        }
        workload_score = workload_scores.get(workload["workload_level"], 0.5)

        # Calculate weighted speed score
        speed_score = (
            prep_score * 0.30 +
            completion_score * 0.30 +
            queue_score * 0.20 +
            workload_score * 0.20
        )

        # Determine speed label
        if speed_score >= 0.8:
            speed_label = "FAST"
        elif speed_score >= 0.6:
            speed_label = "NORMAL"
        elif speed_score >= 0.4:
            speed_label = "BUSY"
        else:
            speed_label = "VERY_BUSY"

        # Generate recommendations
        recommendations = []
        if prep_score < 0.5:
            recommendations.append("Consider optimizing preparation process")
        if completion_score < 0.8:
            recommendations.append("Focus on completing orders on time")
        if queue_score < 0.5:
            recommendations.append("Reduce order queue during peak hours")
        if workload_score < 0.5:
            recommendations.append("Consider adding more staff or capacity")

        return {
            "speed_score": round(speed_score, 2),
            "speed_label": speed_label,
            "factors": {
                "prep_time_score": round(prep_score, 2),
                "completion_score": round(completion_score, 2),
                "queue_score": round(queue_score, 2),
                "workload_score": round(workload_score, 2),
            },
            "metrics": {
                "avg_prep_time": prep_time["avg_prep_time"],
                "completion_rate": completion["completion_rate"],
                "queue_depth": queue["queue_depth"],
                "workload_level": workload["workload_level"],
            },
            "recommendations": recommendations,
        }

    def calculate_predicted_waiting_time(self, vendor_id: int, order_size: int = 1) -> Dict[str, Any]:
        """Calculate predicted waiting time for a new order.

        Args:
            vendor_id: Vendor ID
            order_size: Number of items in order (default: 1)

        Returns:
            - base_wait_time: Base waiting time in minutes
            - queue_wait_time: Additional wait due to queue
            - total_wait_time: Total predicted wait time
            - confidence: Prediction confidence
        """
        prep_time = self.measure_avg_preparation_time(vendor_id)
        queue = self.measure_current_queue(vendor_id)
        workload = self.measure_current_workload(vendor_id)

        # Base wait time (average prep time × order size)
        base_wait_time = prep_time["avg_prep_time"] * order_size

        # Queue wait time (each order adds ~5 minutes)
        queue_wait_time = queue["queue_depth"] * 5

        # Workload multiplier
        workload_multipliers = {
            "LOW": 1.0,
            "MEDIUM": 1.2,
            "HIGH": 1.5,
            "CRITICAL": 2.0,
        }
        workload_multiplier = workload_multipliers.get(workload["workload_level"], 1.2)

        # Calculate total wait time
        total_wait_time = (base_wait_time + queue_wait_time) * workload_multiplier

        # Calculate confidence
        confidence = prep_time["confidence"]
        if queue["queue_depth"] > 10:
            confidence *= 0.8  # Lower confidence with large queue

        return {
            "base_wait_time": round(base_wait_time, 1),
            "queue_wait_time": round(queue_wait_time, 1),
            "workload_multiplier": workload_multiplier,
            "total_wait_time": round(total_wait_time, 1),
            "confidence": round(confidence, 2),
        }

    def calculate_suggested_delay(self, vendor_id: int) -> Dict[str, Any]:
        """Calculate suggested ordering delay to avoid congestion.

        Args:
            vendor_id: Vendor ID

        Returns:
            - should_delay: Whether ordering should be delayed
            - suggested_delay_minutes: Recommended delay in minutes
            - optimal_order_time: When to place order (ISO datetime)
            - reason: Explanation for delay suggestion
        """
        workload = self.measure_current_workload(vendor_id)
        queue = self.measure_current_queue(vendor_id)

        should_delay = False
        suggested_delay = 0
        reason = ""

        # Suggest delay if vendor is busy
        if workload["workload_level"] == "CRITICAL":
            should_delay = True
            suggested_delay = 15  # Wait 15 minutes
            reason = "Vendor is critically overloaded. Consider ordering later."
        elif workload["workload_level"] == "HIGH":
            should_delay = True
            suggested_delay = 10  # Wait 10 minutes
            reason = "Vendor is very busy. Short delay recommended."
        elif workload["workload_level"] == "MEDIUM" and queue["queue_depth"] > 10:
            should_delay = True
            suggested_delay = 5  # Wait 5 minutes
            reason = "Queue is building up. Small delay may help."
        else:
            reason = "Vendor is operating normally. No delay needed."

        # Calculate optimal order time
        now = utcnow_naive()
        optimal_time = now + timedelta(minutes=suggested_delay)

        return {
            "should_delay": should_delay,
            "suggested_delay_minutes": suggested_delay,
            "optimal_order_time": optimal_time.isoformat(),
            "reason": reason,
            "current_workload": workload["workload_level"],
            "queue_depth": queue["queue_depth"],
        }

    # ── Public API ────────────────────────────────────────────────────────

    def get_vendor_speed_metrics(self, vendor_id: int) -> Dict[str, Any]:
        """Get comprehensive vendor speed metrics.

        This is the main entry point for vendor speed analysis.

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
        # Calculate speed score
        speed = self.calculate_vendor_speed_score(vendor_id)

        # Calculate predicted waiting time
        wait_time = self.calculate_predicted_waiting_time(vendor_id)

        # Calculate suggested delay
        delay = self.calculate_suggested_delay(vendor_id)

        # Get raw measurements
        prep_time = self.measure_avg_preparation_time(vendor_id)
        queue = self.measure_current_queue(vendor_id)
        completion = self.measure_completion_rate(vendor_id)
        workload = self.measure_current_workload(vendor_id)

        return {
            "vendor_id": vendor_id,
            "speed_score": speed["speed_score"],
            "speed_label": speed["speed_label"],
            "predicted_waiting_time": wait_time["total_wait_time"],
            "suggested_delay": delay,
            "measurements": {
                "preparation_time": prep_time,
                "queue": queue,
                "completion_rate": completion,
                "workload": workload,
            },
            "factors": speed["factors"],
            "recommendations": speed["recommendations"],
        }

    def get_batch_vendor_speeds(self, vendor_ids: list[int]) -> list[Dict[str, Any]]:
        """Get speed metrics for multiple vendors.

        Args:
            vendor_ids: List of vendor IDs

        Returns:
            List of vendor speed metrics
        """
        return [self.get_vendor_speed_metrics(vid) for vid in vendor_ids]

    def update_eta_with_vendor_speed(self, order_id: int) -> Dict[str, Any]:
        """Update ETA for an order based on current vendor speed.

        This integrates with the existing ETA system to provide
        dynamic ETA updates based on real-time vendor performance.

        Args:
            order_id: Order ID

        Returns:
            - order_id
            - original_eta: Original ETA
            - updated_eta: Updated ETA based on vendor speed
            - speed_label: Current vendor speed
            - adjustment_factor: Multiplier applied
        """
        order = self.db.query(Order).filter(Order.id == order_id).first()

        if not order:
            return {
                "order_id": None,
                "original_eta": 0,
                "updated_eta": 0,
                "speed_label": "UNKNOWN",
                "adjustment_factor": 1.0,
            }

        # Get original ETA
        original_eta = order.eta_minutes or 15

        # Get vendor speed
        speed_metrics = self.get_vendor_speed_metrics(order.vendor_id)
        speed_label = speed_metrics["speed_label"]

        # Calculate adjustment factor based on speed
        speed_factors = {
            "FAST": 0.85,      # 15% faster
            "NORMAL": 1.0,     # No change
            "BUSY": 1.2,       # 20% slower
            "VERY_BUSY": 1.5,  # 50% slower
        }
        adjustment_factor = speed_factors.get(speed_label, 1.0)

        # Calculate updated ETA
        updated_eta = int(original_eta * adjustment_factor)

        # Ensure bounds
        updated_eta = max(5, min(updated_eta, 90))

        # Update order ETA if significantly different
        if abs(updated_eta - original_eta) > 3:
            order.eta_minutes = updated_eta
            self.db.commit()

        return {
            "order_id": order_id,
            "original_eta": original_eta,
            "updated_eta": updated_eta,
            "speed_label": speed_label,
            "adjustment_factor": adjustment_factor,
            "speed_score": speed_metrics["speed_score"],
        }