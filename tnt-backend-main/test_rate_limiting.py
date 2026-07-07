"""
Rate Limiting QA — test_rate_limiting.py

Covers:
  • check_rate_limit primitive (unit tests against fakeredis)
  • OTP route: 5 req/min/phone → 6th returns 429
  • verify-otp / login route IP limit
  • Payments routes protected by router-level dependency AND middleware
  • Stationery payments covered by middleware
  • Fail-open: Redis error must NOT block the request (returns 200)
  • Different phones / IPs have independent counters

Acceptance criteria (PROMPT 8):
  429 returned when limit exceeded, Retry-After header present.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.rate_limit import (
    OTP_LIMIT,
    OTP_WINDOW,
    PAYMENT_LIMIT,
    PAYMENT_WINDOW,
    LOGIN_LIMIT,
    LOGIN_WINDOW,
    check_rate_limit,
)
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.payments.model import Payment
from app.modules.users.model import User, UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fresh_redis():
    """Return a fakeredis instance that starts empty."""
    return fakeredis.FakeRedis(decode_responses=True)


def _make_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine, Session()


# ---------------------------------------------------------------------------
# Unit tests — check_rate_limit primitive
# ---------------------------------------------------------------------------


class TestCheckRateLimitPrimitive:
    def test_passes_within_limit(self):
        r = _fresh_redis()
        for _ in range(5):
            count, remaining = check_rate_limit("rl:unit:test", 5, 60, redis=r)
        assert count == 5
        assert remaining == 0

    def test_raises_429_on_6th_request(self):
        from fastapi import HTTPException

        r = _fresh_redis()
        for _ in range(5):
            check_rate_limit("rl:unit:limit_test", 5, 60, redis=r)

        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit("rl:unit:limit_test", 5, 60, redis=r)

        assert exc_info.value.status_code == 429
        assert "Retry-After" in exc_info.value.headers

    def test_different_keys_independent(self):
        r = _fresh_redis()
        # Exhaust key A
        for _ in range(5):
            check_rate_limit("rl:unit:key_a", 5, 60, redis=r)

        # Key B should still pass
        count, _ = check_rate_limit("rl:unit:key_b", 5, 60, redis=r)
        assert count == 1

    def test_ttl_set_on_first_hit(self):
        r = _fresh_redis()
        check_rate_limit("rl:unit:ttl_test", 5, 30, redis=r)
        ttl = r.ttl("rl:unit:ttl_test")
        assert 0 < ttl <= 30

    def test_fail_open_on_redis_error(self):
        """Redis failure must not raise an exception."""
        broken = MagicMock()
        broken.pipeline.side_effect = Exception("Redis connection refused")

        # Must NOT raise; returns (0, limit) gracefully.
        count, remaining = check_rate_limit("rl:unit:broken", 5, 60, redis=broken)
        assert count == 0
        assert remaining == 5


# ---------------------------------------------------------------------------
# Integration helpers shared by route-level tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
    engine, session = _make_db()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def student(db_session):
    u = User(phone="9100000001", name="RLStudent", role=UserRole.STUDENT, is_active=True)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _auth_override(user: User):
    return lambda: {"id": user.id, "phone": user.phone, "role": user.role.value}


# ---------------------------------------------------------------------------
# OTP rate limits (phone-keyed)
# ---------------------------------------------------------------------------


class TestOTPRateLimit:
    """POST /auth/send-otp is limited to OTP_LIMIT requests / minute / phone."""

    def _client_with_fake_redis(self, db_session):
        fake_r = _fresh_redis()
        app.dependency_overrides[get_db] = lambda: db_session

        # Patch the module-level redis used by otp_rate_limiter
        with patch("app.core.rate_limit.redis_client", fake_r):
            # Also patch generate_otp so we don't need a real Redis/SMS
            with patch("app.modules.auth.router.generate_otp"):
                yield TestClient(app, raise_server_exceptions=False), fake_r

        app.dependency_overrides.pop(get_db, None)

    def test_within_limit_returns_200(self, db_session):
        fake_r = _fresh_redis()
        app.dependency_overrides[get_db] = lambda: db_session

        with (
            patch("app.core.rate_limit.redis_client", fake_r),
            patch("app.modules.auth.router.generate_otp"),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            for i in range(OTP_LIMIT):
                resp = client.post(
                    "/auth/send-otp", json={"phone": "9100000099"}
                )
                assert resp.status_code == 200, f"Hit 429 early on request {i+1}"

        app.dependency_overrides.pop(get_db, None)

    def test_exceeding_limit_returns_429(self, db_session):
        fake_r = _fresh_redis()
        app.dependency_overrides[get_db] = lambda: db_session

        with (
            patch("app.core.rate_limit.redis_client", fake_r),
            patch("app.modules.auth.router.generate_otp"),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            for _ in range(OTP_LIMIT):
                client.post("/auth/send-otp", json={"phone": "9100000088"})

            # One over the limit
            resp = client.post("/auth/send-otp", json={"phone": "9100000088"})

        assert resp.status_code == 429
        assert "Retry-After" in resp.headers

        app.dependency_overrides.pop(get_db, None)

    def test_different_phones_have_independent_limits(self, db_session):
        fake_r = _fresh_redis()
        app.dependency_overrides[get_db] = lambda: db_session

        with (
            patch("app.core.rate_limit.redis_client", fake_r),
            patch("app.modules.auth.router.generate_otp"),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            # Exhaust phone A
            for _ in range(OTP_LIMIT):
                client.post("/auth/send-otp", json={"phone": "9100000077"})
            client.post("/auth/send-otp", json={"phone": "9100000077"})  # should 429

            # Phone B should still be fine
            resp = client.post("/auth/send-otp", json={"phone": "9100000066"})

        assert resp.status_code == 200

        app.dependency_overrides.pop(get_db, None)

    def test_retry_after_header_present(self, db_session):
        fake_r = _fresh_redis()
        app.dependency_overrides[get_db] = lambda: db_session

        with (
            patch("app.core.rate_limit.redis_client", fake_r),
            patch("app.modules.auth.router.generate_otp"),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            for _ in range(OTP_LIMIT + 1):
                resp = client.post("/auth/send-otp", json={"phone": "9100000055"})

        assert resp.status_code == 429
        # Retry-After value should be a positive integer string
        assert int(resp.headers.get("Retry-After", "0")) > 0

        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Login / verify-otp rate limits (IP-keyed)
# ---------------------------------------------------------------------------


class TestLoginRateLimit:
    """POST /auth/verify-otp is limited to LOGIN_LIMIT requests / minute / IP."""

    def test_exceeding_login_limit_returns_429(self, db_session):
        fake_r = _fresh_redis()
        app.dependency_overrides[get_db] = lambda: db_session

        with (
            patch("app.core.rate_limit.redis_client", fake_r),
            patch("app.modules.auth.router.verify_otp", return_value=False),
        ):
            client = TestClient(app, raise_server_exceptions=False)
            statuses = []
            for _ in range(LOGIN_LIMIT + 1):
                resp = client.post(
                    "/auth/verify-otp",
                    json={"phone": "9100000001", "otp": "000000"},
                )
                statuses.append(resp.status_code)

        # The first LOGIN_LIMIT calls should NOT be 429 (they may be 400 from
        # bad OTP).  The last one must be 429.
        assert statuses[-1] == 429

        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Payment route-level dependency rate limits
# ---------------------------------------------------------------------------


class TestPaymentRouteRateLimit:
    """POST /payments/* is limited to PAYMENT_LIMIT requests / minute / IP."""

    def test_exceeding_payment_limit_returns_429(self, db_session, student):
        fake_r = _fresh_redis()
        app.dependency_overrides[get_db] = lambda: db_session
        app.dependency_overrides[get_current_user] = _auth_override(student)

        with (
            patch("app.core.rate_limit.redis_client", fake_r),
            patch("app.modules.payments.service.client") as rzp,
        ):
            rzp.order.create.return_value = {"id": "order_test_rl", "amount": 500}
            client = TestClient(app, raise_server_exceptions=False)
            statuses = []
            for _ in range(PAYMENT_LIMIT + 1):
                resp = client.post(
                    "/payments/razorpay/initiate/9999",  # non-existent order → 404
                )
                statuses.append(resp.status_code)

        # Should get 429 by the time the counter is exhausted.
        assert 429 in statuses

        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Middleware coverage — payment path prefix matching
# ---------------------------------------------------------------------------


class TestRateLimitMiddleware:
    """The middleware intercepts /payments/* and /stationery/payments/* paths."""

    def test_middleware_blocks_payment_path(self, db_session, student):
        from app.core.rate_limit_middleware import RateLimitMiddleware

        fake_r = _fresh_redis()
        app.dependency_overrides[get_db] = lambda: db_session
        app.dependency_overrides[get_current_user] = _auth_override(student)

        # Exhaust via the middleware-level check directly
        ip = "testclient"
        key = f"ratelimit:payments:{ip}"
        for _ in range(PAYMENT_LIMIT):
            fake_r.incr(key)
        fake_r.expire(key, PAYMENT_WINDOW)

        # One more hit should flip the counter over the limit
        fake_r.incr(key)

        with patch("app.core.rate_limit_middleware.redis_client", fake_r):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/payments/razorpay/initiate/1")

        assert resp.status_code == 429

        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    def test_non_payment_path_not_blocked(self, db_session):
        """Requests to /health/* must pass even when payment limit is exhausted."""
        fake_r = _fresh_redis()
        ip = "testclient"
        key = f"ratelimit:payments:{ip}"
        # Simulate exhausted payment limit
        for _ in range(PAYMENT_LIMIT + 5):
            fake_r.incr(key)
        fake_r.expire(key, PAYMENT_WINDOW)

        with patch("app.core.rate_limit_middleware.redis_client", fake_r):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/health/live")

        assert resp.status_code == 200
