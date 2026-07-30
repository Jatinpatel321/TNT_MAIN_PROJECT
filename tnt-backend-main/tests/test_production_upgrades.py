"""
Unit tests for app/modules/ai_intelligence/production_upgrades.py

Covers all classes, functions, decorators, context managers, and edge cases:
  1. MetricType & Metric (to_prometheus formatting for COUNTER, GAUGE, HISTOGRAM)
  2. MetricsCollector (initialize, increment, set, observe, export_prometheus, get_summary)
  3. CorrelationContext (set, get, clear)
  4. StructuredLogger (debug, info, warning, error, critical)
  5. CircuitBreaker & CircuitBreakerState (call, call_async, OPEN/CLOSED/HALF_OPEN transitions, recovery timeout, failure threshold, get_state, get_circuit_breaker)
  6. RetryConfig & retry_with_backoff (success, max attempts exhausted, jitter true/false, backoff delays)
  7. HealthStatus, HealthCheckResult, & HealthChecker (_check_database success/fail, _check_redis success/fail, _check_ml_models empty/degraded/healthy/fail, _check_disk_space critical/degraded/healthy/fail, run_all_checks, run_check)
  8. DataValidator (validate_vendor_id, validate_order_id, validate_slot_id, validate_days_ahead, validate_item_count, validate_prediction_result)
  9. Decorators (with_correlation_id success/fail, with_metrics success/fail, with_validation success/fail, with_circuit_breaker)
  10. Context Managers (timed_context success/fail, db_session_scope commit/rollback/close)
  11. FeatureDriftDetector (update_reference, detect_drift with insufficient samples, drift detected z-score, no drift)
  12. FallbackStrategy (ml_to_heuristic_eta, ml_to_heuristic_demand, redis_to_database)
  13. DataFreshnessChecker (check_orders_freshness stale/degraded/fresh, check_menu_availability critical/degraded/healthy)
  14. RequestValidator (validate_eta_request valid/invalid, validate_demand_request valid/invalid)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.modules.ai_intelligence.production_upgrades import (
    CircuitBreaker,
    CircuitBreakerState,
    CorrelationContext,
    DataFreshnessChecker,
    DataValidator,
    FallbackStrategy,
    FeatureDriftDetector,
    HealthChecker,
    HealthCheckResult,
    HealthStatus,
    Metric,
    MetricsCollector,
    MetricType,
    RequestValidator,
    RetryConfig,
    StructuredLogger,
    db_session_scope,
    get_circuit_breaker,
    metrics_collector,
    retry_with_backoff,
    timed_context,
    with_circuit_breaker,
    with_correlation_id,
    with_metrics,
    with_validation,
)

# ---------------------------------------------------------------------------
# 1. MetricType & Metric
# ---------------------------------------------------------------------------

class TestMetric:

    def test_metric_to_prometheus_formatting(self):
        dt = datetime(2024, 1, 1, 12, 0, 0)
        ts_ms = int(dt.timestamp() * 1000)

        counter_m = Metric("test_counter", MetricType.COUNTER, value=5.0, labels={"env": "prod"}, timestamp=dt)
        assert counter_m.to_prometheus() == f'test_counter{{env="prod"}} 5.0 {ts_ms}'

        gauge_m = Metric("test_gauge", MetricType.GAUGE, value=42.0, labels={"env": "dev"}, timestamp=dt)
        assert gauge_m.to_prometheus() == f'test_gauge{{env="dev"}} 42.0 {ts_ms}'

        other_m = Metric("test_summary", MetricType.SUMMARY, value=1.5, labels={"path": "/api"}, timestamp=None)
        assert "test_summary{path=\"/api\"} 1.5" in other_m.to_prometheus()


# ---------------------------------------------------------------------------
# 2. MetricsCollector
# ---------------------------------------------------------------------------

class TestMetricsCollector:

    def test_metrics_collector_init_and_operations(self):
        mc = MetricsCollector()
        assert "ai_requests_total" in mc.metrics

        # increment
        mc.increment("ai_requests_total", 2.0, labels={"endpoint": "/eta"})
        assert mc.metrics["ai_requests_total"].value == 2.0
        assert mc.metrics["ai_requests_total"].labels["endpoint"] == "/eta"

        # set
        mc.set("ai_cache_hit_ratio", 0.85, labels={"type": "memory"})
        assert mc.metrics["ai_cache_hit_ratio"].value == 0.85

        # observe
        mc.observe("ai_request_duration_seconds", 0.5)
        mc.observe("ai_request_duration_seconds", 1.5)
        # avg of 0.5 and 1.5 = 1.0
        assert mc.metrics["ai_request_duration_seconds"].value == 1.0
        assert mc.metrics["ai_request_duration_seconds"].labels["_count"] == "2"

        # export & summary
        prom_export = mc.export_prometheus()
        assert "ai_requests_total" in prom_export
        summary = mc.get_summary()
        assert summary["ai_requests_total"]["value"] == 2.0
        assert summary["ai_requests_total"]["type"] == "counter"

    def test_unknown_metric_ignored(self):
        mc = MetricsCollector()
        mc.increment("unknown_metric")
        mc.set("unknown_metric", 1.0)
        mc.observe("unknown_metric", 1.0)
        assert "unknown_metric" not in mc.metrics


# ---------------------------------------------------------------------------
# 3. CorrelationContext & StructuredLogger
# ---------------------------------------------------------------------------

class TestCorrelationContextAndLogger:

    def test_correlation_context_lifecycle(self):
        CorrelationContext.clear()
        assert CorrelationContext.get() == {}

        CorrelationContext.set("corr-123", user_id=42)
        ctx = CorrelationContext.get()
        assert ctx["correlation_id"] == "corr-123"
        assert ctx["user_id"] == 42

        CorrelationContext.clear()
        assert CorrelationContext.get() == {}

    def test_structured_logger_methods(self):
        logger = StructuredLogger("test.logger")
        with patch.object(logger.logger, "info") as mock_info, \
             patch.object(logger.logger, "debug") as mock_debug, \
             patch.object(logger.logger, "warning") as mock_warning, \
             patch.object(logger.logger, "error") as mock_error, \
             patch.object(logger.logger, "critical") as mock_critical:

            CorrelationContext.set("corr-456")
            logger.debug("debug msg")
            logger.info("info msg")
            logger.warning("warn msg")
            logger.error("error msg")
            logger.critical("crit msg")

            mock_debug.assert_called_once()
            mock_info.assert_called_once()
            mock_warning.assert_called_once()
            mock_error.assert_called_once()
            mock_critical.assert_called_once()
            assert "corr-456" in mock_info.call_args[0][0]
            CorrelationContext.clear()


# ---------------------------------------------------------------------------
# 4. CircuitBreaker
# ---------------------------------------------------------------------------

class TestCircuitBreaker:

    def test_circuit_breaker_closed_success(self):
        cb = CircuitBreaker("test_cb", failure_threshold=2, recovery_timeout=10)
        res = cb.call(lambda x: x * 2, 5)
        assert res == 10
        assert cb.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_trip_to_open(self):
        cb = CircuitBreaker("test_cb", failure_threshold=2, recovery_timeout=10)

        with pytest.raises(ValueError):
            cb.call(MagicMock(side_effect=ValueError("fail 1")))
        assert cb.state == CircuitBreakerState.CLOSED

        with pytest.raises(ValueError):
            cb.call(MagicMock(side_effect=ValueError("fail 2")))
        assert cb.state == CircuitBreakerState.OPEN

        # Call while OPEN raises Exception
        with pytest.raises(Exception, match="Circuit breaker OPEN"):
            cb.call(lambda: 42)

    def test_circuit_breaker_half_open_recovery(self):
        cb = CircuitBreaker("test_cb", failure_threshold=1, recovery_timeout=0, success_threshold=2)

        with pytest.raises(ValueError):
            cb.call(MagicMock(side_effect=ValueError("fail")))
        assert cb.state == CircuitBreakerState.OPEN

        # Recovery timeout passed (recovery_timeout=0) -> switches to HALF_OPEN on call
        res = cb.call(lambda: 100)
        assert res == 100
        assert cb.state == CircuitBreakerState.HALF_OPEN

        # Second success -> CLOSED
        res2 = cb.call(lambda: 200)
        assert res2 == 200
        assert cb.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_half_open_failure_reopens(self):
        cb = CircuitBreaker("test_cb", failure_threshold=1, recovery_timeout=0, success_threshold=2)

        with pytest.raises(ValueError):
            cb.call(MagicMock(side_effect=ValueError("fail")))
        assert cb.state == CircuitBreakerState.OPEN

        # Re-enters HALF_OPEN then fails -> returns to OPEN
        with pytest.raises(ValueError):
            cb.call(MagicMock(side_effect=ValueError("fail in half open")))
        assert cb.state == CircuitBreakerState.OPEN

    def test_circuit_breaker_call_async(self):
        cb = CircuitBreaker("async_cb", failure_threshold=2, recovery_timeout=10)

        async def async_fn():
            return 42

        res = asyncio.run(cb.call_async(async_fn))
        assert res == 42

        # Async failure path
        async def async_fail():
            raise ValueError("async fail")

        with pytest.raises(ValueError):
            asyncio.run(cb.call_async(async_fail))
        with pytest.raises(ValueError):
            asyncio.run(cb.call_async(async_fail))

        assert cb.state == CircuitBreakerState.OPEN

        # Call while OPEN raises Exception
        with pytest.raises(Exception, match="Circuit breaker OPEN"):
            asyncio.run(cb.call_async(async_fn))

        # Recovery timeout check when last_failure_time is None
        cb.last_failure_time = None
        assert cb._should_attempt_recovery() is True

    def test_get_circuit_breaker_factory(self):
        cb1 = get_circuit_breaker("custom_cb")
        cb2 = get_circuit_breaker("custom_cb")
        assert cb1 is cb2
        assert cb1.get_state()["name"] == "custom_cb"


# ---------------------------------------------------------------------------
# 5. RetryConfig & retry_with_backoff
# ---------------------------------------------------------------------------

class TestRetryWithBackoff:

    def test_retry_success_first_try(self):
        @retry_with_backoff(RetryConfig(max_attempts=3, initial_delay=0.01))
        def fn():
            return "ok"

        assert fn() == "ok"

    def test_retry_success_after_failure_no_jitter(self):
        mock_fn = MagicMock(side_effect=[ValueError("err1"), "success"])

        @retry_with_backoff(RetryConfig(max_attempts=3, initial_delay=0.001, jitter=False))
        def fn():
            return mock_fn()

        assert fn() == "success"
        assert mock_fn.call_count == 2

    def test_retry_exhausted_raises_last_exception(self):
        mock_fn = MagicMock(side_effect=ValueError("persistent error"))

        @retry_with_backoff(RetryConfig(max_attempts=2, initial_delay=0.001, jitter=True))
        def fn():
            return mock_fn()

        with pytest.raises(ValueError, match="persistent error"):
            fn()
        assert mock_fn.call_count == 2


# ---------------------------------------------------------------------------
# 6. HealthChecker & HealthCheckResult
# ---------------------------------------------------------------------------

class TestHealthChecker:

    def test_health_check_result_to_dict(self):
        hcr = HealthCheckResult(
            component="test",
            status=HealthStatus.HEALTHY,
            message="OK",
            details={"foo": "bar"}
        )
        d = hcr.to_dict()
        assert d["component"] == "test"
        assert d["status"] == "healthy"
        assert d["details"]["foo"] == "bar"

    def test_check_database_success_and_failure(self):
        mock_db = MagicMock()
        hc = HealthChecker(mock_db)

        # Success
        res = hc._check_database()
        assert res.status == HealthStatus.HEALTHY

        # Failure
        mock_db.execute.side_effect = Exception("DB Connection Lost")
        res_fail = hc._check_database()
        assert res_fail.status == HealthStatus.UNHEALTHY

    def test_check_redis_success_and_failure(self):
        hc = HealthChecker(MagicMock())

        with patch("app.core.redis.redis_client") as mock_redis:
            mock_redis.ping.return_value = True
            res = hc._check_redis()
            assert res.status == HealthStatus.HEALTHY

            mock_redis.ping.side_effect = Exception("Redis Down")
            res_degraded = hc._check_redis()
            assert res_degraded.status == HealthStatus.DEGRADED

    def test_check_ml_models_all_statuses(self):
        hc = HealthChecker(MagicMock())

        with patch("app.ml.registry.ModelRegistry.get_registry_summary") as mock_reg:
            # Empty
            mock_reg.return_value = {}
            res_empty = hc._check_ml_models()
            assert res_empty.status == HealthStatus.DEGRADED

            # Degraded (1 missing active)
            mock_reg.return_value = {"m1": {"latest": True}, "m2": {"latest": False}}
            res_deg = hc._check_ml_models()
            assert res_deg.status == HealthStatus.DEGRADED

            # Healthy
            mock_reg.return_value = {"m1": {"latest": True}, "m2": {"latest": True}}
            res_healthy = hc._check_ml_models()
            assert res_healthy.status == HealthStatus.HEALTHY

            # Failure
            mock_reg.side_effect = Exception("Registry error")
            res_fail = hc._check_ml_models()
            assert res_fail.status == HealthStatus.UNHEALTHY

    def test_check_disk_space_thresholds(self):
        hc = HealthChecker(MagicMock())

        with patch("shutil.disk_usage") as mock_usage:
            # Healthy (<75% used)
            mock_usage.return_value = MagicMock(total=100 * 1024**3, free=30 * 1024**3, used=70 * 1024**3)
            assert hc._check_disk_space().status == HealthStatus.HEALTHY

            # Degraded (>75% used)
            mock_usage.return_value = MagicMock(total=100 * 1024**3, free=20 * 1024**3, used=80 * 1024**3)
            assert hc._check_disk_space().status == HealthStatus.DEGRADED

            # Unhealthy (>90% used)
            mock_usage.return_value = MagicMock(total=100 * 1024**3, free=5 * 1024**3, used=95 * 1024**3)
            assert hc._check_disk_space().status == HealthStatus.UNHEALTHY

            # Exception
            mock_usage.side_effect = Exception("Disk error")
            assert hc._check_disk_space().status == HealthStatus.DEGRADED

    def test_run_all_checks_and_single_check(self):
        mock_db = MagicMock()
        hc = HealthChecker(mock_db)

        with patch.object(hc, "_check_redis") as mr, \
             patch.object(hc, "_check_ml_models") as mm, \
             patch.object(hc, "_check_disk_space") as md:

            mr.return_value = HealthCheckResult("redis", HealthStatus.HEALTHY, "OK")
            mm.return_value = HealthCheckResult("ml_models", HealthStatus.HEALTHY, "OK")
            md.return_value = HealthCheckResult("disk_space", HealthStatus.HEALTHY, "OK")

            all_res = hc.run_all_checks()
            assert all_res["status"] == "healthy"
            assert "database" in all_res["checks"]

        # Run single check valid & invalid
        single_res = hc.run_check("database")
        assert single_res.component == "database"

        invalid_res = hc.run_check("invalid_component")
        assert invalid_res.status == HealthStatus.UNHEALTHY


# ---------------------------------------------------------------------------
# 7. DataValidator
# ---------------------------------------------------------------------------

class TestDataValidator:

    def test_validate_vendor_id(self):
        assert DataValidator.validate_vendor_id(10) == (True, None)
        assert DataValidator.validate_vendor_id("5") == (True, None)
        assert DataValidator.validate_vendor_id(None)[0] is False
        assert DataValidator.validate_vendor_id(-1)[0] is False
        assert DataValidator.validate_vendor_id("abc")[0] is False

    def test_validate_order_id(self):
        assert DataValidator.validate_order_id(1) == (True, None)
        assert DataValidator.validate_order_id(None)[0] is False
        assert DataValidator.validate_order_id(0)[0] is False
        assert DataValidator.validate_order_id("xyz")[0] is False

    def test_validate_slot_id(self):
        assert DataValidator.validate_slot_id(1) == (True, None)
        assert DataValidator.validate_slot_id(None)[0] is False
        assert DataValidator.validate_slot_id(0)[0] is False
        assert DataValidator.validate_slot_id("bad")[0] is False

    def test_validate_days_ahead(self):
        assert DataValidator.validate_days_ahead(None) == (True, None)
        assert DataValidator.validate_days_ahead(7) == (True, None)
        assert DataValidator.validate_days_ahead(0)[0] is False
        assert DataValidator.validate_days_ahead(400)[0] is False
        assert DataValidator.validate_days_ahead("invalid")[0] is False

    def test_validate_item_count(self):
        assert DataValidator.validate_item_count(None) == (True, None)
        assert DataValidator.validate_item_count(5) == (True, None)
        assert DataValidator.validate_item_count(0)[0] is False
        assert DataValidator.validate_item_count(100)[0] is False
        assert DataValidator.validate_item_count("bad")[0] is False

    def test_validate_prediction_result(self):
        valid_res = {
            "predicted_eta_minutes": 15,
            "confidence_score": 0.8,
            "delay_risk_level": "LOW",
        }
        assert DataValidator.validate_prediction_result(valid_res) == (True, None)

        assert DataValidator.validate_prediction_result("not a dict")[0] is False
        assert DataValidator.validate_prediction_result({"predicted_eta_minutes": 15})[0] is False
        assert DataValidator.validate_prediction_result({**valid_res, "predicted_eta_minutes": 200})[0] is False
        assert DataValidator.validate_prediction_result({**valid_res, "confidence_score": 1.5})[0] is False
        assert DataValidator.validate_prediction_result({**valid_res, "delay_risk_level": "INVALID"})[0] is False


# ---------------------------------------------------------------------------
# 8. Decorators
# ---------------------------------------------------------------------------

class TestProductionDecorators:

    def test_with_correlation_id_success_and_failure(self):
        @with_correlation_id
        def sample_func(x):
            return x * 2

        assert sample_func(5) == 10

        @with_correlation_id
        def failing_func():
            raise RuntimeError("Correlation failure")

        with pytest.raises(RuntimeError):
            failing_func()

    def test_with_metrics_success_and_failure(self):
        @with_metrics
        def sample_func(a, b):
            return a + b

        assert sample_func(2, 3) == 5

        @with_metrics
        def failing_func():
            raise ValueError("Metrics failure")

        with pytest.raises(ValueError):
            failing_func()

    def test_with_validation_success_and_failure(self):
        @with_validation(vendor_id=DataValidator.validate_vendor_id)
        def func_with_val(vendor_id: int):
            return vendor_id

        assert func_with_val(vendor_id=10) == 10

        with pytest.raises(ValueError, match="Validation failed for vendor_id"):
            func_with_val(vendor_id=-5)

    def test_with_circuit_breaker_decorator(self):
        @with_circuit_breaker("test_decorator_breaker")
        def cb_func():
            return "protected"

        assert cb_func() == "protected"


# ---------------------------------------------------------------------------
# 9. Context Managers
# ---------------------------------------------------------------------------

class TestContextManagers:

    def test_timed_context_success_and_failure(self):
        with timed_context("test_operation"):
            pass  # success path

        with pytest.raises(ValueError):
            with timed_context("failing_operation"):
                raise ValueError("Operation failed")

    def test_db_session_scope_commit_and_rollback(self):
        mock_db = MagicMock()

        # Success path (commits and closes)
        with db_session_scope(mock_db) as db:
            assert db is mock_db
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

        # Failure path (rollbacks and closes)
        mock_db_fail = MagicMock()
        with pytest.raises(RuntimeError):
            with db_session_scope(mock_db_fail):
                raise RuntimeError("DB Error")
        mock_db_fail.rollback.assert_called_once()
        mock_db_fail.close.assert_called_once()


# ---------------------------------------------------------------------------
# 10. FeatureDriftDetector
# ---------------------------------------------------------------------------

class TestFeatureDriftDetector:

    def test_drift_detector_reference_and_detection(self):
        detector = FeatureDriftDetector()

        # Insufficient samples (<10)
        for _ in range(5):
            detector.update_reference({"f1": 10.0})
        res_insufficient = detector.detect_drift({"f1": 50.0})
        assert res_insufficient["drift_detected"] is False

        # Build reference >= 10 samples (mean ~ 10, std small)
        for _ in range(15):
            detector.update_reference({"f1": 10.0})
        detector.update_reference({"f1": 11.0})
        detector.update_reference({"f1": 9.0})

        # No drift
        res_no_drift = detector.detect_drift({"f1": 10.2})
        assert res_no_drift["drift_detected"] is False

        # Drift detected (z-score > 2.0)
        res_drift = detector.detect_drift({"f1": 100.0})
        assert res_drift["drift_detected"] is True
        assert res_drift["drift_count"] == 1


# ---------------------------------------------------------------------------
# 11. FallbackStrategy
# ---------------------------------------------------------------------------

class TestFallbackStrategy:

    def test_fallback_strategies(self):
        eta_res = FallbackStrategy.ml_to_heuristic_eta(vendor_id=1, slot_id=2, item_count=3)
        assert eta_res["method"] == "heuristic_fallback"
        assert eta_res["predicted_eta_minutes"] >= 5

        demand_res = FallbackStrategy.ml_to_heuristic_demand(vendor_id=1, days_ahead=7)
        assert demand_res["method"] == "heuristic_fallback"

        redis_res = FallbackStrategy.redis_to_database("recommendations", "u123")
        assert redis_res is None


# ---------------------------------------------------------------------------
# 12. DataFreshnessChecker
# ---------------------------------------------------------------------------

class TestDataFreshnessChecker:

    def test_check_orders_freshness_ratios(self, db_session: Session):
        mock_db = MagicMock()

        # Stale (<10% recent)
        mock_db.query.return_value.filter.return_value.count.side_effect = [1, 100]
        res_stale = DataFreshnessChecker.check_orders_freshness(mock_db, vendor_id=1)
        assert res_stale["status"] == "stale"

        # Degraded (<30% recent)
        mock_db.query.return_value.filter.return_value.count.side_effect = [20, 100]
        res_deg = DataFreshnessChecker.check_orders_freshness(mock_db, vendor_id=1)
        assert res_deg["status"] == "degraded"

        # Fresh (>=30% recent)
        mock_db.query.return_value.filter.return_value.count.side_effect = [50, 100]
        res_fresh = DataFreshnessChecker.check_orders_freshness(mock_db, vendor_id=1)
        assert res_fresh["status"] == "fresh"

    def test_check_menu_availability_ratios(self, db_session: Session):
        mock_db = MagicMock()

        # Critical (<50% available)
        mock_db.query.return_value.filter.return_value.count.side_effect = [10, 3]
        res_crit = DataFreshnessChecker.check_menu_availability(mock_db, vendor_id=1)
        assert res_crit["status"] == "critical"

        # Degraded (<80% available)
        mock_db.query.return_value.filter.return_value.count.side_effect = [10, 7]
        res_deg = DataFreshnessChecker.check_menu_availability(mock_db, vendor_id=1)
        assert res_deg["status"] == "degraded"

        # Healthy (>=80% available)
        mock_db.query.return_value.filter.return_value.count.side_effect = [10, 9]
        res_healthy = DataFreshnessChecker.check_menu_availability(mock_db, vendor_id=1)
        assert res_healthy["status"] == "healthy"


# ---------------------------------------------------------------------------
# 13. RequestValidator
# ---------------------------------------------------------------------------

class TestRequestValidator:

    def test_validate_eta_request(self):
        valid = RequestValidator.validate_eta_request(vendor_id=1, slot_id=2, item_count=3)
        assert valid["valid"] is True
        assert valid["vendor_id"] == 1

        invalid = RequestValidator.validate_eta_request(vendor_id=-1, slot_id=None, item_count=100)
        assert invalid["valid"] is False
        assert len(invalid["errors"]) == 3

    def test_validate_demand_request(self):
        valid = RequestValidator.validate_demand_request(vendor_id=5, days=14)
        assert valid["valid"] is True
        assert valid["days"] == 14

        invalid = RequestValidator.validate_demand_request(vendor_id="bad", days=500)
        assert invalid["valid"] is False
        assert len(invalid["errors"]) == 2
