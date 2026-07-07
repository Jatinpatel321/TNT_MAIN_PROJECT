"""
Forecast Validation Pipeline
=============================

Compares predicted vs actual values for forecasting accuracy:

- Predicted Orders vs Actual Orders
- Predicted Revenue vs Actual Revenue
- Predicted Demand vs Actual Demand

Calculates:
- MAPE (Mean Absolute Percentage Error)
- RMSE (Root Mean Square Error)
- Prediction Accuracy (1 - error rate)

Stores validation history in memory/database.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from sqlalchemy import func, extract, and_
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive

logger = logging.getLogger("tnt.ai.validation")


# ── Data Models ─────────────────────────────────────────────────────────


class ValidationPeriodType(Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class AccuracyGrade(Enum):
    EXCELLENT = "excellent"     # >= 90%
    GOOD = "good"              # >= 80%
    FAIR = "fair"              # >= 70%
    POOR = "poor"              # >= 50%
    FAIL = "fail"              # < 50%


@dataclass
class PredictionActualPair:
    """A single prediction vs actual comparison."""
    period_label: str
    period_start: str
    predicted_orders: int
    actual_orders: int
    predicted_revenue: float
    actual_revenue: float
    orders_accuracy: float  # 0-100
    revenue_accuracy: float  # 0-100
    order_error: int  # absolute difference
    revenue_error: float  # absolute difference


@dataclass
class ValidationMetricResult:
    """Validation metrics for a set of predictions."""
    metric_name: str  # "orders", "revenue", "demand"
    
    # Core metrics
    mape: float  # Mean Absolute Percentage Error
    rmse: float  # Root Mean Square Error
    prediction_accuracy: float  # 0-100
    
    # Detailed
    mean_error: float
    max_error: float
    min_error: float
    error_std_dev: float
    
    # Grade
    grade: AccuracyGrade
    samples_count: int
    
    # Individual comparisons
    comparisons: List[PredictionActualPair]


@dataclass
class ValidationResult:
    """Complete validation result for a vendor."""
    vendor_id: int
    period_type: ValidationPeriodType
    period_count: int
    generated_at: str
    
    # Metrics by type
    orders: ValidationMetricResult
    revenue: ValidationMetricResult
    demand: Optional[ValidationMetricResult]
    
    # Overall
    overall_accuracy: float
    overall_grade: AccuracyGrade
    
    # Insights
    insights: List[str]
    recommendations: List[str]


# ── Validation History Store (In-Memory + DB) ──────────────────────────


class ValidationHistoryEntry:
    """A stored validation record."""
    def __init__(self, vendor_id: int, period_type: str, period_start: str,
                 predicted_orders: int, actual_orders: int,
                 predicted_revenue: float, actual_revenue: float,
                 orders_accuracy: float, revenue_accuracy: float,
                 mape: float, rmse: float):
        self.vendor_id = vendor_id
        self.period_type = period_type
        self.period_start = period_start
        self.predicted_orders = predicted_orders
        self.actual_orders = actual_orders
        self.predicted_revenue = predicted_revenue
        self.actual_revenue = actual_revenue
        self.orders_accuracy = orders_accuracy
        self.revenue_accuracy = revenue_accuracy
        self.mape = mape
        self.rmse = rmse
        self.created_at = utcnow_naive()


class ValidationHistoryStore:
    """In-memory store for validation history.
    
    In production, this would be backed by a database table.
    """

    def __init__(self):
        self._entries: List[ValidationHistoryEntry] = []
        self._metrics_history: Dict[str, List[float]] = defaultdict(list)

    def store(self, entry: ValidationHistoryEntry) -> None:
        """Store a validation entry."""
        self._entries.append(entry)
        
        # Track accuracy history
        key = f"{entry.vendor_id}:{entry.period_type}:orders_accuracy"
        self._metrics_history[key].append(entry.orders_accuracy)
        
        # Keep only last 1000 entries
        if len(self._entries) > 1000:
            self._entries = self._entries[-1000:]

    def get_history(self, vendor_id: int, period_type: str, limit: int = 50) -> List[Dict]:
        """Get validation history for vendor."""
        relevant = [
            e for e in self._entries
            if e.vendor_id == vendor_id and e.period_type == period_type
        ]
        recent = sorted(relevant, key=lambda e: e.created_at, reverse=True)[:limit]
        
        return [
            {
                "period_start": e.period_start,
                "period_type": e.period_type,
                "predicted_orders": e.predicted_orders,
                "actual_orders": e.actual_orders,
                "predicted_revenue": e.predicted_revenue,
                "actual_revenue": e.actual_revenue,
                "orders_accuracy": round(e.orders_accuracy, 1),
                "revenue_accuracy": round(e.revenue_accuracy, 1),
                "mape": round(e.mape, 1),
                "rmse": round(e.rmse, 1),
                "created_at": e.created_at.isoformat(),
            }
            for e in recent
        ]

    def get_accuracy_trend(self, vendor_id: int, period_type: str, days: int = 30) -> Dict[str, Any]:
        """Get accuracy trend over time."""
        cutoff = utcnow_naive() - timedelta(days=days)
        
        relevant = [
            e for e in self._entries
            if e.vendor_id == vendor_id
            and e.period_type == period_type
            and e.created_at >= cutoff
        ]
        
        if not relevant:
            return {
                "status": "no_data",
                "average_accuracy": 0,
                "trend": "unknown",
                "days_analyzed": days,
                "entries_found": 0,
            }
        
        sorted_entries = sorted(relevant, key=lambda e: e.created_at)
        accuracies = [e.orders_accuracy for e in sorted_entries]
        avg_accuracy = sum(accuracies) / len(accuracies)
        
        # Determine trend
        if len(accuracies) >= 5:
            recent_avg = sum(accuracies[-5:]) / 5
            older_avg = sum(accuracies[:-5]) / len(accuracies[:-5]) if len(accuracies) > 5 else recent_avg
            
            if recent_avg > older_avg + 2:
                trend = "improving"
            elif recent_avg < older_avg - 2:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "status": "active",
            "average_accuracy": round(avg_accuracy, 1),
            "trend": trend,
            "days_analyzed": days,
            "entries_found": len(relevant),
            "latest_accuracy": round(accuracies[-1], 1),
            "best_accuracy": round(max(accuracies), 1),
            "worst_accuracy": round(min(accuracies), 1),
        }


# Global store instance
_validation_store = ValidationHistoryStore()


# ── Forecast Validation Service ────────────────────────────────────────


class ForecastValidationService:
    """Service for validating forecast accuracy."""

    def __init__(self, db: Session):
        self.db = db
        self.store = _validation_store

    # ── Main Validation Engine ───────────────────────────────────────────

    def validate_forecast(
        self, vendor_id: int,
        predictions: List[Dict[str, Any]],
        actuals: List[Dict[str, Any]],
        period_type: ValidationPeriodType = ValidationPeriodType.DAILY,
    ) -> ValidationResult:
        """Validate forecast predictions against actuals.
        
        Args:
            vendor_id: Vendor ID
            predictions: List of predictions with period_label, predicted_orders, predicted_revenue
            actuals: List of actuals with period_label, actual_orders, actual_revenue
            period_type: Type of validation period
            
        Returns:
            ValidationResult with metrics and insights
        """
        # Build comparison pairs
        comparisons = []
        actual_map = {a["period_label"]: a for a in actuals}
        
        for pred in predictions:
            label = pred["period_label"]
            actual = actual_map.get(label)
            
            if actual:
                pred_orders = pred.get("predicted_orders", 0)
                act_orders = actual.get("actual_orders", 0)
                pred_revenue = pred.get("predicted_revenue", 0.0)
                act_revenue = actual.get("actual_revenue", 0.0)
                
                orders_acc = self._calc_accuracy(pred_orders, act_orders)
                revenue_acc = self._calc_accuracy(pred_revenue, act_revenue)
                
                comparisons.append(PredictionActualPair(
                    period_label=label,
                    period_start=actual.get("period_start", label),
                    predicted_orders=pred_orders,
                    actual_orders=act_orders,
                    predicted_revenue=pred_revenue,
                    actual_revenue=act_revenue,
                    orders_accuracy=orders_acc,
                    revenue_accuracy=revenue_acc,
                    order_error=abs(pred_orders - act_orders),
                    revenue_error=abs(pred_revenue - act_revenue),
                ))
        
        if not comparisons:
            return self._empty_result(vendor_id, period_type, "No matching prediction-actual pairs found")
        
        # Calculate metrics
        orders_metrics = self._calculate_metrics(
            "orders", comparisons,
            [c.predicted_orders for c in comparisons],
            [c.actual_orders for c in comparisons],
        )
        
        revenue_metrics = self._calculate_metrics(
            "revenue", comparisons,
            [c.predicted_revenue for c in comparisons],
            [c.actual_revenue for c in comparisons],
        )
        
        # Calculate overall accuracy
        overall_acc = (orders_metrics.prediction_accuracy + revenue_metrics.prediction_accuracy) / 2
        overall_grade = self._accuracy_to_grade(overall_acc)
        
        # Generate insights
        insights = self._generate_insights(orders_metrics, revenue_metrics, comparisons)
        recommendations = self._generate_recommendations(orders_metrics, revenue_metrics, overall_grade)
        
        # Store validation history
        self._store_validation(vendor_id, period_type, comparisons, orders_metrics, revenue_metrics)
        
        return ValidationResult(
            vendor_id=vendor_id,
            period_type=period_type,
            period_count=len(comparisons),
            generated_at=utcnow_naive().isoformat(),
            orders=orders_metrics,
            revenue=revenue_metrics,
            demand=None,
            overall_accuracy=round(overall_acc, 1),
            overall_grade=overall_grade,
            insights=insights,
            recommendations=recommendations,
        )

    def _calc_accuracy(self, predicted: float, actual: float) -> float:
        """Calculate prediction accuracy (0-100)."""
        if actual == 0:
            return 100.0 if predicted == 0 else 50.0  # Partial credit if no orders
        
        error_rate = abs(predicted - actual) / max(actual, 0.01)
        return max(0, (1 - error_rate) * 100)

    def _calculate_metrics(
        self, metric_name: str,
        comparisons: List[PredictionActualPair],
        predicted_values: List[float],
        actual_values: List[float],
    ) -> ValidationMetricResult:
        """Calculate MAPE, RMSE, and accuracy metrics."""
        n = len(comparisons)
        if n == 0:
            return ValidationMetricResult(
                metric_name=metric_name,
                mape=0, rmse=0, prediction_accuracy=0,
                mean_error=0, max_error=0, min_error=0, error_std_dev=0,
                grade=AccuracyGrade.FAIL, samples_count=0,
                comparisons=comparisons,
            )
        
        # Calculate errors
        errors = [abs(p - a) for p, a in zip(predicted_values, actual_values)]
        pct_errors = []
        for p, a in zip(predicted_values, actual_values):
            if a > 0:
                pct_errors.append(abs(p - a) / a * 100)
            else:
                pct_errors.append(0.0 if p == 0 else 100.0)
        
        # MAPE: Mean Absolute Percentage Error
        mape = sum(pct_errors) / n
        
        # RMSE: Root Mean Square Error
        squared_errors = [(p - a) ** 2 for p, a in zip(predicted_values, actual_values)]
        mse = sum(squared_errors) / n
        rmse = math.sqrt(mse)
        
        # Prediction accuracy
        accuracy_scores = []
        for c in comparisons:
            if metric_name == "orders":
                accuracy_scores.append(c.orders_accuracy)
            else:
                accuracy_scores.append(c.revenue_accuracy)
        avg_accuracy = sum(accuracy_scores) / n
        
        # Error statistics
        mean_error = sum(errors) / n
        max_error = max(errors) if errors else 0
        min_error = min(errors) if errors else 0
        
        # Standard deviation of errors
        variance = sum((e - mean_error) ** 2 for e in errors) / n
        std_dev = math.sqrt(variance)
        
        # Grade
        grade = self._accuracy_to_grade(avg_accuracy)
        
        return ValidationMetricResult(
            metric_name=metric_name,
            mape=round(mape, 2),
            rmse=round(rmse, 2),
            prediction_accuracy=round(avg_accuracy, 1),
            mean_error=round(mean_error, 2),
            max_error=round(max_error, 2),
            min_error=round(min_error, 2),
            error_std_dev=round(std_dev, 2),
            grade=grade,
            samples_count=n,
            comparisons=comparisons,
        )

    def _accuracy_to_grade(self, accuracy: float) -> AccuracyGrade:
        """Convert accuracy percentage to grade."""
        if accuracy >= 90:
            return AccuracyGrade.EXCELLENT
        elif accuracy >= 80:
            return AccuracyGrade.GOOD
        elif accuracy >= 70:
            return AccuracyGrade.FAIR
        elif accuracy >= 50:
            return AccuracyGrade.POOR
        else:
            return AccuracyGrade.FAIL

    def _empty_result(self, vendor_id: int, period_type: ValidationPeriodType, reason: str) -> ValidationResult:
        """Return empty validation result."""
        empty_metrics = ValidationMetricResult(
            metric_name="orders", mape=0, rmse=0, prediction_accuracy=0,
            mean_error=0, max_error=0, min_error=0, error_std_dev=0,
            grade=AccuracyGrade.FAIL, samples_count=0, comparisons=[],
        )
        return ValidationResult(
            vendor_id=vendor_id,
            period_type=period_type,
            period_count=0,
            generated_at=utcnow_naive().isoformat(),
            orders=empty_metrics,
            revenue=empty_metrics,
            demand=None,
            overall_accuracy=0,
            overall_grade=AccuracyGrade.FAIL,
            insights=[reason],
            recommendations=["Collect more data to start validation"],
        )

    def _store_validation(
        self, vendor_id: int, period_type: ValidationPeriodType,
        comparisons: List[PredictionActualPair],
        orders_metrics: ValidationMetricResult,
        revenue_metrics: ValidationMetricResult,
    ) -> None:
        """Store validation results in history."""
        for c in comparisons:
            entry = ValidationHistoryEntry(
                vendor_id=vendor_id,
                period_type=period_type.value,
                period_start=c.period_start,
                predicted_orders=c.predicted_orders,
                actual_orders=c.actual_orders,
                predicted_revenue=c.predicted_revenue,
                actual_revenue=c.actual_revenue,
                orders_accuracy=c.orders_accuracy,
                revenue_accuracy=c.revenue_accuracy,
                mape=orders_metrics.mape,
                rmse=orders_metrics.rmse,
            )
            self.store.store(entry)

    def _generate_insights(
        self, orders: ValidationMetricResult, revenue: ValidationMetricResult,
        comparisons: List[PredictionActualPair],
    ) -> List[str]:
        """Generate insights from validation results."""
        insights = []
        
        # Overall performance
        avg_acc = (orders.prediction_accuracy + revenue.prediction_accuracy) / 2
        insights.append(f"Overall forecast accuracy: {avg_acc:.1f}% ({orders.grade.value})")
        
        # Orders insights
        insights.append(f"Orders: MAPE={orders.mape:.1f}%, RMSE={orders.rmse:.1f}, Accuracy={orders.prediction_accuracy:.1f}%")
        
        # Revenue insights
        insights.append(f"Revenue: MAPE={revenue.mape:.1f}%, RMSE=${revenue.rmse:.2f}, Accuracy={revenue.prediction_accuracy:.1f}%")
        
        # Best/worst periods
        if comparisons:
            best = max(comparisons, key=lambda c: c.orders_accuracy)
            worst = min(comparisons, key=lambda c: c.orders_accuracy)
            insights.append(f"Best prediction: {best.period_label} ({best.orders_accuracy:.1f}% accuracy)")
            insights.append(f"Worst prediction: {worst.period_label} ({worst.orders_accuracy:.1f}% accuracy)")
        
        # Trends
        if orders.prediction_accuracy < 70:
            insights.append("Orders accuracy below 70% - model needs adjustment")
        if revenue.prediction_accuracy < 70:
            insights.append("Revenue accuracy below 70% - check pricing consistency")
        
        return insights

    def _generate_recommendations(
        self, orders: ValidationMetricResult, revenue: ValidationMetricResult,
        overall_grade: AccuracyGrade,
    ) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        if overall_grade in (AccuracyGrade.FAIL, AccuracyGrade.POOR):
            recommendations.append("URGENT: Re-train forecasting model with recent data")
            recommendations.append("Increase historical data window for better pattern detection")
        elif overall_grade == AccuracyGrade.FAIR:
            recommendations.append("Consider adding more features to improve accuracy")
            recommendations.append("Validate seasonal patterns are being captured correctly")
        else:
            recommendations.append("Forecast model is performing well - maintain regularly")
        
        if revenue.prediction_accuracy < orders.prediction_accuracy:
            recommendations.append("Revenue predictions lag behind orders - check average order value assumptions")
        
        if orders.mape > 30:
            recommendations.append(f"High MAPE ({orders.mape:.1f}%) indicates significant over/under prediction")
        
        return recommendations

    # ── Public API Methods ──────────────────────────────────────────────

    def get_validation_result(
        self, vendor_id: int, predictions: List[Dict], actuals: List[Dict],
        period_type_str: str = "daily",
    ) -> Dict[str, Any]:
        """Get validation result comparing predictions vs actuals."""
        try:
            period_type = ValidationPeriodType(period_type_str)
        except ValueError:
            period_type = ValidationPeriodType.DAILY
        
        result = self.validate_forecast(vendor_id, predictions, actuals, period_type)
        
        return self._result_to_dict(result)

    def _result_to_dict(self, result: ValidationResult) -> Dict[str, Any]:
        """Convert ValidationResult to dictionary."""
        return {
            "vendor_id": result.vendor_id,
            "period_type": result.period_type.value,
            "period_count": result.period_count,
            "generated_at": result.generated_at,
            "overall_accuracy": result.overall_accuracy,
            "overall_grade": result.overall_grade.value,
            "orders": {
                "mape": result.orders.mape,
                "rmse": result.orders.rmse,
                "prediction_accuracy": result.orders.prediction_accuracy,
                "grade": result.orders.grade.value,
                "samples": result.orders.samples_count,
                "mean_error": result.orders.mean_error,
                "max_error": result.orders.max_error,
                "min_error": result.orders.min_error,
                "error_std_dev": result.orders.error_std_dev,
            },
            "revenue": {
                "mape": result.revenue.mape,
                "rmse": result.revenue.rmse,
                "prediction_accuracy": result.revenue.prediction_accuracy,
                "grade": result.revenue.grade.value,
                "samples": result.revenue.samples_count,
                "mean_error": result.revenue.mean_error,
                "max_error": result.revenue.max_error,
                "min_error": result.revenue.min_error,
                "error_std_dev": result.revenue.error_std_dev,
            },
            "comparisons": [
                {
                    "period_label": c.period_label,
                    "predicted_orders": c.predicted_orders,
                    "actual_orders": c.actual_orders,
                    "predicted_revenue": c.predicted_revenue,
                    "actual_revenue": c.actual_revenue,
                    "orders_accuracy": c.orders_accuracy,
                    "revenue_accuracy": c.revenue_accuracy,
                }
                for c in result.orders.comparisons
            ],
            "insights": result.insights,
            "recommendations": result.recommendations,
        }

    def get_history(self, vendor_id: int, period_type: str = "daily", limit: int = 50) -> Dict[str, Any]:
        """Get validation history for vendor."""
        entries = self.store.get_history(vendor_id, period_type, limit)
        trend = self.store.get_accuracy_trend(vendor_id, period_type)
        
        return {
            "vendor_id": vendor_id,
            "period_type": period_type,
            "entries_count": len(entries),
            "entries": entries,
            "trend": trend,
        }

    def compare_with_database(
        self, vendor_id: int,
        predictions: List[Dict[str, Any]],
        days_back: int = 30,
    ) -> Dict[str, Any]:
        """Compare predictions with actual orders from database."""
        from app.modules.orders.model import Order, OrderStatus
        
        cutoff = utcnow_naive() - timedelta(days=days_back)
        
        # Get actual orders from database grouped by date
        actuals_result = self.db.query(
            func.date(Order.created_at).label("order_date"),
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("total_revenue"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= cutoff,
            Order.status != OrderStatus.CANCELLED,
        ).group_by(func.date(Order.created_at)).all()
        
        # Build actuals list
        actuals = []
        for row in actuals_result:
            actuals.append({
                "period_label": str(row.order_date),
                "period_start": str(row.order_date),
                "actual_orders": row.order_count,
                "actual_revenue": float(row.total_revenue or 0) / 100.0,  # Convert cents
            })
        
        # Build actuals map for quick lookup
        actual_map = {a["period_label"]: a for a in actuals}
        
        # Filter predictions to only those with actuals
        valid_predictions = []
        for pred in predictions:
            if pred.get("period_label") in actual_map:
                valid_predictions.append(pred)
        
        if not valid_predictions:
            return {
                "status": "no_data",
                "message": "No matching prediction-actual pairs found. Ensure predictions have period_label matching actual order dates.",
                "days_back": days_back,
                "total_orders_in_db": len(actuals),
            }
        
        # Validate
        result = self.validate_forecast(
            vendor_id, valid_predictions, actuals, ValidationPeriodType.DAILY
        )
        
        return self._result_to_dict(result)
