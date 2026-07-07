# Production Upgrade Guide
## Vendor AI Forecasting System

---

## Table of Contents
1. [Upgrade Overview](#upgrade-overview)
2. [Phase 1: Observability](#phase-1-observability)
3. [Phase 2: Resilience](#phase-2-resilience)
4. [Phase 3: Data Quality](#phase-3-data-quality)
5. [Phase 4: Scalability](#phase-4-scalability)
6. [Phase 5: API Governance](#phase-5-api-governance)
7. [Deployment Checklist](#deployment-checklist)
8. [Monitoring Setup](#monitoring-setup)
9. [Rollback Procedures](#rollback-procedures)

---

## Upgrade Overview

### Current State
- ✅ Multi-layered prediction (Heuristic + ML + Real-time)
- ✅ Model versioning with Postgres registry
- ✅ Redis caching with TTL management
- ✅ 20+ API endpoints
- ✅ Basic explainability

### Target State
- 🎯 Full observability with Prometheus metrics
- 🎯 Circuit breakers and graceful degradation
- 🎯 Data validation and drift detection
- 🎯 Health checks and monitoring
- 🎯 Production-grade resilience

### Upgrade Phases
| Phase | Focus | Duration | Risk |
|-------|-------|----------|------|
| 1 | Observability | 1 week | Low |
| 2 | Resilience | 1 week | Medium |
| 3 | Data Quality | 3 days | Low |
| 4 | Scalability | 1 week | Medium |
| 5 | API Governance | 3 days | Low |

---

## Phase 1: Observability

### 1.1 Structured Logging

**File to modify**: All AI service files

```python
# Before
import logging
logger = logging.getLogger("tnt.ai.service")

logger.info("Processing request")

# After
from app.modules.ai_intelligence.production_upgrades import StructuredLogger, CorrelationContext

logger = StructuredLogger("tnt.ai.service")

# In request handler
correlation_id = str(uuid.uuid4())
CorrelationContext.set(correlation_id, user_id=user_id, vendor_id=vendor_id)

logger.info("Processing request", operation="eta_prediction")
```

**Implementation Steps**:
1. Add `StructuredLogger` import to all AI services
2. Wrap API endpoints with correlation ID generation
3. Update log format to JSON in production
4. Configure log aggregation (ELK/Splunk)

**Files to update**:
- `app/modules/ai_intelligence/vendor_speed_service.py`
- `app/modules/ai_intelligence/planners/enhanced_eta_engine.py`
- `app/modules/vendors/vendor_ai_service.py`
- `app/modules/vendors/demand_dashboard_service.py`
- `app/ml/predictions.py`

### 1.2 Metrics Collection

**File to modify**: API routers

```python
# Add to endpoint
from app.modules.ai_intelligence.production_upgrades import metrics_collector

@router.get("/vendor-speed/{vendor_id}")
async def get_vendor_speed(
    vendor_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    metrics_collector.increment("ai_requests_total", labels={"endpoint": "vendor_speed"})
    start_time = time.time()
    
    try:
        service = VendorSpeedService(db)
        result = service.get_vendor_speed_metrics(vendor_id)
        
        duration = time.time() - start_time
        metrics_collector.observe("ai_request_duration_seconds", duration, labels={"endpoint": "vendor_speed"})
        
        return result
    except Exception as e:
        metrics_collector.increment("ai_errors_total", labels={"endpoint": "vendor_speed", "error": type(e).__name__})
        raise
```

**Metrics to expose**:
```python
# Prometheus endpoint: GET /metrics
- ai_requests_total{endpoint, function}
- ai_request_duration_seconds{endpoint, function}
- ai_errors_total{endpoint, error}
- ai_cache_hits_total{category}
- ai_cache_misses_total{category}
- ai_model_predictions_total{model_type}
- ai_model_fallbacks_total{model_type}
- ai_model_confidence_avg{model_type}
```

### 1.3 Health Check Endpoints

**New file**: `app/modules/ai_intelligence/health_router.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.deps import get_db
from app.modules.ai_intelligence.production_upgrades import HealthChecker

router = APIRouter(prefix="/health", tags=["Health Checks"])

@router.get("/")
async def health_check(db: Session = Depends(get_db)):
    """Overall health check."""
    checker = HealthChecker(db)
    return checker.run_all_checks()

@router.get("/{component}")
async def component_health(component: str, db: Session = Depends(get_db)):
    """Check specific component health."""
    checker = HealthChecker(db)
    result = checker.run_check(component)
    return result.to_dict()
```

**Add to main router**:
```python
# app/api/v1.py
from app.modules.ai_intelligence.health_router import router as health_router
router.include_router(health_router)
```

---

## Phase 2: Resilience

### 2.1 Circuit Breakers

**File to modify**: `app/ml/predictions.py`

```python
from app.modules.ai_intelligence.production_upgrades import get_circuit_breaker

class MLPredictionService:
    def predict_eta(self, vendor_id: int, slot_id: int, item_count: int = 1):
        """Predict ETA with circuit breaker protection."""
        breaker = get_circuit_breaker("eta_prediction")
        
        try:
            return breaker.call(self._predict_eta_impl, vendor_id, slot_id, item_count)
        except Exception as e:
            # Fallback to heuristic
            return self._heuristic_eta(vendor_id, slot_id, item_count)
    
    def _predict_eta_impl(self, vendor_id: int, slot_id: int, item_count: int):
        """Actual ML prediction implementation."""
        # Existing ML prediction logic
        pass
```

**Circuit breaker configuration**:
```python
# app/modules/ai_intelligence/production_upgrades.py

circuit_breakers = {
    "eta_prediction": CircuitBreaker(
        name="eta_prediction",
        failure_threshold=5,      # Open after 5 failures
        recovery_timeout=60,      # Wait 60s before retry
        success_threshold=2       # Close after 2 successes
    ),
    "demand_forecast": CircuitBreaker(
        name="demand_forecast",
        failure_threshold=5,
        recovery_timeout=60,
        success_threshold=2
    ),
}
```

### 2.2 Retry Logic

**File to modify**: Database and Redis operations

```python
from app.modules.ai_intelligence.production_upgrades import retry_with_backoff, RetryConfig

# Configure retry
retry_config = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True
)

@retry_with_backoff(retry_config)
def query_with_retry(db: Session, query):
    """Execute database query with retry."""
    return db.execute(query)
```

### 2.3 Graceful Degradation

**File to modify**: All prediction services

```python
from app.modules.ai_intelligence.production_upgrades import FallbackStrategy

class MLPredictionService:
    def predict_eta(self, vendor_id: int, slot_id: int, item_count: int = 1):
        """Predict ETA with fallback."""
        try:
            # Try ML model first
            model_data = ModelRegistry.load("eta_prediction")
            if model_data:
                return self._ml_predict(vendor_id, slot_id, item_count)
        except Exception as e:
            logger.warning(f"ML prediction failed: {e}")
        
        # Fallback to heuristic
        return FallbackStrategy.ml_to_heuristic_eta(vendor_id, slot_id, item_count)
```

---

## Phase 3: Data Quality

### 3.1 Input Validation

**File to modify**: All API endpoints

```python
from app.modules.ai_intelligence.production_upgrades import RequestValidator

@router.get("/predict/eta")
def predict_eta(
    vendor_id: int = Query(...),
    slot_id: int = Query(...),
    item_count: int = Query(1),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # Validate input
    validation = RequestValidator.validate_eta_request(vendor_id, slot_id, item_count)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["errors"])
    
    vendor_id = validation["vendor_id"]
    slot_id = validation["slot_id"]
    item_count = validation["item_count"]
    
    # Continue with prediction
    service = MLPredictionService(db)
    return service.predict_eta(vendor_id, slot_id, item_count)
```

### 3.2 Data Freshness Checks

**File to modify**: `app/modules/vendors/demand_dashboard_service.py`

```python
from app.modules.ai_intelligence.production_upgrades import DataFreshnessChecker

class DemandDashboardService:
    def get_demand_overview(self, vendor_id: int):
        # Check data freshness first
        freshness = DataFreshnessChecker.check_orders_freshness(self.db, vendor_id)
        
        if freshness["status"] == "stale":
            logger.warning(f"Stale data for vendor {vendor_id}: {freshness['message']}")
            # Add warning to response
            overview = self._compute_overview(vendor_id)
            overview["data_quality_warning"] = freshness["message"]
            return overview
        
        return self._compute_overview(vendor_id)
```

### 3.3 Feature Drift Detection

**File to modify**: `app/ml/predictions.py`

```python
from app.modules.ai_intelligence.production_upgrades import feature_drift_detector

class MLPredictionService:
    def predict_eta(self, vendor_id: int, slot_id: int, item_count: int = 1):
        # Extract features
        features = self._extract_features(vendor_id, slot_id, item_count)
        
        # Check for drift
        drift_result = feature_drift_detector.detect_drift(features)
        if drift_result["drift_detected"]:
            logger.warning(
                f"Feature drift detected: {drift_result['drift_count']} features",
                drift_details=drift_result["drift_details"]
            )
            # Trigger model retraining
            self._trigger_retraining(vendor_id)
        
        # Update reference statistics
        feature_drift_detector.update_reference(features)
        
        # Continue with prediction
        return self._predict(features)
```

---

## Phase 4: Scalability

### 4.1 Background Model Training

**New file**: `app/ml/background_tasks.py`

```python
from celery import Celery
from app.ml.training_pipeline import train_eta_models, train_demand_forecast

celery_app = Celery(
    "ml_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

@celery_app.task
def retrain_eta_model(vendor_id: int, days: int = 90):
    """Background task to retrain ETA model."""
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        result = train_eta_models(db, days=days)
        logger.info(f"ETA model retrained: {result}")
        return result
    finally:
        db.close()

@celery_app.task
def retrain_demand_model(vendor_id: int, days: int = 90):
    """Background task to retrain demand model."""
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        result = train_demand_forecast(db, vendor_id, days=days)
        logger.info(f"Demand model retrained for vendor {vendor_id}: {result}")
        return result
    finally:
        db.close()
```

### 4.2 Batch Prediction Processing

**File to modify**: `app/ml/predictions.py`

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

class MLPredictionService:
    def batch_predict_eta(self, requests: list[dict]) -> list[dict]:
        """Process multiple ETA predictions in parallel."""
        results = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(
                    self.predict_eta,
                    req["vendor_id"],
                    req["slot_id"],
                    req.get("item_count", 1)
                ): req
                for req in requests
            }
            
            for future in as_completed(futures):
                req = futures[future]
                try:
                    result = future.result()
                    results.append({
                        "request": req,
                        "result": result,
                        "status": "success"
                    })
                except Exception as e:
                    results.append({
                        "request": req,
                        "error": str(e),
                        "status": "failed"
                    })
        
        return results
```

### 4.3 Connection Pooling

**File to modify**: `app/database/session.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,           # Number of connections to maintain
    max_overflow=10,        # Additional connections if pool is full
    pool_timeout=30,        # Timeout for getting connection
    pool_recycle=3600,      # Recycle connections after 1 hour
    pool_pre_ping=True,     # Check connection health before use
)
```

---

## Phase 5: API Governance

### 5.1 Rate Limiting

**New file**: `app/core/rate_limit.py`

```python
from fastapi import HTTPException
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple

class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self.requests: Dict[str, list[datetime]] = defaultdict(list)
    
    def is_allowed(
        self,
        key: str,
        max_requests: int = 100,
        window_seconds: int = 60
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)
        
        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > window_start
        ]
        
        # Check limit
        recent_requests = self.requests[key]
        if len(recent_requests) >= max_requests:
            return False, {
                "error": "Rate limit exceeded",
                "limit": max_requests,
                "window_seconds": window_seconds,
                "retry_after": (recent_requests[0] + timedelta(seconds=window_seconds) - now).total_seconds()
            }
        
        # Add current request
        self.requests[key].append(now)
        
        return True, {
            "limit": max_requests,
            "remaining": max_requests - len(recent_requests) - 1,
            "reset": (now + timedelta(seconds=window_seconds)).isoformat()
        }

rate_limiter = RateLimiter()

def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """Decorator for rate limiting."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get user ID from request
            user = kwargs.get("user")
            if user:
                key = f"user:{user['id']}"
            else:
                key = "anonymous"
            
            allowed, info = rate_limiter.is_allowed(key, max_requests, window_seconds)
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail=info["error"],
                    headers={"Retry-After": str(int(info["retry_after"]))}
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

**Usage**:
```python
@router.get("/predict/eta")
@rate_limit(max_requests=50, window_seconds=60)
async def predict_eta(...):
    # Endpoint logic
    pass
```

### 5.2 Request Validation Middleware

**File to modify**: `app/api/v1.py`

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.modules.ai_intelligence.production_upgrades import RequestValidator

class ValidationMiddleware(BaseHTTPMiddleware):
    """Validate all incoming requests."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip validation for non-API routes
        if not request.url.path.startswith(("/ml/", "/ai/", "/vendors/demand-dashboard")):
            return await call_next(request)
        
        # Validate based on endpoint
        path = request.url.path
        query_params = dict(request.query_params)
        
        if "/predict/eta" in path:
            validation = RequestValidator.validate_eta_request(
                query_params.get("vendor_id"),
                query_params.get("slot_id"),
                query_params.get("item_count")
            )
            if not validation["valid"]:
                return JSONResponse(
                    status_code=400,
                    content={"errors": validation["errors"]}
                )
        
        return await call_next(request)

# Add to app
app.add_middleware(ValidationMiddleware)
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] **Code Review**
  - [ ] All production upgrades implemented
  - [ ] Unit tests pass (coverage > 80%)
  - [ ] Integration tests pass
  - [ ] Code review approved

- [ ] **Configuration**
  - [ ] Environment variables set
  - [ ] Database connection strings configured
  - [ ] Redis connection configured
  - [ ] Logging level set to INFO
  - [ ] Metrics endpoint enabled

- [ ] **Database**
  - [ ] Migration scripts ready
  - [ ] Backup taken
  - [ ] Indexes created for performance
  - [ ] Connection pool configured

- [ ] **ML Models**
  - [ ] Models trained and validated
  - [ ] Models registered in ModelRegistry
  - [ ] Model artifacts backed up
  - [ ] Fallback strategies tested

### Deployment

- [ ] **Staging Deployment**
  - [ ] Deploy to staging environment
  - [ ] Run smoke tests
  - [ ] Verify health checks pass
  - [ ] Load test (1000 RPS)
  - [ ] Monitor metrics for 24 hours

- [ ] **Production Deployment**
  - [ ] Deploy during low-traffic window
  - [ ] Enable feature flags (gradual rollout)
  - [ ] Monitor error rates
  - [ ] Monitor latency (p50, p95, p99)
  - [ ] Monitor cache hit rates
  - [ ] Monitor circuit breaker states

### Post-Deployment

- [ ] **Validation**
  - [ ] All health checks pass
  - [ ] Error rate < 1%
  - [ ] Latency p95 < 500ms
  - [ ] Cache hit rate > 70%
  - [ ] No circuit breaker trips

- [ ] **Documentation**
  - [ ] API documentation updated
  - [ ] Runbook created
  - [ ] On-call team trained
  - [ ] Monitoring dashboards shared

- [ ] **Monitoring Setup**
  - [ ] Prometheus scraping configured
  - [ ] Grafana dashboards created
  - [ ] Alerts configured
  - [ ] Log aggregation working
  - [ ] APM tool integrated

---

## Monitoring Setup

### Prometheus Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'ai-services'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Grafana Dashboards

**Dashboard 1: AI Services Overview**
```
Panels:
- Request Rate (requests/sec)
- Error Rate (%)
- Latency (p50, p95, p99)
- Cache Hit Ratio (%)
- Active Circuit Breakers
```

**Dashboard 2: ML Model Performance**
```
Panels:
- Predictions per Model
- Model Confidence (avg)
- Model Fallbacks
- Feature Drift Alerts
- Model Accuracy Trend
```

**Dashboard 3: Vendor Analytics**
```
Panels:
- ETA Prediction Accuracy
- Demand Forecast Accuracy
- Vendor Speed Distribution
- Queue Depth Trends
- Completion Rate Trends
```

### Alerts

```yaml
# alerts.yml
groups:
  - name: ai_services
    rules:
      - alert: HighErrorRate
        expr: rate(ai_errors_total[5m]) / rate(ai_requests_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          
      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state{state="open"} == 1
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Circuit breaker open for {{ $labels.name }}"
          
      - alert: LowCacheHitRate
        expr: ai_cache_hit_ratio < 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Cache hit rate below 50%"
```

---

## Rollback Procedures

### Immediate Rollback (< 5 minutes)

```bash
# 1. Disable new features via feature flags
curl -X POST http://localhost:8000/admin/features/disable \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"features": ["circuit_breakers", "drift_detection"]}'

# 2. Rollback model to previous version
curl -X POST http://localhost:8000/ml/registry/eta_prediction/rollback/1 \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 3. Clear Redis cache
redis-cli FLUSHDB

# 4. Restart previous version
git checkout v1.2.0
docker-compose up -d
```

### Partial Rollback (5-15 minutes)

```bash
# 1. Disable specific endpoints
# Comment out in router configuration

# 2. Revert database migration
alembic downgrade -1

# 3. Restore model artifacts
cp ml_models/backup/eta_prediction_v1.pkl ml_models/eta_prediction/

# 4. Restart services
docker-compose restart api
```

### Full Rollback (15-30 minutes)

```bash
# 1. Stop all services
docker-compose down

# 2. Restore database from backup
pg_restore -d tnt_db backup_20240101.dump

# 3. Restore code
git checkout v1.1.0

# 4. Restore models
cp -r ml_models/backup/* ml_models/

# 5. Start services
docker-compose up -d

# 6. Verify health
curl http://localhost:8000/health
```

---

## Performance Targets

### Latency Targets
| Endpoint | p50 | p95 | p99 |
|----------|-----|-----|-----|
| ETA Prediction | 50ms | 150ms | 300ms |
| Demand Forecast | 100ms | 300ms | 500ms |
| Vendor Speed | 80ms | 200ms | 400ms |
| Dashboard | 200ms | 500ms | 1000ms |

### Availability Targets
| Component | Target |
|-----------|--------|
| API Uptime | 99.9% |
| ML Model Availability | 99.5% |
| Redis Cache | 99.9% |
| Database | 99.99% |

### Accuracy Targets
| Model | Target |
|-------|--------|
| ETA Prediction | MAE < 5 minutes |
| Demand Forecast | MAPE < 15% |
| Vendor Ranking | Correlation > 0.7 |

---

## Troubleshooting Guide

### High Error Rate

1. Check circuit breaker states: `GET /health`
2. Check ML model availability: `GET /ml/registry`
3. Check database connectivity: `GET /health/database`
4. Review logs for exceptions
5. Rollback if necessary

### High Latency

1. Check cache hit rate: `GET /metrics`
2. Check database query performance
3. Check Redis latency
4. Review slow query logs
5. Consider scaling up

### Low Cache Hit Rate

1. Check TTL settings
2. Review cache invalidation logic
3. Check Redis memory usage
4. Verify cache keys are consistent
5. Consider increasing TTL

### Model Accuracy Drop

1. Check feature drift: Review drift detection logs
2. Check data freshness: `DataFreshnessChecker`
3. Retrain model with recent data
4. Compare with previous version
5. Rollback if degraded

---

## Appendix

### A. Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/tnt_db
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0

# ML Models
MODEL_STORAGE_DIR=./ml_models
MODEL_RETRAIN_INTERVAL=86400  # 24 hours

# Monitoring
PROMETHEUS_ENABLED=true
METRICS_PORT=8000
LOG_LEVEL=INFO

# Circuit Breakers
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60
```

### B. Useful Commands

```bash
# Check health
curl http://localhost:8000/health

# View metrics
curl http://localhost:8000/metrics

# List models
curl http://localhost:8000/ml/registry

# Retrain model
curl -X POST http://localhost:8000/ml/train/eta \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Clear cache
redis-cli FLUSHDB

# View logs
tail -f logs/ai_services.log

# Database query
psql -d tnt_db -c "SELECT * FROM ml_models ORDER BY trained_at DESC LIMIT 10;"
```

### C. Contact Information

- **On-Call Engineer**: [PagerDuty link]
- **ML Team**: [Slack channel]
- **DevOps**: [Slack channel]
- **Documentation**: [Wiki link]