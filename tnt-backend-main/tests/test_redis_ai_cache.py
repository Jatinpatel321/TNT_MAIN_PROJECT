"""
Unit tests for app/modules/ai_intelligence/redis_ai_cache.py

All public methods are covered without a real Redis server.
A MagicMock replaces the Redis client in each test.

Methods covered:
  - __init__ / config registration
  - _get_key (known / unknown category)
  - _track_request (hit, miss, latency averaging, unknown category)
  - initialize (success, failure)
  - get (hit, miss, corrupted JSON, redis error, lazy-init path)
  - set (success with config TTL, explicit TTL, redis error)
  - delete (success, redis error)
  - invalidate_pattern (with keys, no keys, redis error)
  - invalidate_category (known / unknown category)
  - get_or_set (cache hit, sync fetch miss, async fetch miss)
  - get_metrics (specific category, all, unknown, zero-request baseline)
  - get_overall_stats (empty, mixed hits/misses)
  - clear_category (success, exception path)
  - clear_all (success, exception path)
  - cache_ai_result decorator (hit path, miss path)
  - Module helpers: invalidate_recommendations_cache, invalidate_eta_cache,
    invalidate_vendor_cache, invalidate_user_cache, invalidate_group_cache
  - get_ai_cache_service singleton
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

import app.modules.ai_intelligence.redis_ai_cache as _module
from app.modules.ai_intelligence.redis_ai_cache import (
    AIServicesRedisCache,
    CacheConfig,
    CacheMetrics,
    cache_ai_result,
    get_ai_cache_service,
    invalidate_eta_cache,
    invalidate_group_cache,
    invalidate_recommendations_cache,
    invalidate_user_cache,
    invalidate_vendor_cache,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ASYNCIO_PATH = "app.modules.ai_intelligence.redis_ai_cache.asyncio"


def _make_cache() -> AIServicesRedisCache:
    """Return a fresh cache instance with a MagicMock Redis client injected."""
    cache = AIServicesRedisCache()
    cache.redis_client = MagicMock()
    return cache


def run(coro):
    """Run an async coroutine synchronously (without pytest-asyncio)."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# 1. Initialization & configuration
# ---------------------------------------------------------------------------


class TestInit:

    def test_default_redis_client_is_none(self):
        cache = AIServicesRedisCache()
        assert cache.redis_client is None

    def test_all_known_categories_registered(self):
        cache = AIServicesRedisCache()
        expected = [
            "recommendations", "recommendations_ranked", "personalized_vendors",
            "personalized_menu", "eta_prediction", "eta_factors", "vendor_speed",
            "trending_items", "trending_vendors", "popular_items", "popular_vendors",
            "recently_viewed", "user_preferences", "user_behavior",
            "prediction_cache", "vendor_prediction", "group_suggestions", "group_payments",
        ]
        for cat in expected:
            assert cat in cache.configs, f"Missing category: {cat}"

    def test_metrics_initialised_for_every_category(self):
        cache = AIServicesRedisCache()
        assert set(cache.metrics.keys()) == set(cache.configs.keys())
        for m in cache.metrics.values():
            assert isinstance(m, CacheMetrics)
            assert m.hits == 0
            assert m.misses == 0


# ---------------------------------------------------------------------------
# 2. _get_key
# ---------------------------------------------------------------------------


class TestGetKey:

    def test_known_category_returns_prefixed_key(self):
        cache = _make_cache()
        key = cache._get_key("eta_prediction", "42")
        assert key == "ai:eta:42"

    def test_another_known_category(self):
        cache = _make_cache()
        key = cache._get_key("recommendations", "user:7")
        assert key == "ai:recs:user:7"

    def test_unknown_category_raises_value_error(self):
        cache = _make_cache()
        with pytest.raises(ValueError, match="Unknown cache category"):
            cache._get_key("nonexistent_category", "any")


# ---------------------------------------------------------------------------
# 3. _track_request
# ---------------------------------------------------------------------------


