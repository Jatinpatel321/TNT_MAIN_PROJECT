# Forecast Confidence Scoring System
## Comprehensive Prediction Reliability Assessment

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Confidence Metrics](#confidence-metrics)
4. [API Endpoints](#api-endpoints)
5. [Confidence Levels](#confidence-levels)
6. [Risk Assessment](#risk-assessment)
7. [Frontend Integration](#frontend-integration)
8. [Integration Guide](#integration-guide)

---

## Overview

The Forecast Confidence Scoring System provides comprehensive reliability assessment for all predictions. Every forecast includes:

- **Confidence %**: Overall confidence score (0-100%)
- **Forecast Quality**: Assessment of forecast reliability (excellent/good/fair/poor)
- **Historical Accuracy**: Track prediction vs actual accuracy (0-100%)
- **Prediction Reliability**: Consistency of predictions (0-100%)
- **Risk Level**: Risk assessment for business decisions (low/medium/high/critical)

### Key Features
- ✅ Multi-factor confidence calculation
- ✅ Historical accuracy tracking
- ✅ Prediction reliability assessment
- ✅ Risk level classification
- ✅ Confidence history storage
- ✅ AI-generated recommendations
- ✅ Frontend visualization with color coding

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                        │
│  GET /vendor/forecast/confidence/{type}                      │
│  GET /vendor/forecast/confidence/report/{type}               │
│  GET /vendor/forecast/confidence/summary                     │
│  GET /vendor/forecast/confidence/history/{type}              │
│  GET /vendor/forecast/confidence/levels                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           ConfidenceScoringService                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Confidence Calculation                                 │ │
│  │  - Data availability (25%)                              │ │
│  │  - Historical consistency (20%)                         │ │
│  │  - Pattern strength (20%)                               │ │
│  │  - Horizon distance (15%)                               │ │
│  │  - Sample size (20%)                                    │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Quality Assessment                                     │ │
│  │  - Forecast quality (excellent/good/fair/poor)          │ │
│  │  - Historical accuracy tracking                          │ │
│  │  - Prediction reliability                                │ │
│  │  - Risk level assessment                                 │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  History Tracking                                       │ │
│  │  - Record predictions                                    │ │
│  │  - Update with actual values                             │ │
│  │  - Calculate accuracy metrics                            │ │
│  │  - Track trends                                          │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Confidence Integration Service                   │
│  - Integrates with EnhancedForecastingService                │
│  - Adds confidence scores to all forecasts                   │
│  - Generates confidence-based insights                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Frontend Dashboard (React Native)                │
│  - Confidence score visualization                             │
│  - Color-coded levels (Green/Yellow/Red)                     │
│  - Detailed breakdown                                         │
│  - Recommendations display                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Confidence Metrics

### 1. Confidence Percentage (0-100%)

Overall confidence score calculated from 5 factors:

**Factor 1: Data Availability (25%)**
- 100+ data points: 100% score
- 50-99 data points: 80% score
- 20-49 data points: 60% score
- 10-19 data points: 40% score
- <10 data points: 20% score

**Factor 2: Historical Consistency (20%)**
- Coefficient of variation < 0.3: 100% score
- CV 0.3-0.5: 80% score
- CV 0.5-0.8: 60% score
- CV 0.8-1.2: 40% score
- CV > 1.2: 20% score

**Factor 3: Pattern Strength (20%)**
- 3+ strong patterns: 100% score
- 2 strong patterns: 80% score
- 1 strong pattern: 60% score
- No strong patterns: 40% score

**Factor 4: Horizon Distance (15%)**
- Decreases linearly with forecast distance
- 1 day: 15% score
- 365 days: 0% score

**Factor 5: Sample Size (20%)**
- 2x minimum samples: 100% score
- 1x minimum samples: 80% score
- 0.5x minimum samples: 60% score
- 0.25x minimum samples: 40% score
- <0.25x minimum samples: 20% score

### 2. Forecast Quality

Assessment of forecast reliability:

- **Excellent** (≥85% confidence): Highly reliable with strong historical backing
- **Good** (70-84% confidence): Reliable with good historical support
- **Fair** (50-69% confidence): Moderately reliable, use with caution
- **Poor** (<50% confidence): Limited reliability, consider alternatives

### 3. Historical Accuracy

Track prediction vs actual accuracy:

- Calculated from past predictions
- Error rate = |predicted - actual| / actual
- Accuracy = (1 - error rate) * 100
- Default: 75% (when no history available)

### 4. Prediction Reliability

Consistency of predictions:

- Based on coefficient of variation of error margins
- Lower variance = higher reliability
- Score range: 55-100%

### 5. Risk Level

Risk assessment for business decisions:

- **Low** (<20% risk score): Safe to use for decisions
- **Medium** (20-40% risk score): Use with standard precautions
- **High** (40-60% risk score): Use with caution, have contingencies
- **Critical** (>60% risk score): Avoid major decisions

**Risk Score Calculation**:
```
risk_score = (100 - confidence) * 0.4 + 
             (100 - accuracy) * 0.3 + 
             (100 - reliability) * 0.3
```

---

## API Endpoints

### 1. GET /vendor/forecast/confidence/{forecast_type}

Get confidence score for a specific forecast type.

**Path Parameters**:
- `forecast_type`: short_term, daily, weekly, monthly

**Query Parameters**:
- `predicted_value` (int, required): The predicted value
- `horizon_days` (int, default: 7): Forecast horizon in days

**Response**:
```json
{
  "vendor_id": 123,
  "forecast_type": "daily",
  "predicted_value": 175,
  "confidence_percentage": 82.5,
  "confidence_level": "high",
  "forecast_quality": "good",
  "historical_accuracy": 78.3,
  "prediction_reliability": 85.2,
  "risk_level": "low",
  "factors": {
    "data_quality": {
      "score": 82.5,
      "sample_size": 45,
      "data_completeness": "high"
    },
    "pattern_stability": {
      "score": 78.3,
      "patterns_detected": 5,
      "trend_direction": "up"
    },
    "prediction_consistency": {
      "score": 85.2,
      "volatility": "low"
    },
    "forecast_quality": {
      "rating": "good",
      "description": "Forecast is reliable with good historical support"
    }
  },
  "recommendations": [
    "High confidence: Forecast is reliable for planning purposes",
    "Good forecast quality: Monitor actual results closely and adjust as needed",
    "Low risk level: Safe to use for business decisions"
  ]
}
```

### 2. GET /vendor/forecast/confidence/report/{forecast_type}

Get detailed confidence report for a forecast type.

**Path Parameters**:
- `forecast_type`: short_term, daily, weekly, monthly

**Response**:
```json
{
  "vendor_id": 123,
  "forecast_type": "daily",
  "status": "active",
  "total_predictions": 25,
  "average_accuracy": 78.5,
  "average_error_margin": 8.3,
  "accuracy_trend": "improving",
  "best_accuracy": 95.2,
  "worst_accuracy": 62.1,
  "recent_predictions": [
    {
      "date": "2024-01-15",
      "predicted": 25,
      "actual": 23,
      "accuracy": 92.0,
      "error_margin": 2
    }
  ],
  "insights": [
    "Good prediction accuracy (75-90%)",
    "Accuracy is improving over time",
    "Low error margin (8.3) - predictions are precise"
  ]
}
```

### 3. GET /vendor/forecast/confidence/summary

Get overall confidence summary across all forecast types.

**Response**:
```json
{
  "vendor_id": 123,
  "overall_accuracy": 79.8,
  "total_predictions": 85,
  "by_forecast_type": {
    "short_term": {
      "average_accuracy": 85.2,
      "total_predictions": 20,
      "accuracy_trend": "stable"
    },
    "daily": {
      "average_accuracy": 78.5,
      "total_predictions": 25,
      "accuracy_trend": "improving"
    },
    "weekly": {
      "average_accuracy": 76.3,
      "total_predictions": 20,
      "accuracy_trend": "stable"
    },
    "monthly": {
      "average_accuracy": 72.1,
      "total_predictions": 20,
      "accuracy_trend": "improving"
    }
  },
  "overall_rating": "good",
  "recommendations": [
    "Forecast confidence is good across all types"
  ]
}
```

### 4. GET /vendor/forecast/confidence/history/{forecast_type}

Get prediction history for a forecast type.

**Path Parameters**:
- `forecast_type`: short_term, daily, weekly, monthly

**Query Parameters**:
- `limit` (int, default: 20, max: 100): Number of records to return

**Response**:
```json
{
  "vendor_id": 123,
  "forecast_type": "daily",
  "total_records": 25,
  "history": [
    {
      "forecast_date": "2024-01-15",
      "predicted_value": 25,
      "actual_value": 23,
      "confidence_score": 82.5,
      "accuracy": 92.0,
      "error_margin": 2,
      "created_at": "2024-01-14T10:30:00"
    }
  ]
}
```

### 5. GET /vendor/forecast/confidence/levels

Get details for all confidence and risk levels.

**Response**:
```json
{
  "confidence_levels": {
    "high": {
      "label": "High Confidence",
      "color": "#10B981",
      "description": "Forecast is highly reliable for planning",
      "icon": "✓",
      "min_percentage": 80
    },
    "medium": {
      "label": "Medium Confidence",
      "color": "#F59E0B",
      "description": "Forecast is reasonably reliable with some uncertainty",
      "icon": "~",
      "min_percentage": 50
    },
    "low": {
      "label": "Low Confidence",
      "color": "#EF4444",
      "description": "Forecast has high uncertainty, use with caution",
      "icon": "!",
      "min_percentage": 0
    }
  },
  "risk_levels": {
    "low": {
      "label": "Low Risk",
      "color": "#10B981",
      "description": "Safe to use for business decisions",
      "min_score": 0
    },
    "medium": {
      "label": "Medium Risk",
      "color": "#F59E0B",
      "description": "Use with standard precautions",
      "min_score": 20
    },
    "high": {
      "label": "High Risk",
      "color": "#F97316",
      "description": "Use with caution, have contingency plans",
      "min_score": 40
    },
    "critical": {
      "label": "Critical Risk",
      "color": "#EF4444",
      "description": "Avoid major decisions based on this forecast",
      "min_score": 60
    }
  }
}
```

---

## Confidence Levels

### Visual Representation

**High Confidence (≥80%)**
- Color: Green (#10B981)
- Icon: ✓
- Description: Forecast is highly reliable for planning
- Action: Safe to use for business decisions

**Medium Confidence (50-80%)**
- Color: Yellow (#F59E0B)
- Icon: ~
- Description: Forecast is reasonably reliable with some uncertainty
- Action: Use with standard precautions

**Low Confidence (<50%)**
- Color: Red (#EF4444)
- Icon: !
- Description: Forecast has high uncertainty, use with caution
- Action: Consider gathering more data or use alternative methods

---

## Risk Assessment

### Risk Levels

**Low Risk (<20% risk score)**
- Color: Green (#10B981)
- Description: Safe to use for business decisions
- Recommendation: Proceed with confidence

**Medium Risk (20-40% risk score)**
- Color: Yellow (#F59E0B)
- Description: Use with standard precautions
- Recommendation: Validate with additional data

**High Risk (40-60% risk score)**
- Color: Orange (#F97316)
- Description: Use with caution, have contingency plans
- Recommendation: Have backup plans ready

**Critical Risk (>60% risk score)**
- Color: Red (#EF4444)
- Description: Avoid major decisions based on this forecast
- Recommendation: Gather more data or use alternative methods

---

## Frontend Integration

### Display Requirements

**1. Confidence Score Card**
```
┌─────────────────────────────────────┐
│  Forecast Confidence                │
│  ████████████████░░░░  82.5%        │
│  High Confidence ✓                  │
│  Based on historical data quality   │
└─────────────────────────────────────┘
```

**2. Confidence Level Badge**
- High: Green background with ✓ icon
- Medium: Yellow background with ~ icon
- Low: Red background with ! icon

**3. Detailed Breakdown**
```
┌─────────────────────────────────────┐
│  Confidence Details                 │
│  ┌───────────────────────────────┐  │
│  │ Forecast Quality: Good        │  │
│  │ Historical Accuracy: 78.3%    │  │
│  │ Prediction Reliability: 85.2% │  │
│  │ Risk Level: Low               │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

**4. Recommendations Panel**
```
┌─────────────────────────────────────┐
│  AI Recommendations                 │
│  • High confidence: Forecast is     │
│    reliable for planning            │
│  • Good forecast quality: Monitor   │
│    actual results closely           │
└─────────────────────────────────────┘
```

### Color Coding

```typescript
const getConfidenceColor = (confidence: number) => {
  if (confidence >= 80) return '#10B981'; // Green - High
  if (confidence >= 50) return '#F59E0B'; // Yellow - Medium
  return '#EF4444'; // Red - Low
};

const getConfidenceLabel = (confidence: number) => {
  if (confidence >= 80) return 'High';
  if (confidence >= 50) return 'Medium';
  return 'Low';
};
```

---

## Integration Guide

### Backend Integration

#### 1. Integrate with Enhanced Forecasting

```python
# app/modules/vendors/enhanced_forecasting_router.py
from app.modules.vendors.confidence_integration_service import ConfidenceIntegrationService

def get_comprehensive_forecast(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    vendor_id = _get_vendor_id(user, db)
    service = ConfidenceIntegrationService(db)
    return service.get_comprehensive_forecast_with_confidence(vendor_id)
```

#### 2. Add Confidence to Existing Forecasts

```python
# In enhanced_forecasting_service.py
from app.modules.vendors.confidence_scoring_service import ConfidenceScoringService

class EnhancedForecastingService:
    def __init__(self, db: Session):
        self.db = db
        self.confidence_service = ConfidenceScoringService(db)
    
    def forecast_daily(self, vendor_id: int, days: int = 7) -> Dict[str, Any]:
        # Existing forecast logic
        forecast = {...}
        
        # Add confidence score
        confidence_score = self.confidence_service.calculate_confidence(
            vendor_id=vendor_id,
            forecast_type="daily",
            predicted_value=forecast["summary"]["total_orders"],
            historical_data={"sample_size": 30, "patterns": [], "trend": "stable"},
            horizon_days=days,
        )
        
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
```

### Frontend Integration

#### 1. Display Confidence in Dashboard

```typescript
// EnhancedForecastDashboard.tsx
const getConfidenceColor = (confidence: number) => {
  if (confidence >= 80) return '#10B981'; // Green
  if (confidence >= 50) return '#F59E0B'; // Yellow
  return '#EF4444'; // Red
};

const getConfidenceLabel = (confidence: number) => {
  if (confidence >= 80) return 'High';
  if (confidence >= 50) return 'Medium';
  return 'Low';
};

// In component
<View style={styles.confidenceCard}>
  <Text style={styles.confidenceLabel}>Forecast Confidence</Text>
  <View style={styles.confidenceBar}>
    <View
      style={[
        styles.confidenceFill,
        {
          width: `${forecast.confidence_score.confidence_percentage}%`,
          backgroundColor: getConfidenceColor(
            forecast.confidence_score.confidence_percentage
          ),
        },
      ]}
    />
  </View>
  <Text style={styles.confidenceText}>
    {forecast.confidence_score.confidence_percentage}% - 
    {getConfidenceLabel(forecast.confidence_score.confidence_percentage)}
  </Text>
</View>
```

#### 2. Display Risk Level

```typescript
<View style={styles.riskCard}>
  <Text style={styles.riskLabel}>Risk Level</Text>
  <Text style={[
    styles.riskValue,
    {color: getRiskColor(forecast.confidence_score.risk_level)}
  ]}>
    {forecast.confidence_score.risk_level.toUpperCase()}
  </Text>
</View>
```

---

## Usage Examples

### Example 1: Get Confidence for Daily Forecast

```bash
curl -X GET "http://localhost:8000/v1/vendor/forecast/confidence/daily?predicted_value=175&horizon_days=7" \
  -H "Authorization: Bearer {token}"
```

### Example 2: Get Confidence Report

```bash
curl -X GET "http://localhost:8000/v1/vendor/forecast/confidence/report/daily" \
  -H "Authorization: Bearer {token}"
```

### Example 3: Get Overall Summary

```bash
curl -X GET "http://localhost:8000/v1/vendor/forecast/confidence/summary" \
  -H "Authorization: Bearer {token}"
```

### Example 4: Frontend Integration

```typescript
import {vendorApi} from '../services/vendorApi';

function ForecastDashboard() {
  const [forecast, setForecast] = useState(null);
  
  useEffect(() => {
    loadForecast();
  }, []);
  
  const loadForecast = async () => {
    const response = await vendorApi.getComprehensiveForecast();
    setForecast(response.data);
  };
  
  const renderConfidence = (confidence: any) => {
    const percentage = confidence.confidence_percentage;
    const level = confidence.confidence_level;
    const color = getConfidenceColor(percentage);
    
    return (
      <View style={styles.confidenceContainer}>
        <Text style={[styles.confidenceText, {color}]}>
          {percentage}% - {level.toUpperCase()}
        </Text>
        <View style={styles.confidenceBar}>
          <View style={[styles.confidenceFill, {width: `${percentage}%`, backgroundColor: color}]} />
        </View>
      </View>
    );
  };
  
  return (
    <ScrollView>
      {forecast?.daily && renderConfidence(forecast.daily.confidence_score)}
      {/* Other forecast horizons */}
    </ScrollView>
  );
}
```

---

## Performance Considerations

### Caching
- **Confidence scores**: Cache for 30 minutes
- **Historical data**: Cache for 1 hour
- **Reports**: Cache for 15 minutes

### Database Queries
- **Optimized**: Uses indexed queries on vendor_id and forecast_type
- **Efficient**: Single query for history retrieval
- **Paginated**: Limit/offset for large history sets

### Scalability
- **Horizontal**: Stateless service
- **Vertical**: Can handle 1000+ vendors concurrently
- **Background**: Can be extended with Celery for async confidence calculation

---

## Future Enhancements

### Phase 2: Advanced Metrics
- [ ] Confidence intervals (upper/lower bounds)
- [ ] Prediction intervals
- [ ] Seasonal confidence adjustments
- [ ] Vendor-specific confidence models

### Phase 3: ML Integration
- [ ] Automated confidence model training
- [ ] Feature importance for confidence factors
- [ ] Anomaly detection for confidence drops
- [ ] A/B testing for confidence algorithms

### Phase 4: Real-time Updates
- [ ] Real-time confidence updates as actuals come in
- [ ] WebSocket notifications for confidence changes
- [ ] Automated alerts for low confidence predictions

---

## Troubleshooting

### Low Confidence Scores
- **Cause**: Insufficient historical data
- **Solution**: Ensure vendor has at least 30 days of order history
- **Solution**: Check data availability scoring

### Inaccurate Confidence
- **Cause**: Historical accuracy not reflecting current performance
- **Solution**: Recalculate historical accuracy with recent data
- **Solution**: Adjust confidence calculation weights

### Missing History
- **Cause**: Predictions not being recorded
- **Solution**: Implement prediction recording in forecasting service
- **Solution**: Verify database schema for confidence_history table

---

## Appendix

### A. Database Schema

```sql
-- Confidence history table
CREATE TABLE confidence_history (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    forecast_type VARCHAR(50) NOT NULL,
    forecast_date DATE NOT NULL,
    predicted_value INTEGER NOT NULL,
    actual_value INTEGER,
    confidence_score FLOAT,
    accuracy FLOAT,
    error_margin FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_vendor_forecast_type (vendor_id, forecast_type),
    INDEX idx_forecast_date (forecast_date)
);

-- Confidence reports table (optional)
CREATE TABLE confidence_reports (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    forecast_type VARCHAR(50) NOT NULL,
    report_data JSONB NOT NULL,
    generated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_vendor_report (vendor_id, forecast_type, generated_at)
);
```

### B. Configuration

```python
# Confidence Scoring Configuration
CONFIDENCE_CONFIG = {
    "data_availability_thresholds": {
        "excellent": 100,
        "good": 50,
        "fair": 20,
        "poor": 10,
    },
    "consistency_thresholds": {
        "excellent": 0.3,
        "good": 0.5,
        "fair": 0.8,
        "poor": 1.2,
    },
    "pattern_deviation_threshold": 30,  # % deviation for strong pattern
    "min_samples": {
        "short_term": 30,
        "daily": 30,
        "weekly": 12,
        "monthly": 6,
    },
    "confidence_weights": {
        "data_availability": 0.25,
        "consistency": 0.20,
        "pattern_strength": 0.20,
        "horizon_distance": 0.15,
        "sample_size": 0.20,
    },
    "risk_weights": {
        "confidence": 0.4,
        "accuracy": 0.3,
        "reliability": 0.3,
    },
}
```

### C. Monitoring Metrics

```python
# Key metrics to track
- confidence_requests_total{endpoint, forecast_type}
- confidence_calculation_duration_seconds{forecast_type}
- confidence_score_avg{forecast_type, confidence_level}
- confidence_history_records_total{vendor_id}
- confidence_accuracy_avg{forecast_type}
- confidence_risk_distribution{risk_level}
```

---

## Contact & Support

- **Documentation**: [Wiki Link]
- **Issues**: [GitHub Issues]
- **Team**: [ML Team Slack Channel]