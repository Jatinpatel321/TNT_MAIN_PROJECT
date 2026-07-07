"""
API Versioning QA — test_api_versioning.py

Acceptance criteria (PROMPT 9):
  • All domain endpoints are accessible under /v1/<domain>/...
  • Legacy /<domain>/... routes still respond (backward-compat)
  • Health / infrastructure endpoints remain at the root (unversioned)
  • OpenAPI schema exposes /v1/* paths
  • Rate-limit middleware guards /v1/payments/* paths
  • Emergency-shutdown guard covers /v1/* guarded prefixes
  • GET /v1/openapi-version returns the canonical version document
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_db
from app.core.security import get_current_user
from app.main import app, SHUTDOWN_GUARDED_PREFIXES, SHUTDOWN_EXEMPT_PATHS
from app.modules.users.model import User, UserRole

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database.base import Base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def student(db_session):
    u = User(phone="9200000001", name="VStudent", role=UserRole.STUDENT, is_active=True)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture()
def client(db_session, student):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: {
        "id": student.id,
        "phone": student.phone,
        "role": student.role.value,
    }
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture()
def anon_client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper: collect all registered paths from the OpenAPI schema
# ---------------------------------------------------------------------------


def _openapi_paths(client: TestClient) -> set[str]:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    return set(resp.json()["paths"].keys())


# ---------------------------------------------------------------------------
# 1. All v1 routes exist in the OpenAPI schema
# ---------------------------------------------------------------------------


EXPECTED_V1_PREFIXES = [
    "/v1/auth/send-otp",
    "/v1/auth/verify-otp",
    "/v1/payments/razorpay/initiate/{order_id}",
    "/v1/payments/razorpay/verify/{payment_id}",
    "/v1/payments/razorpay/refund/{payment_id}",
    "/v1/orders",
    "/v1/users",
    "/v1/slots",
    "/v1/admin",
    "/v1/stationery",
    "/v1/rewards",
    "/v1/groups",
    "/v1/menu",
    "/v1/vendors",
    "/v1/ledger",
    "/v1/feedback",
    "/v1/complaints",
    "/v1/cart",
    "/v1/ai",
]


class TestV1RoutesRegistered:
    def test_v1_auth_send_otp_in_schema(self, anon_client):
        paths = _openapi_paths(anon_client)
        assert "/v1/auth/send-otp" in paths

    def test_v1_auth_verify_otp_in_schema(self, anon_client):
        paths = _openapi_paths(anon_client)
        assert "/v1/auth/verify-otp" in paths

    def test_v1_payments_initiate_in_schema(self, anon_client):
        paths = _openapi_paths(anon_client)
        assert "/v1/payments/razorpay/initiate/{order_id}" in paths

    def test_v1_payments_refund_in_schema(self, anon_client):
        paths = _openapi_paths(anon_client)
        assert "/v1/payments/razorpay/refund/{payment_id}" in paths

    def test_v1_orders_in_schema(self, anon_client):
        paths = _openapi_paths(anon_client)
        assert any(p.startswith("/v1/orders") for p in paths)

    def test_v1_stationery_in_schema(self, anon_client):
        paths = _openapi_paths(anon_client)
        assert any(p.startswith("/v1/stationery") for p in paths)

    def test_all_expected_v1_prefixes_covered(self, anon_client):
        """Every domain must have at least one /v1/* route in the schema."""
        paths = _openapi_paths(anon_client)
        missing = [
            prefix for prefix in EXPECTED_V1_PREFIXES
            if not any(p.startswith(prefix.split("{")[0]) for p in paths)
        ]
        assert not missing, f"Missing v1 route prefixes in schema: {missing}"


# ---------------------------------------------------------------------------
# 2. Legacy routes still respond (backward-compat)
# ---------------------------------------------------------------------------


class TestLegacyRoutesBackwardCompat:
    def test_legacy_auth_send_otp_in_schema(self, anon_client):
        paths = _openapi_paths(anon_client)
        assert "/auth/send-otp" in paths

    def test_legacy_payments_initiate_in_schema(self, anon_client):
        paths = _openapi_paths(anon_client)
        assert "/payments/razorpay/initiate/{order_id}" in paths

    def test_legacy_orders_in_schema(self, anon_client):
        paths = _openapi_paths(anon_client)
        assert any(p.startswith("/orders") and not p.startswith("/v1") for p in paths)

    def test_legacy_send_otp_responds(self, anon_client):
        """Legacy /auth/send-otp must still return a real response (not 404)."""
        with patch("app.modules.auth.router.generate_otp"):
            resp = anon_client.post("/auth/send-otp", json={"phone": "9200000099"})
        assert resp.status_code != 404

    def test_v1_send_otp_responds(self, anon_client):
        """Versioned /v1/auth/send-otp must also return a real response."""
        with patch("app.modules.auth.router.generate_otp"):
            resp = anon_client.post("/v1/auth/send-otp", json={"phone": "9200000088"})
        assert resp.status_code != 404


# ---------------------------------------------------------------------------
# 3. Infrastructure endpoints remain unversioned
# ---------------------------------------------------------------------------


class TestInfraEndpointsUnversioned:
    def test_health_live_at_root(self, anon_client):
        resp = anon_client.get("/health/live")
        assert resp.status_code == 200

    def test_health_ready_at_root(self, anon_client):
        resp = anon_client.get("/health/ready")
        assert resp.status_code in (200, 503)  # 503 if DB guard enabled

    def test_metrics_at_root(self, anon_client):
        resp = anon_client.get("/metrics")
        assert resp.status_code == 200

    def test_no_v1_health_live(self, anon_client):
        """/v1/health/* should NOT exist — infra is intentionally unversioned."""
        resp = anon_client.get("/v1/health/live")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 4. Shutdown guard covers /v1/* prefixes
# ---------------------------------------------------------------------------


class TestShutdownGuardCoversV1:
    def test_v1_payments_in_guarded_prefixes(self):
        assert "/v1/payments" in SHUTDOWN_GUARDED_PREFIXES

    def test_v1_orders_in_guarded_prefixes(self):
        assert "/v1/orders" in SHUTDOWN_GUARDED_PREFIXES

    def test_v1_cart_in_guarded_prefixes(self):
        assert "/v1/cart" in SHUTDOWN_GUARDED_PREFIXES

    def test_v1_stationery_in_guarded_prefixes(self):
        assert "/v1/stationery" in SHUTDOWN_GUARDED_PREFIXES

    def test_v1_groups_in_guarded_prefixes(self):
        assert "/v1/groups" in SHUTDOWN_GUARDED_PREFIXES

    def test_v1_admin_shutdown_in_exempt_paths(self):
        assert "/v1/admin/shutdown" in SHUTDOWN_EXEMPT_PATHS

    def test_v1_payment_blocked_during_shutdown(self, client):
        with patch("app.main.is_emergency_shutdown_enabled", return_value=True):
            resp = client.post("/v1/payments/razorpay/initiate/1")
        assert resp.status_code == 503

    def test_v1_orders_blocked_during_shutdown(self, client):
        with patch("app.main.is_emergency_shutdown_enabled", return_value=True):
            resp = client.post("/v1/orders")
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# 5. Rate-limit middleware covers /v1/payments/* prefix
# ---------------------------------------------------------------------------


class TestRateLimitCoversV1:
    def test_v1_payment_prefix_in_middleware_guarded_list(self):
        from app.core.rate_limit_middleware import _GUARDED_PREFIXES
        assert "/v1/payments/" in _GUARDED_PREFIXES

    def test_v1_stationery_payment_prefix_in_middleware_guarded_list(self):
        from app.core.rate_limit_middleware import _GUARDED_PREFIXES
        assert "/v1/stationery/payments/" in _GUARDED_PREFIXES


# ---------------------------------------------------------------------------
# 6. OpenAPI schema: both /v1/* and legacy /* paths co-exist
# ---------------------------------------------------------------------------


class TestOpenApiSchemaStructure:
    def test_schema_has_v1_and_legacy_paths(self, anon_client):
        paths = _openapi_paths(anon_client)
        v1_paths = [p for p in paths if p.startswith("/v1/")]
        legacy_paths = [p for p in paths if not p.startswith("/v1/") and p not in ("/health/live", "/health/ready", "/health/deep", "/metrics", "/openapi.json")]
        assert len(v1_paths) > 0, "No /v1/* paths found in schema"
        assert len(legacy_paths) > 0, "No legacy paths found — backward-compat broken"

    def test_schema_version_field(self, anon_client):
        resp = anon_client.get("/openapi.json")
        info = resp.json().get("info", {})
        # FastAPI defaults to "0.1.0" — we just assert the field exists
        assert "version" in info
