# ML Integration Map

**Audit Date:** 2026-07-29  
**Repository:** TNT (Tap N Take) FastAPI Backend  

---

## Executive Summary

This document maps the 5 core AI/ML capabilities across:
1. Heuristic planners in `app/modules/ai_intelligence/planners/` currently driving live API responses.
2. Trained ML models registered in `app/ml/` and stored in `ml_models/`.
3. Code paths calling `ModelRegistry.load()`.
4. Current heuristic formulas serving production traffic.

---

## Capabilities Integration Matrix

| Capability | (a) Currently Served By (`ai_intelligence/planners/`) | (b) Trained Model Exists in `app/ml` & `ml_models/` | (c) `ModelRegistry.load()` Called for Model Type | (d) Current Heuristic Formula (One Line) |
|---|---|---|---|---|
| **ETA Prediction** | `app/modules/ai_intelligence/planners/eta_engine.py` (and `enhanced_eta_engine.py`) | **Yes** (`eta_prediction` model type in `training_pipeline.py`; `.pkl` artifacts: `eta_prediction_v1.pkl`, `eta_prediction_v2.pkl`) | **No** (Only called in generic admin endpoints `/ml/explain/eta_prediction` & `seed_and_train.py`, not in live planner) | `predicted_eta = max(5, min(int(base_prep_time * queue_factor * efficiency_factor), 60))` where `base_prep_time` is 30d avg prep, `queue_factor` is slot utilization multiplier, `efficiency_factor = 2.0 - completion_rate` |
| **Demand Forecasting** | `app/modules/ai_intelligence/planners/demand_planner.py` | **Yes** (`demand_forecast` model type in `training_pipeline.py`; `.pkl` artifacts: `demand_forecast_v1.pkl`, `demand_forecast_v2.pkl`) | **No** (Only called in generic admin endpoints `/ml/explain/demand_forecast` & `seed_and_train.py`, not in live planner) | `forecast_orders = int((recent_30d_orders / max(days, 1)) * 1.05)` (30-day daily average multiplied by 5% growth projection for 7-day forecast) |
| **Vendor Ranking** | `app/modules/ai_intelligence/planners/vendor_ranker.py` | **Yes** (`vendor_ranking` model type in `training_pipeline.py`; `.pkl` artifacts: `vendor_ranking_v1.pkl`, `vendor_ranking_v2.pkl`) | **Yes** (Called in `app/modules/recommendations/smart_engine.py:492` & `ranking_service.py:719`, but **NOT** in `vendor_ranker.py`) | `rank_score = completion_speed*0.30 + success_rate*0.25 + satisfaction_score*0.20 + efficiency_score*0.15 + recent_performance*0.10` (0–100 score) |
| **Slot Recommendation** | `app/modules/ai_intelligence/planners/slot_planner.py` | **Yes** (`slot_recommendation` model type in `training_pipeline.py`; `.pkl` artifacts: `slot_recommendation_v1.pkl`, `slot_recommendation_v2.pkl`) | **Yes** (Called in `app/modules/recommendations/ranking_service.py:655`, but **NOT** in `slot_planner.py`) | `recommended_capacity = max(5, min(int(avg_orders_per_slot * speed_factor), 50))` where `speed_factor = 0.8 + (completion_rate * 0.4)` |
| **Fraud Detection** | **None** (Not in `ai_intelligence/planners/`; handled in `app/modules/fraud/fraud_rules.py` & `fraud_detection_service.py`) | **Yes** (`fraud_detection` model type in `training_pipeline.py`; `.pkl` artifacts: `fraud_detection_v1.pkl`, `fraud_detection_v2.pkl`) | **No** (Only called in generic admin endpoints `/ml/explain/fraud_detection` & `seed_and_train.py`, not in live fraud service) | Rule-based checks (rapid frequency > 3 in 5 min, total > $200 for new user, > 3 payment failures) setting `order.fraud_flag = True` when triggered |

---

## Detailed Audit Findings

### 1. Disconnect Between `ai_intelligence/planners` and `app/ml`
- The `ai_intelligence/planners/` directory uses pure SQL-aggregation heuristic logic (arithmetic averages, hardcoded growth factors, simple weighted sums).
- None of the planners in `ai_intelligence/planners/` import or invoke `ModelRegistry.load()`.
- While trained RandomForest/XGBoost/LightGBM model artifacts exist under `ml_models/` (e.g. `eta_prediction_v1.pkl`, `demand_forecast_v1.pkl`, `slot_recommendation_v1.pkl`, `vendor_ranking_v1.pkl`, `fraud_detection_v1.pkl`), they remain isolated in `app/ml/`.

### 2. Partial Calls to `ModelRegistry.load()`
- Model loading calls exist in `app/modules/recommendations/smart_engine.py` and `app/modules/recommendations/ranking_service.py` for `recommendation_engine`, `vendor_ranking`, and `slot_recommendation`.
- However, the primary `ai_intelligence` service layer (`service.py`, `analytics_service.py`) and planners (`eta_engine.py`, `demand_planner.py`, `vendor_ranker.py`, `slot_planner.py`) operate purely on heuristics.
