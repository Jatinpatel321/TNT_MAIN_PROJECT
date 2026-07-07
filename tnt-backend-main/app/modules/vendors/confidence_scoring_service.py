"""
Forecast Confidence Scoring Service
====================================

Provides comprehensive confidence scoring for all predictions:

- Confidence %: Overall confidence score (0-100%)
- Forecast Quality: Assessment of forecast reliability
- Historical Accuracy: Track prediction vs actual accuracy
- Prediction Reliability: Consistency of predictions
- Risk Level: Risk assessment for business decisions

Stores confidence history for continuous improvement.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from sqlalchemy import func, extract, and_, or_
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderStatus

logger = logging.getLogger("tnt.ai.confidence")


# ── Data Models ─────────────────────────────────────────────────────────


class ConfidenceLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ForecastQuality(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ConfidenceScore:
    """Comprehensive confidence score for a prediction."""
    confidence_percentage: float  # 0-100
    confidence_level: ConfidenceLevel
    forecast_quality: ForecastQuality
    historical_accuracy: float  # 0-100
    prediction_reliability: float  # 0-100
    risk_level: RiskLevel
    factors: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ConfidenceHistory:
    """Historical confidence tracking."""
    vendor_id: int
    forecast_type: str
    forecast_date: date
    predicted_value: int
    actual_value: int
    confidence_score: float
    accuracy: float
    error_margin: float
    created_at: datetime


# ── Confidence Scoring Service ──────────────────────────────────────────


class ConfidenceScoringService:
    """Service for calculating and tracking forecast confidence."""

    def __init__(self, db: Session):
        self.db = db
        self._confidence_cache: Dict[str, ConfidenceScore] = {}
        self._history_cache: Dict[int, List[ConfidenceHistory]] = {}

    # ── Main Confidence Calculation ──────────────────────────────────────

    def calculate_confidence(
        self,
        vendor_id: int,
        forecast_type: str,
        predicted_value: int,
        historical_data: Dict[str, Any],
        horizon_days: int = 7,
    ) -> ConfidenceScore:
        """Calculate comprehensive confidence score for a prediction.
        
        Args:
            vendor_id: Vendor ID
            forecast_type: Type of forecast (short_term, daily, weekly, monthly)
            predicted_value: Predicted value (orders, revenue, etc.)
            historical_data: Historical data used for prediction
            horizon_days: Forecast horizon in days
            
        Returns:
            ConfidenceScore with all metrics
        """
        # Calculate component scores
        confidence_pct = self._calculate_confidence_percentage(
            vendor_id, forecast_type, historical_data, horizon_days
        )
        
        forecast_quality = self._assess_forecast_quality(
            confidence_pct, historical_data
        )
        
        historical_accuracy = self._calculate_historical_accuracy(
            vendor_id, forecast_type
        )
        
        prediction_reliability = self._calculate_prediction_reliability(
            vendor_id, forecast_type, historical_data
        )
        
        risk_level = self._assess_risk_level(
            confidence_pct, historical_accuracy, prediction_reliability
        )
        
        # Generate factors and recommendations
        factors = self._generate_factors(
            confidence_pct, forecast_quality, historical_accuracy,
            prediction_reliability, historical_data
        )
        
        recommendations = self._generate_recommendations(
            confidence_pct, forecast_quality, risk_level, historical_data
        )
        
        # Determine confidence level
        if confidence_pct >= 80:
            confidence_level = ConfidenceLevel.HIGH
        elif confidence_pct >= 50:
            confidence_level = ConfidenceLevel.MEDIUM
        else:
            confidence_level = ConfidenceLevel.LOW
        
        return ConfidenceScore(
            confidence_percentage=round(confidence_pct, 1),
            confidence_level=confidence_level,
            forecast_quality=forecast_quality,
            historical_accuracy=round(historical_accuracy, 1),
            prediction_reliability=round(prediction_reliability, 1),
            risk_level=risk_level,
            factors=factors,
            recommendations=recommendations,
        )

    def _calculate_confidence_percentage(
        self,
        vendor_id: int,
        forecast_type: str,
        historical_data: Dict[str, Any],
        horizon_days: int,
    ) -> float:
        """Calculate overall confidence percentage."""
        base_confidence = 0.5
        
        # Factor 1: Data availability (0-25 points)
        data_score = self._score_data_availability(vendor_id, forecast_type)
        base_confidence += data_score * 0.25
        
        # Factor 2: Historical consistency (0-20 points)
        consistency_score = self._score_historical_consistency(vendor_id, forecast_type)
        base_confidence += consistency_score * 0.20
        
        # Factor 3: Pattern strength (0-20 points)
        pattern_score = self._score_pattern_strength(historical_data)
        base_confidence += pattern_score * 0.20
        
        # Factor 4: Horizon distance (0-15 points, decreases with distance)
        horizon_score = max(0, 1 - (horizon_days / 365)) * 0.15
        base_confidence += horizon_score
        
        # Factor 5: Sample size (0-20 points)
        sample_score = self._score_sample_size(vendor_id, forecast_type)
        base_confidence += sample_score * 0.20
        
        return min(0.95, max(0.1, base_confidence)) * 100

    def _score_data_availability(self, vendor_id: int, forecast_type: str) -> float:
        """Score data availability (0-1)."""
        now = utcnow_naive()
        
        # Determine lookback period based on forecast type
        if forecast_type == "short_term":
            lookback = timedelta(days=30)
        elif forecast_type == "daily":
            lookback = timedelta(days=90)
        elif forecast_type == "weekly":
            lookback = timedelta(days=180)
        else:  # monthly
            lookback = timedelta(days=365)
        
        cutoff = now - lookback
        
        # Count data points
        data_points = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= cutoff,
            Order.status != OrderStatus.CANCELLED,
        ).scalar() or 0
        
        # Score based on data points
        if data_points >= 100:
            return 1.0
        elif data_points >= 50:
            return 0.8
        elif data_points >= 20:
            return 0.6
        elif data_points >= 10:
            return 0.4
        else:
            return 0.2

    def _score_historical_consistency(self, vendor_id: int, forecast_type: str) -> float:
        """Score historical consistency (0-1)."""
        now = utcnow_naive()
        
        # Get recent orders
        if forecast_type in ["short_term", "daily"]:
            cutoff = now - timedelta(days=30)
            orders = self.db.query(
                func.date(Order.created_at).label("order_date"),
                func.count(Order.id).label("order_count"),
            ).filter(
                Order.vendor_id == vendor_id,
                Order.created_at >= cutoff,
                Order.status != OrderStatus.CANCELLED,
            ).group_by(func.date(Order.created_at)).all()
            
            if not orders:
                return 0.0
            
            counts = [row.order_count for row in orders]
            avg = sum(counts) / len(counts)
            
            if avg == 0:
                return 0.0
            
            # Calculate coefficient of variation (lower = more consistent)
            variance = sum((c - avg) ** 2 for c in counts) / len(counts)
            std_dev = variance ** 0.5
            cv = std_dev / avg
            
            # Score: lower CV = higher score
            if cv < 0.3:
                return 1.0
            elif cv < 0.5:
                return 0.8
            elif cv < 0.8:
                return 0.6
            elif cv < 1.2:
                return 0.4
            else:
                return 0.2
        
        return 0.7  # Default for weekly/monthly

    def _score_pattern_strength(self, historical_data: Dict[str, Any]) -> float:
        """Score pattern strength (0-1)."""
        # Check if clear patterns exist
        patterns = historical_data.get("patterns", [])
        
        if not patterns:
            return 0.3
        
        # Count strong patterns
        strong_patterns = 0
        for pattern in patterns:
            # Check for day-of-week patterns with clear peaks/lows
            if pattern.get("type") == "day_of_week":
                vs_avg = abs(pattern.get("vs_overall_avg", 0))
                if vs_avg > 30:  # >30% deviation
                    strong_patterns += 1
        
        # Score based on pattern strength
        if strong_patterns >= 3:
            return 1.0
        elif strong_patterns >= 2:
            return 0.8
        elif strong_patterns >= 1:
            return 0.6
        else:
            return 0.4

    def _score_sample_size(self, vendor_id: int, forecast_type: str) -> float:
        """Score sample size (0-1)."""
        now = utcnow_naive()
        
        # Determine minimum required samples
        if forecast_type == "short_term":
            min_samples = 30  # 30 days of hourly data
        elif forecast_type == "daily":
            min_samples = 30  # 30 days
        elif forecast_type == "weekly":
            min_samples = 12  # 12 weeks
        else:  # monthly
            min_samples = 6  # 6 months
        
        # Count actual samples
        cutoff = now - timedelta(days=min_samples * 7)
        samples = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= cutoff,
            Order.status != OrderStatus.CANCELLED,
        ).scalar() or 0
        
        # Score
        if samples >= min_samples * 2:
            return 1.0
        elif samples >= min_samples:
            return 0.8
        elif samples >= min_samples // 2:
            return 0.6
        elif samples >= min_samples // 4:
            return 0.4
        else:
            return 0.2

    def _assess_forecast_quality(
        self, confidence_pct: float, historical_data: Dict[str, Any]
    ) -> ForecastQuality:
        """Assess forecast quality."""
        # Check data completeness
        has_patterns = len(historical_data.get("patterns", [])) > 0
        has_sufficient_data = historical_data.get("sample_size", 0) >= 30
        
        # Calculate quality score
        quality_score = confidence_pct / 100
        
        if quality_score >= 0.85 and has_patterns and has_sufficient_data:
            return ForecastQuality.EXCELLENT
        elif quality_score >= 0.70 and has_patterns:
            return ForecastQuality.GOOD
        elif quality_score >= 0.50:
            return ForecastQuality.FAIR
        else:
            return ForecastQuality.POOR

    def _calculate_historical_accuracy(self, vendor_id: int, forecast_type: str) -> float:
        """Calculate historical accuracy from past predictions."""
        # Get recent confidence history
        recent_history = self._get_recent_history(vendor_id, forecast_type, limit=10)
        
        if not recent_history:
            return 75.0  # Default moderate accuracy
        
        # Calculate average accuracy
        accuracies = [h.accuracy for h in recent_history]
        avg_accuracy = sum(accuracies) / len(accuracies)
        
        return avg_accuracy

    def _calculate_prediction_reliability(
        self, vendor_id: int, forecast_type: str, historical_data: Dict[str, Any]
    ) -> float:
        """Calculate prediction reliability."""
        # Get recent history
        recent_history = self._get_recent_history(vendor_id, forecast_type, limit=5)
        
        if not recent_history:
            return 70.0  # Default moderate reliability
        
        # Calculate consistency (lower variance = higher reliability)
        errors = [abs(h.error_margin) for h in recent_history]
        avg_error = sum(errors) / len(errors)
        
        if avg_error == 0:
            return 100.0
        
        # Calculate coefficient of variation
        variance = sum((e - avg_error) ** 2 for e in errors) / len(errors)
        std_dev = variance ** 0.5
        cv = std_dev / avg_error if avg_error > 0 else 0
        
        # Score: lower CV = higher reliability
        if cv < 0.2:
            return 95.0
        elif cv < 0.4:
            return 85.0
        elif cv < 0.6:
            return 75.0
        elif cv < 0.8:
            return 65.0
        else:
            return 55.0

    def _assess_risk_level(
        self,
        confidence_pct: float,
        historical_accuracy: float,
        prediction_reliability: float,
    ) -> RiskLevel:
        """Assess risk level for business decisions."""
        # Calculate composite risk score
        risk_score = (
            (100 - confidence_pct) * 0.4 +
            (100 - historical_accuracy) * 0.3 +
            (100 - prediction_reliability) * 0.3
        )
        
        if risk_score < 20:
            return RiskLevel.LOW
        elif risk_score < 40:
            return RiskLevel.MEDIUM
        elif risk_score < 60:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _generate_factors(
        self,
        confidence_pct: float,
        forecast_quality: ForecastQuality,
        historical_accuracy: float,
        prediction_reliability: float,
        historical_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate detailed factors affecting confidence."""
        factors = {
            "data_quality": {
                "score": round(confidence_pct, 1),
                "sample_size": historical_data.get("sample_size", 0),
                "data_completeness": "high" if historical_data.get("sample_size", 0) >= 30 else "medium" if historical_data.get("sample_size", 0) >= 10 else "low",
            },
            "pattern_stability": {
                "score": round(historical_accuracy, 1),
                "patterns_detected": len(historical_data.get("patterns", [])),
                "trend_direction": historical_data.get("trend", "stable"),
            },
            "prediction_consistency": {
                "score": round(prediction_reliability, 1),
                "volatility": "low" if prediction_reliability >= 80 else "medium" if prediction_reliability >= 60 else "high",
            },
            "forecast_quality": {
                "rating": forecast_quality.value,
                "description": self._get_quality_description(forecast_quality),
            },
        }
        
        return factors

    def _generate_recommendations(
        self,
        confidence_pct: float,
        forecast_quality: ForecastQuality,
        risk_level: RiskLevel,
        historical_data: Dict[str, Any],
    ) -> List[str]:
        """Generate recommendations based on confidence analysis."""
        recommendations = []
        
        # Confidence-based recommendations
        if confidence_pct < 50:
            recommendations.append(
                "Low confidence: Consider gathering more historical data before making critical decisions"
            )
        elif confidence_pct < 70:
            recommendations.append(
                "Medium confidence: Use forecast as guidance but validate with additional data"
            )
        else:
            recommendations.append(
                "High confidence: Forecast is reliable for planning purposes"
            )
        
        # Quality-based recommendations
        if forecast_quality == ForecastQuality.POOR:
            recommendations.append(
                "Poor forecast quality: Consider manual review or alternative forecasting methods"
            )
        elif forecast_quality == ForecastQuality.FAIR:
            recommendations.append(
                "Fair forecast quality: Monitor actual results closely and adjust as needed"
            )
        
        # Risk-based recommendations
        if risk_level == RiskLevel.CRITICAL:
            recommendations.append(
                "Critical risk level: Avoid making major business decisions based on this forecast"
            )
        elif risk_level == RiskLevel.HIGH:
            recommendations.append(
                "High risk level: Use forecast with caution and have contingency plans ready"
            )
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.append(
                "Medium risk level: Forecast is usable but should be validated regularly"
            )
        
        # Data-based recommendations
        sample_size = historical_data.get("sample_size", 0)
        if sample_size < 30:
            recommendations.append(
                f"Insufficient data ({sample_size} samples): Collect at least 30 days of data for better accuracy"
            )
        
        return recommendations

    def _get_quality_description(self, quality: ForecastQuality) -> str:
        """Get description for forecast quality."""
        descriptions = {
            ForecastQuality.EXCELLENT: "Forecast is highly reliable with strong historical backing",
            ForecastQuality.GOOD: "Forecast is reliable with good historical support",
            ForecastQuality.FAIR: "Forecast is moderately reliable, use with some caution",
            ForecastQuality.POOR: "Forecast has limited reliability, consider alternative methods",
        }
        return descriptions.get(quality, "Unknown quality")

    # ── Confidence History Tracking ──────────────────────────────────────

    def record_prediction(
        self,
        vendor_id: int,
        forecast_type: str,
        forecast_date: date,
        predicted_value: int,
        confidence_score: float,
    ) -> None:
        """Record a prediction for future accuracy tracking."""
        # This would be called when a forecast is generated
        # The actual value will be updated later when data becomes available
        pass

    def update_actual_value(
        self,
        vendor_id: int,
        forecast_type: str,
        forecast_date: date,
        actual_value: int,
    ) -> Optional[ConfidenceHistory]:
        """Update prediction with actual value and calculate accuracy."""
        # Find the prediction record
        history = self.db.query(ConfidenceHistory).filter(
            ConfidenceHistory.vendor_id == vendor_id,
            ConfidenceHistory.forecast_type == forecast_type,
            ConfidenceHistory.forecast_date == forecast_date,
        ).first()
        
        if not history:
            return None
        
        # Update actual value and calculate metrics
        history.actual_value = actual_value
        history.accuracy = self._calculate_accuracy(
            history.predicted_value, actual_value
        )
        history.error_margin = abs(history.predicted_value - actual_value)
        
        self.db.commit()
        
        return history

    def _calculate_accuracy(self, predicted: int, actual: int) -> float:
        """Calculate prediction accuracy."""
        if actual == 0:
            return 100.0 if predicted == 0 else 0.0
        
        error_rate = abs(predicted - actual) / actual
        accuracy = max(0, (1 - error_rate) * 100)
        
        return accuracy

    def _get_recent_history(
        self, vendor_id: int, forecast_type: str, limit: int = 10
    ) -> List[ConfidenceHistory]:
        """Get recent confidence history."""
        return self.db.query(ConfidenceHistory).filter(
            ConfidenceHistory.vendor_id == vendor_id,
            ConfidenceHistory.forecast_type == forecast_type,
            ConfidenceHistory.actual_value.isnot(None),
        ).order_by(ConfidenceHistory.created_at.desc()).limit(limit).all()

    # ── Public API ────────────────────────────────────────────────────────

    def get_confidence_report(self, vendor_id: int, forecast_type: str) -> Dict[str, Any]:
        """Get comprehensive confidence report for a forecast type."""
        # Get recent history
        recent_history = self._get_recent_history(vendor_id, forecast_type, limit=20)
        
        if not recent_history:
            return {
                "vendor_id": vendor_id,
                "forecast_type": forecast_type,
                "status": "insufficient_data",
                "message": "No prediction history available yet",
                "recommendation": "Generate more forecasts to build confidence history",
            }
        
        # Calculate statistics
        accuracies = [h.accuracy for h in recent_history]
        error_margins = [h.error_margin for h in recent_history]
        
        avg_accuracy = sum(accuracies) / len(accuracies)
        avg_error = sum(error_margins) / len(error_margins)
        
        # Calculate trend
        if len(accuracies) >= 5:
            recent_avg = sum(accuracies[:5]) / 5
            older_avg = sum(accuracies[5:]) / len(accuracies[5:])
            trend = "improving" if recent_avg > older_avg else "declining" if recent_avg < older_avg else "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "vendor_id": vendor_id,
            "forecast_type": forecast_type,
            "status": "active",
            "total_predictions": len(recent_history),
            "average_accuracy": round(avg_accuracy, 1),
            "average_error_margin": round(avg_error, 1),
            "accuracy_trend": trend,
            "best_accuracy": round(max(accuracies), 1),
            "worst_accuracy": round(min(accuracies), 1),
            "recent_predictions": [
                {
                    "date": h.forecast_date.isoformat(),
                    "predicted": h.predicted_value,
                    "actual": h.actual_value,
                    "accuracy": round(h.accuracy, 1),
                    "error_margin": h.error_margin,
                }
                for h in recent_history[:10]
            ],
            "insights": self._generate_accuracy_insights(
                avg_accuracy, trend, error_margins
            ),
        }

    def _generate_accuracy_insights(
        self, avg_accuracy: float, trend: str, error_margins: List[int]
    ) -> List[str]:
        """Generate insights from accuracy analysis."""
        insights = []
        
        # Overall accuracy
        if avg_accuracy >= 90:
            insights.append("Excellent prediction accuracy (>90%)")
        elif avg_accuracy >= 75:
            insights.append("Good prediction accuracy (75-90%)")
        elif avg_accuracy >= 60:
            insights.append("Fair prediction accuracy (60-75%)")
        else:
            insights.append("Poor prediction accuracy (<60%) - model needs improvement")
        
        # Trend
        if trend == "improving":
            insights.append("Accuracy is improving over time")
        elif trend == "declining":
            insights.append("Accuracy is declining - investigate recent changes")
        
        # Error analysis
        avg_error = sum(error_margins) / len(error_margins) if error_margins else 0
        if avg_error > 20:
            insights.append(f"High average error margin ({avg_error:.1f}) - predictions may be unreliable")
        elif avg_error > 10:
            insights.append(f"Moderate error margin ({avg_error:.1f}) - acceptable for planning")
        else:
            insights.append(f"Low error margin ({avg_error:.1f}) - predictions are precise")
        
        return insights

    def get_overall_confidence_summary(self, vendor_id: int) -> Dict[str, Any]:
        """Get overall confidence summary across all forecast types."""
        forecast_types = ["short_term", "daily", "weekly", "monthly"]
        
        summaries = {}
        for forecast_type in forecast_types:
            report = self.get_confidence_report(vendor_id, forecast_type)
            summaries[forecast_type] = {
                "average_accuracy": report.get("average_accuracy", 0),
                "total_predictions": report.get("total_predictions", 0),
                "accuracy_trend": report.get("accuracy_trend", "no_data"),
            }
        
        # Calculate overall score
        total_predictions = sum(s["total_predictions"] for s in summaries.values())
        if total_predictions > 0:
            overall_accuracy = sum(
                s["average_accuracy"] * s["total_predictions"] for s in summaries.values()
            ) / total_predictions
        else:
            overall_accuracy = 0.0
        
        return {
            "vendor_id": vendor_id,
            "overall_accuracy": round(overall_accuracy, 1),
            "total_predictions": total_predictions,
            "by_forecast_type": summaries,
            "overall_rating": self._get_overall_rating(overall_accuracy),
            "recommendations": self._get_overall_recommendations(summaries),
        }

    def _get_overall_rating(self, accuracy: float) -> str:
        """Get overall rating based on accuracy."""
        if accuracy >= 90:
            return "excellent"
        elif accuracy >= 75:
            return "good"
        elif accuracy >= 60:
            return "fair"
        else:
            return "poor"

    def _get_overall_recommendations(self, summaries: Dict[str, Any]) -> List[str]:
        """Generate overall recommendations."""
        recommendations = []
        
        # Check for low accuracy
        low_accuracy_types = [
            ft for ft, data in summaries.items()
            if data["average_accuracy"] < 60 and data["total_predictions"] > 0
        ]
        
        if low_accuracy_types:
            recommendations.append(
                f"Improve accuracy for: {', '.join(low_accuracy_types)}"
            )
        
        # Check for insufficient data
        no_data_types = [
            ft for ft, data in summaries.items()
            if data["total_predictions"] == 0
        ]
        
        if no_data_types:
            recommendations.append(
                f"Generate predictions for: {', '.join(no_data_types)} to build confidence history"
            )
        
        # Check for declining trends
        declining_types = [
            ft for ft, data in summaries.items()
            if data["accuracy_trend"] == "declining"
        ]
        
        if declining_types:
            recommendations.append(
                f"Investigate declining accuracy in: {', '.join(declining_types)}"
            )
        
        if not recommendations:
            recommendations.append("Forecast confidence is good across all types")
        
        return recommendations

    # ── Helper Methods ────────────────────────────────────────────────────

    def get_confidence_level_details(self, level: ConfidenceLevel) -> Dict[str, Any]:
        """Get details for a confidence level."""
        details = {
            ConfidenceLevel.HIGH: {
                "label": "High Confidence",
                "color": "#10B981",
                "description": "Forecast is highly reliable for planning",
                "icon": "✓",
                "min_percentage": 80,
            },
            ConfidenceLevel.MEDIUM: {
                "label": "Medium Confidence",
                "color": "#F59E0B",
                "description": "Forecast is reasonably reliable with some uncertainty",
                "icon": "~",
                "min_percentage": 50,
            },
            ConfidenceLevel.LOW: {
                "label": "Low Confidence",
                "color": "#EF4444",
                "description": "Forecast has high uncertainty, use with caution",
                "icon": "!",
                "min_percentage": 0,
            },
        }
        return details.get(level, {})

    def get_risk_level_details(self, level: RiskLevel) -> Dict[str, Any]:
        """Get details for a risk level."""
        details = {
            RiskLevel.LOW: {
                "label": "Low Risk",
                "color": "#10B981",
                "description": "Safe to use for business decisions",
                "min_score": 0,
            },
            RiskLevel.MEDIUM: {
                "label": "Medium Risk",
                "color": "#F59E0B",
                "description": "Use with standard precautions",
                "min_score": 20,
            },
            RiskLevel.HIGH: {
                "label": "High Risk",
                "color": "#F97316",
                "description": "Use with caution, have contingency plans",
                "min_score": 40,
            },
            RiskLevel.CRITICAL: {
                "label": "Critical Risk",
                "color": "#EF4444",
                "description": "Avoid major decisions based on this forecast",
                "min_score": 60,
            },
        }
        return details.get(level, {})
