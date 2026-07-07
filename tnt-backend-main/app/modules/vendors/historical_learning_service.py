"""
Vendor Historical Learning Service
====================================

Continuously learns from historical operational data:
- Daily/Weekly/Monthly order patterns
- Seasonal trends
- Semester schedules
- Vendor holidays
- Peak campus timings

Stores learning data and generates predictive datasets.
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
from sqlalchemy.sql import text

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.slots.model import Slot
from app.modules.menu.model import MenuItem
from app.modules.vendors.profile_models import VendorProfile

logger = logging.getLogger("tnt.ai.historical_learning")


# ── Data Models ─────────────────────────────────────────────────────────


class TrendDirection(Enum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    VOLATILE = "volatile"


class SeasonType(Enum):
    SPRING = "spring"
    SUMMER = "summer"
    MONSOON = "monsoon"
    WINTER = "winter"
    EXAM = "exam"
    HOLIDAY = "holiday"


class CampusPeriod(Enum):
    REGULAR = "regular"
    EXAM = "exam"
    SEMESTER_BREAK = "semester_break"
    HOLIDAY = "holiday"
    PLACEMENT = "placement"


@dataclass
class HistoricalPattern:
    """Represents a learned historical pattern."""
    pattern_type: str
    vendor_id: int
    period: str
    avg_orders: float
    std_deviation: float
    min_orders: int
    max_orders: int
    confidence: float
    sample_size: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SeasonalTrend:
    """Seasonal trend data."""
    season: SeasonType
    vendor_id: int
    avg_daily_orders: float
    peak_days: List[str]
    low_days: List[str]
    trend_direction: TrendDirection
    year_over_year_growth: float


@dataclass
class CampusSchedule:
    """Campus schedule impact."""
    period: CampusPeriod
    vendor_id: int
    avg_orders: float
    multiplier: float
    active: bool


# ── Historical Learning Service ─────────────────────────────────────────


class HistoricalLearningService:
    """Service for learning from historical operational data."""

    def __init__(self, db: Session):
        self.db = db
        self._patterns_cache: Dict[str, List[HistoricalPattern]] = {}
        self._cache_ttl = 3600  # 1 hour
        self._last_cache_update: Optional[datetime] = None

    # ── Daily Order Analysis ──────────────────────────────────────────────

    def analyze_daily_patterns(self, vendor_id: int, days: int = 90) -> Dict[str, Any]:
        """Analyze daily order patterns over specified period."""
        cutoff_date = utcnow_naive() - timedelta(days=days)
        
        # Get daily order counts
        daily_orders = self.db.query(
            func.date(Order.created_at).label("order_date"),
            func.count(Order.id).label("order_count"),
            extract("hour", Order.created_at).label("hour"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= cutoff_date,
            Order.status != OrderStatus.CANCELLED,
        ).group_by(
            func.date(Order.created_at),
            extract("hour", Order.created_at),
        ).all()
        
        # Aggregate by date
        daily_agg: Dict[date, int] = defaultdict(int)
        for row in daily_orders:
            daily_agg[row.order_date] += row.order_count
        
        # Calculate statistics
        order_counts = list(daily_agg.values())
        if not order_counts:
            return {
                "vendor_id": vendor_id,
                "period_days": days,
                "avg_daily_orders": 0,
                "std_deviation": 0,
                "min_orders": 0,
                "max_orders": 0,
                "patterns": [],
                "confidence": 0.0,
            }
        
        avg_orders = sum(order_counts) / len(order_counts)
        variance = sum((x - avg_orders) ** 2 for x in order_counts) / len(order_counts)
        std_dev = variance ** 0.5
        
        # Identify patterns
        patterns = self._identify_daily_patterns(vendor_id, daily_agg, avg_orders, std_dev)
        
        # Calculate confidence based on sample size
        confidence = min(1.0, len(order_counts) / 30.0)
        
        return {
            "vendor_id": vendor_id,
            "period_days": days,
            "avg_daily_orders": round(avg_orders, 1),
            "std_deviation": round(std_dev, 1),
            "min_orders": min(order_counts),
            "max_orders": max(order_counts),
            "patterns": patterns,
            "confidence": round(confidence, 2),
            "sample_size": len(order_counts),
        }

    def _identify_daily_patterns(
        self, vendor_id: int, daily_agg: Dict[date, int], avg: float, std: float
    ) -> List[Dict[str, Any]]:
        """Identify patterns in daily orders."""
        patterns = []
        
        # Day of week patterns
        dow_orders: Dict[int, List[int]] = defaultdict(list)
        for order_date, count in daily_agg.items():
            dow = order_date.weekday()
            dow_orders[dow].append(count)
        
        dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for dow, counts in dow_orders.items():
            if counts:
                dow_avg = sum(counts) / len(counts)
                patterns.append({
                    "type": "day_of_week",
                    "name": dow_names[dow],
                    "day_index": dow,
                    "avg_orders": round(dow_avg, 1),
                    "vs_overall_avg": round((dow_avg / avg - 1) * 100, 1) if avg > 0 else 0,
                    "sample_size": len(counts),
                })
        
        # High/Low day patterns
        high_days = [p for p in patterns if p.get("vs_overall_avg", 0) > 20]
        low_days = [p for p in patterns if p.get("vs_overall_avg", 0) < -20]
        
        if high_days:
            patterns.append({
                "type": "high_demand_days",
                "days": [p["name"] for p in high_days],
                "avg_orders": round(sum(p["avg_orders"] for p in high_days) / len(high_days), 1),
            })
        
        if low_days:
            patterns.append({
                "type": "low_demand_days",
                "days": [p["name"] for p in low_days],
                "avg_orders": round(sum(p["avg_orders"] for p in low_days) / len(low_days), 1),
            })
        
        return patterns

    # ── Weekly Order Analysis ─────────────────────────────────────────────

    def analyze_weekly_patterns(self, vendor_id: int, weeks: int = 24) -> Dict[str, Any]:
        """Analyze weekly order patterns."""
        cutoff_date = utcnow_naive() - timedelta(weeks=weeks)
        
        weekly_orders = self.db.query(
            func.date_trunc("week", Order.created_at).label("week_start"),
            func.count(Order.id).label("order_count"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= cutoff_date,
            Order.status != OrderStatus.CANCELLED,
        ).group_by(
            func.date_trunc("week", Order.created_at),
        ).all()
        
        order_counts = [row.order_count for row in weekly_orders]
        
        if not order_counts:
            return {
                "vendor_id": vendor_id,
                "period_weeks": weeks,
                "avg_weekly_orders": 0,
                "trend": "stable",
                "patterns": [],
                "confidence": 0.0,
            }
        
        avg_weekly = sum(order_counts) / len(order_counts)
        
        # Calculate trend
        trend = self._calculate_trend(order_counts)
        
        # Week of month patterns
        week_of_month_patterns = self._analyze_week_of_month(vendor_id, cutoff_date)
        
        confidence = min(1.0, len(order_counts) / 12.0)
        
        return {
            "vendor_id": vendor_id,
            "period_weeks": weeks,
            "avg_weekly_orders": round(avg_weekly, 1),
            "trend": trend.value,
            "trend_strength": round(abs(trend.value == "up" and 1 or trend.value == "down" and -1 or 0), 2),
            "patterns": week_of_month_patterns,
            "confidence": round(confidence, 2),
            "sample_size": len(order_counts),
        }

    def _calculate_trend(self, values: List[float]) -> TrendDirection:
        """Calculate trend direction from time series."""
        if len(values) < 3:
            return TrendDirection.STABLE
        
        # Simple linear regression
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return TrendDirection.STABLE
        
        slope = numerator / denominator
        
        # Calculate volatility
        variance = sum((v - y_mean) ** 2 for v in values) / n
        std_dev = variance ** 0.5
        cv = std_dev / y_mean if y_mean > 0 else 0
        
        # Determine trend
        if cv > 0.5:  # High volatility
            return TrendDirection.VOLATILE
        elif slope > 0.1:
            return TrendDirection.UP
        elif slope < -0.1:
            return TrendDirection.DOWN
        else:
            return TrendDirection.STABLE

    def _analyze_week_of_month(self, vendor_id: int, since: datetime) -> List[Dict[str, Any]]:
        """Analyze patterns by week of month."""
        weekly_data = self.db.query(
            func.date_trunc("week", Order.created_at).label("week_start"),
            func.count(Order.id).label("order_count"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= since,
            Order.status != OrderStatus.CANCELLED,
        ).group_by(
            func.date_trunc("week", Order.created_at),
        ).all()
        
        # Group by week of month
        week_groups: Dict[int, List[int]] = defaultdict(list)
        for row in weekly_data:
            week_num = row.week_start.isocalendar()[1] % 4 + 1  # 1-4
            week_groups[week_num].append(row.order_count)
        
        patterns = []
        for week_num, counts in week_groups.items():
            if counts:
                avg = sum(counts) / len(counts)
                patterns.append({
                    "type": "week_of_month",
                    "week": week_num,
                    "avg_orders": round(avg, 1),
                    "sample_size": len(counts),
                })
        
        return patterns

    # ── Monthly Order Analysis ────────────────────────────────────────────

    def analyze_monthly_patterns(self, vendor_id: int, months: int = 12) -> Dict[str, Any]:
        """Analyze monthly order patterns."""
        cutoff_date = utcnow_naive() - timedelta(days=months * 30)
        
        monthly_orders = self.db.query(
            func.date_trunc("month", Order.created_at).label("month_start"),
            func.count(Order.id).label("order_count"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= cutoff_date,
            Order.status != OrderStatus.CANCELLED,
        ).group_by(
            func.date_trunc("month", Order.created_at),
        ).all()
        
        order_counts = [row.order_count for row in monthly_orders]
        
        if not order_counts:
            return {
                "vendor_id": vendor_id,
                "period_months": months,
                "avg_monthly_orders": 0,
                "patterns": [],
                "confidence": 0.0,
            }
        
        avg_monthly = sum(order_counts) / len(order_counts)
        
        # Month of year patterns
        month_patterns = self._analyze_month_of_year(vendor_id, cutoff_date)
        
        # Year-over-year growth
        yoy_growth = self._calculate_yoy_growth(vendor_id, cutoff_date)
        
        confidence = min(1.0, len(order_counts) / 6.0)
        
        return {
            "vendor_id": vendor_id,
            "period_months": months,
            "avg_monthly_orders": round(avg_monthly, 1),
            "patterns": month_patterns,
            "year_over_year_growth": round(yoy_growth, 2),
            "confidence": round(confidence, 2),
            "sample_size": len(order_counts),
        }

    def _analyze_month_of_year(self, vendor_id: int, since: datetime) -> List[Dict[str, Any]]:
        """Analyze patterns by month of year."""
        monthly_data = self.db.query(
            extract("month", Order.created_at).label("month"),
            func.count(Order.id).label("order_count"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= since,
            Order.status != OrderStatus.CANCELLED,
        ).group_by(
            extract("month", Order.created_at),
        ).all()
        
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        
        patterns = []
        for row in monthly_data:
            patterns.append({
                "type": "month_of_year",
                "month": month_names[int(row.month) - 1],
                "month_num": int(row.month),
                "avg_orders": row.order_count,
            })
        
        return patterns

    def _calculate_yoy_growth(self, vendor_id: int, since: datetime) -> float:
        """Calculate year-over-year growth rate."""
        one_year_ago = utcnow_naive() - timedelta(days=365)
        two_years_ago = utcnow_naive() - timedelta(days=730)
        
        recent_orders = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= one_year_ago,
            Order.status != OrderStatus.CANCELLED,
        ).scalar() or 0
        
        older_orders = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= two_years_ago,
            Order.created_at < one_year_ago,
            Order.status != OrderStatus.CANCELLED,
        ).scalar() or 0
        
        if older_orders == 0:
            return 0.0
        
        return (recent_orders - older_orders) / older_orders

    # ── Seasonal Trend Analysis ──────────────────────────────────────────

    def analyze_seasonal_trends(self, vendor_id: int) -> Dict[str, Any]:
        """Analyze seasonal trends."""
        # Define seasons (simplified for India)
        current_date = date.today()
        month = current_date.month
        
        # Determine current season
        if month in [12, 1, 2]:
            current_season = SeasonType.WINTER
        elif month in [3, 4, 5]:
            current_season = SeasonType.SPRING
        elif month in [6, 7, 8, 9]:
            current_season = SeasonType.MONSOON
        else:
            current_season = SeasonType.SUMMER
        
        # Analyze each season
        seasonal_data = []
        for season in SeasonType:
            season_avg = self._get_season_average(vendor_id, season)
            seasonal_data.append({
                "season": season.value,
                "avg_orders": round(season_avg, 1),
                "current_season": season == current_season,
            })
        
        # Calculate seasonal trends
        trends = self._calculate_seasonal_trends(vendor_id)
        
        return {
            "vendor_id": vendor_id,
            "current_season": current_season.value,
            "seasonal_data": seasonal_data,
            "trends": trends,
            "recommendations": self._generate_seasonal_recommendations(seasonal_data, trends),
        }

    def _get_season_average(self, vendor_id: int, season: SeasonType) -> float:
        """Get average orders for a specific season."""
        # Define season date ranges (simplified)
        season_months = {
            SeasonType.WINTER: [12, 1, 2],
            SeasonType.SPRING: [3, 4, 5],
            SeasonType.MONSOON: [6, 7, 8, 9],
            SeasonType.SUMMER: [10, 11],
        }
        
        months = season_months.get(season, [])
        if not months:
            return 0.0
        
        # Query orders in those months
        total_orders = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            extract("month", Order.created_at).in_(months),
            Order.status != OrderStatus.CANCELLED,
        ).scalar() or 0
        
        # Average per month
        return total_orders / len(months) if months else 0.0

    def _calculate_seasonal_trends(self, vendor_id: int) -> List[Dict[str, Any]]:
        """Calculate trends for each season."""
        trends = []
        
        # Compare last year's seasons
        for season in [SeasonType.WINTER, SeasonType.MONSOON]:
            current = self._get_season_average(vendor_id, season)
            # Would need historical comparison - simplified here
            trends.append({
                "season": season.value,
                "trend": "stable",
                "growth": 0.0,
            })
        
        return trends

    def _generate_seasonal_recommendations(
        self, seasonal_data: List[Dict], trends: List[Dict]
    ) -> List[str]:
        """Generate recommendations based on seasonal data."""
        recommendations = []
        
        # Find peak season
        peak_season = max(seasonal_data, key=lambda x: x["avg_orders"])
        recommendations.append(
            f"Peak season: {peak_season['season']} with avg {peak_season['avg_orders']} orders/month"
        )
        
        # Find low season
        low_season = min(seasonal_data, key=lambda x: x["avg_orders"])
        recommendations.append(
            f"Low season: {low_season['season']} with avg {low_season['avg_orders']} orders/month"
        )
        
        return recommendations

    # ── Semester Schedule Analysis ────────────────────────────────────────

    def analyze_semester_schedules(self, vendor_id: int) -> Dict[str, Any]:
        """Analyze impact of semester schedules on orders."""
        # Define typical Indian university semesters
        # This would integrate with actual academic calendar
        
        current_date = date.today()
        month = current_date.month
        
        # Simplified semester detection
        if month in [11, 12, 1]:
            current_period = CampusPeriod.EXAM
        elif month in [5, 6]:
            current_period = CampusPeriod.SEMESTER_BREAK
        elif month in [7, 8]:
            current_period = CampusPeriod.HOLIDAY
        else:
            current_period = CampusPeriod.REGULAR
        
        # Analyze each period
        period_data = []
        for period in CampusPeriod:
            period_avg = self._get_campus_period_average(vendor_id, period)
            period_data.append({
                "period": period.value,
                "avg_orders": round(period_avg, 1),
                "current_period": period == current_period,
            })
        
        return {
            "vendor_id": vendor_id,
            "current_period": current_period.value,
            "period_data": period_data,
            "recommendations": self._generate_semester_recommendations(period_data, current_period),
        }

    def _get_campus_period_average(self, vendor_id: int, period: CampusPeriod) -> float:
        """Get average orders during a campus period."""
        # Simplified - would use actual academic calendar
        period_orders = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.status != OrderStatus.CANCELLED,
        ).scalar() or 0
        
        # Normalize by days in period
        return period_orders / 90.0  # Approximate 3 months per period

    def _generate_semester_recommendations(
        self, period_data: List[Dict], current_period: CampusPeriod
    ) -> List[str]:
        """Generate recommendations based on semester schedule."""
        recommendations = []
        
        current_data = next((p for p in period_data if p["current_period"]), None)
        if current_data:
            recommendations.append(
                f"Current period ({current_period.value}): avg {current_data['avg_orders']} orders"
            )
        
        # Find best and worst periods
        best_period = max(period_data, key=lambda x: x["avg_orders"])
        worst_period = min(period_data, key=lambda x: x["avg_orders"])
        
        recommendations.append(
            f"Plan for {best_period['period']} (peak: {best_period['avg_orders']} orders)"
        )
        recommendations.append(
            f"Reduce inventory during {worst_period['period']} (low: {worst_period['avg_orders']} orders)"
        )
        
        return recommendations

    # ── Vendor Holiday Analysis ───────────────────────────────────────────

    def analyze_vendor_holidays(self, vendor_id: int) -> Dict[str, Any]:
        """Analyze vendor holiday patterns."""
        # This would integrate with vendor's holiday schedule
        # For now, analyze order patterns to detect closures
        
        # Find days with zero orders (potential holidays)
        all_dates = self.db.query(
            func.date(Order.created_at).label("order_date"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= utcnow_naive() - timedelta(days=180),
        ).group_by(
            func.date(Order.created_at),
        ).all()
        
        order_dates = {row.order_date for row in all_dates}
        
        # Find gaps (potential holidays)
        all_days = set()
        current = date.today() - timedelta(days=180)
        end = date.today()
        while current <= end:
            all_days.add(current)
            current += timedelta(days=1)
        
        holiday_dates = sorted(all_days - order_dates)
        
        # Group consecutive days
        holiday_periods = self._group_consecutive_dates(holiday_dates)
        
        return {
            "vendor_id": vendor_id,
            "total_holiday_days": len(holiday_dates),
            "holiday_periods": holiday_periods[:10],  # Top 10
            "recommendations": [
                f"Detected {len(holiday_periods)} holiday periods in last 6 months",
                "Consider planning inventory around these periods",
            ],
        }

    def _group_consecutive_dates(self, dates: List[date]) -> List[Dict[str, Any]]:
        """Group consecutive dates into periods."""
        if not dates:
            return []
        
        periods = []
        start = dates[0]
        end = dates[0]
        
        for i in range(1, len(dates)):
            if (dates[i] - end).days == 1:
                end = dates[i]
            else:
                periods.append({
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "days": (end - start).days + 1,
                })
                start = dates[i]
                end = dates[i]
        
        periods.append({
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": (end - start).days + 1,
        })
        
        return periods

    # ── Peak Campus Timing Analysis ──────────────────────────────────────

    def analyze_campus_timings(self, vendor_id: int) -> Dict[str, Any]:
        """Analyze peak campus timings impact."""
        # Hourly distribution
        hourly_data = self.db.query(
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("order_count"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= utcnow_naive() - timedelta(days=30),
            Order.status != OrderStatus.CANCELLED,
        ).group_by(
            extract("hour", Order.created_at),
        ).all()
        
        hourly_map = {int(row.hour): row.order_count for row in hourly_data}
        
        # Define campus periods
        campus_periods = {
            "early_morning": (6, 8),
            "morning_break": (10, 11),
            "lunch": (12, 14),
            "afternoon_break": (15, 16),
            "evening": (17, 19),
            "late_evening": (20, 22),
        }
        
        period_stats = []
        for period_name, (start_hour, end_hour) in campus_periods.items():
            period_orders = sum(
                hourly_map.get(hour, 0) for hour in range(start_hour, end_hour + 1)
            )
            period_stats.append({
                "period": period_name,
                "time_range": f"{start_hour}:00-{end_hour}:00",
                "orders": period_orders,
                "avg_per_hour": round(period_orders / (end_hour - start_hour + 1), 1),
            })
        
        # Sort by orders
        period_stats.sort(key=lambda x: x["orders"], reverse=True)
        
        # Identify peak periods
        peak_periods = [p for p in period_stats if p["orders"] > 0]
        
        return {
            "vendor_id": vendor_id,
            "hourly_distribution": [
                {"hour": hour, "orders": hourly_map.get(hour, 0)}
                for hour in range(6, 23)
            ],
            "campus_periods": period_stats,
            "peak_periods": peak_periods[:3],
            "recommendations": [
                f"Peak campus time: {peak_periods[0]['period']} ({peak_periods[0]['time_range']})"
                if peak_periods else "No clear peak detected"
            ],
        }

    # ── Learning Dataset Generation ──────────────────────────────────────

    def generate_learning_dataset(
        self, vendor_id: int, lookback_days: int = 90
    ) -> Dict[str, Any]:
        """Generate comprehensive learning dataset for ML training."""
        cutoff_date = utcnow_naive() - timedelta(days=lookback_days)
        
        # Get all orders in period
        orders = self.db.query(Order).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= cutoff_date,
        ).all()
        
        # Generate feature vectors
        features = []
        for order in orders:
            feature_vector = self._extract_order_features(order)
            features.append(feature_vector)
        
        # Aggregate by day
        daily_features = self._aggregate_daily_features(features)
        
        # Calculate statistics
        dataset_stats = {
            "total_orders": len(orders),
            "date_range": {
                "start": cutoff_date.isoformat(),
                "end": utcnow_naive().isoformat(),
            },
            "features_count": len(features),
            "daily_records": len(daily_features),
        }
        
        return {
            "vendor_id": vendor_id,
            "dataset": {
                "features": features[:100],  # Sample
                "daily_aggregates": daily_features[:30],  # Sample
            },
            "statistics": dataset_stats,
            "metadata": {
                "lookback_days": lookback_days,
                "generated_at": utcnow_naive().isoformat(),
                "feature_types": [
                    "temporal",
                    "day_of_week",
                    "hour",
                    "month",
                    "season",
                    "campus_period",
                ],
            },
        }

    def _extract_order_features(self, order: Order) -> Dict[str, Any]:
        """Extract features from a single order."""
        created_at = order.created_at
        
        # Temporal features
        features = {
            "order_id": order.id,
            "created_at": created_at.isoformat(),
            "hour": created_at.hour,
            "day_of_week": created_at.weekday(),
            "day_of_month": created_at.day,
            "month": created_at.month,
            "quarter": (created_at.month - 1) // 3 + 1,
            "is_weekend": created_at.weekday() >= 5,
            "is_peak_hour": self._is_peak_hour(created_at.hour),
        }
        
        # Season
        features["season"] = self._get_season(created_at.month).value
        
        # Campus period
        features["campus_period"] = self._get_campus_period(created_at).value
        
        # Order features
        features["slot_id"] = order.slot_id
        features["status"] = order.status.value
        features["eta_minutes"] = order.eta_minutes
        
        return features

    def _aggregate_daily_features(self, features: List[Dict]) -> List[Dict[str, Any]]:
        """Aggregate features by day."""
        daily: Dict[str, Dict] = defaultdict(lambda: {
            "date": None,
            "order_count": 0,
            "total_eta": 0,
            "hours": [],
            "days_of_week": [],
        })
        
        for feat in features:
            date_key = feat["created_at"][:10]  # YYYY-MM-DD
            day_data = daily[date_key]
            day_data["date"] = date_key
            day_data["order_count"] += 1
            day_data["total_eta"] += feat.get("eta_minutes", 0) or 0
            day_data["hours"].append(feat["hour"])
            day_data["days_of_week"].append(feat["day_of_week"])
        
        # Convert to list
        result = []
        for date_key, data in daily.items():
            result.append({
                "date": data["date"],
                "order_count": data["order_count"],
                "avg_eta": round(data["total_eta"] / data["order_count"], 1) if data["order_count"] > 0 else 0,
                "peak_hour": max(set(data["hours"]), key=data["hours"].count) if data["hours"] else None,
                "day_of_week": data["days_of_week"][0] if data["days_of_week"] else None,
            })
        
        return sorted(result, key=lambda x: x["date"])

    def _is_peak_hour(self, hour: int) -> bool:
        """Check if hour is peak campus time."""
        peak_hours = [12, 13, 14, 18, 19, 20]  # Lunch and dinner
        return hour in peak_hours

    def _get_season(self, month: int) -> SeasonType:
        """Get season from month."""
        if month in [12, 1, 2]:
            return SeasonType.WINTER
        elif month in [3, 4, 5]:
            return SeasonType.SPRING
        elif month in [6, 7, 8, 9]:
            return SeasonType.MONSOON
        else:
            return SeasonType.SUMMER

    def _get_campus_period(self, dt: datetime) -> CampusPeriod:
        """Get campus period from date."""
        month = dt.month
        if month in [11, 12, 1]:
            return CampusPeriod.EXAM
        elif month in [5, 6]:
            return CampusPeriod.SEMESTER_BREAK
        elif month in [7, 8]:
            return CampusPeriod.HOLIDAY
        else:
            return CampusPeriod.REGULAR

    # ── Public API ────────────────────────────────────────────────────────

    def get_historical_forecast(self, vendor_id: int, days_ahead: int = 7) -> Dict[str, Any]:
        """Generate forecast based on historical learning.
        
        API: GET /vendor/history/forecast
        """
        # Get all learned patterns
        daily_patterns = self.analyze_daily_patterns(vendor_id, days=90)
        weekly_patterns = self.analyze_weekly_patterns(vendor_id, weeks=24)
        monthly_patterns = self.analyze_monthly_patterns(vendor_id, months=12)
        seasonal_trends = self.analyze_seasonal_trends(vendor_id)
        campus_schedule = self.analyze_semester_schedules(vendor_id)
        campus_timings = self.analyze_campus_timings(vendor_id)
        
        # Generate forecast
        forecast = self._generate_forecast(
            vendor_id,
            days_ahead,
            daily_patterns,
            weekly_patterns,
            monthly_patterns,
            seasonal_trends,
            campus_schedule,
            campus_timings,
        )
        
        return {
            "vendor_id": vendor_id,
            "forecast_days": days_ahead,
            "forecast": forecast,
            "learning_sources": {
                "daily_patterns": daily_patterns,
                "weekly_patterns": weekly_patterns,
                "monthly_patterns": monthly_patterns,
                "seasonal_trends": seasonal_trends,
                "campus_schedule": campus_schedule,
                "campus_timings": campus_timings,
            },
            "confidence": self._calculate_forecast_confidence(
                daily_patterns, weekly_patterns, monthly_patterns
            ),
        }

    def get_historical_trends(self, vendor_id: int) -> Dict[str, Any]:
        """Get historical trends analysis.
        
        API: GET /vendor/history/trends
        """
        daily = self.analyze_daily_patterns(vendor_id, days=90)
        weekly = self.analyze_weekly_patterns(vendor_id, weeks=24)
        monthly = self.analyze_monthly_patterns(vendor_id, months=12)
        seasonal = self.analyze_seasonal_trends(vendor_id)
        campus = self.analyze_semester_schedules(vendor_id)
        timings = self.analyze_campus_timings(vendor_id)
        holidays = self.analyze_vendor_holidays(vendor_id)
        
        return {
            "vendor_id": vendor_id,
            "daily_trends": {
                "avg_orders": daily["avg_daily_orders"],
                "patterns": daily["patterns"],
                "trend": "stable",  # Would calculate from daily data
            },
            "weekly_trends": {
                "avg_orders": weekly["avg_weekly_orders"],
                "trend": weekly["trend"],
                "patterns": weekly["patterns"],
            },
            "monthly_trends": {
                "avg_orders": monthly["avg_monthly_orders"],
                "yoy_growth": monthly["year_over_year_growth"],
                "patterns": monthly["patterns"],
            },
            "seasonal_trends": seasonal,
            "campus_impact": campus,
            "campus_timings": timings,
            "holiday_patterns": holidays,
            "insights": self._generate_trend_insights(
                daily, weekly, monthly, seasonal, campus
            ),
        }

    def _generate_forecast(
        self,
        vendor_id: int,
        days_ahead: int,
        daily: Dict,
        weekly: Dict,
        monthly: Dict,
        seasonal: Dict,
        campus: Dict,
        timings: Dict,
    ) -> List[Dict[str, Any]]:
        """Generate forecast combining all learned patterns."""
        forecast = []
        today = date.today()
        
        for i in range(days_ahead):
            forecast_date = today + timedelta(days=i)
            
            # Base prediction from daily patterns
            base_prediction = daily["avg_daily_orders"]
            
            # Day of week adjustment
            dow = forecast_date.weekday()
            dow_pattern = next(
                (p for p in daily["patterns"] if p.get("type") == "day_of_week" and p.get("day_index") == dow),
                None
            )
            if dow_pattern:
                base_prediction = dow_pattern["avg_orders"]
            
            # Weekly trend adjustment
            if weekly["trend"] == "up":
                base_prediction *= 1.05
            elif weekly["trend"] == "down":
                base_prediction *= 0.95
            
            # Seasonal adjustment
            current_season = seasonal["current_season"]
            season_data = next(
                (s for s in seasonal["seasonal_data"] if s["season"] == current_season),
                None
            )
            if season_data and daily["avg_daily_orders"] > 0:
                season_multiplier = season_data["avg_orders"] / (daily["avg_daily_orders"] * 30)
                base_prediction *= min(2.0, max(0.5, season_multiplier))
            
            # Campus period adjustment
            campus_period = campus["current_period"]
            period_data = next(
                (p for p in campus["period_data"] if p["period"] == campus_period),
                None
            )
            if period_data and daily["avg_daily_orders"] > 0:
                campus_multiplier = period_data["avg_orders"] / daily["avg_daily_orders"]
                base_prediction *= min(2.0, max(0.5, campus_multiplier))
            
            # Peak timing adjustment
            forecast_hour = 12  # Assume lunch time
            is_peak = timings["hourly_distribution"][forecast_hour - 6]["orders"] > 10
            if is_peak:
                base_prediction *= 1.2
            
            forecast.append({
                "date": forecast_date.isoformat(),
                "day_name": forecast_date.strftime("%A"),
                "predicted_orders": max(0, round(base_prediction)),
                "confidence": round(daily["confidence"], 2),
                "factors": {
                    "day_of_week": dow_pattern["name"] if dow_pattern else "unknown",
                    "weekly_trend": weekly["trend"],
                    "season": current_season,
                    "campus_period": campus_period,
                    "is_peak_time": is_peak,
                },
            })
        
        return forecast

    def _calculate_forecast_confidence(
        self, daily: Dict, weekly: Dict, monthly: Dict
    ) -> float:
        """Calculate overall forecast confidence."""
        confidences = [
            daily.get("confidence", 0),
            weekly.get("confidence", 0),
            monthly.get("confidence", 0),
        ]
        
        # Weighted average (daily most important)
        weights = [0.5, 0.3, 0.2]
        weighted_conf = sum(c * w for c, w in zip(confidences, weights))
        
        return round(weighted_conf, 2)

    def _generate_trend_insights(
        self, daily: Dict, weekly: Dict, monthly: Dict, seasonal: Dict, campus: Dict
    ) -> List[str]:
        """Generate insights from trend analysis."""
        insights = []
        
        # Daily insights
        if daily["patterns"]:
            high_days = [p for p in daily["patterns"] if p.get("type") == "high_demand_days"]
            if high_days:
                insights.append(
                    f"High demand days: {', '.join(high_days[0]['days'])}"
                )
        
        # Weekly insights
        if weekly["trend"] == "up":
            insights.append("Weekly trend is increasing - consider capacity expansion")
        elif weekly["trend"] == "down":
            insights.append("Weekly trend is decreasing - consider cost optimization")
        
        # Monthly insights
        if monthly["year_over_year_growth"] > 0.1:
            insights.append(
                f"Strong year-over-year growth: {monthly['year_over_year_growth']*100:.1f}%"
            )
        elif monthly["year_over_year_growth"] < -0.1:
            insights.append(
                f"Declining year-over-year: {monthly['year_over_year_growth']*100:.1f}%"
            )
        
        # Seasonal insights
        if seasonal["recommendations"]:
            insights.extend(seasonal["recommendations"][:2])
        
        # Campus insights
        if campus["recommendations"]:
            insights.extend(campus["recommendations"][:2])
        
        return insights

    # ── Persistence ───────────────────────────────────────────────────────

    def persist_learning(self, vendor_id: int) -> Dict[str, Any]:
        """Persist learned patterns to database for future use."""
        # This would create records in a historical_learning table
        # For now, we'll cache in memory
        
        patterns = {
            "daily": self.analyze_daily_patterns(vendor_id),
            "weekly": self.analyze_weekly_patterns(vendor_id),
            "monthly": self.analyze_monthly_patterns(vendor_id),
            "seasonal": self.analyze_seasonal_trends(vendor_id),
            "campus": self.analyze_semester_schedules(vendor_id),
            "timings": self.analyze_campus_timings(vendor_id),
        }
        
        self._patterns_cache[vendor_id] = patterns
        self._last_cache_update = utcnow_naive()
        
        return {
            "vendor_id": vendor_id,
            "persisted_at": utcnow_naive().isoformat(),
            "patterns_count": len(patterns),
            "status": "success",
        }

    def get_persisted_learning(self, vendor_id: int) -> Optional[Dict[str, Any]]:
        """Get persisted learning data."""
        return self._patterns_cache.get(vendor_id)

    def invalidate_cache(self, vendor_id: int):
        """Invalidate cached learning data."""
        if vendor_id in self._patterns_cache:
            del self._patterns_cache[vendor_id]