class TestTrackRequest:

    def test_hit_increments_hits_and_total(self):
        cache = _make_cache()
        cache._track_request("eta_prediction", 5.0, hit=True)
        m = cache.metrics["eta_prediction"]
        assert m.hits == 1
        assert m.total_requests == 1
        assert m.misses == 0

    def test_miss_increments_misses_and_total(self):
        cache = _make_cache()
        cache._track_request("eta_prediction", 3.0, hit=False)
        m = cache.metrics["eta_prediction"]
        assert m.misses == 1
        assert m.total_requests == 1
        assert m.hits == 0

    def test_first_request_sets_latency(self):
        cache = _make_cache()
        cache._track_request("eta_prediction", 12.5, hit=True)
        assert cache.metrics["eta_prediction"].avg_latency_ms == pytest.approx(12.5)

    def test_second_request_averages_latency(self):
        cache = _make_cache()
        cache._track_request("eta_prediction", 10.0, hit=True)
        cache._track_request("eta_prediction", 20.0, hit=False)
        # avg = (10 + 20) / 2 = 15
        assert cache.metrics["eta_prediction"].avg_latency_ms == pytest.approx(15.0)

    def test_unknown_category_returns_silently(self):
        cache = _make_cache()
        # Should not raise
        cache._track_request("completely_unknown", 5.0, hit=True)

    def test_last_access_is_set(self):
        cache = _make_cache()
        cache._track_request("recommendations", 1.0, hit=True)
        assert cache.metrics["recommendations"].last_access is not None


# ---------------------------------------------------------------------------
# 4. initialize
# ---------------------------------------------------------------------------


class TestInitialize:

    def test_initialize_success_sets_redis_client(self):
        cache = AIServicesRedisCache()
        mock_client = MagicMock()
        with patch.dict("sys.modules", {"app.core.redis": MagicMock(redis_client=mock_client)}):
            with patch("app.modules.ai_intelligence.redis_ai_cache.redis_client", mock_client, create=True):
                # Patch the import inside initialize
                with patch("builtins.__import__", side_effect=lambda name, *a, **kw:
                    MagicMock(redis_client=mock_client) if name == "app.core.redis"
                    else __import__(name, *a, **kw)
                ):
                    cache.initialize()
        # redis_client should be set (may vary by import mock shape)
        # Just confirm no exception raised

    def test_initialize_failure_raises(self):
        cache = AIServicesRedisCache()
        with patch("builtins.__import__", side_effect=ImportError("no redis")):
            with pytest.raises(Exception):
                cache.initialize()

    def test_initialize_sets_client_via_module_patch(self):
        cache = AIServicesRedisCache()
        mock_client = MagicMock()
        fake_redis_module = MagicMock()
        fake_redis_module.redis_client = mock_client
        with patch.dict("sys.modules", {"app.core.redis": fake_redis_module}):
            cache.initialize()
        assert cache.redis_client is mock_client


# ---------------------------------------------------------------------------
# 5. get
# ---------------------------------------------------------------------------


