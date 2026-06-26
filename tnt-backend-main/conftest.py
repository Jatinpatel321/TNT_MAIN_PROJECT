"""
Global pytest configuration.

Auto-patches the app's Redis client with fakeredis for every test in this
workspace.  This means:

  • No test needs a live Redis server.
  • Rate-limit counters are isolated per test (fakeredis.FakeRedis() is
    reset for each test via ``autouse=True``).
  • Tests that previously passed without caring about Redis continue to
    work — they just have a harmless in-memory Redis available.
  • Tests that explicitly want to control Redis (e.g. test_rate_limiting.py)
    can still patch ``app.core.rate_limit.redis_client`` with their own
    fakeredis instance inside the test; their local patch takes precedence
    over this session-level one.
"""

from __future__ import annotations

import fakeredis
import pytest


@pytest.fixture(autouse=True)
def _auto_fake_redis(monkeypatch):
    """Replace the live Redis client with an isolated fakeredis instance.

    ``autouse=True`` means this fixture is applied to *every* test
    automatically without needing to declare it explicitly.

    A fresh ``FakeRedis`` instance is created for each test, so rate-limit
    counters and OTP keys do not bleed between tests.
    """
    fake = fakeredis.FakeRedis(decode_responses=True)

    # Patch every module that holds a reference to the real redis_client.
    monkeypatch.setattr("app.core.redis.redis_client", fake)
    monkeypatch.setattr("app.core.rate_limit.redis_client", fake)
    monkeypatch.setattr("app.core.rate_limit_middleware.redis_client", fake)
    # otp_service uses "from app.core.redis import redis_client" (local binding)
    # so it must be patched on the otp_service module directly.
    monkeypatch.setattr("app.modules.auth.otp_service.redis_client", fake)
    # Patch cache_service.redis_client to prevent cache state bleed between tests
    monkeypatch.setattr("app.core.redis_cache.cache_service.redis_client", fake)
    # notifications.service imports redis_client inside function body,
    # so it resolves from app.core.redis at call time — already patched above.

    yield fake
