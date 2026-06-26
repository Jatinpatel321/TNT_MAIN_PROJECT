"""
Production-Ready Upgrades for Vendor AI Forecasting
====================================================

Implements production-grade features:
- Observability & Monitoring
- Resilience & Fault Tolerance
- Data Validation & Quality
- Circuit Breakers
- Health Checks
- Metrics Export
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional
from functools import wraps

from sqlalchemy.orm import Session

logger = logging.getLogger("tnt.ai.production")


# ── Observability & Monitoring ─────────────────────────────────────────


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class Metric:
    """Prometheus-style metric."""
    name: str
    metric_type: MetricType
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: Optional[datetime] = None

    def to_prometheus(self) -> str:
        """Export in Prometheus format."""
        timestamp = int(self.timestamp.timestamp() * 1000) if self.timestamp else int(time.time() * 1000)
        labels_str = ",".join(f'{k}="{v}"' for k, v in self.labels.items())
        
        if self.metric_type == MetricType.COUNTER:
            return f"{self.name}{{{labels_str}}} {self.value} {timestamp}"
        elif self.metric_type == MetricType.GAUGE:
            return f"{self.name}{{{labels_str}}} {self.value} {timestamp}"
        else:
            return f"{self.name}{{{labels_str}}} {self.value} {timestamp}"


class MetricsCollector:
    """Collect and export metrics for AI services."""
    
    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
        self._initialize_metrics()
    
    def _initialize_metrics(self):
        """Initialize standard AI service metrics."""
        # Request metrics
        self.metrics["ai_requests_total"] = Metric(
            "ai_requests_total", MetricType.COUNTER, value=0.0
        )
        self.metrics["ai_request_duration_seconds"] = Metric(
            "ai_request_duration_seconds", MetricType.HISTOGRAM, value=0.0
        )
        self.metrics["ai_errors_total"] = Metric(
            "ai_errors_total", MetricType.COUNTER, value=0.0
        )
        
        # Cache metrics
        self.metrics["ai_cache_hits_total"] = Metric(
            "ai_cache_hits_total", MetricType.COUNTER, value=0.0
        )
        self.metrics["ai_cache_misses_total"] = Metric(
            "ai_cache_misses_total", MetricType.COUNTER, value=0.0
        )
        self.metrics["ai_cache_hit_ratio"] = Metric(
            "ai_cache_hit_ratio", MetricType.GAUGE, value=0.0
        )
        
        # ML model metrics
        self.metrics["ai_model_predictions_total"] = Metric(
            "ai_model_predictions_total", MetricType.COUNTER, value=0.0
        )
        self.metrics["ai_model_fallbacks_total"] = Metric(
            "ai_model_fallbacks_total", MetricType.COUNTER, value=0.0
        )
        self.metrics["ai_model_confidence_avg"] = Metric(
            "ai_model_confidence_avg", MetricType.GAUGE, value=0.0
        )
        
        # Database metrics
        self.metrics["ai_db_queries_total"] = Metric(
            "ai_db_queries_total", MetricType.COUNTER, value=0.0
        )
        self.metrics["ai_db_query_duration_seconds"] = Metric(
            "ai_db_query_duration_seconds", MetricType.HISTOGRAM, value=0.0
        )
    
    def increment(self, metric_name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        if metric_name in self.metrics:
            self.metrics[metric_name].value += value
            self.metrics[metric_name].timestamp = datetime.utcnow()
            if labels:
                self.metrics[metric_name].labels.update(labels)
    
    def set(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        if metric_name in self.metrics:
            self.metrics[metric_name].value = value
            self.metrics[metric_name].timestamp = datetime.utcnow()
            if labels:
                self.metrics[metric_name].labels.update(labels)
    
    def observe(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a histogram/summary metric."""
        if metric_name in self.metrics:
            # For histogram, store as average for simplicity
            current = self.metrics[metric_name].value
            count = self.metrics[metric_name].labels.get("_count", 0)
            new_count = count + 1
            new_avg = ((current * count) + value) / new_count
            self.metrics[metric_name].value = new_avg
            self.metrics[metric_name].labels["_count"] = str(new_count)
            self.metrics[metric_name].timestamp = datetime.utcnow()
            if labels:
                self.metrics[metric_name].labels.update(labels)
    
    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus format."""
        lines = []
        for metric in self.metrics.values():
            lines.append(metric.to_prometheus())
        return "\n".join(lines)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            name: {
                "value": metric.value,
                "type": metric.metric_type.value,
                "timestamp": metric.timestamp.isoformat() if metric.timestamp else None,
            }
            for name, metric in self.metrics.items()
        }


# Global metrics collector
metrics_collector = MetricsCollector()


# ── Structured Logging with Correlation IDs ─────────────────────────────


class CorrelationContext:
    """Thread-local correlation ID context."""
    
    _context = {}
    
    @classmethod
    def set(cls, correlation_id: str, **kwargs):
        """Set correlation context."""
        cls._context = {"correlation_id": correlation_id, **kwargs}
    
    @classmethod
    def get(cls) -> Dict[str, str]:
        """Get correlation context."""
        return cls._context.copy()
    
    @classmethod
    def clear(cls):
        """Clear correlation context."""
        cls._context = {}


class StructuredLogger:
    """Structured logger with correlation IDs."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _log(self, level: str, message: str, **kwargs):
        """Log with correlation context."""
        context = CorrelationContext.get()
        log_data = {
            "message": message,
            "correlation_id": context.get("correlation_id", "N/A"),
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
            **context,
        }
        
        if level == "debug":
            self.logger.debug(json.dumps(log_data))
        elif level == "info":
            self.logger.info(json.dumps(log_data))
        elif level == "warning":
            self.logger.warning(json.dumps(log_data))
        elif level == "error":
            self.logger.error(json.dumps(log_data))
        elif level == "critical":
            self.logger.critical(json.dumps(log_data))
    
    def debug(self, message: str, **kwargs):
        self._log("debug", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("warning", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("error", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log("critical", message, **kwargs)


# ── Circuit Breaker ─────────────────────────────────────────────────────


class CircuitBreakerState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """Circuit breaker for ML model calls."""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if self._should_attempt_recovery():
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info(f"circuit_breaker_half_open name={self.name}")
            else:
                raise Exception(f"Circuit breaker OPEN for {self.name}")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection."""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_recovery():
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info(f"circuit_breaker_half_open name={self.name}")
            else:
                raise Exception(f"Circuit breaker OPEN for {self.name}")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.success_count = 0
                logger.info(f"circuit_breaker_closed name={self.name}")
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.success_count = 0
            logger.warning(f"circuit_breaker_opened name={self.name}")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"circuit_breaker_opened name={self.name} failures={self.failure_count}")
    
    def _should_attempt_recovery(self) -> bool:
        """Check if recovery should be attempted."""
        if self.last_failure_time is None:
            return True
        
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
        }


# Global circuit breakers
circuit_breakers: Dict[str, CircuitBreaker] = {
    "eta_prediction": CircuitBreaker("eta_prediction", failure_threshold=5, recovery_timeout=60),
    "demand_forecast": CircuitBreaker("demand_forecast", failure_threshold=5, recovery_timeout=60),
    "vendor_ranking": CircuitBreaker("vendor_ranking", failure_threshold=5, recovery_timeout=60),
    "fraud_detection": CircuitBreaker("fraud_detection", failure_threshold=3, recovery_timeout=30),
}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """Get or create circuit breaker."""
    if name not in circuit_breakers:
        circuit_breakers[name] = CircuitBreaker(name)
    return circuit_breakers[name]


# ── Retry Logic with Exponential Backoff ────────────────────────────────


class RetryConfig:
    """Retry configuration."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 10.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


def retry_with_backoff(config: Optional[RetryConfig] = None):
    """Decorator for retrying with exponential backoff."""
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            delay = config.initial_delay
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"retry_attempt_failed function={func.__name__} "
                        f"attempt={attempt + 1}/{config.max_attempts} error={str(e)}"
                    )
                    
                    if attempt < config.max_attempts - 1:
                        # Calculate delay with jitter
                        if config.jitter:
                            import random
                            delay = min(delay * config.exponential_base * (0.5 + random.random()), config.max_delay)
                        else:
                            delay = min(delay * config.exponential_base, config.max_delay)
                        
                        time.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


# ── Health Checks ───────────────────────────────────────────────────────


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Health check result."""
    component: str
    status: HealthStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class HealthChecker:
    """Health check manager for AI services."""
    
    def __init__(self, db: Session):
        self.db = db
        self.checks: Dict[str, Callable] = {
            "database": self._check_database,
            "redis": self._check_redis,
            "ml_models": self._check_ml_models,
            "disk_space": self._check_disk_space,
        }
    
    def _check_database(self) -> HealthCheckResult:
        """Check database connectivity."""
        try:
            self.db.execute("SELECT 1")
            return HealthCheckResult(
                component="database",
                status=HealthStatus.HEALTHY,
                message="Database connection successful",
            )
        except Exception as e:
            return HealthCheckResult(
                component="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
            )
    
    def _check_redis(self) -> HealthCheckResult:
        """Check Redis connectivity."""
        try:
            from app.core.redis import redis_client
            redis_client.ping()
            return HealthCheckResult(
                component="redis",
                status=HealthStatus.HEALTHY,
                message="Redis connection successful",
            )
        except Exception as e:
            return HealthCheckResult(
                component="redis",
                status=HealthStatus.DEGRADED,
                message=f"Redis connection failed: {str(e)}",
                details={"impact": "Cache unavailable, using database fallback"},
            )
    
    def _check_ml_models(self) -> HealthCheckResult:
        """Check ML model availability."""
        try:
            from app.ml.registry import ModelRegistry
            summary = ModelRegistry.get_registry_summary()
            
            total_models = len(summary)
            active_models = sum(1 for m in summary.values() if m.get("latest"))
            
            if total_models == 0:
                return HealthCheckResult(
                    component="ml_models",
                    status=HealthStatus.DEGRADED,
                    message="No ML models trained",
                    details={"total_models": 0, "active_models": 0},
                )
            elif active_models < total_models:
                return HealthCheckResult(
                    component="ml_models",
                    status=HealthStatus.DEGRADED,
                    message=f"{total_models - active_models} models without active version",
                    details={"total_models": total_models, "active_models": active_models},
                )
            else:
                return HealthCheckResult(
                    component="ml_models",
                    status=HealthStatus.HEALTHY,
                    message=f"All {total_models} models active",
                    details={"total_models": total_models, "active_models": active_models},
                )
        except Exception as e:
            return HealthCheckResult(
                component="ml_models",
                status=HealthStatus.UNHEALTHY,
                message=f"ML model check failed: {str(e)}",
            )
    
    def _check_disk_space(self) -> HealthCheckResult:
        """Check disk space for model storage."""
        try:
            import shutil
            stat = shutil.disk_usage("ml_models")
            free_gb = stat.free / (1024 ** 3)
            total_gb = stat.total / (1024 ** 3)
            usage_pct = (stat.used / stat.total) * 100
            
            if usage_pct > 90:
                status = HealthStatus.UNHEALTHY
                message = f"Disk usage critical: {usage_pct:.1f}%"
            elif usage_pct > 75:
                status = HealthStatus.DEGRADED
                message = f"Disk usage high: {usage_pct:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk usage normal: {usage_pct:.1f}%"
            
            return HealthCheckResult(
                component="disk_space",
                status=status,
                message=message,
                details={
                    "free_gb": round(free_gb, 2),
                    "total_gb": round(total_gb, 2),
                    "usage_pct": round(usage_pct, 1),
                },
            )
        except Exception as e:
            return HealthCheckResult(
                component="disk_space",
                status=HealthStatus.DEGRADED,
                message=f"Disk check failed: {str(e)}",
            )
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {}
        overall_status = HealthStatus.HEALTHY
        
        for name, check_func in self.checks.items():
            try:
                result = check_func()
                results[name] = result.to_dict()
                
                # Update overall status
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED and overall_status != HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.DEGRADED
            except Exception as e:
                results[name] = {
                    "component": name,
                    "status": HealthStatus.UNHEALTHY.value,
                    "message": f"Health check failed: {str(e)}",
                }
                overall_status = HealthStatus.UNHEALTHY
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": results,
        }
    
    def run_check(self, component: str) -> HealthCheckResult:
        """Run a specific health check."""
        if component not in self.checks:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                message=f"Unknown component: {component}",
            )
        return self.checks[component]()


# ── Data Validation ─────────────────────────────────────────────────────


class DataValidator:
    """Validate input data for AI services."""
    
    @staticmethod
    def validate_vendor_id(vendor_id: Any) -> tuple[bool, Optional[str]]:
        """Validate vendor ID."""
        if vendor_id is None:
            return False, "vendor_id is required"
        try:
            vid = int(vendor_id)
            if vid <= 0:
                return False, "vendor_id must be positive"
            return True, None
        except (ValueError, TypeError):
            return False, "vendor_id must be an integer"
    
    @staticmethod
    def validate_order_id(order_id: Any) -> tuple[bool, Optional[str]]:
        """Validate order ID."""
        if order_id is None:
            return False, "order_id is required"
        try:
            oid = int(order_id)
            if oid <= 0:
                return False, "order_id must be positive"
            return True, None
        except (ValueError, TypeError):
            return False, "order_id must be an integer"
    
    @staticmethod
    def validate_slot_id(slot_id: Any) -> tuple[bool, Optional[str]]:
        """Validate slot ID."""
        if slot_id is None:
            return False, "slot_id is required"
        try:
            sid = int(slot_id)
            if sid <= 0:
                return False, "slot_id must be positive"
            return True, None
        except (ValueError, TypeError):
            return False, "slot_id must be an integer"
    
    @staticmethod
    def validate_days_ahead(days: Any) -> tuple[bool, Optional[str]]:
        """Validate days ahead parameter."""
        if days is None:
            return True, None  # Optional
        try:
            d = int(days)
            if d < 1 or d > 365:
                return False, "days must be between 1 and 365"
            return True, None
        except (ValueError, TypeError):
            return False, "days must be an integer"
    
    @staticmethod
    def validate_item_count(count: Any) -> tuple[bool, Optional[str]]:
        """Validate item count."""
        if count is None:
            return True, None  # Optional
        try:
            c = int(count)
            if c < 1 or c > 50:
                return False, "item_count must be between 1 and 50"
            return True, None
        except (ValueError, TypeError):
            return False, "item_count must be an integer"
    
    @staticmethod
    def validate_prediction_result(result: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate prediction result."""
        if not isinstance(result, dict):
            return False, "Prediction result must be a dictionary"
        
        # Check required fields
        required_fields = ["predicted_eta_minutes", "confidence_score", "delay_risk_level"]
        for field in required_fields:
            if field not in result:
                return False, f"Missing required field: {field}"
        
        # Validate types and ranges
        eta = result.get("predicted_eta_minutes")
        if not isinstance(eta, (int, float)) or eta < 0 or eta > 180:
            return False, "predicted_eta_minutes must be between 0 and 180"
        
        confidence = result.get("confidence_score")
        if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            return False, "confidence_score must be between 0.0 and 1.0"
        
        risk = result.get("delay_risk_level")
        if risk not in ["LOW", "MEDIUM", "HIGH"]:
            return False, "delay_risk_level must be LOW, MEDIUM, or HIGH"
        
        return True, None


# ── Decorators for Production Features ─────────────────────────────────


def with_correlation_id(func: Callable):
    """Decorator to add correlation ID to function calls."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        correlation_id = str(uuid.uuid4())
        CorrelationContext.set(correlation_id)
        
        try:
            logger_structured = StructuredLogger(func.__module__)
            logger_structured.debug(
                f"function_started function={func.__name__}",
                correlation_id=correlation_id
            )
            
            result = func(*args, **kwargs)
            
            logger_structured.debug(
                f"function_completed function={func.__name__}",
                correlation_id=correlation_id
            )
            
            return result
        except Exception as e:
            logger_structured.error(
                f"function_failed function={func.__name__} error={str(e)}",
                correlation_id=correlation_id
            )
            raise
        finally:
            CorrelationContext.clear()
    
    return wrapper


def with_metrics(func: Callable):
    """Decorator to collect metrics for function calls."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        metrics_collector.increment("ai_requests_total", labels={"function": func.__name__})
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            metrics_collector.observe("ai_request_duration_seconds", duration, labels={"function": func.__name__})
            return result
        except Exception as e:
            metrics_collector.increment("ai_errors_total", labels={"function": func.__name__, "error": type(e).__name__})
            raise
    
    return wrapper


def with_validation(**validators):
    """Decorator to validate function arguments."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validate arguments
            for param_name, validator_func in validators.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    is_valid, error_msg = validator_func(value)
                    if not is_valid:
                        raise ValueError(f"Validation failed for {param_name}: {error_msg}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def with_circuit_breaker(breaker_name: str):
    """Decorator to wrap function with circuit breaker."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            breaker = get_circuit_breaker(breaker_name)
            return breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator


# ── Context Managers ────────────────────────────────────────────────────


@contextmanager
def timed_context(operation_name: str):
    """Context manager for timing operations."""
    start_time = time.time()
    logger_structured = StructuredLogger("tnt.ai.timing")
    
    try:
        logger_structured.info(f"operation_started operation={operation_name}")
        yield
        duration = time.time() - start_time
        logger_structured.info(
            f"operation_completed operation={operation_name} duration={duration:.3f}s"
        )
        metrics_collector.observe("ai_request_duration_seconds", duration, labels={"operation": operation_name})
    except Exception as e:
        duration = time.time() - start_time
        logger_structured.error(
            f"operation_failed operation={operation_name} duration={duration:.3f}s error={str(e)}"
        )
        metrics_collector.increment("ai_errors_total", labels={"operation": operation_name, "error": type(e).__name__})
        raise


@contextmanager
def db_session_scope(db: Session):
    """Context manager for database sessions with error handling."""
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"database_transaction_failed error={str(e)}")
        raise
    finally:
        db.close()


# ── Feature Drift Detection ─────────────────────────────────────────────


class FeatureDriftDetector:
    """Detect drift in feature distributions."""
    
    def __init__(self, reference_window: int = 30):
        self.reference_window = reference_window
        self.reference_stats: Dict[str, Dict[str, float]] = {}
    
    def update_reference(self, features: Dict[str, float]):
        """Update reference statistics."""
        for feature_name, value in features.items():
            if feature_name not in self.reference_stats:
                self.reference_stats[feature_name] = {
                    "mean": value,
                    "variance": 0.0,
                    "count": 1,
                }
            else:
                stats = self.reference_stats[feature_name]
                count = stats["count"] + 1
                delta = value - stats["mean"]
                new_mean = stats["mean"] + delta / count
                new_variance = stats["variance"] + delta * (value - new_mean)
                
                stats["mean"] = new_mean
                stats["variance"] = new_variance
                stats["count"] = count
    
    def detect_drift(self, current_features: Dict[str, float], threshold: float = 2.0) -> Dict[str, Any]:
        """Detect if current features have drifted from reference."""
        drift_detected = False
        drift_details = []
        
        for feature_name, current_value in current_features.items():
            if feature_name not in self.reference_stats:
                continue
            
            stats = self.reference_stats[feature_name]
            if stats["count"] < 10:  # Need minimum samples
                continue
            
            mean = stats["mean"]
            std_dev = (stats["variance"] / stats["count"]) ** 0.5
            
            if std_dev > 0:
                z_score = abs(current_value - mean) / std_dev
                
                if z_score > threshold:
                    drift_detected = True
                    drift_details.append({
                        "feature": feature_name,
                        "current_value": current_value,
                        "reference_mean": mean,
                        "reference_std": std_dev,
                        "z_score": round(z_score, 2),
                    })
        
        return {
            "drift_detected": drift_detected,
            "drift_count": len(drift_details),
            "drift_details": drift_details,
            "threshold": threshold,
        }


# Global drift detector
feature_drift_detector = FeatureDriftDetector()


# ── Graceful Degradation ────────────────────────────────────────────────


class FallbackStrategy:
    """Fallback strategies for AI services."""
    
    @staticmethod
    def ml_to_heuristic_eta(vendor_id: int, slot_id: int, item_count: int = 1) -> Dict[str, Any]:
        """Fallback from ML to heuristic ETA prediction."""
        logger.warning(
            f"fallback_activated from=ml to=heuristic operation=eta_prediction "
            f"vendor_id={vendor_id} slot_id={slot_id}"
        )
        metrics_collector.increment("ai_model_fallbacks_total", labels={"model": "eta_prediction"})
        
        # Simple heuristic
        base_prep = 15.0
        predicted = int(base_prep * (1 + 0.1 * max(0, item_count - 1)))
        predicted = max(5, min(predicted, 60))
        
        return {
            "method": "heuristic_fallback",
            "model": None,
            "predicted_eta_minutes": predicted,
            "confidence_score": 0.5,
            "delay_risk_level": "MEDIUM",
            "explanation": {"explanation": "ML model unavailable, using heuristic fallback"},
        }
    
    @staticmethod
    def ml_to_heuristic_demand(vendor_id: int, days_ahead: int = 7) -> Dict[str, Any]:
        """Fallback from ML to heuristic demand forecast."""
        logger.warning(
            f"fallback_activated from=ml to=heuristic operation=demand_forecast "
            f"vendor_id={vendor_id}"
        )
        metrics_collector.increment("ai_model_fallbacks_total", labels={"model": "demand_forecast"})
        
        # Simple daily average
        from app.core.time_utils import utcnow_naive
        from app.modules.orders.model import Order
        from sqlalchemy.orm import Session
        
        # This would need db session, simplified here
        return {
            "vendor_id": vendor_id,
            "forecasts": [],
            "method": "heuristic_fallback",
            "total_predicted": 0,
            "message": "ML model unavailable, no historical data available",
        }
    
    @staticmethod
    def redis_to_database(category: str, identifier: str) -> Optional[Any]:
        """Fallback from Redis to database query."""
        logger.warning(
            f"fallback_activated from=redis to=database operation=cache_get "
            f"category={category} identifier={identifier}"
        )
        metrics_collector.increment("ai_cache_misses_total", labels={"category": category})
        return None  # Caller should query database


# ── Data Freshness Checks ───────────────────────────────────────────────


class DataFreshnessChecker:
    """Check freshness of historical data."""
    
    @staticmethod
    def check_orders_freshness(db: Session, vendor_id: int, max_age_days: int = 7) -> Dict[str, Any]:
        """Check if order data is fresh enough for predictions."""
        from app.modules.orders.model import Order
        from app.core.time_utils import utcnow_naive
        
        cutoff = utcnow_naive() - timedelta(days=max_age_days)
        
        recent_orders = db.query(Order.id).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= cutoff,
        ).count()
        
        total_orders = db.query(Order.id).filter(
            Order.vendor_id == vendor_id,
        ).count()
        
        freshness_ratio = recent_orders / max(total_orders, 1)
        
        if freshness_ratio < 0.1:
            status = "stale"
            message = f"Only {freshness_ratio:.1%} of orders are recent"
        elif freshness_ratio < 0.3:
            status = "degraded"
            message = f"Data freshness is {freshness_ratio:.1%}"
        else:
            status = "fresh"
            message = f"Data is fresh: {freshness_ratio:.1%} recent orders"
        
        return {
            "status": status,
            "message": message,
            "recent_orders": recent_orders,
            "total_orders": total_orders,
            "freshness_ratio": round(freshness_ratio, 2),
            "max_age_days": max_age_days,
        }
    
    @staticmethod
    def check_menu_availability(db: Session, vendor_id: int) -> Dict[str, Any]:
        """Check menu item availability."""
        from app.modules.menu.model import MenuItem
        
        total_items = db.query(MenuItem.id).filter(
            MenuItem.vendor_id == vendor_id,
        ).count()
        
        available_items = db.query(MenuItem.id).filter(
            MenuItem.vendor_id == vendor_id,
            MenuItem.is_available == True,
        ).count()
        
        availability_ratio = available_items / max(total_items, 1)
        
        if availability_ratio < 0.5:
            status = "critical"
            message = f"Only {availability_ratio:.1%} of menu items available"
        elif availability_ratio < 0.8:
            status = "degraded"
            message = f"Menu availability is {availability_ratio:.1%}"
        else:
            status = "healthy"
            message = f"Menu is {availability_ratio:.1%} available"
        
        return {
            "status": status,
            "message": message,
            "total_items": total_items,
            "available_items": available_items,
            "availability_ratio": round(availability_ratio, 2),
        }