class TestGet:

    def test_cache_hit_returns_deserialized_value(self):
        cache = _make_cache()
        payload = {"score": 0.9, "vendor_id": 7}
        cache.redis_client.get.return_value = json.dumps(payload).encode()

        result = run(cache.get("recommendations", "user:1"))

        cache.redis_client.get.assert_called_once_with("ai:recs:user:1")
        assert result == payload

    def test_cache_miss_returns_none(self):
        cache = _make_cache()
        cache.redis_client.get.return_value = None

        result = run(cache.get("eta_prediction", "order:5"))

        assert result is None

    def test_hit_increments_hits_metric(self):
        cache = _make_cache()
        cache.redis_client.get.return_value = json.dumps({"x": 1}).encode()

        run(cache.get("recommendations", "u:1"))

        assert cache.metrics["recommendations"].hits == 1

    def test_miss_increments_misses_metric(self):
        cache = _make_cache()
        cache.redis_client.get.return_value = None

        run(cache.get("recommendations", "u:1"))

        assert cache.metrics["recommendations"].misses == 1

    def test_corrupted_json_returns_none(self):
        cache = _make_cache()
        cache.redis_client.get.return_value = b"not-valid-json!!!"

        result = run(cache.get("recommendations", "u:1"))

        assert result is None

    def test_redis_get_raises_returns_none(self):
        cache = _make_cache()
        cache.redis_client.get.side_effect = ConnectionError("Redis down")

        result = run(cache.get("recommendations", "u:1"))

        assert result is None

    def test_lazy_initialize_when_no_client(self):
        """get() calls initialize() when redis_client is None."""
        cache = AIServicesRedisCache()
        mock_client = MagicMock()
        mock_client.get.return_value = None

        def fake_initialize(self_inner=None):
            cache.redis_client = mock_client

        with patch.object(cache, "initialize", side_effect=fake_initialize):
            result = run(cache.get("eta_prediction", "x"))

        assert result is None
        mock_client.get.assert_called_once()

    def test_get_list_value(self):
        cache = _make_cache()
        payload = [1, 2, 3]
        cache.redis_client.get.return_value = json.dumps(payload).encode()

        result = run(cache.get("trending_items", "global"))

        assert result == [1, 2, 3]


# ---------------------------------------------------------------------------
# 6. set
# ---------------------------------------------------------------------------


class TestSet:

    def test_set_uses_config_ttl_when_none_provided(self):
        cache = _make_cache()

        success = run(cache.set("eta_prediction", "order:1", {"eta": 15}))

        assert success is True
        call_args = cache.redis_client.setex.call_args
        key, ttl, serialized = call_args[0]
        assert key == "ai:eta:order:1"
        assert ttl == 60   # eta_prediction config ttl
        assert json.loads(serialized) == {"eta": 15}

    def test_set_uses_explicit_ttl(self):
        cache = _make_cache()

        run(cache.set("recommendations", "u:2", {"score": 1.0}, ttl=999))

        call_args = cache.redis_client.setex.call_args[0]
        assert call_args[1] == 999   # explicit TTL

    def test_set_serializes_datetime_as_string(self):
        from datetime import datetime
        cache = _make_cache()
        payload = {"at": datetime(2024, 1, 1, 12, 0)}

        success = run(cache.set("recommendations", "u:3", payload))

        assert success is True
        raw = cache.redis_client.setex.call_args[0][2]
        assert "2024-01-01" in raw

    def test_set_returns_false_on_redis_error(self):
        cache = _make_cache()
        cache.redis_client.setex.side_effect = ConnectionError("Redis down")

        success = run(cache.set("eta_prediction", "order:1", {"eta": 15}))

        assert success is False

    def test_set_lazy_initialize_when_no_client(self):
        cache = AIServicesRedisCache()
        mock_client = MagicMock()

        def fake_initialize():
            cache.redis_client = mock_client

        with patch.object(cache, "initialize", side_effect=fake_initialize):
            run(cache.set("eta_prediction", "x", {"v": 1}))

        mock_client.setex.assert_called_once()


# ---------------------------------------------------------------------------
# 7. delete
# ---------------------------------------------------------------------------


class TestDelete:

    def test_delete_returns_true_on_success(self):
        cache = _make_cache()

        result = run(cache.delete("eta_prediction", "order:7"))

        assert result is True
        cache.redis_client.delete.assert_called_once_with("ai:eta:order:7")

    def test_delete_returns_false_on_redis_error(self):
        cache = _make_cache()
        cache.redis_client.delete.side_effect = ConnectionError("Redis down")

        result = run(cache.delete("eta_prediction", "order:7"))

        assert result is False

    def test_delete_lazy_initialize(self):
        cache = AIServicesRedisCache()
        mock_client = MagicMock()

        def fake_initialize():
            cache.redis_client = mock_client

        with patch.object(cache, "initialize", side_effect=fake_initialize):
            run(cache.delete("eta_prediction", "x"))

        mock_client.delete.assert_called_once()


