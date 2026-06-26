from contextlib import asynccontextmanager
import uuid
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.emergency import is_emergency_shutdown_enabled
from app.core.logging_setup import configure_logging
from app.core.observability import observability
from app.core.rate_limit_middleware import RateLimitMiddleware
from app.core.redis import redis_client
from app.core.security import require_role
from app.core.startup_checks import validate_production_settings, verify_database_revision
from app.database.init_db import init_db
from app.database.session import engine
from app.api.v1 import api_v1_router
from app.modules.orders.lifecycle_simulator import order_lifecycle_simulator

from fastapi import Response
from starlette.requests import Request


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.LOG_JSON)
    validate_production_settings(settings.APP_ENV, settings.CORS_ORIGINS)
    init_db()
    if settings.DB_REVISION_GUARD:
        verify_database_revision()

    import sys
    # Only run the lifecycle simulator in non-production environments and not during pytest
    if settings.APP_ENV != "production" and "pytest" not in sys.modules:
        await order_lifecycle_simulator.start()

    yield

    if settings.APP_ENV != "production" and "pytest" not in sys.modules:
        await order_lifecycle_simulator.stop()


app = FastAPI(title="TNT – Tap N Take", lifespan=lifespan)

# CORS: reads from settings.CORS_ORIGINS (env var CORS_ORIGINS).
# In development defaults to localhost origins; in production must be explicit.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Extra safety: ensure CORS headers exist even if an exception path
# bypasses Starlette's normal CORSMiddleware handling.
from app.core.cors_always import ForceCORSAlwaysMiddleware

app.add_middleware(ForceCORSAlwaysMiddleware)

# Ensure CORS preflight (OPTIONS) always returns valid CORS headers.
# Some failure/short-circuit paths can still yield responses without the expected headers.
@app.middleware("http")
async def cors_preflight_handler(request: Request, call_next):
    if request.method == "OPTIONS":
        origin = request.headers.get("origin", "*")
        req_method = request.headers.get("access-control-request-method", "*")

        res = Response(status_code=204)
        res.headers["Access-Control-Allow-Origin"] = origin
        res.headers["Access-Control-Allow-Methods"] = req_method
        res.headers["Access-Control-Allow-Headers"] = request.headers.get(
            "access-control-request-headers", "*"
        )
        res.headers["Access-Control-Max-Age"] = "86400"
        return res

    return await call_next(request)

# Rate-limiting middleware — protects /payments/* and /stationery/payments/*
# by IP address.  Auth route limits are handled via route-level dependencies
# in app/modules/auth/router.py.
app.add_middleware(RateLimitMiddleware)



MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SHUTDOWN_GUARDED_PREFIXES = (
    # legacy (un-prefixed) paths
    "/cart",
    "/checkout",
    "/orders",
    "/payments",
    "/stationery",
    "/groups",
    # v1 paths
    "/v1/cart",
    "/v1/checkout",
    "/v1/orders",
    "/v1/payments",
    "/v1/stationery",
    "/v1/groups",
)
SHUTDOWN_EXEMPT_PATHS = {
    "/admin/shutdown",
    "/v1/admin/shutdown",
}


@app.middleware("http")
async def emergency_shutdown_gate(request: Request, call_next):
    path = request.url.path
    if request.method in MUTATING_METHODS:
        if path not in SHUTDOWN_EXEMPT_PATHS and path.startswith(SHUTDOWN_GUARDED_PREFIXES):
            if is_emergency_shutdown_enabled():
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": "Service temporarily unavailable due to emergency shutdown",
                        "emergency_shutdown": True,
                    },
                )

    return await call_next(request)


