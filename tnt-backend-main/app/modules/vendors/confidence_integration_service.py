"""
Confidence Integration Service
===============================

Integrates confidence scoring with existing forecasting services.
"""

from __future__ import annotations

from typing import Any, Dict

from app.modules.vendors.confidence_scoring_service import ConfidenceScoringService
from app.modules.vendors.enhanced_forecasting_service import EnhancedForecastingService


class ConfidenceIntegrationService:
    """Service to integrate confidence scoring with forecasting."""

    def __init__(self, db):
        self.db = db
        self.forecasting_service = EnhancedForecastingService(db)
        self.confidence_service = ConfidenceScoringService(db)

    def get_forecast_with_confidence(self, vendor_id: int, forecast_type: str, **kwargs) -> Dict[str, Any]:
        """Get forecast with integrated confidence scoring.
        
        Args:
            vendor_id: Vendor ID
            forecast_type: Type of forecast (short_term, daily, weekly, monthly)
            **kwargs: Additional arguments for forecast method
            
        Returns:
            Forecast data with integrated confidence scores
        """
        # Get forecast based on type
        if forecast_type == "short_term":
            forecast = self.forecasting_service.forecast_short_term(vendor_id)
            predicted_value = forecast.get("total_orders", 0)
            horizon_days = 1
        elif forecast_type == "daily":
            days = kwargs.get("days", 7)
            forecast = self.forecasting_service.forecast_daily(vendor_id, days=days)
            predicted_value = forecast.get("summary", {}).get("total_orders", 0)
            horizon_days = days
        elif forecast_type == "weekly":
            weeks = kwargs.get("weeks", 4)
            forecast = self.forecasting_service.forecast_weekly(vendor_id, weeks=weeks)
            predicted_value = forecast.get("summary", {}).get("total_orders", 0)
            horizon_days = weeks * 7
        elif forecast_type == "monthly":
            months = kwargs.get("months", 3)
            forecast = self.forecasting_service.forecast_monthly(vendor_id, months=months)
            predicted_value = forecast.get("summary", {}).get("total_orders", 0)
            horizon_days = months * 30
        else:
            raise ValueError(f"Unknown forecast type: {forecast_type}")
        
        # Get historical data from forecast
        historical_data = {
            "sample_size": forecast.get("confidence", 0.5) * 100,
            "patterns": [],
            "trend": forecast.get("trend", "stable"),
        }
        
        # Calculate confidence score
        confidence_score = self.confidence_service.calculate_confidence(
            vendor_id=vendor_id,
            forecast_type=forecast_type,
            predicted_value=predicted_value,
            historical_data=historical_data,
            horizon_days=horizon_days,
        )
        
        # Integrate confidence into forecast
        forecast["confidence_score"] = {
            "confidence_percentage": confidence_score.confidence_percentage,
            "confidence_level": confidence_score.confidence_level.value,
            "forecast_quality": confidence_score.forecast_quality.value,
            "historical_accuracy": confidence_score.historical_accuracy,
            "prediction_reliability": confidence_score.prediction_reliability,
            "risk_level": confidence_score.risk_level.value,
            "factors": confidence_score.factors,
            "recommendations": confidence_score.recommendations,
        }
        
        return forecast

    def get_comprehensive_forecast_with_confidence(self, vendor_id: int) -> Dict[str, Any]:
        """Get comprehensive forecast with confidence for all horizons."""
        result = {
            "vendor_id": vendor_id,
            "short_term": self.get_forecast_with_confidence(vendor_id, "short_term"),
            "daily": self.get_forecast_with_confidence(vendor_id, "daily", days=7),
            "weekly": self.get_forecast_with_confidence(vendor_id, "weekly", weeks=4),
            "monthly": self.get_forecast_with_confidence(vendor_id, "monthly", months=3),
        }
        
        # Generate insights
        result["insights"] = self._generate_confidence_insights(result)
        
        return result

    def _generate_confidence_insights(self, forecast_data: Dict[str, Any]) -> list:
        """Generate insights based on confidence scores."""
        insights = []
        
        # Check each horizon
        for horizon in ["short_term", "daily", "weekly", "monthly"]:
            confidence = forecast_data.get(horizon, {}).get("confidence_score", {})
            if not confidence:
                continue
            
            level = confidence.get("confidence_level", "unknown")
            quality = confidence.get("forecast_quality", "unknown")
            risk = confidence.get("risk_level", "unknown")
            
            # Add horizon-specific insights
            if horizon == "short_term":
                insights.append(
                    f"Short-term forecast: {confidence.get('confidence_percentage', 0)}% confidence ({level})"
                )
            elif horizon == "daily":
                insights.append(
                    f"Daily forecast quality: {quality} ({confidence.get('confidence_percentage', 0)}% confidence)"
                )
            elif horizon == "weekly":
                trend = forecast_data.get(horizon, {}).get("trend", "stable")
                insights.append(
                    f"Weekly trend: {trend} with {confidence.get('confidence_percentage', 0)}% confidence"
                )
            elif horizon == "monthly":
                yoy = forecast_data.get(horizon, {}).get("yoy_growth", 0)
                insights.append(
                    f"Monthly YoY growth: {yoy*100:.1f}% (Risk: {risk})"
                )
        
        # Add overall recommendations
        recommendations = []
        for horizon in ["short_term", "daily", "weekly", "monthly"]:
            confidence = forecast_data.get(horizon, {}).get("confidence_score", {})
            if confidence:
                recommendations.extend(confidence.get("recommendations", [])[:1])
        
        if recommendations:
            insights.append("Top recommendation: " + recommendations[0])
        
        return insights