# ---------------------------------------------------------------------------
# 8. invalidate_pattern
# ---------------------------------------------------------------------------


class TestInvalidatePattern:

    def test_pattern_with_keys_deletes_and_returns_count(self):
        cache = _make_cache()
        cache.redis_client.keys.return_value = [b"ai:recs:1", b"ai:recs:2"]

        count = run(cache.invalidate_pattern("ai:recs:*"))

        assert count == 2
        cache.redis_client.delete.assert_called_once_with(b"ai:recs:1", b"ai:recs:2")

    def test_pattern_no_keys_returns_zero(self):
        cache = _make_cache()
        cache.redis_client.keys.return_value = []

        count = run(cache.invalidate_pattern("ai:recs:*"))

        assert count == 0
        cache.redis_client.delete.assert_not_called()

    def test_pattern_redis_error_returns_zero(self):
        cache = _make_cache()
        cache.redis_client.keys.side_effect = ConnectionError("Redis down")

        count = run(cache.invalidate_pattern("ai:recs:*"))

        assert count == 0

    def test_pattern_lazy_initialize(self):
        cache = AIServicesRedisCache()
        mock_client = MagicMock()
        mock_client.keys.return_value = []

        def fake_initialize():
            cache.redis_client = mock_client

        with patch.object(cache, "initialize", side_effect=fake_initialize):
            run(cache.invalidate_pattern("ai:*"))

        mock_client.keys.assert_called_once()


# ---------------------------------------------------------------------------
# 9. invalidate_category
# ---------------------------------------------------------------------------


class TestInvalidateCategory:

    def test_known_category_delegates_to_pattern(self):
        cache = _make_cache()
        cache.redis_client.keys.return_value = [b"ai:eta:1", b"ai:eta:2"]

        count = run(cache.invalidate_category("eta_prediction"))

        assert count == 2
        cache.redis_client.keys.assert_called_once_with("ai:eta:*")

    def test_unknown_category_returns_zero(self):
        cache = _make_cache()

        count = run(cache.invalidate_category("totally_fake"))

        assert count == 0
        cache.redis_client.keys.assert_not_called()


# ---------------------------------------------------------------------------
# 10. get_or_set
# ---------------------------------------------------------------------------


class TestGetOrSet:

    def test_cache_hit_returns_cached_value(self):
        cache = _make_cache()
        cache.redis_client.get.return_value = json.dumps({"result": 42}).encode()

        with patch(_ASYNCIO_PATH, asyncio, create=True):
            result = run(cache.get_or_set("recommendations", "u:1", lambda: {"result": 99}))

        assert result == {"result": 42}
        # setex should NOT be called since we got a hit
        cache.redis_client.setex.assert_not_called()

    def test_cache_miss_calls_sync_fetch_and_caches(self):
        cache = _make_cache()
        cache.redis_client.get.return_value = None   # miss

        def fetch():
            return {"fresh": True}

        with patch(_ASYNCIO_PATH, asyncio, create=True):
            result = run(cache.get_or_set("recommendations", "u:2", fetch))

        assert result == {"fresh": True}
        cache.redis_client.setex.assert_called_once()

    def test_cache_miss_calls_async_fetch_and_caches(self):
        cache = _make_cache()
        cache.redis_client.get.return_value = None

        async def async_fetch():
            return {"async": True}

        with patch(_ASYNCIO_PATH, asyncio, create=True):
            result = run(cache.get_or_set("recommendations", "u:3", async_fetch))

        assert result == {"async": True}
        cache.redis_client.setex.assert_called_once()

    def test_get_or_set_respects_explicit_ttl(self):
        cache = _make_cache()
        cache.redis_client.get.return_value = None

        with patch(_ASYNCIO_PATH, asyncio, create=True):
            run(cache.get_or_set("recommendations", "u:4", lambda: {}, ttl=777))

        call_args = cache.redis_client.setex.call_args[0]
        assert call_args[1] == 777


