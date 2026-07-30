# TNT Backend

## Code Quality Automation

This project is configured with:

- **pre-commit** hooks for local quality checks
- **GitHub Actions CI** for linting and tests on push/PR

### Local setup

```bash
pip install -r requirements.txt
pip install pre-commit ruff pytest
pre-commit install
```

### Run hooks manually

```bash
pre-commit run --all-files
```

## Database Migrations (Alembic)

This project now uses Alembic for schema evolution.

### Install

```bash
pip install -r requirements.txt
```

### Existing databases (already have tables)

Stamp the baseline once, then upgrade:

```bash
alembic stamp 20260214_0001
alembic upgrade head
```

### New databases

```bash
alembic upgrade head
```

### Create a new migration

```bash
alembic revision --autogenerate -m "your change message"
alembic upgrade head
```

## Production Runtime Settings

Set these in `.env` for production:

```bash
APP_ENV=production
CORS_ORIGINS=https://your-frontend.example.com
DB_REVISION_GUARD=true
ENABLE_METRICS=true
ERROR_BUDGET_PERCENT=1.0
ERROR_BUDGET_MIN_REQUESTS=100
ALERT_WEBHOOK_URL=https://alerts.example.com/hooks/tnt
LOG_JSON=true
```

Operational endpoints:

- `GET /health/live`
- `GET /health/ready`
- `GET /health/deep`
- `GET /metrics`

Operational docs and scripts:

- Runbook: `PRODUCTION_RUNBOOK.md`
- Load smoke test: `python scripts/load_smoke.py --base-url http://127.0.0.1:8000`

### CI checks

CI runs the following in `.github/workflows/ci.yml`:

1. `ruff check . --select I`
2. `pytest -q`

### Notes

Current test scripts include request-based integration tests that may require an API server in some local environments. Keep that in mind when running tests manually outside CI.

## AI Signal API Migration

Signal APIs are now owned by the AI module.

- Canonical endpoints:
	- `GET /ai/signals`
	- `GET /ai/signals/rush-hour`
	- `GET /ai/signals/slot-suggestions`
	- `GET /ai/signals/reorder-prompts`
- Legacy `/signals/*` endpoints are removed and return `404`.

## Training ML Models

To generate synthetic training data, run the training pipeline for all models, and save the resulting artifacts to the registry, run the following standalone script:

```bash
python seed_and_train.py
```

### Expected Output

```
Initializing database session...
Step 1: Seeding synthetic training data...
Starting AI seed data generation...
Generating categories...
  ✓ Generated 10 categories
Generating 10 vendors...
  ✓ Generated 10 vendors
...
✓ All seed data generated successfully!
Step 2: Running training pipeline...
Training ETA Prediction...
Finished training ETA Prediction: success
...
================================================================================
                       ML MODEL TRAINING PIPELINE SUMMARY                       
================================================================================
Model Name                | Features | Metric Value (RMSE/Acc)   | Artifact Path
--------------------------------------------------------------------------------
ETA Prediction            | 7        | RMSE: 2.1032              | ml_models/eta_prediction/eta_prediction_v1.pkl
Demand Forecasting        | 9        | RMSE: 1.4589              | ml_models/demand_forecast/demand_forecast_v1.pkl
Slot Recommendation       | 10       | RMSE: 4.8912              | ml_models/slot_recommendation/slot_recommendation_v1.pkl
Recommendation Engine     | 0        | ExpVar: 0.8920            | ml_models/recommendation_engine/recommendation_engine_v1.pkl
Vendor Ranking            | 15       | RMSE: 3.1254              | ml_models/vendor_ranking/vendor_ranking_v1.pkl
Fraud Detection           | 6        | Accuracy: 0.9650          | ml_models/fraud_detection/fraud_detection_v1.pkl
================================================================================
```

### Artifacts Storage

Trained model artifacts (.pkl files) are stored on disk under the directory specified by the `MODEL_STORAGE_DIR` environment variable (defaults to `ml_models/` at the project root).

## AI/ML Testing & Safety Validation

The AI/ML subsystem (`app.ml` and `app.modules.ai_intelligence`) is governed by strict unit testing, safety regression rules, and a **95% code coverage gate**.

### AI/ML Coverage Gate Command (95% Minimum)

```bash
python -m pytest \
  tests/test_ml_engine.py tests/test_ml_bridge.py tests/test_ml_predictions.py \
  tests/test_ml_registry.py tests/test_ml_router.py tests/test_ml_promotion_retraining.py \
  tests/test_training_pipeline_coverage.py tests/test_ml_safety_regression.py \
  tests/test_model_performance_validation.py tests/test_targeted_aiml_coverage.py \
  tests/test_ai_service.py tests/test_analytics_service.py tests/test_enhanced_eta_engine.py \
  tests/test_redis_ai_cache.py tests/test_vendor_speed_service.py \
  tests/test_production_upgrades.py tests/test_preference_engine.py \
  tests/test_ai_routers.py tests/test_ai.py tests/test_analytics.py \
  --cov=app.ml --cov=app.modules.ai_intelligence \
  --cov-report=term-missing --cov-fail-under=95 -q
```

### Safety Regression Gates

The following safety controls fall back to calibrated heuristics when data volume or confidence thresholds are not met:

1. **ETA Model Gate:** Vendors with `< 30` completed orders use calibrated baseline heuristics.
2. **Demand Model Gate:** Vendors with `< 90` days of order history use time-bucket heuristics.
3. **Slot Safety Hard Limit:** Slots at `>= 90%` capacity are strictly excluded regardless of ML recommendations.
4. **Vendor Ranking Express Pickup:** Express pickup eligibility is enforced as a hard filter independent of model ranking scores.
5. **Deterministic Fraud Rules:** Hard risk rules trigger regardless of ML confidence or availability.
6. **Payload Source Transparency:** AI response payloads expose a `source` field (`heuristic` or `model`) for auditability.

### Model Performance Metrics & Backtesting

- **Fraud Model Metrics:** Exposes `accuracy`, `precision`, `recall`, `f1`, and `cv_f1` in training outputs and model registry metadata.
- **ETA Backtest Engine (`backtest_eta`):** Validates `within_3_min_pct`, `within_5_min_pct`, and `mae_minutes`.
- **Vendor Ranking Backtest Engine (`backtest_vendor_ranking`):** Evaluates `top_1_hit_rate` and `top_3_hit_rate`.

For complete details, see the latest formal report: [docs/AI_ML_Testing_Validation_Report_2026-07-30.md](docs/AI_ML_Testing_Validation_Report_2026-07-30.md).


