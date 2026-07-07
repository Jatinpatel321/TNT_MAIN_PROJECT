"""
Peak Hour Prediction Service
=============================

Predicts traffic patterns for optimal slot and staff management:

- Rush hours: High-demand time slots
- Quiet hours: Low-demand time slots
- Vendor workload: Expected orders per time block
- Slot utilization: Projected slot fill rates

Generates:
- Peak Hour Heatmap: Hourly traffic intensity matrix
- Recommended Capacity: Optimal slot capacity per hour
- Suggested Additional Staff: Staff needed during peak times
- Expected Waiting Time: Projected wait times per slot
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date, time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive, ist_now
from app.modules.orders.model import Order, OrderStatus
from app.modules.slots.model import Slot, SlotBooking, SlotStatus, BookingStatus

logger = logging.getLogger("tnt.ai.peak")


# ── Data Models ─────────────────────────────────────────────────────────


class HourCategory(Enum):
    RUSH = "rush"
    MODERATE = "moderate"
    QUIET = "quiet"
    CLOSED = "closed"


@dataclass
class HourlyPrediction:
    """Prediction for a single hour block."""
    hour: int  # 0-23
    time_label: str  # "09:00"
    category: HourCategory
    
    # Traffic
    predicted_orders: int
    predicted_customers: int
    congestion_percent: float  # 0-100
    slot_utilization: float  # 0-100
    
    # Capacity
    current_capacity: int
    recommended_capacity: int
    available_slots: int
    total_slots: int
    
    # Staff & Wait
    suggested_staff: int
    expected_wait_minutes: float
    
    # Heatmap color
    intensity_score: float  # 0-1


@dataclass
class PeakHourPredictionResult:
    """Complete peak hour prediction results."""
    vendor_id: int
    prediction_date: str
    
    # Predictions
    hourly_predictions: List[HourlyPrediction]
    
    # Summaries
    rush_hours: List[Dict[str, Any]]
    quiet_hours: List[Dict[str, Any]]
    
    # Generated outputs
    heatmap: Dict[str, Any]
    capacity_recommendations: List[Dict[str, Any]]
    staff_suggestions: List[Dict[str, Any]]
    waiting_time_estimates: List[Dict[str, Any]]
    
    # Analysis
    summary: Dict[str, Any]
    insights: List[str]


# ── Peak Hour Prediction Service ───────────────────────────────────────


class PeakHourPredictionService:
    """Service for predicting peak hours and optimizing slot/staff planning."""

    def __init__(self, db: Session):
        self.db = db

    # ── Main Prediction Engine ───────────────────────────────────────────

    def predict_peak_hours(self, vendor_id: int, days_ahead: int = 1) -> PeakHourPredictionResult:
        """Generate complete peak hour predictions for a vendor.
        
        Args:
            vendor_id: Vendor ID
            days_ahead: Number of days ahead to predict (default: 1)
            
        Returns:
            PeakHourPredictionResult with all predictions and recommendations
        """
        now = utcnow_naive()
        prediction_date = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        # Get historical orders for pattern analysis
        cutoff_7d = now - timedelta(days=7)
        cutoff_30d = now - timedelta(days=30)
        cutoff_90d = now - timedelta(days=90)
        
        # Aggregate orders by hour
        hourly_pattern_7d = self._aggregate_orders_by_hour(vendor_id, cutoff_7d, now)
        hourly_pattern_30d = self._aggregate_orders_by_hour(vendor_id, cutoff_30d, now)
        hourly_pattern_90d = self._aggregate_orders_by_hour(vendor_id, cutoff_90d, now)
        
        # Get day-of-week pattern for prediction day
        dow = (now + timedelta(days=days_ahead)).weekday()
        day_pattern = self._aggregate_by_day_of_week(vendor_id, cutoff_90d, now)
        
        # Get existing slots for the prediction day
        slots = self._get_slots_for_date(vendor_id, prediction_date)
        
        # Build hourly predictions
        hourly_predictions = []
        rush_hours = []
        quiet_hours = []
        heatmap_data = {}
        
        for hour in range(24):
            # Predict orders for this hour
            predicted_orders = self._predict_hourly_orders(
                hour, dow, hourly_pattern_7d, hourly_pattern_30d, hourly_pattern_90d, day_pattern
            )
            
            # Predict customers
            predicted_customers = max(1, round(predicted_orders * 0.85))
            
            # Slot data
            hour_slots = [s for s in slots if s.start_time.hour <= hour < s.end_time.hour or s.start_time.hour == hour]
            total_slots = len(hour_slots) if hour_slots else max(1, round(len(slots) / 12))
            available_slots = sum(1 for s in hour_slots if s.current_orders < s.max_orders) if hour_slots else total_slots
            
            # Current capacity
            current_capacity = sum(s.max_orders for s in hour_slots) if hour_slots else total_slots * 3
            
            # Determine category
            if predicted_orders <= 0:
                category = HourCategory.CLOSED
            elif predicted_orders >= self._get_high_threshold(hourly_pattern_30d):
                category = HourCategory.RUSH
            elif predicted_orders <= self._get_low_threshold(hourly_pattern_30d):
                category = HourCategory.QUIET
            else:
                category = HourCategory.MODERATE
            
            # Calculate metrics
            congestion = min(100, (predicted_orders / max(current_capacity, 1)) * 100)
            slot_util = min(100, (predicted_orders / max(current_capacity, 1)) * 100)
            intensity = min(1.0, predicted_orders / max(self._get_high_threshold(hourly_pattern_30d), 1))
            
            # Staff needed
            suggested_staff = self._calculate_staff_needed(predicted_orders, category)
            
            # Expected wait time
            expected_wait = self._calculate_expected_wait(predicted_orders, current_capacity, slot_util)
            
            # Recommended capacity
            recommended_cap = self._calculate_recommended_capacity(predicted_orders, category)
            
            prediction = HourlyPrediction(
                hour=hour,
                time_label=f"{hour:02d}:00",
                category=category,
                predicted_orders=predicted_orders,
                predicted_customers=predicted_customers,
                congestion_percent=round(congestion, 1),
                slot_utilization=round(slot_util, 1),
                current_capacity=current_capacity,
                recommended_capacity=recommended_cap,
                available_slots=available_slots,
                total_slots=total_slots,
                suggested_staff=suggested_staff,
                expected_wait_minutes=round(expected_wait, 1),
                intensity_score=round(intensity, 2),
            )
            
            hourly_predictions.append(prediction)
            
            # Track rush/quiet hours
            if category == HourCategory.RUSH:
                rush_hours.append({
                    "hour": hour,
                    "time_label": f"{hour:02d}:00",
                    "predicted_orders": predicted_orders,
                    "congestion": round(congestion, 1),
                    "intensity": round(intensity, 2),
                })
            elif category == HourCategory.QUIET:
                quiet_hours.append({
                    "hour": hour,
                    "time_label": f"{hour:02d}:00",
                    "predicted_orders": predicted_orders,
                    "available_slots": available_slots,
                })
            
            # Heatmap data
            heatmap_data[f"{hour:02d}:00"] = {
                "orders": predicted_orders,
                "intensity": round(intensity, 2),
                "category": category.value,
                "color": self._get_heatmap_color(intensity),
            }
        
        # Generate outputs
        heatmap = self._generate_heatmap(heatmap_data)
        capacity_recommendations = self._generate_capacity_recommendations(hourly_predictions)
        staff_suggestions = self._generate_staff_suggestions(hourly_predictions)
        waiting_time_estimates = self._generate_waiting_time_estimates(hourly_predictions)
        summary = self._generate_summary(hourly_predictions, rush_hours, quiet_hours)
        insights = self._generate_insights(hourly_predictions, rush_hours, quiet_hours, summary)
        
        return PeakHourPredictionResult(
            vendor_id=vendor_id,
            prediction_date=prediction_date,
            hourly_predictions=hourly_predictions,
            rush_hours=rush_hours,
            quiet_hours=quiet_hours,
            heatmap=heatmap,
            capacity_recommendations=capacity_recommendations,
            staff_suggestions=staff_suggestions,
            waiting_time_estimates=waiting_time_estimates,
            summary=summary,
            insights=insights,
        )

    def _aggregate_orders_by_hour(self, vendor_id: int, start_date: datetime, end_date: datetime) -> Dict[int, int]:
        """Aggregate order counts by hour of day."""
        orders = self.db.query(
            extract('hour', Order.created_at).label('hour'),
            func.count(Order.id).label('count'),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status != OrderStatus.CANCELLED,
        ).group_by(extract('hour', Order.created_at)).all()
        
        result = {h: 0 for h in range(24)}
        for row in orders:
            result[int(row.hour)] = row.count
        return result

    def _aggregate_by_day_of_week(self, vendor_id: int, start_date: datetime, end_date: datetime) -> Dict[int, float]:
        """Aggregate average orders by day of week."""
        orders = self.db.query(
            extract('dow', Order.created_at).label('dow'),
            func.count(Order.id).label('count'),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status != OrderStatus.CANCELLED,
        ).group_by(extract('dow', Order.created_at)).all()
        
        result = {}
        for row in orders:
            result[int(row.dow)] = row.count
        return result

    def _get_slots_for_date(self, vendor_id: int, date_str: str) -> List[Slot]:
        """Get slots for a specific date."""
        return self.db.query(Slot).filter(
            Slot.vendor_id == vendor_id,
            func.date(Slot.start_time) == date_str,
        ).all()

    def _predict_hourly_orders(
        self, hour: int, dow: int,
        pattern_7d: Dict[int, int], pattern_30d: Dict[int, int], pattern_90d: Dict[int, int],
        day_pattern: Dict[int, float]
    ) -> int:
        """Predict orders for a specific hour using weighted historical data."""
        # Weights: 7d = 0.5, 30d = 0.3, 90d = 0.2
        base_7d = pattern_7d.get(hour, 0) / 7 if sum(pattern_7d.values()) > 0 else 0
        base_30d = pattern_30d.get(hour, 0) / 30 if sum(pattern_30d.values()) > 0 else 0
        base_90d = pattern_90d.get(hour, 0) / 90 if sum(pattern_90d.values()) > 0 else 0
        
        if base_7d > 0:
            predicted = base_7d * 0.5 + base_30d * 0.3 + base_90d * 0.2
        elif base_30d > 0:
            predicted = base_30d * 0.7 + base_90d * 0.3
        elif base_90d > 0:
            predicted = base_90d
        else:
            return 0
        
        # Apply day-of-week multiplier
        dow_avg = day_pattern.get(dow, 0) / 7 if sum(day_pattern.values()) > 0 else 1.0
        dow_factor = max(0.5, min(2.0, dow_avg / (sum(day_pattern.values()) / max(len(day_pattern), 1)))) if day_pattern else 1.0
        
        predicted *= dow_factor
        
        return max(0, round(predicted))

    def _get_high_threshold(self, pattern: Dict[int, int]) -> int:
        """Get threshold for rush hour classification."""
        if not pattern or sum(pattern.values()) == 0:
            return 10
        values = [v for v in pattern.values() if v > 0]
        if not values:
            return 10
        avg = sum(values) / len(values)
        return round(avg * 1.2)

    def _get_low_threshold(self, pattern: Dict[int, int]) -> int:
        """Get threshold for quiet hour classification."""
        if not pattern or sum(pattern.values()) == 0:
            return 3
        values = [v for v in pattern.values() if v > 0]
        if not values:
            return 3
        avg = sum(values) / len(values)
        return round(avg * 0.5)

    def _calculate_staff_needed(self, predicted_orders: int, category: HourCategory) -> int:
        """Calculate suggested staff count for an hour."""
        if category == HourCategory.CLOSED:
            return 0
        
        base_staff = 1
        if predicted_orders <= 5:
            return base_staff
        elif predicted_orders <= 15:
            return max(1, round(predicted_orders / 8))
        elif predicted_orders <= 30:
            return max(2, round(predicted_orders / 10))
        else:
            return max(3, round(predicted_orders / 12))

    def _calculate_expected_wait(self, predicted_orders: int, capacity: int, utilization: float) -> float:
        """Calculate expected waiting time in minutes."""
        if predicted_orders <= 0 or capacity <= 0:
            return 0.0
        
        if utilization < 50:
            return 2.0  # Low wait
        elif utilization < 70:
            return 5.0  # Moderate wait
        elif utilization < 85:
            return 10.0  # Noticeable wait
        elif utilization < 95:
            return 15.0  # Long wait
        else:
            return 20.0  # Very long wait

    def _calculate_recommended_capacity(self, predicted_orders: int, category: HourCategory) -> int:
        """Calculate recommended slot capacity for an hour."""
        if category == HourCategory.CLOSED:
            return 0
        
        # Recommend 20% buffer above predicted
        return max(1, round(predicted_orders * 1.2))

    def _get_heatmap_color(self, intensity: float) -> str:
        """Get hex color for heatmap based on intensity."""
        if intensity >= 0.8:
            return "#EF4444"  # Red - Rush
        elif intensity >= 0.5:
            return "#F59E0B"  # Yellow - Moderate
        elif intensity >= 0.2:
            return "#10B981"  # Green - Quiet
        else:
            return "#374151"  # Gray - Closed/Inactive

    # ── Output Generators ───────────────────────────────────────────────

    def _generate_heatmap(self, heatmap_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured heatmap data."""
        hours = sorted(heatmap_data.keys())
        
        return {
            "type": "hourly_heatmap",
            "hours": hours,
            "data": heatmap_data,
            "legend": [
                {"label": "Rush", "color": "#EF4444", "min_intensity": 0.8},
                {"label": "Moderate", "color": "#F59E0B", "min_intensity": 0.5},
                {"label": "Quiet", "color": "#10B981", "min_intensity": 0.2},
                {"label": "Closed", "color": "#374151", "min_intensity": 0.0},
            ],
        }

    def _generate_capacity_recommendations(self, predictions: List[HourlyPrediction]) -> List[Dict]:
        """Generate capacity recommendations per hour."""
        recommendations = []
        for p in predictions:
            if p.current_capacity != p.recommended_capacity:
                recommendations.append({
                    "hour": p.hour,
                    "time_label": p.time_label,
                    "current_capacity": p.current_capacity,
                    "recommended_capacity": p.recommended_capacity,
                    "difference": p.recommended_capacity - p.current_capacity,
                    "reason": self._get_capacity_reason(p),
                })
        return recommendations

    def _get_capacity_reason(self, p: HourlyPrediction) -> str:
        """Get reason for capacity change recommendation."""
        if p.recommended_capacity > p.current_capacity:
            return f"Predicted {p.predicted_orders} orders - need {p.recommended_capacity} capacity"
        elif p.recommended_capacity < p.current_capacity:
            return f"Low demand predicted ({p.predicted_orders} orders) - reduce capacity"
        return "Current capacity adequate"

    def _generate_staff_suggestions(self, predictions: List[HourlyPrediction]) -> List[Dict]:
        """Generate staff suggestions per hour."""
        suggestions = []
        for p in predictions:
            suggestions.append({
                "hour": p.hour,
                "time_label": p.time_label,
                "category": p.category.value,
                "suggested_staff": p.suggested_staff,
                "predicted_orders": p.predicted_orders,
                "reason": f"Predicted {p.predicted_orders} orders need {p.suggested_staff} staff",
            })
        return suggestions

    def _generate_waiting_time_estimates(self, predictions: List[HourlyPrediction]) -> List[Dict]:
        """Generate waiting time estimates per hour."""
        estimates = []
        for p in predictions:
            estimates.append({
                "hour": p.hour,
                "time_label": p.time_label,
                "expected_wait_minutes": p.expected_wait_minutes,
                "congestion_percent": p.congestion_percent,
                "utilization": p.slot_utilization,
                "wait_category": self._get_wait_category(p.expected_wait_minutes),
            })
        return estimates

    def _get_wait_category(self, wait_minutes: float) -> str:
        """Categorize wait time."""
        if wait_minutes <= 2:
            return "minimal"
        elif wait_minutes <= 5:
            return "short"
        elif wait_minutes <= 10:
            return "moderate"
        elif wait_minutes <= 15:
            return "long"
        else:
            return "very_long"

    def _generate_summary(
        self, predictions: List[HourlyPrediction],
        rush_hours: List[Dict], quiet_hours: List[Dict]
    ) -> Dict[str, Any]:
        """Generate summary statistics."""
        active_hours = [p for p in predictions if p.category != HourCategory.CLOSED]
        
        if not active_hours:
            return {
                "total_predicted_orders": 0,
                "rush_hours_count": 0,
                "quiet_hours_count": 0,
                "peak_hour": None,
                "peak_orders": 0,
                "avg_congestion": 0,
                "total_staff_needed": 0,
                "peak_staff_needed": 0,
            }
        
        peak = max(active_hours, key=lambda p: p.predicted_orders)
        
        return {
            "total_predicted_orders": sum(p.predicted_orders for p in active_hours),
            "rush_hours_count": len(rush_hours),
            "quiet_hours_count": len(quiet_hours),
            "peak_hour": {
                "hour": peak.hour,
                "time_label": peak.time_label,
                "orders": peak.predicted_orders,
                "congestion": peak.congestion_percent,
            },
            "peak_orders": peak.predicted_orders,
            "avg_congestion": round(sum(p.congestion_percent for p in active_hours) / len(active_hours), 1),
            "total_staff_needed": sum(p.suggested_staff for p in active_hours),
            "peak_staff_needed": peak.suggested_staff,
        }

    def _generate_insights(
        self, predictions: List[HourlyPrediction],
        rush_hours: List[Dict], quiet_hours: List[Dict],
        summary: Dict[str, Any]
    ) -> List[str]:
        """Generate AI insights from predictions."""
        insights = []
        
        if summary["rush_hours_count"] > 0:
            peak_times = ", ".join(r["time_label"] for r in rush_hours[:3])
            insights.append(f"Rush hours: {peak_times} - prepare {summary['peak_staff_needed']}+ staff")
        
        if summary["quiet_hours_count"] > 0:
            quiet_times = ", ".join(q["time_label"] for q in quiet_hours[:3])
            insights.append(f"Quiet hours: {quiet_times} - consider reduced staffing")
        
        peak = summary.get("peak_hour")
        if peak:
            insights.append(f"Peak hour at {peak['time_label']} with {peak['orders']} orders ({peak['congestion']}% congestion)")
        
        if summary["avg_congestion"] > 70:
            insights.append(f"High average congestion ({summary['avg_congestion']}%) - consider increasing slot capacity")
        elif summary["avg_congestion"] < 30:
            insights.append(f"Low average congestion ({summary['avg_congestion']}%) - consider reducing slot capacity")
        
        total_orders = summary["total_predicted_orders"]
        if total_orders > 0:
            insights.append(f"Total predicted orders: ~{total_orders} - plan staffing accordingly")
        
        # Staff insights
        staff_needed = summary.get("peak_staff_needed", 0)
        if staff_needed > 3:
            insights.append(f"Peak staff requirement: {staff_needed} - ensure adequate coverage")
        
        return insights

    # ── Public API Methods ──────────────────────────────────────────────

    def get_peak_hours(self, vendor_id: int, days_ahead: int = 1) -> Dict[str, Any]:
        """Get rush hours prediction."""
        result = self.predict_peak_hours(vendor_id, days_ahead)
        return {
            "vendor_id": vendor_id,
            "prediction_date": result.prediction_date,
            "rush_hours": result.rush_hours,
            "summary": result.summary,
            "insights": [i for i in result.insights if "rush" in i.lower() or "peak" in i.lower()],
        }

    def get_quiet_hours(self, vendor_id: int, days_ahead: int = 1) -> Dict[str, Any]:
        """Get quiet hours prediction."""
        result = self.predict_peak_hours(vendor_id, days_ahead)
        return {
            "vendor_id": vendor_id,
            "prediction_date": result.prediction_date,
            "quiet_hours": result.quiet_hours,
            "insights": [i for i in result.insights if "quiet" in i.lower()],
        }

    def get_heatmap(self, vendor_id: int, days_ahead: int = 1) -> Dict[str, Any]:
        """Get peak hour heatmap."""
        result = self.predict_peak_hours(vendor_id, days_ahead)
        return {
            "vendor_id": vendor_id,
            "prediction_date": result.prediction_date,
            "heatmap": result.heatmap,
            "insights": result.insights[:3],
        }

    def get_capacity_recommendations(self, vendor_id: int, days_ahead: int = 1) -> Dict[str, Any]:
        """Get capacity recommendations."""
        result = self.predict_peak_hours(vendor_id, days_ahead)
        return {
            "vendor_id": vendor_id,
            "prediction_date": result.prediction_date,
            "recommendations": result.capacity_recommendations,
            "insights": [i for i in result.insights if "capacity" in i.lower() or "congestion" in i.lower()],
        }

    def get_staff_suggestions(self, vendor_id: int, days_ahead: int = 1) -> Dict[str, Any]:
        """Get staff suggestions."""
        result = self.predict_peak_hours(vendor_id, days_ahead)
        return {
            "vendor_id": vendor_id,
            "prediction_date": result.prediction_date,
            "suggestions": result.staff_suggestions,
            "peak_staff": result.summary.get("peak_staff_needed", 0),
            "total_staff": result.summary.get("total_staff_needed", 0),
            "insights": [i for i in result.insights if "staff" in i.lower()],
        }

    def get_waiting_time_estimates(self, vendor_id: int, days_ahead: int = 1) -> Dict[str, Any]:
        """Get waiting time estimates."""
        result = self.predict_peak_hours(vendor_id, days_ahead)
        return {
            "vendor_id": vendor_id,
            "prediction_date": result.prediction_date,
            "estimates": result.waiting_time_estimates,
            "insights": [i for i in result.insights if "wait" in i.lower() or "congestion" in i.lower()],
        }