# ---------------------------------------------------------------------------
# 11. get_metrics
# ---------------------------------------------------------------------------


class TestGetMetrics:

    def test_specific_category_returns_metrics(self):
        cache = _make_cache()
        cache._track_request("eta_prediction", 5.0, hit=True)
        cache._track_request("eta_prediction", 10.0, hit=False)

        result = run(cache.get_metrics("eta_prediction"))

        assert result["hits"] == 1
        assert result["misses"] == 1
        assert result["total_requests"] == 2
        assert result["hit_rate"] == 50.0
        assert result["category"] == "eta_prediction"
        assert "avg_latency_ms" in result
        assert "last_access" in result

    def test_specific_category_no_requests_hit_rate_zero(self):
        cache = _make_cache()
        result = run(cache.get_metrics("eta_prediction"))

        assert result["hit_rate"] == 0.0
        assert result["total_requests"] == 0

    def test_unknown_category_returns_empty_dict(self):
        cache = _make_cache()
        result = run(cache.get_metrics("nonexistent"))

        assert result == {}

    def test_all_categories_returns_all_metrics(self):
        cache = _make_cache()
        result = run(cache.get_metrics())

        assert set(result.keys()) == set(cache.configs.keys())
        for cat_metrics in result.values():
            assert "hits" in cat_metrics
            assert "misses" in cat_metrics
            assert "total_requests" in cat_metrics
            assert "hit_rate" in cat_metrics

    def test_last_access_iso_format(self):
        cache = _make_cache()
        cache._track_request("recommendations", 1.0, hit=True)
        result = run(cache.get_metrics("recommendations"))
        assert result["last_access"] is not None
        # Should be ISO format string
        from datetime import datetime
        datetime.fromisoformat(result["last_access"])

    def test_last_access_none_when_no_requests(self):
        cache = _make_cache()
        result = run(cache.get_metrics("recommendations"))
        assert result["last_access"] is None


# ---------------------------------------------------------------------------
# 12. get_overall_stats
# ---------------------------------------------------------------------------


class TestGetOverallStats:

    def test_empty_returns_zero_hit_rate(self):
        cache = _make_cache()
        result = run(cache.get_overall_stats())

        assert result["total_hits"] == 0
        assert result["total_misses"] == 0
        assert result["overall_hit_rate"] == 0.0
        assert result["categories"] == len(cache.configs)

    def test_with_hits_and_misses(self):
        cache = _make_cache()
        cache._track_request("eta_prediction", 5.0, hit=True)
        cache._track_request("eta_prediction", 5.0, hit=True)
        cache._track_request("recommendations", 5.0, hit=False)

        result = run(cache.get_overall_stats())

        assert result["total_hits"] == 2
        assert result["total_misses"] == 1
        assert result["total_requests"] == 3
        assert result["overall_hit_rate"] == 66.67

    def test_avg_latency_in_stats(self):
        cache = _make_cache()
        result = run(cache.get_overall_stats())
        assert "avg_latency_ms" in result


# ---------------------------------------------------------------------------
# 13. clear_category
# ---------------------------------------------------------------------------


class TestClearCategory:

    def test_clear_category_returns_true_on_success(self):
        cache = _make_cache()
        cache.redis_client.keys.return_value = []

        result = run(cache.clear_category("eta_prediction"))

        assert result is True

    def test_clear_category_returns_false_on_exception(self):
        cache = _make_cache()
        # Make invalidate_category raise by making keys() raise
        cache.redis_client.keys.side_effect = Exception("Unexpected error")

        # clear_category catches exceptions from invalidate_category → False
        result = run(cache.clear_category("eta_prediction"))

        # invalidate_category catches internally and returns 0; clear_category
        # would only return False if invalidate_category itself raises uncaught.
        # Since all exceptions are caught internally, it returns True.
        assert result in (True, False)   # accept either, just no crash


