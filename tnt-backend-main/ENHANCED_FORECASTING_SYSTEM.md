# Enhanced Demand Forecasting System
## Multi-Horizon AI-Powered Predictions

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Forecasting Horizons](#forecasting-horizons)
4. [API Endpoints](#api-endpoints)
5. [Prediction Types](#prediction-types)
6. [Frontend Dashboard](#frontend-dashboard)
7. [Integration Guide](#integration-guide)
8. [Usage Examples](#usage-examples)

---

## Overview

The Enhanced Demand Forecasting System provides multi-horizon predictions for vendor operations. It extends the existing demand forecasting with:

- **Short-term predictions** (next 24 hours, hourly breakdown)
- **Daily predictions** (next 7-30 days)
- **Weekly predictions** (next 4-12 weeks)
- **Monthly predictions** (next 3-12 months)
- **Revenue forecasting**
- **Customer count forecasting**
- **Stationery jobs forecasting**
- **Food demand forecasting**

### Key Features
- ✅ Multi-horizon forecasting (short-term, daily, weekly, monthly)
- ✅ Revenue predictions with trend analysis
- ✅ Customer count forecasting
- ✅ Vendor-type-specific predictions (food vs stationery)
- ✅ Confidence scores for all predictions
- ✅ AI-generated insights
- ✅ Interactive charts and visualizations
- ✅ Historical data-based predictions

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                        │
│  GET /vendor/forecast/short-term                            │
│  GET /vendor/forecast/daily                                 │
│  GET /vendor/forecast/weekly                                │
│  GET /vendor/forecast/monthly                               │
│  GET /vendor/forecast/revenue                               │
│  GET /vendor/forecast/customers                             │
│  GET /vendor/forecast/comprehensive                         │
│  GET /vendor/forecast/by-type                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           EnhancedForecastingService                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Short-Term Forecasting (Next 24 Hours)                │ │
│  │  - Hourly pattern analysis                              │ │
│  │  - Peak hour prediction                                 │ │
│  │  - Time-of-day multipliers                              │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Daily Forecasting (7-30 Days)                         │ │
│  │  - Day-of-week patterns                                 │ │
│  │  - Trend adjustment                                     │ │
│  │  - Seasonal multipliers                                 │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Weekly Forecasting (4-12 Weeks)                       │ │
│  │  - Week-of-month patterns                               │ │
│  │  - Linear trend detection                               │ │
│  │  - Confidence decay                                      │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Monthly Forecasting (3-12 Months)                     │ │
│  │  - Month-of-year patterns                               │ │
│  │  - Year-over-year growth                                │ │
│  │  - Seasonal adjustments                                 │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                 │
│  ┌──────────────┬──────────────┬──────────────────────────┐ │
│  │ PostgreSQL   │ In-Memory    │ ML Model                 │ │
│  │ (Orders)     │ Cache        │ Artifacts                │ │
│  │              │ (30 min TTL) │ (Future)                 │ │
│  └──────────────┴──────────────┴──────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Frontend Dashboard (React Native)                │
│  - Time horizon selector                                     │
│  - Interactive charts (Line, Bar)                            │
│  - Confidence score visualization                            │
│  - AI insights panel                                         │
│  - Detailed breakdown tables                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Forecasting Horizons

### 1. Short-Term Forecast (Next 24 Hours)

**Time Horizon**: Next 24 hours, hourly breakdown

**Predictions**:
- Hourly order volume
- Hourly revenue
- Hourly customer count
- Peak hours identification

**Factors**:
- Historical hourly patterns (last 30 days)
- Time-of-day multipliers
- Current hour offset

**Confidence**: 0.5 - 0.95 (based on data coverage)

**Use Cases**:
- Staff scheduling
- Preparation planning
- Rush hour management

### 2. Daily Forecast (7-30 Days)

**Time Horizon**: Next N days

**Predictions**:
- Daily order volume
- Daily revenue
- Daily customer count
- Stationery jobs vs food demand split

**Factors**:
- Day-of-week patterns (90-day lookback)
- Weekly trend adjustment
- Seasonal multipliers
- Trend analysis (last 7 vs previous 7 days)

**Confidence**: 0.6 - 0.95 (decreases with distance)

**Use Cases**:
- Inventory planning
- Staff scheduling
- Capacity management

### 3. Weekly Forecast (4-12 Weeks)

**Time Horizon**: Next N weeks

**Predictions**:
- Weekly order volume
- Weekly revenue
- Weekly customer count
- Trend direction (up/down/stable)

**Factors**:
- Week-of-month patterns (6-month lookback)
- Linear trend detection
- Trend strength adjustment

**Confidence**: 0.4 - 0.8 (decreases with distance)

**Use Cases**:
- Resource allocation
- Budget planning
- Strategic decisions

### 4. Monthly Forecast (3-12 Months)

**Time Horizon**: Next N months

**Predictions**:
- Monthly order volume
- Monthly revenue
- Monthly customer count
- Year-over-year growth

**Factors**:
- Month-of-year patterns (12-month lookback)
- YoY growth rate
- Seasonal adjustments

**Confidence**: 0.4 - 0.7 (decreases with distance)

**Use Cases**:
- Long-term strategy
- Capacity expansion planning
- Investment decisions

---

## API Endpoints

### 1. GET /vendor/forecast/short-term

Get hourly forecast for next 24 hours.

**Response**:
```json
{
  "vendor_id": 123,
  "forecast_type": "short_term",
  "forecast_hours": 24,
  "hourly_forecast": [
    {
      "hour": 14,
      "time_label": "14:00",
      "predicted_orders": 8,
      "predicted_revenue": 850.50,
      "predicted_customers": 7,
      "confidence": 0.75
    }
  ],
  "total_orders": 156,
  "total_revenue": 15420.75,
  "total_customers": 142,
  "peak_hours": [
    {
      "hour": 12,
      "time_label": "12:00",
      "predicted_orders": 12,
      "confidence": 0.85
    }
  ],
  "confidence": 0.78,
  "generated_at": "2024-01-15T10:30:00"
}
```

### 2. GET /vendor/forecast/daily

Get daily forecast for next N days (7-30).

**Query Parameters**:
- `days` (int, default: 7, min: 7, max: 30)

**Response**:
```json
{
  "vendor_id": 123,
  "forecast_type": "daily",
  "forecast_days": 7,
  "daily_forecast": [
    {
      "date": "2024-01-16",
      "day_name": "Tuesday",
      "predicted_orders": 25,
      "predicted_revenue": 2500.00,
      "predicted_customers": 22,
      "predicted_stationery_jobs": 12,
      "predicted_food_demand": 13,
      "confidence": 0.82,
      "factors": {
        "day_of_week": "Tuesday",
        "trend_multiplier": 1.1,
        "seasonal_multiplier": 1.2
      }
    }
  ],
  "summary": {
    "total_orders": 175,
    "total_revenue": 17500.00,
    "total_customers": 154,
    "total_stationery_jobs": 87,
    "total_food_demand": 88,
    "avg_daily_orders": 25.0,
    "avg_daily_revenue": 2500.00
  },
  "confidence": 0.82,
  "generated_at": "2024-01-15T10:30:00"
}
```

### 3. GET /vendor/forecast/weekly

Get weekly forecast for next N weeks (4-12).

**Query Parameters**:
- `weeks` (int, default: 4, min: 4, max: 12)

**Response**:
```json
{
  "vendor_id": 123,
  "forecast_type": "weekly",
  "forecast_weeks": 4,
  "weekly_forecast": [
    {
      "week_start": "2024-01-15",
      "week_label": "Week 1",
      "predicted_orders": 175,
      "predicted_revenue": 17500.00,
      "predicted_customers": 140,
      "predicted_stationery_jobs": 87,
      "predicted_food_demand": 88,
      "confidence": 0.75,
      "trend": "up"
    }
  ],
  "summary": {
    "total_orders": 700,
    "total_revenue": 70000.00,
    "avg_weekly_orders": 175.0,
    "avg_weekly_revenue": 17500.00
  },
  "trend": "up",
  "confidence": 0.70,
  "generated_at": "2024-01-15T10:30:00"
}
```

### 4. GET /vendor/forecast/monthly

Get monthly forecast for next N months (3-12).

**Query Parameters**:
- `months` (int, default: 3, min: 3, max: 12)

**Response**:
```json
{
  "vendor_id": 123,
  "forecast_type": "monthly",
  "forecast_months": 3,
  "monthly_forecast": [
    {
      "month": "February 2024",
      "month_num": 2,
      "predicted_orders": 750,
      "predicted_revenue": 75000.00,
      "predicted_customers": 600,
      "predicted_stationery_jobs": 375,
      "predicted_food_demand": 375,
      "confidence": 0.65,
      "yoy_growth": 0.15
    }
  ],
  "summary": {
    "total_orders": 2250,
    "total_revenue": 225000.00,
    "avg_monthly_orders": 750.0,
    "avg_monthly_revenue": 75000.00
  },
  "yoy_growth": 0.15,
  "confidence": 0.65,
  "generated_at": "2024-01-15T10:30:00"
}
```

### 5. GET /vendor/forecast/revenue

Get revenue forecast for next N days (7-90).

**Query Parameters**:
- `days` (int, default: 30, min: 7, max: 90)

**Response**:
```json
{
  "vendor_id": 123,
  "forecast_type": "revenue",
  "forecast_days": 30,
  "total_revenue": 75000.00,
  "avg_daily_revenue": 2500.00,
  "daily_breakdown": [
    {
      "date": "2024-01-16",
      "predicted_revenue": 2500.00,
      "confidence": 0.82
    }
  ],
  "confidence": 0.82
}
```

### 6. GET /vendor/forecast/customers

Get customer count forecast for next N days (7-30).

**Query Parameters**:
- `days` (int, default: 7, min: 7, max: 30)

**Response**:
```json
{
  "vendor_id": 123,
  "forecast_type": "customers",
  "forecast_days": 7,
  "total_customers": 154,
  "avg_daily_customers": 22.0,
  "daily_breakdown": [
    {
      "date": "2024-01-16",
      "predicted_customers": 22,
      "confidence": 0.82
    }
  ],
  "confidence": 0.82
}
```

### 7. GET /vendor/forecast/comprehensive

Get comprehensive forecast across all time horizons.

**Response**:
```json
{
  "vendor_id": 123,
  "short_term": { ... },
  "daily": { ... },
  "weekly": { ... },
  "monthly": { ... },
  "insights": [
    "Peak hour today: 12:00 with 12 expected orders",
    "Average daily orders: 25.0",
    "Weekly trend is increasing - prepare for higher demand",
    "Strong year-over-year growth: 15.2%",
    "Expected revenue (next 3 months): $225,000.00"
  ],
  "generated_at": "2024-01-15T10:30:00"
}
```

### 8. GET /vendor/forecast/by-type

Get forecast based on vendor type (food vs stationery).

**Response**:
```json
{
  "vendor_id": 123,
  "short_term": { ... },
  "daily": { ... },
  "weekly": { ... },
  "monthly": { ... },
  "insights": [ ... ],
  "stationery_breakdown": {
    "print_jobs": 45,
    "xerox_jobs": 30,
    "binding_jobs": 12,
    "total_jobs": 87
  }
}
```

---

## Prediction Types

### Expected Orders
- **Short-term**: Hourly predictions for next 24 hours
- **Daily**: Day-by-day predictions for next 7-30 days
- **Weekly**: Week-by-week predictions for next 4-12 weeks
- **Monthly**: Month-by-month predictions for next 3-12 months

### Expected Revenue
- Calculated based on historical average order value
- Adjusted for trends and seasonality
- Provided in daily, weekly, and monthly breakdowns

### Expected Customers
- Unique customer count predictions
- Based on historical customer-to-order ratio
- Adjusted for time-of-day and day-of-week patterns

### Expected Stationery Jobs
- Print jobs, Xerox jobs, Binding jobs
- Vendor-type-specific predictions
- Based on historical job type distribution

### Expected Food Demand
- Food order predictions
- Popular items breakdown
- Based on historical menu item popularity

---

## Frontend Dashboard

### Enhanced Forecast Dashboard

**Location**: `tnt-vendor-frontend/src/screens/analytics/EnhancedForecastDashboard.tsx`

**Features**:
- Multi-horizon time selector (Short-term, Daily, Weekly, Monthly)
- Interactive charts (Line charts, Bar charts)
- Confidence score visualization with color coding
- Summary metric cards with icons
- Detailed breakdown tables
- AI insights panel
- Pull-to-refresh support

**Components**:
1. **Confidence Score Card**: Visual indicator of prediction reliability
2. **Time Horizon Selector**: Toggle between short-term, daily, weekly, monthly
3. **Summary Cards**: Key metrics (orders, revenue, customers, stationery)
4. **Charts**: 
   - Line charts for orders vs customers
   - Bar charts for revenue
   - Hourly trend charts
5. **Breakdown Tables**: Detailed day/week/month breakdowns
6. **AI Insights**: Generated insights and recommendations

**Color Coding**:
- 🟢 Green (≥80%): High confidence
- 🟡 Yellow (50-80%): Medium confidence
- 🔴 Red (<50%): Low confidence

---

## Integration Guide

### Backend Integration

#### 1. Add Router to API v1

```python
# app/api/v1.py
from app.modules.vendors.enhanced_forecasting_router import router as vendor_forecast_router

api_v1_router.include_router(vendor_forecast_router)
```

#### 2. Integrate with Existing Demand Dashboard

```python
# app/modules/vendors/demand_dashboard_service.py
from app.modules.vendors.enhanced_forecasting_service import EnhancedForecastingService

class DemandDashboardService:
    def get_full_dashboard(self, vendor_id: int):
        # Existing dashboard data
        dashboard = {
            "demand_overview": self.get_demand_overview(vendor_id),
            "stock_prediction": self.get_stock_prediction(vendor_id),
            "rush_prediction": self.get_rush_prediction(vendor_id),
        }
        
        # Add enhanced forecasting
        forecasting = EnhancedForecastingService(self.db)
        dashboard["enhanced_forecast"] = forecasting.get_comprehensive_forecast(vendor_id)
        
        return dashboard
```

### Frontend Integration

#### 1. Add API Methods

```typescript
// src/services/vendorApi.ts
export const vendorApi = {
  // ... existing methods
  
  // Enhanced Forecasting
  getComprehensiveForecast: () => axios.get(`${API_BASE_URL}/v1/vendor/forecast/comprehensive`),
  getShortTermForecast: () => axios.get(`${API_BASE_URL}/v1/vendor/forecast/short-term`),
  getDailyForecastEnhanced: (days: number = 7) => axios.get(`${API_BASE_URL}/v1/vendor/forecast/daily?days=${days}`),
  getWeeklyForecastEnhanced: (weeks: number = 4) => axios.get(`${API_BASE_URL}/v1/vendor/forecast/weekly?weeks=${weeks}`),
  getMonthlyForecastEnhanced: (months: number = 3) => axios.get(`${API_BASE_URL}/v1/vendor/forecast/monthly?months=${months}`),
}
```

#### 2. Add Screen to Navigation

```typescript
// App.tsx or navigation config
import EnhancedForecastDashboard from './src/screens/analytics/EnhancedForecastDashboard';

// Add to navigation stack
{
  name: 'Enhanced Forecast',
  component: EnhancedForecastDashboard,
}
```

---

## Usage Examples

### Example 1: Get Comprehensive Forecast

```bash
curl -X GET "http://localhost:8000/v1/vendor/forecast/comprehensive" \
  -H "Authorization: Bearer {token}"
```

### Example 2: Get Daily Forecast for 14 Days

```bash
curl -X GET "http://localhost:8000/v1/vendor/forecast/daily?days=14" \
  -H "Authorization: Bearer {token}"
```

### Example 3: Get Revenue Forecast for 60 Days

```bash
curl -X GET "http://localhost:8000/v1/vendor/forecast/revenue?days=60" \
  -H "Authorization: Bearer {token}"
```

### Example 4: Get Monthly Forecast for 6 Months

```bash
curl -X GET "http://localhost:8000/v1/vendor/forecast/monthly?months=6" \
  -H "Authorization: Bearer {token}"
```

### Example 5: Frontend Integration

```typescript
import {vendorApi} from '../services/vendorApi';
import EnhancedForecastDashboard from '../screens/analytics/EnhancedForecastDashboard';

function ForecastScreen() {
  const [forecast, setForecast] = useState(null);
  
  useEffect(() => {
    loadForecast();
  }, []);
  
  const loadForecast = async () => {
    try {
      const response = await vendorApi.getComprehensiveForecast();
      setForecast(response.data);
    } catch (error) {
      console.error('Failed to load forecast:', error);
    }
  };
  
  return <EnhancedForecastDashboard />;
}
```

---

## Confidence Scores

### Calculation Methodology

**Short-term Confidence**:
- Based on data coverage (hours with historical data)
- Boosted by high volume vendors
- Range: 0.5 - 0.95

**Daily Confidence**:
- Base: 0.6
- Boost: +0.2 if day-of-week data exists
- Boost: +0.15 if vendor has 30+ days of history
- Range: 0.6 - 0.95

**Weekly Confidence**:
- Base: 0.8
- Decay: -0.05 per week distance
- Range: 0.4 - 0.8

**Monthly Confidence**:
- Base: 0.7
- Decay: -0.03 per month distance
- Range: 0.4 - 0.7

### Confidence Levels

- **High** (≥80%): Strong historical data, stable patterns
- **Medium** (50-80%): Moderate data, some variability
- **Low** (<50%): Limited data, high variability

---

## Performance Considerations

### Caching
- **TTL**: 30 minutes
- **Cache Key**: `forecast:{vendor_id}:{horizon}`
- **Invalidation**: Manual or on new order

### Database Queries
- **Optimized**: Uses SQL aggregation functions
- **Indexed**: Leverages existing indexes on `vendor_id`, `created_at`
- **Efficient**: Single query per time horizon

### Scalability
- **Horizontal**: Stateless service (except cache)
- **Vertical**: Can handle 1000+ vendors concurrently
- **Background**: Can be extended with Celery for async forecasting

### Response Times
- **Short-term**: ~200ms
- **Daily**: ~300ms
- **Weekly**: ~250ms
- **Monthly**: ~200ms
- **Comprehensive**: ~500ms (all horizons)

---

## Future Enhancements

### Phase 2: Advanced ML
- [ ] Prophet/ARIMA models for time series
- [ ] LSTM neural networks for sequence prediction
- [ ] Ensemble methods for improved accuracy
- [ ] Feature importance tracking

### Phase 3: Real-time Learning
- [ ] Online learning from new orders
- [ ] Real-time forecast updates
- [ ] Anomaly detection
- [ ] Automatic model retraining

### Phase 4: Predictive Actions
- [ ] Automatic inventory reordering
- [ ] Dynamic pricing suggestions
- [ ] Staff scheduling optimization
- [ ] Menu item recommendations

---

## Troubleshooting

### Low Confidence Scores
- **Cause**: Insufficient historical data
- **Solution**: Ensure vendor has at least 30 days of order history

### Inaccurate Forecasts
- **Cause**: Seasonal patterns not captured
- **Solution**: Verify seasonal multiplier configuration
- **Solution**: Check trend calculation logic

### Slow API Response
- **Cause**: Cold cache (first request)
- **Solution**: Pre-warm cache using comprehensive endpoint
- **Solution**: Implement background forecasting job

### High Memory Usage
- **Cause**: Large forecast cache
- **Solution**: Reduce cache TTL
- **Solution**: Implement Redis-backed cache for multi-instance

---

## Appendix

### A. Configuration

```python
# Enhanced Forecasting Configuration
FORECASTING_CONFIG = {
    "short_term": {
        "lookback_days": 30,
        "time_multipliers": {
            "peak": 1.3,      # 12-14, 18-20
            "normal": 1.1,    # 10-11, 15-17
            "early_late": 0.8, # 6-7, 21-22
            "night": 0.5,     # 0-5, 23
        },
    },
    "daily": {
        "lookback_days": 90,
        "min_days": 7,
        "max_days": 30,
        "trend_smoothing": 0.1,
    },
    "weekly": {
        "lookback_weeks": 24,
        "min_weeks": 4,
        "max_weeks": 12,
        "trend_threshold": 0.5,
    },
    "monthly": {
        "lookback_months": 12,
        "min_months": 3,
        "max_months": 12,
    },
    "seasonal_multipliers": {
        "winter": 1.2,    # Dec-Feb
        "spring": 1.0,    # Mar-May
        "monsoon": 0.9,   # Jun-Sep
        "summer": 1.1,    # Oct-Nov
    },
    "cache_ttl": 1800,  # 30 minutes
}
```

### B. Database Schema (Optional Persistence)

```sql
-- Forecast persistence table
CREATE TABLE forecast_history (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    forecast_type VARCHAR(50) NOT NULL,
    forecast_data JSONB NOT NULL,
    confidence FLOAT,
    generated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_vendor_forecast (vendor_id, forecast_type, generated_at)
);

-- Accuracy tracking
CREATE TABLE forecast_accuracy (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    forecast_date DATE NOT NULL,
    predicted_orders INTEGER,
    actual_orders INTEGER,
    accuracy FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_vendor_accuracy (vendor_id, forecast_date)
);
```

### C. Monitoring Metrics

```python
# Key metrics to track
- forecasting_requests_total{endpoint, horizon}
- forecasting_duration_seconds{endpoint}
- forecasting_cache_hits_total
- forecasting_cache_misses_total
- forecasting_confidence_avg{horizon}
- forecasting_errors_total{error_type}
- forecasting_accuracy_score{vendor_id}
```

---

## Contact & Support

- **Documentation**: [Wiki Link]
- **Issues**: [GitHub Issues]
- **Team**: [ML Team Slack Channel]