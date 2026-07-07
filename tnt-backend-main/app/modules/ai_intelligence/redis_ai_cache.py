"""
AI Services Redis Cache
========================

Comprehensive Redis caching for AI services:

- Recommendations
- ETA predictions
- Trending vendors
- Popular items
- Recently viewed
- Prediction cache

Features:
- TTL management
- Cache invalidation
- Performance monitoring
- Hit/miss tracking
- Latency reduction
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger("tnt.ai.redis_cache")


@dataclass
class CacheConfig:
    """Cache configuration with TTL and monitoring."""
    ttl_seconds: int
    prefix: str
    enabled: bool = True
    track_metrics: bool = True


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    avg_latency_ms: float = 0.0
    last_access: Optional[datetime] = None


class AIServicesRedisCache:
    """Comprehensive Redis caching for AI services."""

    def __init__(self):
        self.redis_client = None
        self.configs: Dict[str, CacheConfig] = {
            # Recommendations
            'recommendations': CacheConfig(ttl_seconds=300, prefix='ai:recs'),  # 5 min
            'recommendations_ranked': CacheConfig(ttl_seconds=300, prefix='ai:recs:ranked'),  # 5 min
            'personalized_vendors': CacheConfig(ttl_seconds=600, prefix='ai:vendors'),  # 10 min
            'personalized_menu': CacheConfig(ttl_seconds=300, prefix='ai:menu'),  # 5 min
            
            # ETA predictions
            'eta_prediction': CacheConfig(ttl_seconds=60, prefix='ai:eta'),  # 1 min
            'eta_factors': CacheConfig(ttl_seconds=120, prefix='ai:eta:factors'),  # 2 min
            'vendor_speed': CacheConfig(ttl_seconds=120, prefix='ai:speed'),  # 2 min
            
            # Trending & Popular
            'trending_items': CacheConfig(ttl_seconds=600, prefix='ai:trending'),  # 10 min
            'trending_vendors': CacheConfig(ttl_seconds=600, prefix='ai:trending:vendor'),  # 10 min
            'popular_items': CacheConfig(ttl_seconds=1800, prefix='ai:popular'),  # 30 min
            'popular_vendors': CacheConfig(ttl_seconds=1800, prefix='ai:popular:vendor'),  # 30 min
            
            # User behavior
            'recently_viewed': CacheConfig(ttl_seconds=1800, prefix='ai:viewed'),  # 30 min
            'user_preferences': CacheConfig(ttl_seconds=3600, prefix='ai:prefs'),  # 1 hour
            'user_behavior': CacheConfig(ttl_seconds=3600, prefix='ai:behavior'),  # 1 hour
            
            # Predictions
            'prediction_cache': CacheConfig(ttl_seconds=300, prefix='ai:pred'),  # 5 min
            'vendor_prediction': CacheConfig(ttl_seconds=300, prefix='ai:pred:vendor'),  # 5 min
            
            # Group AI
            'group_suggestions': CacheConfig(ttl_seconds=600, prefix='ai:group'),  # 10 min
            'group_payments': CacheConfig(ttl_seconds=120, prefix='ai:group:payments'),  # 2 min
        }
        
        # Metrics tracking
        self.metrics: Dict[str, CacheMetrics] = {}
        for category in self.configs:
            self.metrics[category] = CacheMetrics()

    def initialize(self):
        """Initialize Redis connection."""
        try:
            from app.core.redis import redis_client
            self.redis_client = redis_client
            logger.info("ai_redis_cache_initialized")
        except Exception as e:
            logger.error("ai_redis_cache_init_failed error=%s", e)
            raise

    def _get_key(self, category: str, identifier: str) -> str:
        """Generate cache key."""
        config = self.configs.get(category)
        if not config:
            raise ValueError(f"Unknown cache category: {category}")
        return f"{config.prefix}:{identifier}"

    def _track_request(self, category: str, latency_ms: float, hit: bool):
        """Track cache performance metrics."""
        if category not in self.metrics:
            return
        
        metrics = self.metrics[category]
        metrics.total_requests += 1
        metrics.last_access = datetime.utcnow()
        
        if hit:
            metrics.hits += 1
        else:
            metrics.misses += 1
        
        # Update average latency
        if metrics.avg_latency_ms == 0:
            metrics.avg_latency_ms = latency_ms
        else:
            metrics.avg_latency_ms = (metrics.avg_latency_ms + latency_ms) / 2

    async def get(self, category: str, identifier: str) -> Optional[Any]:
        """Get value from cache with metrics tracking."""
        start_time = time.time()
        
        if not self.redis_client:
            self.initialize()

        try:
            key = self._get_key(category, identifier)
            value = self.redis_client.get(key)
            
            latency_ms = (time.time() - start_time) * 1000
            
            if value:
                logger.debug("ai_cache_hit category=%s key=%s latency=%.2fms", category, identifier, latency_ms)
                self._track_request(category, latency_ms, hit=True)
                return json.loads(value)
            
            logger.debug("ai_cache_miss category=%s key=%s latency=%.2fms", category, identifier, latency_ms)
            self._track_request(category, latency_ms, hit=False)
            return None
        except Exception as e:
            logger.error("ai_cache_get_failed category=%s error=%s", category, e)
            return None

    async def set(self, category: str, identifier: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with metrics tracking."""
        start_time = time.time()
        
        if not self.redis_client:
            self.initialize()

        try:
            key = self._get_key(category, identifier)
            config = self.configs.get(category)
            ttl_seconds = ttl or (config.ttl_seconds if config else 300)
            
            serialized = json.dumps(value, default=str)
            self.redis_client.setex(key, ttl_seconds, serialized)
            
            latency_ms = (time.time() - start_time) * 1000
            logger.debug("ai_cache_set category=%s key=%s ttl=%s latency=%.2fms", category, identifier, ttl_seconds, latency_ms)
            
            return True
        except Exception as e:
            logger.error("ai_cache_set_failed category=%s error=%s", category, e)
            return False

    async def delete(self, category: str, identifier: str) -> bool:
        """Delete value from cache."""
        if not self.redis_client:
            self.initialize()

        try:
            key = self._get_key(category, identifier)
            self.redis_client.delete(key)
            logger.debug("ai_cache_delete category=%s key=%s", category, identifier)
            return True
        except Exception as e:
            logger.error("ai_cache_delete_failed category=%s error=%s", category, e)
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        if not self.redis_client:
            self.initialize()

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info("ai_cache_invalidated pattern=%s count=%s", pattern, len(keys))
                return len(keys)
            return 0
        except Exception as e:
            logger.error("ai_cache_invalidate_failed pattern=%s error=%s", pattern, e)
            return 0

    async def invalidate_category(self, category: str) -> int:
        """Invalidate all keys in a category."""
        config = self.configs.get(category)
        if not config:
            return 0
        pattern = f"{config.prefix}:*"
        return await self.invalidate_pattern(pattern)

    async def get_or_set(self, category: str, identifier: str, fetch_func, ttl: Optional[int] = None) -> Any:
        """Get from cache or fetch and cache."""
        start_time = time.time()
        
        cached = await self.get(category, identifier)
        if cached is not None:
            return cached

        value = await fetch_func() if asyncio.iscoroutinefunction(fetch_func) else fetch_func()
        await self.set(category, identifier, value, ttl)
        
        total_latency = (time.time() - start_time) * 1000
        logger.debug("ai_cache_fetch category=%s key=%s total_latency=%.2fms", category, identifier, total_latency)
        
        return value

    async def get_metrics(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get cache performance metrics."""
        if category:
            if category not in self.metrics:
                return {}
            metrics = self.metrics[category]
            hit_rate = (metrics.hits / metrics.total_requests * 100) if metrics.total_requests > 0 else 0
            return {
                'category': category,
                'hits': metrics.hits,
                'misses': metrics.misses,
                'total_requests': metrics.total_requests,
                'hit_rate': round(hit_rate, 2),
                'avg_latency_ms': round(metrics.avg_latency_ms, 2),
                'last_access': metrics.last_access.isoformat() if metrics.last_access else None,
            }
        
        # Return all categories
        all_metrics = {}
        for cat, metrics in self.metrics.items():
            hit_rate = (metrics.hits / metrics.total_requests * 100) if metrics.total_requests > 0 else 0
            all_metrics[cat] = {
                'hits': metrics.hits,
                'misses': metrics.misses,
                'total_requests': metrics.total_requests,
                'hit_rate': round(hit_rate, 2),
                'avg_latency_ms': round(metrics.avg_latency_ms, 2),
            }
        
        return all_metrics

    async def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall cache statistics."""
        total_hits = sum(m.hits for m in self.metrics.values())
        total_misses = sum(m.misses for m in self.metrics.values())
        total_requests = total_hits + total_misses
        overall_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
        
        avg_latency = sum(m.avg_latency_ms for m in self.metrics.values()) / len(self.metrics) if self.metrics else 0
        
        return {
            'total_hits': total_hits,
            'total_misses': total_misses,
            'total_requests': total_requests,
            'overall_hit_rate': round(overall_hit_rate, 2),
            'avg_latency_ms': round(avg_latency, 2),
            'categories': len(self.configs),
        }

    async def clear_category(self, category: str) -> bool:
        """Clear all cache in a category."""
        try:
            count = await self.invalidate_category(category)
            logger.info("ai_cache_cleared category=%s keys_removed=%s", category, count)
            return True
        except Exception as e:
            logger.error("ai_cache_clear_failed category=%s error=%s", category, e)
            return False

    async def clear_all(self) -> bool:
        """Clear all AI cache."""
        try:
            for category in self.configs:
                await self.invalidate_category(category)
            logger.warning("ai_cache_cleared_all_categories")
            return True
        except Exception as e:
            logger.error("ai_cache_clear_all_failed error=%s", e)
            return False


# Global instance
ai_cache_service = AIServicesRedisCache()


def get_ai_cache_service() -> AIServicesRedisCache:
    """Get AI cache service instance."""
    return ai_cache_service


# Decorator for caching AI service results
def cache_ai_result(category: str, ttl: Optional[int] = None):
    """Decorator to cache AI service function results."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            identifier = f"{func.__name__}:{':'.join(str(arg) for arg in args)}"
            
            result = await ai_cache_service.get_or_set(
                category=category,
                identifier=identifier,
                fetch_func=lambda: func(*args, **kwargs),
                ttl=ttl
            )
            return result
        return wrapper
    return decorator


# Cache invalidation helpers for AI services
async def invalidate_recommendations_cache(user_id: int):
    """Invalidate all recommendation caches for user."""
    await ai_cache_service.invalidate_pattern(f"ai:recs:*{user_id}*")
    await ai_cache_service.invalidate_pattern(f"ai:recs:ranked:*{user_id}*")


async def invalidate_eta_cache(order_id: int):
    """Invalidate ETA cache for order."""
    await ai_cache_service.invalidate_pattern(f"ai:eta:*{order_id}*")


async def invalidate_vendor_cache(vendor_id: int):
    """Invalidate all vendor-related caches."""
    await ai_cache_service.invalidate_pattern(f"ai:vendors:*{vendor_id}*")
    await ai_cache_service.invalidate_pattern(f"ai:speed:*{vendor_id}*")
    await ai_cache_service.invalidate_pattern(f"ai:trending:vendor:*{vendor_id}*")


async def invalidate_user_cache(user_id: int):
    """Invalidate all user-related caches."""
    await ai_cache_service.invalidate_pattern(f"ai:recs:*{user_id}*")
    await ai_cache_service.invalidate_pattern(f"ai:menu:*{user_id}*")
    await ai_cache_service.invalidate_pattern(f"ai:viewed:*{user_id}*")
    await ai_cache_service.invalidate_pattern(f"ai:prefs:*{user_id}*")
    await ai_cache_service.invalidate_pattern(f"ai:behavior:*{user_id}*")


async def invalidate_group_cache(group_id: int):
    """Invalidate all group-related caches."""
    await ai_cache_service.invalidate_pattern(f"ai:group:*{group_id}*")