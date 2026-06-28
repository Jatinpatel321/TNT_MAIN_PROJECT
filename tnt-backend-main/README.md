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

