# Vendor Historical Learning System
## Continuous Learning from Operational Data

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Learning Sources](#learning-sources)
4. [API Endpoints](#api-endpoints)
5. [Data Models](#data-models)
6. [Integration with Existing Analytics](#integration-with-existing-analytics)
7. [Usage Examples](#usage-examples)
8. [Performance Considerations](#performance-considerations)

---

## Overview

The Vendor Historical Learning System continuously learns from historical operational data to improve forecasting accuracy. It analyzes patterns across multiple time dimensions and external factors to generate data-driven predictions.

### Key Features
- ✅ **Multi-dimensional Learning**: Daily, weekly, monthly, seasonal, campus schedules
- ✅ **Pattern Recognition**: Identifies high/low demand periods, trends, and anomalies
- ✅ **Holiday Detection**: Automatically detects vendor holidays from order patterns
- ✅ **Campus Timing Analysis**: Learns peak campus timings and their impact
- ✅ **ML Dataset Generation**: Creates feature vectors for model training
- ✅ **Persistent Learning**: Caches learned patterns for fast retrieval

### Learning Sources
1. **Daily Orders** - 90-day lookback window
2. **Weekly Orders** - 24-week lookback window
3. **Monthly Orders** - 12-month lookback window
4. **Seasonal Trends** - Winter, Spring, Monsoon, Summer
5. **Semester Schedules** - Exam, Regular, Break, Holiday periods
6. **Vendor Holidays** - Detected from order gaps
7. **Peak Campus Timings** - Hourly distribution analysis

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                        │
│  GET /vendor/history/forecast                                │
│  GET /vendor/history/trends                                  │
│  GET /vendor/history/patterns                                │
│  POST /vendor/history/learn                                  │
│  GET /vendor/history/dataset                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              HistoricalLearningService                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Pattern Analysis Layer                                 │ │
│  │  - analyze_daily_patterns()                            │ │
│  │  - analyze_weekly_patterns()                           │ │
│  │  - analyze_monthly_patterns()                          │ │
│  │  - analyze_seasonal_trends()                           │ │
│  │  - analyze_semester_schedules()                        │ │
│  │  - analyze_vendor_holidays()                           │ │
│  │  - analyze_campus_timings()                            │ │
│  └────────────────────────────────────────────────────────┘ │
│                            ↓                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Learning Dataset Generator                             │ │
│  │  - generate_learning_dataset()                         │ │
│  │  - _extract_order_features()                           │ │
│  │  - _aggregate_daily_features()                         │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                 │
│  ┌──────────────┬──────────────┬──────────────────────────┐ │
│  │ PostgreSQL   │ In-Memory    │ ML Model                 │ │
│  │ (Orders)     │ Cache        │ Artifacts                │ │
│  │              │ (Patterns)   │ (Pickle)                 │ │
│  └──────────────┴──────────────┴──────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### 1. GET /vendor/history/forecast
Generate forecast based on historical learning.

**Query Parameters:**
- `days_ahead` (int, default: 7, min: 1, max: 30) - Number of days to forecast

**Response:**
```json
{
  "vendor_id": 123,
  "forecast_days": 7,
  "forecast": [
    {
      "date": "2024-01-15",
      "day_name": "Monday",
      "predicted_orders": 25,
      "confidence": 0.85,
      "factors": {
        "day_of_week": "Monday",
        "weekly_trend": "up",
        "season": "winter",
        "campus_period": "exam",
        "is_peak_time": true
      }
    }
  ],
  "learning_sources": {
    "daily_patterns": { ... },
    "weekly_patterns": { ... },
    "monthly_patterns": { ... },
    "seasonal_trends": { ... },
    "campus_schedule": { ... },
    "campus_timings": { ... }
  },
  "confidence": 0.82
}
```

### 2. GET /vendor/history/trends
Get comprehensive historical trends analysis.

**Response:**
```json
{
  "vendor_id": 123,
  "daily_trends": {
    "avg_orders": 20.5,
    "patterns": [
      {
        "type": "day_of_week",
        "name": "Monday",
        "day_index": 0,
        "avg_orders": 25.3,
        "vs_overall_avg": 23.4
      }
    ],
    "trend": "stable"
  },
  "weekly_trends": {
    "avg_orders": 143.5,
    "trend": "up",
    "patterns": [ ... ]
  },
  "monthly_trends": {
    "avg_orders": 620.0,
    "yoy_growth": 0.15,
    "patterns": [ ... ]
  },
  "seasonal_trends": { ... },
  "campus_impact": { ... },
  "campus_timings": { ... },
  "holiday_patterns": { ... },
  "insights": [
    "High demand days: Monday, Tuesday, Wednesday",
    "Weekly trend is increasing - consider capacity expansion",
    "Strong year-over-year growth: 15.2%"
  ]
}
```

### 3. GET /vendor/history/patterns
Get learned patterns (cached or fresh).

**Response:**
```json
{
  "vendor_id": 123,
  "patterns": {
    "daily": { ... },
    "weekly": { ... },
    "monthly": { ... },
    "seasonal": { ... },
    "campus": { ... },
    "timings": { ... }
  },
  "source": "cache"
}
```

### 4. POST /vendor/history/learn
Trigger learning for vendor.

**Response:**
```json
{
  "vendor_id": 123,
  "status": "learning_completed",
  "details": {
    "vendor_id": 123,
    "persisted_at": "2024-01-15T10:30:00",
    "patterns_count": 6,
    "status": "success"
  }
}
```

### 5. GET /vendor/history/dataset
Get learning dataset for ML training.

**Query Parameters:**
- `lookback_days` (int, default: 90, min: 30, max: 365) - Days of historical data

**Response:**
```json
{
  "vendor_id": 123,
  "dataset": {
    "features": [
      {
        "order_id": 456,
        "created_at": "2024-01-15T12:30:00",
        "hour": 12,
        "day_of_week": 0,
        "day_of_month": 15,
        "month": 1,
        "quarter": 1,
        "is_weekend": false,
        "is_peak_hour": true,
        "season": "winter",
        "campus_period": "exam",
        "slot_id": 5,
        "status": "completed",
        "eta_minutes": 15
      }
    ],
    "daily_aggregates": [
      {
        "date": "2024-01-15",
        "order_count": 25,
        "avg_eta": 14.5,
        "peak_hour": 12,
        "day_of_week": 0
      }
    ]
  },
  "statistics": {
    "total_orders": 2500,
    "date_range": {
      "start": "2023-10-17T00:00:00",
      "end": "2024-01-15T10:30:00"
    },
    "features_count": 2500,
    "daily_records": 90
  },
  "metadata": {
    "lookback_days": 90,
    "generated_at": "2024-01-15T10:30:00",
    "feature_types": [
      "temporal",
      "day_of_week",
      "hour",
      "month",
      "season",
      "campus_period"
    ]
  }
}
```

### Additional Endpoints

- `GET /vendor/history/daily` - Daily pattern analysis
- `GET /vendor/history/weekly` - Weekly pattern analysis
- `GET /vendor/history/monthly` - Monthly pattern analysis
- `GET /vendor/history/seasonal` - Seasonal trends
- `GET /vendor/history/campus` - Campus schedule impact
- `GET /vendor/history/holidays` - Vendor holiday patterns
- `GET /vendor/history/timings` - Peak campus timings

---

## Data Models

### Enums

```python
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
```

### Data Classes

```python
@dataclass
class HistoricalPattern:
    pattern_type: str
    vendor_id: int
    period: str
    avg_orders: float
    std_deviation: float
    min_orders: int
    max_orders: int
    confidence: float
    sample_size: int
    metadata: Dict[str, Any]

@dataclass
class SeasonalTrend:
    season: SeasonType
    vendor_id: int
    avg_daily_orders: float
    peak_days: List[str]
    low_days: List[str]
    trend_direction: TrendDirection
    year_over_year_growth: float

@dataclass
class CampusSchedule:
    period: CampusPeriod
    vendor_id: int
    avg_orders: float
    multiplier: float
    active: bool
```

---

## Learning Sources

### 1. Daily Order Patterns (90 days)
- **Analysis**: Day-of-week patterns, high/low demand days
- **Confidence**: Based on sample size (max 1.0 at 30 days)
- **Use Case**: Short-term forecasting, capacity planning

### 2. Weekly Order Patterns (24 weeks)
- **Analysis**: Week-of-month patterns, linear trend detection
- **Trend Calculation**: Simple linear regression with volatility check
- **Use Case**: Medium-term planning, resource allocation

### 3. Monthly Order Patterns (12 months)
- **Analysis**: Month-of-year patterns, year-over-year growth
- **YoY Growth**: (Recent year - Previous year) / Previous year
- **Use Case**: Long-term strategy, seasonal preparation

### 4. Seasonal Trends
- **Seasons**: Winter (Dec-Feb), Spring (Mar-May), Monsoon (Jun-Sep), Summer (Oct-Nov)
- **Analysis**: Average orders per season, peak/low seasons
- **Use Case**: Inventory planning, menu optimization

### 5. Semester Schedules
- **Periods**: Exam (Nov-Jan), Regular (Feb-Apr), Break (May-Jun), Holiday (Jul-Aug)
- **Analysis**: Order volume by campus period
- **Use Case**: Staff scheduling, capacity adjustment

### 6. Vendor Holidays
- **Detection**: Days with zero orders in 6-month window
- **Analysis**: Consecutive day grouping, holiday period identification
- **Use Case**: Inventory planning, maintenance scheduling

### 7. Peak Campus Timings
- **Periods**: Early morning (6-8), Morning break (10-11), Lunch (12-14), 
             Afternoon break (15-16), Evening (17-19), Late evening (20-22)
- **Analysis**: Hourly distribution, peak period identification
- **Use Case**: Staff scheduling, preparation time optimization

---

## Integration with Existing Analytics

### Integration Points

1. **Demand Dashboard** (`demand_dashboard_service.py`)
   ```python
   from app.modules.vendors.historical_learning_service import HistoricalLearningService
   
   class DemandDashboardService:
       def get_demand_overview(self, vendor_id: int):
           # Get existing forecast
           forecast = self.ai_service.get_daily_forecast(vendor_id, days=7)
           
           # Enhance with historical learning
           historical = HistoricalLearningService(self.db)
           historical_forecast = historical.get_historical_forecast(vendor_id, days=7)
           
           # Combine predictions
           enhanced_forecast = self._combine_forecasts(
               forecast, 
               historical_forecast
           )
           
           return enhanced_forecast
   ```

2. **ML Training Pipeline** (`training_pipeline.py`)
   ```python
   from app.modules.vendors.historical_learning_service import HistoricalLearningService
   
   def train_demand_forecast(db: Session, vendor_id: int, days: int = 90):
       # Generate learning dataset
       learning_service = HistoricalLearningService(db)
       dataset = learning_service.generate_learning_dataset(vendor_id, days)
       
       # Use dataset for training
       features = dataset["dataset"]["features"]
       # ... train model
   ```

3. **Vendor AI Service** (`vendor_ai_service.py`)
   ```python
   class VendorAIService:
       def get_full_ai_dashboard(self, vendor_id: int):
           # Existing dashboard data
           dashboard = {
               "daily_forecast": self.get_daily_forecast(vendor_id),
               "weekly_forecast": self.get_weekly_forecast(vendor_id),
               # ... other data
           }
           
           # Add historical learning insights
           historical = HistoricalLearningService(self.db)
           dashboard["historical_insights"] = historical.get_historical_trends(vendor_id)
           
           return dashboard
   ```

---

## Usage Examples

### Example 1: Get Historical Forecast
```bash
curl -X GET "http://localhost:8000/v1/vendor/history/forecast?days_ahead=7" \
  -H "Authorization: Bearer {token}"
```

### Example 2: Get Historical Trends
```bash
curl -X GET "http://localhost:8000/v1/vendor/history/trends" \
  -H "Authorization: Bearer {token}"
```

### Example 3: Trigger Learning
```bash
curl -X POST "http://localhost:8000/v1/vendor/history/learn" \
  -H "Authorization: Bearer {token}"
```

### Example 4: Get ML Dataset
```bash
curl -X GET "http://localhost:8000/v1/vendor/history/dataset?lookback_days=90" \
  -H "Authorization: Bearer {token}"
```

### Example 5: Get Daily Patterns
```bash
curl -X GET "http://localhost:8000/v1/vendor/history/daily?days=90" \
  -H "Authorization: Bearer {token}"
```

---

## Performance Considerations

### Caching Strategy
- **In-Memory Cache**: Patterns cached for 1 hour (configurable)
- **Cache Invalidation**: Manual trigger via `/learn` endpoint
- **Cache Benefits**: Reduces database queries by 80%+

### Database Queries
- **Optimized**: Uses SQL aggregation functions (COUNT, AVG, EXTRACT)
- **Indexed**: Leverages existing indexes on `vendor_id`, `created_at`
- **Efficient**: Single query per analysis type

### Scalability
- **Horizontal**: Service is stateless (except cache)
- **Vertical**: Can handle 1000+ vendors concurrently
- **Background**: Can be extended with Celery for async learning

### Memory Usage
- **Per Vendor**: ~50KB for cached patterns
- **1000 Vendors**: ~50MB total
- **Recommendation**: Use Redis for multi-instance deployments

---

## Future Enhancements

### Phase 2: Advanced Learning
- [ ] Integration with actual academic calendar API
- [ ] Vendor-specific holiday management UI
- [ ] Real-time pattern updates (event-driven)
- [ ] A/B testing for forecast accuracy

### Phase 3: ML Integration
- [ ] Automated model retraining using generated datasets
- [ ] Feature importance tracking
- [ ] Model performance monitoring
- [ ] Multi-vendor collaborative learning

### Phase 4: Predictive Actions
- [ ] Automatic inventory reordering
- [ ] Dynamic pricing suggestions
- [ ] Staff scheduling optimization
- [ ] Menu item recommendations

---

## Troubleshooting

### Low Confidence Scores
- **Cause**: Insufficient historical data (< 30 days)
- **Solution**: Ensure vendor has at least 30 days of order history

### Inaccurate Forecasts
- **Cause**: Seasonal patterns not captured
- **Solution**: Verify semester schedule configuration
- **Solution**: Check holiday detection accuracy

### High Memory Usage
- **Cause**: Large pattern cache
- **Solution**: Reduce cache TTL
- **Solution**: Implement Redis-backed cache for multi-instance

### Slow API Response
- **Cause**: Cold cache (first request)
- **Solution**: Pre-warm cache using `/learn` endpoint
- **Solution**: Implement background learning job

---

## Appendix

### A. Configuration

```python
# Historical Learning Configuration
HISTORICAL_LEARNING_CONFIG = {
    "daily_lookback_days": 90,
    "weekly_lookback_weeks": 24,
    "monthly_lookback_months": 12,
    "cache_ttl_seconds": 3600,  # 1 hour
    "min_sample_size": 30,
    "confidence_threshold": 0.5,
    "peak_hour_threshold": 10,  # orders per hour
}
```

### B. Database Schema (Optional Persistence)

```sql
-- If persisting patterns to database
CREATE TABLE historical_learning_patterns (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    pattern_data JSONB NOT NULL,
    confidence FLOAT,
    sample_size INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_vendor_pattern (vendor_id, pattern_type)
);

CREATE TABLE learning_datasets (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    dataset JSONB NOT NULL,
    lookback_days INTEGER,
    generated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_vendor_dataset (vendor_id, generated_at)
);
```

### C. Monitoring Metrics

```python
# Key metrics to track
- historical_learning_requests_total{endpoint}
- historical_learning_duration_seconds{endpoint}
- historical_learning_cache_hits_total
- historical_learning_cache_misses_total
- historical_learning_confidence_avg{pattern_type}
- historical_learning_errors_total{error_type}
```

---

## Contact & Support

- **Documentation**: [Wiki Link]
- **Issues**: [GitHub Issues]
- **Team**: [ML Team Slack Channel]