@app.middleware("http")
async def capture_metrics(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id

    response = await observability.track_request(request, call_next)
    if settings.ENABLE_METRICS:
        observability.maybe_alert_error_budget(
            threshold_percent=settings.ERROR_BUDGET_PERCENT,
            min_requests=settings.ERROR_BUDGET_MIN_REQUESTS,
            alert_webhook_url=settings.ALERT_WEBHOOK_URL,
        )

    response.headers["x-request-id"] = request_id
    return response


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health")
def health_check() -> JSONResponse:
    """Admin frontend health check — returns db + redis status."""
    db_status = "ok"
    redis_status = "ok"
    shutdown_active = is_emergency_shutdown_enabled()

    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    except Exception:
        db_status = "error"

    try:
        redis_client.ping()
    except Exception:
        redis_status = "error"

    overall = "ok" if db_status == "ok" else "degraded"
    return JSONResponse(
        status_code=200,
        content={
            "status": overall,
            "db": db_status,
            "redis": redis_status,
            "shutdown_active": shutdown_active,
        },
    )



@app.get("/health/ready")
def readiness() -> JSONResponse:
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")

        if settings.DB_REVISION_GUARD:
            verify_database_revision()

        return JSONResponse(status_code=200, content={"status": "ready"})
    except Exception as exc:
        return JSONResponse(status_code=503, content={"status": "not_ready", "detail": str(exc)})


@app.get("/health/deep")
def deep_readiness() -> JSONResponse:
    checks = {
        "database": "fail",
        "redis": "fail",
        "migrations": "skip" if not settings.DB_REVISION_GUARD else "fail",
    }

    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        checks["database"] = "ok"

        redis_client.ping()
        checks["redis"] = "ok"

        if settings.DB_REVISION_GUARD:
            verify_database_revision()
            checks["migrations"] = "ok"

        return JSONResponse(status_code=200, content={"status": "ready", "checks": checks})
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "checks": checks, "detail": str(exc)},
        )


def get_metrics_dependency():
    import sys
    if settings.APP_ENV != "production" or "pytest" in sys.modules:
        return lambda: {"role": "admin"}
    from app.core.security import require_role
    return require_role("admin")


@app.get("/metrics")
def metrics(user=Depends(get_metrics_dependency())) -> dict[str, Any]:
    snapshot = observability.snapshot()
    snapshot["error_budget_percent_threshold"] = settings.ERROR_BUDGET_PERCENT
    snapshot["error_budget_min_requests"] = settings.ERROR_BUDGET_MIN_REQUESTS
    return snapshot

# ── v1 (canonical, going-forward) ────────────────────────────────────────
# All domain routers live under /v1/<domain>/... via the aggregator.
app.include_router(api_v1_router)

# ── Legacy unversioned routers (backward-compat, deprecated) ─────────────
from app.modules.admin.router import router as admin_router
from app.modules.calendar.router import router as calendar_router
from app.modules.auditlog.router import router as audit_log_router
from app.modules.ai_intelligence.router import router as ai_router
from app.modules.auth.router import router as auth_router
from app.modules.auth.refresh_router import router as refresh_router
from app.modules.cart.router import checkout_router, router as cart_router
from app.modules.complaints.router import router as complaints_router
from app.modules.feedback.router import router as feedback_router
from app.modules.group_cart.router import router as group_cart_router
from app.modules.ledger.router import router as ledger_router
from app.modules.menu.router import router as menu_router
from app.modules.notifications.router import router as notification_router
from app.modules.orders.router import router as orders_router
from app.modules.payments.router import router as payments_router
from app.modules.payments.webhook import router as razorpay_webhook_router
from app.modules.rewards.router import router as rewards_router
from app.modules.slots.router import router as slots_router
from app.modules.stationery.payment_router import router as stationery_payment_router
from app.modules.stationery.router import router as stationery_router
from app.modules.users.router import router as users_router
from app.modules.users.profile_router import router as profile_router
from app.modules.vendors.router import router as vendors_router
from app.modules.vendors.auth_router import router as vendor_auth_router
from app.modules.vendors.ai_router import router as vendor_ai_router
from app.modules.vendors.retention_router import router as vendor_retention_router
from app.modules.vendors.analytics_router import router as vendor_analytics_router
from app.modules.vendors.settlement_router import router as vendor_settlement_router
from app.modules.vendors.profile_router import router as vendor_profile_router
from app.modules.vendors.dashboard_router import router as vendor_dashboard_router
from app.modules.vendors.business_hours_router import router as vendor_business_hours_router
from app.modules.vendors.demand_dashboard_router import router as vendor_demand_dashboard_router
from app.modules.vendors.inventory_router import router as vendor_inventory_router
from app.modules.vendors.promotion_router import router as vendor_promotion_router
from app.modules.vendors.historical_learning_router import router as vendor_history_router
from app.modules.vendors.enhanced_forecasting_router import router as vendor_forecast_router
from app.modules.vendors.confidence_router import router as vendor_confidence_router
from app.modules.vendors.performance_router import router as vendor_performance_router
from app.modules.vendors.ai_inventory_router import router as vendor_ai_inventory_router
from app.modules.vendors.peak_hour_router import router as vendor_peak_hour_router
from app.modules.vendors.validation_router import router as vendor_validation_router
from app.modules.orders.ws_router import router as orders_ws_router
from app.modules.orders.vendor_ws_router import router as vendor_ws_router
from app.modules.recommendations.router import router as recommendations_router
from app.modules.recommendations.new_router import router as new_recommendations_router
from app.modules.recommendations.prediction_router import router as prediction_router
from app.modules.search.router import router as search_router
from app.ml.router import router as ml_router