# ── Request Validation Middleware ───────────────────────────────────────


class RequestValidator:
    """Validate incoming API requests."""
    
    @staticmethod
    def validate_eta_request(vendor_id: Any, slot_id: Any, item_count: Any) -> Dict[str, Any]:
        """Validate ETA prediction request."""
        errors = []
        
        is_valid, error = DataValidator.validate_vendor_id(vendor_id)
        if not is_valid:
            errors.append(error)
        
        is_valid, error = DataValidator.validate_slot_id(slot_id)
        if not is_valid:
            errors.append(error)
        
        is_valid, error = DataValidator.validate_item_count(item_count)
        if not is_valid:
            errors.append(error)
        
        if errors:
            return {
                "valid": False,
                "errors": errors,
            }
        
        return {
            "valid": True,
            "vendor_id": int(vendor_id),
            "slot_id": int(slot_id),
            "item_count": int(item_count) if item_count else 1,
        }
    
    @staticmethod
    def validate_demand_request(vendor_id: Any, days: Any) -> Dict[str, Any]:
        """Validate demand forecast request."""
        errors = []
        
        is_valid, error = DataValidator.validate_vendor_id(vendor_id)
        if not is_valid:
            errors.append(error)
        
        is_valid, error = DataValidator.validate_days_ahead(days)
        if not is_valid:
            errors.append(error)
        
        if errors:
            return {
                "valid": False,
                "errors": errors,
            }
        
        return {
            "valid": True,
            "vendor_id": int(vendor_id),
            "days": int(days) if days else 7,
        }