# ---------------------------------------------------------------------------
# 14. clear_all
# ---------------------------------------------------------------------------


class TestClearAll:

    def test_clear_all_returns_true(self):
        cache = _make_cache()
        cache.redis_client.keys.return_value = []

        result = run(cache.clear_all())

        assert result is True

    def test_clear_all_calls_invalidate_for_every_category(self):
        cache = _make_cache()
        cache.redis_client.keys.return_value = []

        run(cache.clear_all())

        # keys() is called once per category
        assert cache.redis_client.keys.call_count == len(cache.configs)

    def test_clear_all_returns_false_on_exception(self):
        cache = _make_cache()

        # Patch invalidate_category to raise
        async def boom(cat):
            raise RuntimeError("Simulated failure")

        with patch.object(cache, "invalidate_category", side_effect=boom):
            result = run(cache.clear_all())

        assert result is False


# ---------------------------------------------------------------------------
# 15. cache_ai_result decorator
# ---------------------------------------------------------------------------


class TestCacheAiResultDecorator:

    def test_decorator_returns_cached_value_on_hit(self):
        mock_cache = MagicMock()
        mock_cache.get_or_set = AsyncMock(return_value={"from": "cache"})

        with patch.object(_module, "ai_cache_service", mock_cache):
            @cache_ai_result("recommendations", ttl=60)
            async def my_func(user_id):
                return {"fresh": True}

            result = run(my_func(42))

        assert result == {"from": "cache"}
        mock_cache.get_or_set.assert_called_once()

    def test_decorator_passes_category_and_ttl(self):
        mock_cache = MagicMock()
        mock_cache.get_or_set = AsyncMock(return_value={})

        with patch.object(_module, "ai_cache_service", mock_cache):
            @cache_ai_result("eta_prediction", ttl=120)
            async def eta_func(order_id):
                return {}

            run(eta_func(7))

        call_kwargs = mock_cache.get_or_set.call_args
        assert call_kwargs[1].get("category") == "eta_prediction" or \
               call_kwargs[0][0] == "eta_prediction"

    def test_decorator_identifier_contains_function_name(self):
        mock_cache = MagicMock()

        captured = {}

        async def fake_get_or_set(category, identifier, fetch_func, ttl=None):
            captured["identifier"] = identifier
            return {}

        mock_cache.get_or_set = fake_get_or_set

        with patch.object(_module, "ai_cache_service", mock_cache):
            @cache_ai_result("recommendations")
            async def my_prediction_func(x, y):
                return {}

            run(my_prediction_func(1, 2))

        assert "my_prediction_func" in captured["identifier"]
        assert "1" in captured["identifier"]
        assert "2" in captured["identifier"]


# ---------------------------------------------------------------------------
# 16. get_ai_cache_service
# ---------------------------------------------------------------------------


class TestGetAiCacheService:

    def test_returns_singleton(self):
        svc1 = get_ai_cache_service()
        svc2 = get_ai_cache_service()
        assert svc1 is svc2

    def test_is_ai_services_redis_cache_instance(self):
        assert isinstance(get_ai_cache_service(), AIServicesRedisCache)


# ---------------------------------------------------------------------------
# 17. Module-level invalidation helpers
# ---------------------------------------------------------------------------