app.include_router(auth_router, deprecated=True)
app.include_router(refresh_router, deprecated=True)
app.include_router(users_router, deprecated=True)
app.include_router(profile_router, deprecated=True)
app.include_router(slots_router, deprecated=True)
app.include_router(orders_router, deprecated=True)
app.include_router(payments_router, deprecated=True)
app.include_router(razorpay_webhook_router, deprecated=True)
app.include_router(admin_router, deprecated=True)
app.include_router(calendar_router, deprecated=True)
app.include_router(audit_log_router, deprecated=True)
app.include_router(stationery_router, deprecated=True)
app.include_router(stationery_payment_router, deprecated=True)
app.include_router(notification_router, deprecated=True)
app.include_router(rewards_router, deprecated=True)
app.include_router(group_cart_router, deprecated=True)
app.include_router(ai_router, deprecated=True)
app.include_router(menu_router, deprecated=True)
app.include_router(vendors_router, deprecated=True)
app.include_router(vendor_auth_router, deprecated=True)
app.include_router(vendor_ai_router, deprecated=True)
app.include_router(vendor_retention_router, deprecated=True)
app.include_router(vendor_analytics_router, deprecated=True)
app.include_router(vendor_settlement_router, deprecated=True)
app.include_router(vendor_profile_router, deprecated=True)
app.include_router(vendor_dashboard_router, deprecated=True)
app.include_router(vendor_business_hours_router, deprecated=True)
app.include_router(vendor_demand_dashboard_router, deprecated=True)
app.include_router(vendor_inventory_router, deprecated=True)
app.include_router(vendor_promotion_router, deprecated=True)
app.include_router(vendor_history_router, deprecated=True)
app.include_router(vendor_forecast_router, deprecated=True)
app.include_router(vendor_confidence_router, deprecated=True)
app.include_router(vendor_performance_router, deprecated=True)
app.include_router(vendor_ai_inventory_router, deprecated=True)
app.include_router(vendor_peak_hour_router, deprecated=True)
app.include_router(vendor_validation_router, deprecated=True)
app.include_router(ledger_router, deprecated=True)
app.include_router(feedback_router, deprecated=True)
app.include_router(complaints_router, deprecated=True)
app.include_router(cart_router, deprecated=True)
app.include_router(checkout_router, deprecated=True)
app.include_router(recommendations_router, deprecated=True)
app.include_router(new_recommendations_router, deprecated=True)
app.include_router(prediction_router, deprecated=True)
app.include_router(search_router, deprecated=True)
app.include_router(ml_router, deprecated=True)
app.include_router(orders_ws_router, deprecated=True)
app.include_router(vendor_ws_router, deprecated=True)

# ── Static file mount (not versioned) ────────────────────────────────────
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
