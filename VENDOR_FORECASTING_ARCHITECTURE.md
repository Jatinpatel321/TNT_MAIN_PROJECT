# Vendor AI Forecasting Architecture
## Production-Ready Implementation Analysis

---

## Executive Summary

The existing vendor AI forecasting system is a **multi-layered architecture** combining:
- **Heuristic-based predictions** (VendorAIService)
- **ML-powered predictions** (MLPredictionService with XGBoost/LightGBM/RandomForest)
- **Enhanced ETA engine** (EnhancedETAEngine with menu complexity & workload analysis)
- **Real-time speed adjustment** (VendorSpeedService)
- **Redis caching layer** (AIServicesRedisCache)
- **Postgres-backed model registry** (ModelRegistry)

This document provides a complete analysis of the existing implementation and identifies production-ready upgrade paths.

---

## 1. Existing Forecasting Workflow

### 1.1 Demand Forecasting Pipeline

```
User Request
    ↓
DemandDashboardRouter (/vendors/demand-dashboard/*)
    ↓
DemandDashboardService
    ├─→ get_demand_overview() - Real-time + historical analysis
    ├─→ get_stock_prediction() - Inventory forecasting
    ├─→ get_rush_prediction() - Hourly rush prediction
    └─→ get_full_dashboard() - Aggregates all above
    ↓
VendorAIService (AI layer)
    ├─→ get_daily_forecast() - Day-of-week averages + trend
    ├─→ get_weekly_forecast() - Weekly linear trend
    ├─→ get_monthly_forecast() - Monthly projections
    ├─→ get_popular_items() - Item popularity + trends
    ├─→ get_peak_time_prediction() - Hourly distribution
    ├─→ get_stationery_workload() - Service-specific prediction
    ├─→ get_waste_reduction_insights() - Cancellation analysis
    ├─→ get_inventory_suggestions() - Stock recommendations
    └─→ get_ai_recommendations() - Comprehensive AI insights
    ↓
MLPredictionService (ML layer)
    ├─→ forecast_demand() - Hourly ML predictions
    └─→ ModelRegistry - Loads trained demand models
    ↓
PostgreSQL (Historical data)
    └─→ Orders table (30-90 day lookback)
```

### 1.2 ETA Prediction Pipeline

```
Order Placement
    ↓
EnhancedETAEngine.predict_eta_enhanced()
    ├─→ Base ETA from ETAEngine (existing)
    ├─→ Menu complexity scoring
    │   ├─→ Base prep time
    │   ├─→ Historical variance
    │   ├─→ Category complexity
    │   └─→ Name complexity
    ├─→ Vendor workload analysis
    │   ├─→ Active orders
    │   ├─→ Avg prep time
    │   └─→ Completion rate
    ├─→ Slot occupancy
    │   ├─→ Current orders / max capacity
    │   └─→ Time-of-day factor
    └─→ Delay risk calculation
    ↓
VendorSpeedService (Real-time adjustment)
    ├─→ measure_avg_preparation_time()
    ├─→ measure_current_queue()
    ├─→ measure_completion_rate()
    ├─→ measure_current_workload()
    └─→ calculate_vendor_speed_score()
    ↓
Final ETA = Enhanced ETA × Speed Adjustment Factor
```

### 1.3 Vendor Speed Adjustment Pipeline

```
Real-time Query
    ↓
VendorSpeedService.get_vendor_speed_metrics()
    ├─→ calculate_vendor_speed_score() (0.0-1.0)
    │   ├─→ Prep time score (30%)
    │   ├─→ Completion rate (30%)
    │   ├─→ Queue score (20%)
    │   └─→ Workload score (20%)
    ├─→ calculate_predicted_waiting_time()
    └─→ calculate_suggested_delay()
    ↓
Speed Labels: FAST → NORMAL → BUSY → VERY_BUSY
Adjustment Factors: 0.85 → 1.0 → 1.2 → 1.5
```

---

## 2. Existing Prediction Engine

### 2.1 ML Models (ModelRegistry)

