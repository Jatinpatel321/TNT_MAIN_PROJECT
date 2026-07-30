# ML Baseline Coverage Report

**Execution Date:** 2026-07-29  
**Command Run:** `pytest --cov=app.modules.ai_intelligence --cov=app.ml --cov-report=term-missing`  
**Target Packages:** `app.modules.ai_intelligence`, `app.ml`  

---

## Target Package Coverage Summary

| Module | Statements | Missing | Coverage | Missing Lines |
|---|---|---|---|---|
| **`app/ml/__init__.py`** | 2 | 0 | **100%** | None |
| **`app/ml/dataset_builder.py`** | 281 | 242 | **14%** | 48, 59-71, 80, 89-106, 117, 126-174, 185, 194-250, 261, 270-327, 338, 347-400, 411, 420-466, 477, 486-538, 549, 558-591, 607-628 |
| **`app/ml/explain.py`** | 41 | 41 | **0%** | 1-125 |
| **`app/ml/features.py`** | 110 | 84 | **24%** | 38-70, 84-118, 131-163, 175-188, 201-213, 226-258, 271-290, 303-315, 328-340 |
| **`app/ml/ml_models_model.py`** | 17 | 1 | **94%** | 34 |
| **`app/ml/predictions.py`** | 218 | 174 | **20%** | 60-61, 65, 83-162, 179-253, 270-345, 361-420, 437-497 |
| **`app/ml/registry.py`** | 134 | 104 | **22%** | 39-44, 48, 62-138, 150, 165-201, 205-230, 236-237, 241-271, 276-297, 301-314, 318-337, 340-347, 350-369 |
| **`app/ml/router.py`** | 110 | 110 | **0%** | 1-285 |
| **`app/ml/training_pipeline.py`** | 405 | 405 | **0%** | 1-830 |
| **`app/modules/ai_intelligence/__init__.py`** | 0 | 0 | **100%** | None |
| **`app/modules/ai_intelligence/analytics_service.py`** | 174 | 174 | **0%** | 1-420 |
| **`app/modules/ai_intelligence/enhanced_eta_router.py`** | 16 | 16 | **0%** | 1-35 |
| **`app/modules/ai_intelligence/learning/historical_learning.py`** | 145 | 145 | **0%** | 1-280 |
| **`app/modules/ai_intelligence/planners/demand_planner.py`** | 49 | 49 | **0%** | 1-205 |
| **`app/modules/ai_intelligence/planners/eta_engine.py`** | 47 | 7 | **85%** | 24, 66-75, 139-140 |
| **`app/modules/ai_intelligence/planners/refund_eta_engine.py`** | 44 | 44 | **0%** | 1-160 |
| **`app/modules/ai_intelligence/planners/reorder_engine.py`** | 41 | 41 | **0%** | 1-120 |
| **`app/modules/ai_intelligence/planners/slot_planner.py`** | 65 | 65 | **0%** | 1-199 |
| **`app/modules/ai_intelligence/planners/vendor_ranker.py`** | 73 | 73 | **0%** | 1-218 |
| **`app/modules/ai_intelligence/production_upgrades.py`** | 185 | 185 | **0%** | 1-375 |
| **`app/modules/ai_intelligence/redis_ai_cache.py`** | 67 | 67 | **0%** | 1-182 |
| **`app/modules/ai_intelligence/router.py`** | 60 | 16 | **73%** | 24-34, 52-54, 71, 79, 90-95, 107 |
| **`app/modules/ai_intelligence/schemas.py`** | 36 | 0 | **100%** | None |
| **`app/modules/ai_intelligence/service.py`** | 114 | 101 | **11%** | 39-65, 87-133, 146-218, 226, 237-279 |
| **`app/modules/ai_intelligence/signals.py`** | 29 | 29 | **0%** | 1-83 |
| **`app/modules/ai_intelligence/utils/confidence.py`** | 17 | 2 | **88%** | 20, 24 |
| **`app/modules/ai_intelligence/vendor_speed_router.py`** | 21 | 21 | **0%** | 1-42 |
| **`app/modules/ai_intelligence/vendor_speed_service.py`** | 119 | 119 | **0%** | 1-218 |
| **TOTAL (Target Modules)** | **1,969** | **1,473** | **25%** | — |

---

## High-Level Findings

1. **`app.ml` Overall Coverage: ~12%**
   - Core ML infrastructure (`router.py`, `explain.py`, `training_pipeline.py`) has 0% test coverage.
   - Model execution (`predictions.py` @ 20%) and dataset builders (`dataset_builder.py` @ 14%) have low coverage.
   - Registry metadata (`registry.py` @ 22%) has limited testing.

2. **`app.modules.ai_intelligence` Overall Coverage: ~18%**
   - Planners: `eta_engine.py` (85%) is covered by basic tests, but `demand_planner.py` (0%), `slot_planner.py` (0%), `vendor_ranker.py` (0%), and `reorder_engine.py` (0%) are untested.
   - Services: `redis_ai_cache.py` (0%), `vendor_speed_service.py` (0%), and `analytics_service.py` (0%) lack coverage.
