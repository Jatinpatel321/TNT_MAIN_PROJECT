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