| Model Type | Algorithm | Features | Status |
|------------|-----------|----------|--------|
| `eta_prediction` | XGBoost/LightGBM/RandomForest | vendor_id, queue_depth, occupancy, item_count, hour, weekday, rush_hour | Active |
| `demand_forecast_vendor{N}` | Time-series (per vendor) | hour, weekday, day_of_month, month, rush_hour | Active |
| `slot_recommendation` | Regression | occupancy, hour, weekday, rush_hour, avg_completion, max_orders | Active |
| `vendor_ranking` | Regression | completion_rate, avg_rating, repeat_rate, cancellations, total_orders | Active |
| `fraud_detection` | Classifier | total_orders, cancelled, cancellation_rate, avg_order_value, device_token, fraud_flagged | Active |

### 2.2 Model Storage

- **Metadata**: PostgreSQL `ml_models` table
  - model_name, model_version, trained_at, accuracy, status
  - metrics_json, hyperparams_json, features_json
- **Artifacts**: Disk-based pickle files (`ml_models/{model_type}/{version}.pkl`)
- **Versioning**: Automatic version numbering + rollback support
- **Registry API**: `/ml/registry/*` endpoints

### 2.3 Training Pipeline

```python
# app/ml/training_pipeline.py
- train_eta_models() - Compares XGBoost vs LightGBM vs RandomForest
- train_demand_forecast() - Per-vendor time-series model
- train_fraud_detection() - Classification model
- train_vendor_ranking() - Regression model
- train_slot_recommendation() - Regression model
- run_full_training_pipeline() - Trains all models
- RetrainingService - Background scheduled retraining
```

---

## 3. Existing AI Dashboard

### 3.1 Vendor Dashboard Endpoints

| Endpoint | Service Method | Data Provided |
|----------|----------------|---------------|
| `GET /vendors/demand-dashboard/` | `get_full_dashboard()` | Complete dashboard |
| `GET /vendors/demand-dashboard/overview` | `get_demand_overview()` | Today's orders, predictions, trends |
| `GET /vendors/demand-dashboard/stock-prediction` | `get_stock_prediction()` | Inventory levels, restock needs |
| `GET /vendors/demand-dashboard/rush-prediction` | `get_rush_prediction()` | Hourly rush predictions |

### 3.2 ML Analytics Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /ml/registry` | Model registry summary |
| `GET /ml/registry/{model_type}` | List model versions |
| `POST /ml/registry/{model_type}/rollback/{version_num}` | Rollback model |
| `POST /ml/train/all` | Train all models |
| `POST /ml/train/eta` | Train ETA model |
| `POST /ml/train/demand/{vendor_id}` | Train demand model |
| `POST /ml/train/fraud` | Train fraud detection |
| `POST /ml/train/vendor-ranking` | Train vendor ranking |
| `POST /ml/train/slot-recommendation` | Train slot recommendation |
| `POST /ml/retrain` | Background retraining |
| `GET /ml/predict/eta` | ML-powered ETA |
| `GET /ml/forecast/demand` | ML demand forecast |
| `GET /ml/recommend/slots` | ML slot recommendation |
| `GET /ml/recommend/personalized` | Hybrid recommendations |
| `GET /ml/rank/vendors` | ML vendor ranking |
| `GET /ml/detect/fraud` | Fraud detection |
| `GET /ml/explain/{model_type}` | Feature importance |
| `GET /ml/accuracy/{model_type}` | Model accuracy tracking |

### 3.3 AI Intelligence Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /ai/enhanced-eta/{order_id}` | Enhanced ETA with ML factors |
| `GET /ai/eta-factors/{order_id}` | Detailed ETA breakdown |
| `GET /ai/vendor-speed/{vendor_id}` | Vendor speed metrics |
| `GET /ai/vendor-speed/batch` | Batch vendor speeds |
| `GET /ai/vendor-speed/waiting-time/{vendor_id}` | Predicted waiting time |
| `GET /ai/vendor-speed/suggested-delay/{vendor_id}` | Order delay suggestion |
| `POST /ai/vendor-speed/update-eta/{order_id}` | Dynamic ETA update |

---

## 4. Historical Data Tables

### 4.1 Primary Data Sources

