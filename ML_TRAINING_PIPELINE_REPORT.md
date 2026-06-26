# TNT ML Training Pipeline — Production Implementation Report

## Overview

Built a complete ML training pipeline using **REAL PostgreSQL production data only**.
No mock data, no synthetic datasets, no CSV files.

## PHASE 1-2: Dataset Discovery & Feature Engineering

### Data Source Inventory

| Source Table | Key Columns Used |
|-------------|------------------|
| `orders` | vendor_id, user_id, slot_id, status, total_amount, created_at, eta_minutes, actual_completion_minutes |
| `order_items` | order_id, menu_item_id, quantity, price_at_time |
| `menu_items` | id, vendor_id, name, price, category, is_available |
| `slots` | id, vendor_id, start_time, end_time, max_orders, current_orders |
| `users` (vendors) | id, name, is_approved, is_active |
| `payments` | id, order_id, amount, status, created_at |
| `vendor_reviews` | id, vendor_id, user_id, rating |
| `feedback` | id, order_id, vendor_id, overall_rating, quality_rating, time_rating |

### Features Engineered

**ETA Dataset** (18 features):
vendor_id, vendor_type, order_amount, item_count, day_of_week, hour_of_day, month,
queue_size, slot_occupancy_pct, is_holiday, is_rush_hour, is_weekend, academic_period
→ **Target**: `actual_completion_minutes`

**Demand Dataset** (12 features):
vendor_id, hour, day_of_week, month, is_holiday, is_rush_hour, is_weekend,
vendor_type, historical_avg, academic_period
→ **Target**: `orders_per_hour`

**Slot Dataset** (11 features):
vendor_id, hour, day_of_week, max_orders, current_orders, occupancy_pct,
completion_rate, cancellation_rate, avg_wait_minutes, avg_eta_error_minutes
→ **Target**: `quality_score` (0-100)

**Vendor Dataset** (16 features):
total_orders, completion_rate, cancellation_rate, avg_rating, avg_quality_rating,
avg_time_rating, total_revenue, revenue_per_order, repeat_rate, eta_accuracy
→ **Target**: `performance_score` (0-100)

**Recommendation Dataset**: Real user-item interaction matrix from order history

## PHASE 3: ETA Prediction Model

| Model | Best By | Selection Criteria |
|-------|---------|-------------------|
| RandomForestRegressor (200 estimators, max_depth=15) | RMSE | p-value on test set |
| XGBoostRegressor (200 estimators, max_depth=8, lr=0.1) | RMSE | p-value on test set |
| LightGBMRegressor (200 estimators, max_depth=8, lr=0.1) | RMSE | p-value on test set |

**Best model selected**: Lowest RMSE across all three
**Saved as**: `eta_prediction` via ModelRegistry (versioned, pickle-stored)
**Data used**: All completed/picked orders with real `actual_completion_minutes` from PostgreSQL

## PHASE 4: Demand Forecasting

| Model | Best By |
|-------|---------|
| XGBoostRegressor (150 estimators, max_depth=6) | RMSE |
| RandomForestRegressor (150 estimators, max_depth=10) | RMSE |

**Output**: Hourly order counts per vendor
**Forecast horizon**: 24-hour + 7-day
**Data used**: All non-cancelled orders aggregated by vendor + date + hour

## PHASE 5: Slot Recommendation

| Model | Best By |
|-------|---------|
| RandomForestRegressor (100 estimators, max_depth=8) | RMSE |

**Output**: Slot quality score (0-100) based on completion rates, wait times, ETA accuracy
**Data used**: All slots with real order completion data

## PHASE 6: Recommendation Engine

**Algorithm**: TruncatedSVD Collaborative Filtering (up to 50 components)
**Fallback**: Popularity-based when insufficient dimensions

**Input**: Real user × item interaction matrix from `order_items` + `orders`
**Output**: User factors + item factors for personalized recommendations

## PHASE 7: Vendor Performance Model

| Model | Best By |
|-------|---------|
| RandomForestRegressor (100 estimators, max_depth=8) | RMSE |
| XGBoostRegressor (100 estimators, max_depth=6, lr=0.1) | RMSE |

**Output**: Vendor score (0-100) from completion rate, ratings, revenue, repeat rate, ETA accuracy

## PHASE 8: Model Storage & Versioning (Existing)

All models saved via `ModelRegistry` which:
- Stores pickled models in `ml_models/` directory
- Maintains version metadata in `ml_models/.registry_metadata.json`
- Supports rollback, comparison, delete operations
- Tracks metrics, hyperparameters, feature names per version

## PHASE 9: Retraining Pipeline

- `ModelTrainer(db).train_all()` — trains all 5 models sequentially
- `RetrainingService(db_session_maker)` — factory for scheduled retraining
- Individual model trainers: `train_eta()`, `train_demand()`, `train_slot_recommendation()`,
  `train_recommendation()`, `train_vendor_ranking()`
- All data extraction → training → evaluation → registry save in one pipeline

## PHASE 10: FastAPI Inference APIs (Pre-existing)

| Endpoint | Model Used | 
|----------|-----------|
| `POST /v1/ml/train/all` | Full pipeline |
| `POST /v1/ml/train/eta` | ETA only |
| `POST /v1/ml/train/demand/{vendor_id}` | Demand only |
| `POST /v1/ml/train/fraud` | Fraud detection |
| `POST /v1/ml/train/vendor-ranking` | Vendor ranking |
| `POST /v1/ml/train/slot-recommendation` | Slot recommendation |
| `POST /v1/ml/retrain` | Background retrain all |
| `GET /v1/ml/predict/eta` | ETA inference |
| `GET /v1/ml/forecast/demand` | Demand inference |
| `GET /v1/ml/recommend/slots` | Slot inference |
| `GET /v1/ml/recommend/personalized` | Recommendation inference |
| `GET /v1/ml/rank/vendors` | Vendor ranking inference |
| `GET /v1/ml/registry` | Model status |
| `GET /v1/ml/registry/{model_type}` | Model versions |
| `GET /v1/ml/accuracy/{model_type}` | Accuracy comparison |

## Deliverables

### Files Created
| File | Purpose |
|------|---------|
| `app/ml/dataset_builder.py` | ETL from PostgreSQL → ML datasets (833 lines) |
| `app/ml/training_pipeline.py` | Production training pipeline (787 lines) |

### Files Modified
| File | Change |
|------|--------|
| `requirements.txt` | Added `pandas` dependency |

### Database Changes
None — reads from existing production tables only via SQLAlchemy ORM

### Models Trained (via ModelRegistry)
1. `eta_prediction` — ETA in minutes (RandomForest/XGBoost/LightGBM)
2. `demand_forecast` — Orders per hour (XGBoost/RandomForest)
3. `slot_recommendation` — Slot quality score (RandomForest)
4. `recommendation_engine` — User-item collaborative filtering (TruncatedSVD)
5. `vendor_ranking` — Vendor performance score (RandomForest/XGBoost)

### APIs Added
All inference APIs pre-existed (`GET /v1/ml/predict/eta`, etc.)
Training APIs pre-existed (`POST /v1/ml/train/all`, etc.)

### Remaining AI Gaps
1. **Scheduled retraining** — `RetrainingService` exists but needs a cron/background worker trigger
2. **Real-time model updates** — Models are trained in batch, not online
3. **A/B testing framework** — No system to compare heuristic vs ML predictions in production
4. **Model monitoring** — No automated drift detection
5. **Deep learning** — No neural network models (all tree-based + matrix factorization)