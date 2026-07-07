# Production Runbook

## Pre-deploy checklist

- Ensure migrations are up-to-date:
  - `alembic upgrade head`
- Confirm service checks on target environment:
  - `GET /health/live`
  - `GET /health/ready`
  - `GET /health/deep`
- Confirm required environment variables:
  - `APP_ENV=production`
  - `CORS_ORIGINS=https://your-frontend.example.com`
  - `DB_REVISION_GUARD=true`
  - `ENABLE_METRICS=true`
  - `ERROR_BUDGET_PERCENT=1.0`
  - `ERROR_BUDGET_MIN_REQUESTS=100`
  - `ALERT_WEBHOOK_URL=https://...` (optional)

## Canary rollout

1. Deploy to 10% traffic.
2. Observe `/metrics` for 10-15 minutes:
   - `error_rate_percent <= 1.0`
   - stable `avg_latency_ms` on key routes.
3. If healthy, increase to 50%, then 100%.

## Rollback plan

1. Route traffic to previous stable release.
2. Validate with:
   - `GET /health/ready`
   - `GET /health/deep`
3. If rollback required due to migration mismatch, restore DB snapshot and re-run:
   - `alembic upgrade head` on fixed artifact.

## Backup and restore drill

- Backup:
  - PostgreSQL: `pg_dump -Fc <db_name> > backup.dump`
- Restore (staging drill):
  - `pg_restore -d <target_db> backup.dump`
- Validate restored environment with health endpoints and smoke tests.

## Load smoke validation

Run against deployed environment:

```bash
python scripts/load_smoke.py --base-url https://your-api.example.com --concurrency 20 --requests-per-worker 25
```

Expected:
- Failure count near zero.
- Stable RPS and no readiness degradation.

## System Dependencies

### libmagic (required by python-magic for content-based MIME detection)

`python-magic` depends on the system library `libmagic`.

```
# On Ubuntu/Debian:
apt-get install -y libmagic1

# On Alpine:
apk add --no-cache libmagic
```

## Fresh Database Setup

When provisioning a new database from scratch, follow these steps to initialise
the schema correctly through Alembic:

```bash
cd tnt-backend-main

# 1. Create the database (PostgreSQL example)
createdb tnt_production

# 2. Set DATABASE_URL in .env
echo 'DATABASE_URL=postgresql://user:pass@localhost:5432/tnt_production' >> .env

# 3. Apply all migrations — this runs the baseline (creates core tables)
#    followed by every subsequent migration in dependency order.
alembic upgrade head

# 4. Verify the database is at the expected migration head
alembic current
# Expected: 20260624_0024 (or whatever the latest revision is)
```

### Existing databases (production / staging)

The baseline migration was originally a no-op (the schema was created by
``Base.metadata.create_all()``).  After the June 2026 re-audit the baseline
was backfilled with actual DDL.  To avoid re-running it on already-provisioned
databases, stamp it as already applied:

```bash
alembic stamp 20260214_0001
```

This tells Alembic "the schema at revision 20260214_0001 is already present"
without executing any DDL.  After stamping, verify the chain is continuous:

```bash
alembic upgrade head   # should be a no-op if already at HEAD
alembic check          # confirm no circular / missing dependencies
```

### What the baseline contains

The script in ``alembic/versions/20260214_0001_baseline.py`` creates every
table that was originally bootstrapped outside of Alembic:

- ``users``, ``slots``, ``orders``, ``order_items``, ``notifications``,
  ``payments``, ``menu_items``, ``stationery_jobs``, ``vendors``,
  ``feedback``, ``rewards``, ``vouchers``, ``stationery_services``,
  ``complaints``, ``ledger_entries``, ``off_peak_policies``,
  ``group_carts``, ``group_members``, ``cart_items``, ``order_history``

Tables added by later migrations (``slot_bookings``, ``ml_models``,
``vendor_reviews``, ``slot_capacity_rules``, ``slot_rules``, etc.) are
NOT in the baseline — they are created by their own ``upgrade()`` functions.

### Safety guard

The startup function ``verify_database_revision()`` in the main app entry
point checks that the database revision matches the expected HEAD before
the server accepts traffic.  This prevents a mismatched schema from silently
serving requests.

## Changelog Notes

### 2026-02-14 - Signals APIs migrated into AI module

- Canonical signal endpoints are now served from AI:
  - `GET /ai/signals`
  - `GET /ai/signals/rush-hour`
  - `GET /ai/signals/slot-suggestions`
  - `GET /ai/signals/reorder-prompts`
- Legacy `GET /signals/*` routes were removed and should return `404`.
- Post-deploy verification:
  - Confirm all `/ai/signals*` endpoints return `200` with a `signals` payload.
  - Confirm `/signals` and `/signals/*` return `404`.