```sql
-- Orders table (core historical data)
SELECT 
    vendor_id,
    created_at,
    status,
    eta_minutes,
    actual_completion_minutes,
    slot_id,
    total_amount,
    fraud_flag
FROM orders
WHERE created_at >= NOW() - INTERVAL '90 days'

-- Order items (for menu-level analysis)
SELECT 
    menu_item_id,
    order_id,
    quantity
FROM order_items

-- Menu items (for complexity scoring)
SELECT 
    id,
    vendor_id,
    name,
    category,
    price,
    is_available
FROM menu_items

-- Slots (for capacity analysis)
SELECT 
    id,
    vendor_id,
    start_time,
    end_time,
    current_orders,
    max_orders,
    status
FROM slots

-- Inventory (for stock prediction)
SELECT 
    menu_item_id,
    current_stock,
    low_stock_threshold,
    auto_disable
FROM inventory

-- Vendor reviews (for ranking)
SELECT 
    vendor_id,
    rating,
    created_at
FROM vendor_reviews
```

### 4.2 Feature Extraction

```python
# app/ml/features.py
- extract_eta_features() - ETA prediction features
- is_rush_hour() - Rush hour detection
- build_user_item_matrix() - Collaborative filtering matrix
- ETA_FEATURE_NAMES - Feature name mapping
```

---

## 5. Redis Cache Implementation

### 5.1 Cache Categories

| Category | TTL | Prefix | Purpose |
|----------|-----|--------|---------|
| `recommendations` | 5 min | `ai:recs` | User recommendations |
| `recommendations_ranked` | 5 min | `ai:recs:ranked` | Ranked recommendations |
| `personalized_vendors` | 10 min | `ai:vendors` | Vendor suggestions |
| `personalized_menu` | 5 min | `ai:menu` | Menu recommendations |
| `eta_prediction` | 1 min | `ai:eta` | ETA predictions |
| `eta_factors` | 2 min | `ai:eta:factors` | ETA factor breakdown |
| `vendor_speed` | 2 min | `ai:speed` | Vendor speed metrics |
| `trending_items` | 10 min | `ai:trending` | Trending menu items |
| `trending_vendors` | 10 min | `ai:trending:vendor` | Trending vendors |
| `popular_items` | 30 min | `ai:popular` | Popular items |
| `popular_vendors` | 30 min | `ai:popular:vendor` | Popular vendors |
| `recently_viewed` | 30 min | `ai:viewed` | User view history |
| `user_preferences` | 1 hour | `ai:prefs` | User preferences |
| `user_behavior` | 1 hour | `ai:behavior` | Behavior patterns |
| `prediction_cache` | 5 min | `ai:pred` | General predictions |
| `vendor_prediction` | 5 min | `ai:pred:vendor` | Vendor predictions |
| `group_suggestions` | 10 min | `ai:group` | Group order suggestions |
| `group_payments` | 2 min | `ai:group:payments` | Payment calculations |

### 5.2 Cache Features

- **TTL Management**: Per-category TTL configuration
- **Cache Invalidation**: Pattern-based invalidation
- **Performance Monitoring**: Hit/miss tracking, latency measurement
- **Decorator Support**: `@cache_ai_result()` for easy caching
- **Fallback**: Graceful degradation if Redis unavailable

---

## 6. PostgreSQL Models

### 6.1 Core Tables

```sql
-- Orders (primary historical data)
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    vendor_id INTEGER,
    slot_id INTEGER,
    status VARCHAR(50),
    eta_minutes INTEGER,
    actual_completion_minutes INTEGER,
    created_at TIMESTAMP,
    total_amount FLOAT,
    fraud_flag BOOLEAN
);

-- Order Items (menu-level granularity)
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER,
    menu_item_id INTEGER,
    quantity INTEGER
);

-- Menu Items (complexity scoring)
CREATE TABLE menu_items (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER,
    name VARCHAR(255),
    category VARCHAR(100),
    price FLOAT,
    is_available BOOLEAN
);

-- Slots (capacity management)
CREATE TABLE slots (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    current_orders INTEGER,
    max_orders INTEGER,
    status VARCHAR(50)
);

-- Inventory (stock prediction)
CREATE TABLE inventory (
    menu_item_id INTEGER PRIMARY KEY,
    current_stock INTEGER,
    low_stock_threshold INTEGER,
    auto_disable BOOLEAN
);

-- Vendor Reviews (ranking)
CREATE TABLE vendor_reviews (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER,
    user_id INTEGER,
    rating FLOAT,
    created_at TIMESTAMP
);

-- ML Models (model registry)
CREATE TABLE ml_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100),
    model_version VARCHAR(100),
    trained_at TIMESTAMP,
    accuracy FLOAT,
    file_path TEXT,
    status VARCHAR(20),
    metrics_json TEXT,
    hyperparams_json TEXT,
    features_json TEXT
);

-- User Behaviour (recommendations)
CREATE TABLE user_behaviour (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    menu_item_id INTEGER,
    interaction_type VARCHAR(50),
    created_at TIMESTAMP
);

-- Prediction History (accuracy tracking)
CREATE TABLE prediction_history (
    id SERIAL PRIMARY KEY,
    model_type VARCHAR(100),
    predicted_value FLOAT,
    actual_value FLOAT,
    created_at TIMESTAMP
);
```

