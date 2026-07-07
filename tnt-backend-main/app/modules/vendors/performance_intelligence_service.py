"""
Vendor Performance Intelligence Service
========================================

Calculates comprehensive vendor performance metrics:

- Preparation Speed: Average time to prepare orders
- Completion Rate: Percentage of orders completed successfully
- Cancellation Rate: Percentage of orders cancelled
- Average Delay: Average delay in order completion
- Customer Satisfaction: Based on order completion and timing
- Order Accuracy: Accuracy of order fulfillment

Generates overall Vendor Score and provides insights for improving:
- Forecast accuracy
- Recommendations
- Inventory suggestions
- Dashboard analytics
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.menu.model import MenuItem

logger = logging.getLogger("tnt.ai.performance")


# ── Data Models ─────────────────────────────────────────────────────────


class PerformanceGrade(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


@dataclass
class VendorPerformanceMetrics:
    """Comprehensive vendor performance metrics."""
    vendor_id: int
    
    # Core metrics
    preparation_speed: float  # Average minutes to prepare
    completion_rate: float  # Percentage (0-100)
    cancellation_rate: float  # Percentage (0-100)
    average_delay: float  # Average minutes delay
    customer_satisfaction: float  # Score (0-100)
    order_accuracy: float  # Percentage (0-100)
    
    # Overall score
    vendor_score: float  # 0-100
    performance_grade: PerformanceGrade
    
    # Detailed breakdown
    metrics_breakdown: Dict[str, Any] = field(default_factory=dict)
    insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class PerformanceHistory:
    """Historical performance tracking."""
    vendor_id: int
    metric_date: datetime
    preparation_speed: float
    completion_rate: float
    cancellation_rate: float
    average_delay: float
    customer_satisfaction: float
    order_accuracy: float
    vendor_score: float
    created_at: datetime


# ── Performance Intelligence Service ────────────────────────────────────


class PerformanceIntelligenceService:
    """Service for calculating vendor performance metrics."""

    def __init__(self, db: Session):
        self.db = db
        self._cache: Dict[int, VendorPerformanceMetrics] = {}
        self._cache_ttl = 1800  # 30 minutes

    # ── Main Performance Calculation ──────────────────────────────────────

    def calculate_performance_metrics(self, vendor_id: int, days: int = 30) -> VendorPerformanceMetrics:
        """Calculate comprehensive performance metrics for a vendor.
        
        Args:
            vendor_id: Vendor ID
            days: Number of days to analyze (default: 30)
            
        Returns:
            VendorPerformanceMetrics with all metrics and insights
        """
        cutoff_date = utcnow_naive() - timedelta(days=days)
        
        # Get orders in period
        orders = self.db.query(Order).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= cutoff_date,
        ).all()
        
        if not orders:
            return self._get_default_metrics(vendor_id)
        
        # Calculate individual metrics
        preparation_speed = self._calculate_preparation_speed(orders)
        completion_rate = self._calculate_completion_rate(orders)
        cancellation_rate = self._calculate_cancellation_rate(orders)
        average_delay = self._calculate_average_delay(orders)
        customer_satisfaction = self._calculate_customer_satisfaction(orders)
        order_accuracy = self._calculate_order_accuracy(orders)
        
        # Calculate overall vendor score
        vendor_score = self._calculate_vendor_score(
            preparation_speed,
            completion_rate,
            cancellation_rate,
            average_delay,
            customer_satisfaction,
            order_accuracy,
        )
        
        # Determine performance grade
        performance_grade = self._get_performance_grade(vendor_score)
        
        # Generate metrics breakdown
        metrics_breakdown = self._generate_metrics_breakdown(
            orders, preparation_speed, completion_rate, cancellation_rate,
            average_delay, customer_satisfaction, order_accuracy
        )
        
        # Generate insights
        insights = self._generate_insights(
            preparation_speed, completion_rate, cancellation_rate,
            average_delay, customer_satisfaction, order_accuracy, vendor_score
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            preparation_speed, completion_rate, cancellation_rate,
            average_delay, customer_satisfaction, order_accuracy
        )
        
        return VendorPerformanceMetrics(
            vendor_id=vendor_id,
            preparation_speed=round(preparation_speed, 1),
            completion_rate=round(completion_rate, 1),
            cancellation_rate=round(cancellation_rate, 1),
            average_delay=round(average_delay, 1),
            customer_satisfaction=round(customer_satisfaction, 1),
            order_accuracy=round(order_accuracy, 1),
            vendor_score=round(vendor_score, 1),
            performance_grade=performance_grade,
            metrics_breakdown=metrics_breakdown,
            insights=insights,
            recommendations=recommendations,
        )

    def _get_default_metrics(self, vendor_id: int) -> VendorPerformanceMetrics:
        """Get default metrics when no orders exist."""
        return VendorPerformanceMetrics(
            vendor_id=vendor_id,
            preparation_speed=0.0,
            completion_rate=0.0,
            cancellation_rate=0.0,
            average_delay=0.0,
            customer_satisfaction=0.0,
            order_accuracy=0.0,
            vendor_score=0.0,
            performance_grade=PerformanceGrade.POOR,
            metrics_breakdown={"total_orders": 0, "message": "No orders in period"},
            insights=["No order data available for analysis"],
            recommendations=["Start accepting orders to build performance history"],
        )

    # ── Metric Calculations ───────────────────────────────────────────────

    def _calculate_preparation_speed(self, orders: List[Order]) -> float:
        """Calculate average preparation speed in minutes."""
        completed_orders = [
            o for o in orders
            if o.status in [OrderStatus.READY, OrderStatus.COMPLETED]
            and o.eta_minutes is not None
            and o.eta_minutes > 0
        ]
        
        if not completed_orders:
            return 0.0
        
        total_time = sum(o.eta_minutes for o in completed_orders)
        avg_time = total_time / len(completed_orders)
        
        return avg_time

    def _calculate_completion_rate(self, orders: List[Order]) -> float:
        """Calculate order completion rate percentage."""
        if not orders:
            return 0.0
        
        completed = sum(1 for o in orders if o.status == OrderStatus.COMPLETED)
        completion_rate = (completed / len(orders)) * 100
        
        return completion_rate

    def _calculate_cancellation_rate(self, orders: List[Order]) -> float:
        """Calculate order cancellation rate percentage."""
        if not orders:
            return 0.0
        
        cancelled = sum(1 for o in orders if o.status == OrderStatus.CANCELLED)
        cancellation_rate = (cancelled / len(orders)) * 100
        
        return cancellation_rate

    def _calculate_average_delay(self, orders: List[Order]) -> float:
        """Calculate average delay in minutes."""
        completed_orders = [
            o for o in orders
            if o.status == OrderStatus.COMPLETED
            and o.eta_minutes is not None
        ]
        
        if not completed_orders:
            return 0.0
        
        # Calculate delay as difference between ETA and actual completion time
        # Simplified: use ETA as proxy for delay
        total_delay = sum(o.eta_minutes for o in completed_orders)
        avg_delay = total_delay / len(completed_orders)
        
        return avg_delay

    def _calculate_customer_satisfaction(self, orders: List[Order]) -> float:
        """Calculate customer satisfaction score (0-100)."""
        if not orders:
            return 0.0
        
        # Factors affecting satisfaction:
        # 1. Completion rate (40% weight)
        # 2. Low cancellation rate (30% weight)
        # 3. Fast preparation (20% weight)
        # 4. Low delay (10% weight)
        
        completion_rate = self._calculate_completion_rate(orders)
        cancellation_rate = self._calculate_cancellation_rate(orders)
        prep_speed = self._calculate_preparation_speed(orders)
        avg_delay = self._calculate_average_delay(orders)
        
        # Normalize scores
        completion_score = completion_rate  # Already 0-100
        cancellation_score = max(0, 100 - cancellation_rate * 2)  # Invert and scale
        
        # Preparation speed: assume 30 min is ideal
        prep_score = max(0, min(100, (30 / max(prep_speed, 1)) * 100))
        
        # Delay score: assume 10 min is ideal
        delay_score = max(0, min(100, (10 / max(avg_delay, 1)) * 100))
        
        # Weighted average
        satisfaction = (
            completion_score * 0.4 +
            cancellation_score * 0.3 +
            prep_score * 0.2 +
            delay_score * 0.1
        )
        
        return satisfaction

    def _calculate_order_accuracy(self, orders: List[Order]) -> float:
        """Calculate order accuracy percentage."""
        if not orders:
            return 0.0
        
        # Orders are considered accurate if:
        # 1. Not cancelled
        # 2. Completed successfully
        # 3. No fraud flags
        
        accurate_orders = sum(
            1 for o in orders
            if o.status == OrderStatus.COMPLETED
            and not o.fraud_flag
        )
        
        total_valid_orders = sum(
            1 for o in orders
            if o.status != OrderStatus.CANCELLED
        )
        
        if total_valid_orders == 0:
            return 0.0
        
        accuracy = (accurate_orders / total_valid_orders) * 100
        
        return accuracy

    def _calculate_vendor_score(
        self,
        prep_speed: float,
        completion_rate: float,
        cancellation_rate: float,
        avg_delay: float,
        satisfaction: float,
        accuracy: float,
    ) -> float:
        """Calculate overall vendor score (0-100)."""
        # Weights for each metric
        weights = {
            "completion_rate": 0.25,
            "cancellation_rate": 0.20,
            "customer_satisfaction": 0.20,
            "order_accuracy": 0.15,
            "preparation_speed": 0.10,
            "average_delay": 0.10,
        }
        
        # Normalize metrics to 0-100 scale
        completion_score = completion_rate
        cancellation_score = max(0, 100 - cancellation_rate * 2)
        satisfaction_score = satisfaction
        accuracy_score = accuracy
        
        # Preparation speed: assume 30 min is ideal (100%), 60 min is poor (0%)
        prep_score = max(0, min(100, (60 - prep_speed) / 30 * 100)) if prep_speed > 0 else 50
        
        # Delay: assume 10 min is ideal (100%), 30 min is poor (0%)
        delay_score = max(0, min(100, (30 - avg_delay) / 20 * 100)) if avg_delay > 0 else 50
        
        # Calculate weighted score
        vendor_score = (
            completion_score * weights["completion_rate"] +
            cancellation_score * weights["cancellation_rate"] +
            satisfaction_score * weights["customer_satisfaction"] +
            accuracy_score * weights["order_accuracy"] +
            prep_score * weights["preparation_speed"] +
            delay_score * weights["average_delay"]
        )
        
        return vendor_score

    def _get_performance_grade(self, vendor_score: float) -> PerformanceGrade:
        """Get performance grade based on score."""
        if vendor_score >= 85:
            return PerformanceGrade.EXCELLENT
        elif vendor_score >= 70:
            return PerformanceGrade.GOOD
        elif vendor_score >= 50:
            return PerformanceGrade.FAIR
        else:
            return PerformanceGrade.POOR

    # ── Breakdown and Insights ────────────────────────────────────────────

    def _generate_metrics_breakdown(
        self, orders: List[Order], prep_speed: float, completion_rate: float,
        cancellation_rate: float, avg_delay: float, satisfaction: float, accuracy: float
    ) -> Dict[str, Any]:
        """Generate detailed metrics breakdown."""
        total_orders = len(orders)
        completed = sum(1 for o in orders if o.status == OrderStatus.COMPLETED)
        cancelled = sum(1 for o in orders if o.status == OrderStatus.CANCELLED)
        pending = sum(1 for o in orders if o.status == OrderStatus.PENDING)
        preparing = sum(1 for o in orders if o.status == OrderStatus.PREPARING)
        ready = sum(1 for o in orders if o.status == OrderStatus.READY)
        
        # Calculate revenue
        total_revenue = sum(o.total_amount for o in orders if o.status == OrderStatus.COMPLETED)
        avg_order_value = total_revenue / completed if completed > 0 else 0
        
        return {
            "total_orders": total_orders,
            "completed_orders": completed,
            "cancelled_orders": cancelled,
            "pending_orders": pending,
            "preparing_orders": preparing,
            "ready_orders": ready,
            "total_revenue": round(total_revenue, 2),
            "avg_order_value": round(avg_order_value, 2),
            "status_distribution": {
                "completed": completed,
                "cancelled": cancelled,
                "pending": pending,
                "preparing": preparing,
                "ready": ready,
            },
        }

    def _generate_insights(
        self, prep_speed: float, completion_rate: float, cancellation_rate: float,
        avg_delay: float, satisfaction: float, accuracy: float, vendor_score: float
    ) -> List[str]:
        """Generate insights from performance metrics."""
        insights = []
        
        # Overall performance
        if vendor_score >= 85:
            insights.append("Excellent overall performance - maintain current standards")
        elif vendor_score >= 70:
            insights.append("Good performance with room for improvement")
        elif vendor_score >= 50:
            insights.append("Fair performance - several areas need attention")
        else:
            insights.append("Poor performance - immediate action required")
        
        # Preparation speed
        if prep_speed > 0:
            if prep_speed <= 15:
                insights.append(f"Excellent preparation speed: {prep_speed:.1f} minutes")
            elif prep_speed <= 25:
                insights.append(f"Good preparation speed: {prep_speed:.1f} minutes")
            elif prep_speed <= 40:
                insights.append(f"Moderate preparation speed: {prep_speed:.1f} minutes - consider optimizing workflow")
            else:
                insights.append(f"Slow preparation speed: {prep_speed:.1f} minutes - needs improvement")
        
        # Completion rate
        if completion_rate >= 95:
            insights.append(f"Excellent completion rate: {completion_rate:.1f}%")
        elif completion_rate >= 80:
            insights.append(f"Good completion rate: {completion_rate:.1f}%")
        elif completion_rate >= 60:
            insights.append(f"Moderate completion rate: {completion_rate:.1f}% - reduce cancellations")
        else:
            insights.append(f"Low completion rate: {completion_rate:.1f}% - critical issue")
        
        # Cancellation rate
        if cancellation_rate <= 2:
            insights.append(f"Excellent low cancellation rate: {cancellation_rate:.1f}%")
        elif cancellation_rate <= 5:
            insights.append(f"Good cancellation rate: {cancellation_rate:.1f}%")
        elif cancellation_rate <= 10:
            insights.append(f"Moderate cancellation rate: {cancellation_rate:.1f}% - investigate causes")
        else:
            insights.append(f"High cancellation rate: {cancellation_rate:.1f}% - urgent attention needed")
        
        # Customer satisfaction
        if satisfaction >= 90:
            insights.append(f"Excellent customer satisfaction: {satisfaction:.1f}/100")
        elif satisfaction >= 75:
            insights.append(f"Good customer satisfaction: {satisfaction:.1f}/100")
        elif satisfaction >= 60:
            insights.append(f"Moderate customer satisfaction: {satisfaction:.1f}/100")
        else:
            insights.append(f"Low customer satisfaction: {satisfaction:.1f}/100 - needs improvement")
        
        # Order accuracy
        if accuracy >= 98:
            insights.append(f"Excellent order accuracy: {accuracy:.1f}%")
        elif accuracy >= 90:
            insights.append(f"Good order accuracy: {accuracy:.1f}%")
        elif accuracy >= 80:
            insights.append(f"Moderate order accuracy: {accuracy:.1f}%")
        else:
            insights.append(f"Low order accuracy: {accuracy:.1f}% - review fulfillment process")
        
        return insights

    def _generate_recommendations(
        self, prep_speed: float, completion_rate: float, cancellation_rate: float,
        avg_delay: float, satisfaction: float, accuracy: float
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Preparation speed recommendations
        if prep_speed > 40:
            recommendations.append("Optimize preparation workflow to reduce preparation time")
            recommendations.append("Consider adding more staff during peak hours")
        elif prep_speed > 25:
            recommendations.append("Streamline preparation process for faster service")
        
        # Completion rate recommendations
        if completion_rate < 80:
            recommendations.append("Investigate reasons for order non-completion")
            recommendations.append("Improve order management and tracking")
        
        # Cancellation rate recommendations
        if cancellation_rate > 10:
            recommendations.append("URGENT: Reduce cancellation rate - review inventory management")
            recommendations.append("Implement pre-order cutoff times to reduce cancellations")
        elif cancellation_rate > 5:
            recommendations.append("Reduce cancellations by improving stock availability")
        
        # Delay recommendations
        if avg_delay > 30:
            recommendations.append("Reduce order delays - improve preparation planning")
            recommendations.append("Set realistic ETAs based on current capacity")
        
        # Customer satisfaction recommendations
        if satisfaction < 60:
            recommendations.append("Focus on customer experience - reduce wait times")
            recommendations.append("Improve communication with customers about order status")
        
        # Order accuracy recommendations
        if accuracy < 90:
            recommendations.append("Improve order accuracy - implement double-check process")
            recommendations.append("Train staff on order fulfillment procedures")
        
        if not recommendations:
            recommendations.append("Maintain current performance standards")
        
        return recommendations

    # ── Performance History Tracking ──────────────────────────────────────

    def record_performance(self, vendor_id: int, metrics: VendorPerformanceMetrics) -> None:
        """Record performance metrics for historical tracking."""
        history = PerformanceHistory(
            vendor_id=vendor_id,
            metric_date=utcnow_naive(),
            preparation_speed=metrics.preparation_speed,
            completion_rate=metrics.completion_rate,
            cancellation_rate=metrics.cancellation_rate,
            average_delay=metrics.average_delay,
            customer_satisfaction=metrics.customer_satisfaction,
            order_accuracy=metrics.order_accuracy,
            vendor_score=metrics.vendor_score,
            created_at=utcnow_naive(),
        )
        
        self.db.add(history)
        self.db.commit()

    def get_performance_history(
        self, vendor_id: int, days: int = 90
    ) -> List[Dict[str, Any]]:
        """Get performance history for a vendor."""
        cutoff_date = utcnow_naive() - timedelta(days=days)
        
        history = self.db.query(PerformanceHistory).filter(
            PerformanceHistory.vendor_id == vendor_id,
            PerformanceHistory.created_at >= cutoff_date,
        ).order_by(PerformanceHistory.created_at.desc()).all()
        
        return [
            {
                "metric_date": h.metric_date.isoformat(),
                "preparation_speed": h.preparation_speed,
                "completion_rate": h.completion_rate,
                "cancellation_rate": h.cancellation_rate,
                "average_delay": h.average_delay,
                "customer_satisfaction": h.customer_satisfaction,
                "order_accuracy": h.order_accuracy,
                "vendor_score": h.vendor_score,
            }
            for h in history
        ]

    # ── Public API ────────────────────────────────────────────────────────

    def get_performance_report(self, vendor_id: int, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        metrics = self.calculate_performance_metrics(vendor_id, days)
        
        return {
            "vendor_id": vendor_id,
            "period_days": days,
            "metrics": {
                "preparation_speed": metrics.preparation_speed,
                "completion_rate": metrics.completion_rate,
                "cancellation_rate": metrics.cancellation_rate,
                "average_delay": metrics.average_delay,
                "customer_satisfaction": metrics.customer_satisfaction,
                "order_accuracy": metrics.order_accuracy,
                "vendor_score": metrics.vendor_score,
                "performance_grade": metrics.performance_grade.value,
            },
            "breakdown": metrics.metrics_breakdown,
            "insights": metrics.insights,
            "recommendations": metrics.recommendations,
            "generated_at": utcnow_naive().isoformat(),
        }

    def get_vendor_score(self, vendor_id: int) -> Dict[str, Any]:
        """Get vendor score with grade."""
        metrics = self.calculate_performance_metrics(vendor_id)
        
        return {
            "vendor_id": vendor_id,
            "vendor_score": metrics.vendor_score,
            "performance_grade": metrics.performance_grade.value,
            "grade_description": self._get_grade_description(metrics.performance_grade),
            "color": self._get_grade_color(metrics.performance_grade),
            "icon": self._get_grade_icon(metrics.performance_grade),
        }

    def _get_grade_description(self, grade: PerformanceGrade) -> str:
        """Get description for performance grade."""
        descriptions = {
            PerformanceGrade.EXCELLENT: "Outstanding performance - top tier",
            PerformanceGrade.GOOD: "Strong performance - above average",
            PerformanceGrade.FAIR: "Adequate performance - needs improvement",
            PerformanceGrade.POOR: "Below average - immediate action required",
        }
        return descriptions.get(grade, "Unknown")

    def _get_grade_color(self, grade: PerformanceGrade) -> str:
        """Get color for performance grade."""
        colors = {
            PerformanceGrade.EXCELLENT: "#10B981",  # Green
            PerformanceGrade.GOOD: "#3B82F6",  # Blue
            PerformanceGrade.FAIR: "#F59E0B",  # Yellow
            PerformanceGrade.POOR: "#EF4444",  # Red
        }
        return colors.get(grade, "#6B7280")

    def _get_grade_icon(self, grade: PerformanceGrade) -> str:
        """Get icon for performance grade."""
        icons = {
            PerformanceGrade.EXCELLENT: "★",
            PerformanceGrade.GOOD: "●",
            PerformanceGrade.FAIR: "◐",
            PerformanceGrade.POOR: "○",
        }
        return icons.get(grade, "?")

    def get_performance_insights_for_forecast(self, vendor_id: int) -> Dict[str, Any]:
        """Get performance insights to improve forecasting."""
        metrics = self.calculate_performance_metrics(vendor_id)
        
        return {
            "vendor_id": vendor_id,
            "vendor_score": metrics.vendor_score,
            "performance_grade": metrics.performance_grade.value,
            "forecast_adjustments": {
                "completion_rate_factor": metrics.completion_rate / 100,
                "cancellation_risk": metrics.cancellation_rate / 100,
                "capacity_efficiency": metrics.completion_rate / 100,
                "reliability_score": metrics.vendor_score / 100,
            },
            "insights": [
                f"Based on {metrics.performance_grade.value} performance, forecast confidence is {'high' if metrics.vendor_score >= 70 else 'moderate' if metrics.vendor_score >= 50 else 'low'}",
                f"Completion rate of {metrics.completion_rate:.1f}% suggests {'reliable' if metrics.completion_rate >= 80 else 'unreliable'} order fulfillment",
            ],
        }

    def get_performance_insights_for_recommendations(self, vendor_id: int) -> Dict[str, Any]:
        """Get performance insights to improve recommendations."""
        metrics = self.calculate_performance_metrics(vendor_id)
        
        return {
            "vendor_id": vendor_id,
            "vendor_score": metrics.vendor_score,
            "recommendation_factors": {
                "reliability": metrics.completion_rate / 100,
                "speed": max(0, min(1, 1 - metrics.preparation_speed / 60)),
                "quality": metrics.order_accuracy / 100,
                "customer_satisfaction": metrics.customer_satisfaction / 100,
            },
            "suggested_actions": metrics.recommendations[:3],
            "priority_areas": self._identify_priority_areas(metrics),
        }

    def _identify_priority_areas(self, metrics: VendorPerformanceMetrics) -> List[str]:
        """Identify priority improvement areas."""
        priorities = []
        
        if metrics.cancellation_rate > 10:
            priorities.append("Reduce cancellations")
        if metrics.preparation_speed > 40:
            priorities.append("Speed up preparation")
        if metrics.completion_rate < 80:
            priorities.append("Improve completion rate")
        if metrics.customer_satisfaction < 60:
            priorities.append("Boost customer satisfaction")
        if metrics.order_accuracy < 90:
            priorities.append("Increase order accuracy")
        
        return priorities[:3]  # Top 3 priorities

    def get_performance_insights_for_inventory(self, vendor_id: int) -> Dict[str, Any]:
        """Get performance insights to improve inventory suggestions."""
        metrics = self.calculate_performance_metrics(vendor_id)
        
        return {
            "vendor_id": vendor_id,
            "vendor_score": metrics.vendor_score,
            "inventory_factors": {
                "stock_accuracy": metrics.order_accuracy / 100,
                "fulfillment_reliability": metrics.completion_rate / 100,
                "cancellation_impact": metrics.cancellation_rate / 100,
            },
            "suggestions": [
                "Focus on high-demand items" if metrics.completion_rate >= 80 else "Reduce stock levels due to high cancellations",
                "Maintain adequate stock" if metrics.cancellation_rate < 5 else "Improve stock availability to reduce cancellations",
            ],
        }

    def get_performance_insights_for_dashboard(self, vendor_id: int) -> Dict[str, Any]:
        """Get performance insights for dashboard analytics."""
        metrics = self.calculate_performance_metrics(vendor_id)
        
        return {
            "vendor_id": vendor_id,
            "vendor_score": metrics.vendor_score,
            "performance_grade": metrics.performance_grade.value,
            "key_metrics": {
                "preparation_speed": {
                    "value": metrics.preparation_speed,
                    "unit": "minutes",
                    "trend": "stable",  # Would calculate from history
                },
                "completion_rate": {
                    "value": metrics.completion_rate,
                    "unit": "%",
                    "trend": "stable",
                },
                "cancellation_rate": {
                    "value": metrics.cancellation_rate,
                    "unit": "%",
                    "trend": "stable",
                },
                "customer_satisfaction": {
                    "value": metrics.customer_satisfaction,
                    "unit": "score",
                    "trend": "stable",
                },
            },
            "breakdown": metrics.metrics_breakdown,
            "insights": metrics.insights[:5],
            "recommendations": metrics.recommendations[:3],
        }
