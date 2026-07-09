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

    # Policy modules hold their own redis_client bindings (from-imports), and
    # university_policy falls through to the LIVE database via SessionLocal on
    # a cache miss — patch the bindings and pre-seed the cache with the
    # default (disabled) policy so test outcomes never depend on whatever
    # policy state the real deployment database happens to hold.
    import json as _json
    from app.core.university_policy import UNIVERSITY_POLICY_KEY, _DEFAULT_POLICY
    monkeypatch.setattr("app.core.university_policy.redis_client", fake)
    monkeypatch.setattr("app.core.faculty_policy.redis_client", fake)
    fake.set(UNIVERSITY_POLICY_KEY, _json.dumps(_DEFAULT_POLICY))

    # faculty_policy keeps a module-global _fallback_policy that
    # set_faculty_priority_policy() rebinds. With redis faked fresh per test,
    # every read cache-misses into that global — so one test enabling the
    # policy would leak "enabled" into all later tests (wall-clock dependent
    # 403s at checkout). Reset it per test; monkeypatch restores on teardown.
    monkeypatch.setattr(
        "app.core.faculty_policy._fallback_policy",
        {"enabled": False, "start_hour": 12, "end_hour": 14},
    )

    yield fake