---

## 7. Production-Ready Architecture Upgrade Plan

### 7.1 Current Strengths

✅ **Multi-layered prediction**: Heuristic + ML + Real-time adjustment  
✅ **Model versioning**: Postgres-backed registry with rollback  
✅ **Comprehensive caching**: Redis with TTL and invalidation  
✅ **Explainability**: Feature importance and confidence scores  
✅ **Historical data**: 30-90 day lookback windows  
✅ **Modular design**: Separate services for ETA, speed, demand  
✅ **API coverage**: 20+ endpoints for forecasting  

### 7.2 Production Upgrade Requirements

#### A. **Observability & Monitoring**

```python
# Add to all services
- Structured logging with correlation IDs
- Metrics export (Prometheus format)
- Health check endpoints
- Model performance monitoring
- Cache hit/miss dashboards
- Prediction accuracy tracking
```

#### B. **Resilience & Fault Tolerance**

```python
# Add circuit breakers
- ML model fallback to heuristic
- Redis fallback to database
- Graceful degradation on service failure
- Retry logic with exponential backoff
- Timeout configuration
```

#### C. **Scalability Improvements**

```python
# Add async processing
- Background model training
- Batch prediction processing
- Queue-based cache warming
- Connection pooling optimization
- Read replicas for historical queries
```

#### D. **Data Quality & Validation**

```python
# Add data validation
- Input schema validation (Pydantic)
- Outlier detection in historical data
- Data freshness checks
- Missing data imputation
- Feature drift detection
```

#### E. **API Governance**

```python
# Add API management
- Rate limiting per endpoint
- Request/response validation
- API versioning strategy
- OpenAPI documentation
- Request tracing
```

### 7.3 Recommended Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway (FastAPI)                     │
│  ┌──────────────┬──────────────┬──────────────────────────┐  │
│  │ Demand       │ ETA          │ Vendor Speed             │  │
│  │ Dashboard    │ Prediction   │ Adjustment               │  │
│  │ Router       │ Router       │ Router                   │  │
│  └──────────────┴──────────────┴──────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                              │
│  ┌──────────────┬──────────────┬──────────────────────────┐  │
│  │ Demand       │ Enhanced     │ Vendor Speed             │  │
│  │ Dashboard    │ ETA Engine   │ Service                  │  │
│  │ Service      │              │                          │  │
│  ├──────────────┼──────────────┼──────────────────────────┤  │
│  │ Vendor AI    │ ML           │ Redis AI Cache           │  │
│  │ Service      │ Prediction   │ Service                  │  │
│  │              │ Service      │                          │  │
│  └──────────────┴──────────────┴──────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    ML Layer                                   │
│  ┌──────────────┬──────────────┬──────────────────────────┐  │
│  │ Model        │ Training     │ Feature                  │  │
│  │ Registry     │ Pipeline     │ Engineering              │  │
│  │ (Postgres)   │              │                          │  │
│  └──────────────┴──────────────┴──────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                 │
│  ┌──────────────┬──────────────┬──────────────────────────┐  │
│  │ PostgreSQL   │ Redis        │ ML Model                 │  │
│  │ (Historical) │ (Cache)      │ Artifacts                │  │
│  │              │              │ (Pickle)                 │  │
│  └──────────────┴──────────────┴────────────────