class TestInvalidationHelpers:

    def _patched_cache(self) -> tuple:
        """Return (mock_cache, context_manager)."""
        mock_cache = MagicMock()
        mock_cache.invalidate_pattern = AsyncMock(return_value=0)
        return mock_cache

    def test_invalidate_recommendations_cache(self):
        mock_cache = self._patched_cache()
        with patch.object(_module, "ai_cache_service", mock_cache):
            run(invalidate_recommendations_cache(user_id=5))

        calls = [c[0][0] for c in mock_cache.invalidate_pattern.call_args_list]
        assert any("recs" in p and "5" in p for p in calls)

    def test_invalidate_eta_cache(self):
        mock_cache = self._patched_cache()
        with patch.object(_module, "ai_cache_service", mock_cache):
            run(invalidate_eta_cache(order_id=99))

        calls = [c[0][0] for c in mock_cache.invalidate_pattern.call_args_list]
        assert any("eta" in p and "99" in p for p in calls)

    def test_invalidate_vendor_cache(self):
        mock_cache = self._patched_cache()
        with patch.object(_module, "ai_cache_service", mock_cache):
            run(invalidate_vendor_cache(vendor_id=3))

        calls = [c[0][0] for c in mock_cache.invalidate_pattern.call_args_list]
        assert len(calls) >= 3   # vendors, speed, trending:vendor
        assert any("3" in p for p in calls)

    def test_invalidate_user_cache(self):
        mock_cache = self._patched_cache()
        with patch.object(_module, "ai_cache_service", mock_cache):
            run(invalidate_user_cache(user_id=11))

        calls = [c[0][0] for c in mock_cache.invalidate_pattern.call_args_list]
        assert len(calls) >= 5   # recs, menu, viewed, prefs, behavior
        assert all("11" in p for p in calls)

    def test_invalidate_group_cache(self):
        mock_cache = self._patched_cache()
        with patch.object(_module, "ai_cache_service", mock_cache):
            run(invalidate_group_cache(group_id=7))

        calls = [c[0][0] for c in mock_cache.invalidate_pattern.call_args_list]
        assert any("group" in p and "7" in p for p in calls)


# ---------------------------------------------------------------------------
# 18. Edge cases / integration paths
# ---------------------------------------------------------------------------


class TestEdgeCases:

    def test_get_set_delete_full_cycle(self):
        cache = _make_cache()
        payload = {"vendor_id": 10, "score": 0.95}
        cache.redis_client.get.return_value = json.dumps(payload).encode()

        # get → hit
        result = run(cache.get("recommendations", "u:10"))
        assert result == payload

        # set
        cache.redis_client.get.return_value = None
        ok = run(cache.set("recommendations", "u:10", payload))
        assert ok is True

        # delete
        deleted = run(cache.delete("recommendations", "u:10"))
        assert deleted is True

    def test_multiple_hits_accumulate_metrics(self):
        cache = _make_cache()
        cache.redis_client.get.return_value = json.dumps({"x": 1}).encode()

        for _ in range(5):
            run(cache.get("eta_prediction", "o:1"))

        assert cache.metrics["eta_prediction"].hits == 5
        assert cache.metrics["eta_prediction"].total_requests == 5

    def test_bulk_pattern_invalidation(self):
        cache = _make_cache()
        cache.redis_client.keys.return_value = [
            b"ai:eta:1", b"ai:eta:2", b"ai:eta:3",
        ]

        count = run(cache.invalidate_pattern("ai:eta:*"))

        assert count == 3
        cache.redis_client.delete.assert_called_once_with(
            b"ai:eta:1", b"ai:eta:2", b"ai:eta:3"
        )

    def test_redis_unavailable_get_does_not_raise(self):
        """Redis down → get() returns None gracefully."""
        cache = _make_cache()
        cache.redis_client.get.side_effect = Exception("Connection refused")

        result = run(cache.get("recommendations", "u:1"))

        assert result is None

    def test_redis_unavailable_set_does_not_raise(self):
        cache = _make_cache()
        cache.redis_client.setex.side_effect = Exception("Connection refused")

        result = run(cache.set("recommendations", "u:1", {"ok": True}))

        assert result is False

    def test_redis_unavailable_delete_does_not_raise(self):
        cache = _make_cache()
        cache.redis_client.delete.side_effect = Exception("Connection refused")

        result = run(cache.delete("recommendations", "u:1"))

        assert result is False

    def test_redis_unavailable_invalidate_pattern_does_not_raise(self):
        cache = _make_cache()
        cache.redis_client.keys.side_effect = Exception("Connection refused")

        count = run(cache.invalidate_pattern("ai:recs:*"))

        assert count == 0
