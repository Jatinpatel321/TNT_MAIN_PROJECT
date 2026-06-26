"""Redis Cache Service - Comprehensive caching for dashboard, analytics, sessions, and notifications."""

from __future__ import annotations

import json
import asyncio
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger("tnt.redis_cache")


@dataclass
class CacheConfig:
    """Cache configuration with TTL."""
    ttl_seconds: int
    prefix: str
    enabled: bool = True


class RedisCacheService:
    """Comprehensive Redis caching service."""

    def __init__(self):
        self.redis_client = None
        self.configs: Dict[str, CacheConfig] = {
            'dashboard': CacheConfig(ttl_seconds=300, prefix='cache:dashboard'),  # 5 min
            'analytics': CacheConfig(ttl_seconds=600, prefix='cache:analytics'),  # 10 min
            'session': CacheConfig(ttl_seconds=3600, prefix='cache:session'),  # 1 hour
            'notification_queue': CacheConfig(ttl_seconds=86400, prefix='queue:notifications'),  # 24 hours
            'menu': CacheConfig(ttl_seconds=1800, prefix='cache:menu'),  # 30 min
            'orders': CacheConfig(ttl_seconds=120, prefix='cache:orders'),  # 2 min
        }

    def initialize(self):
        """Initialize Redis connection."""
        try:
            from app.core.redis import redis_client
            self.redis_client = redis_client
            logger.info("redis_cache_service_initialized")
        except Exception as e:
            logger.error("redis_cache_init_failed error=%s", e)
            raise

    def _get_key(self, category: str, identifier: str) -> str:
        """Generate cache key."""
        config = self.configs.get(category)
        if not config:
            raise ValueError(f"Unknown cache category: {category}")
        return f"{config.prefix}:{identifier}"

    async def get(self, category: str, identifier: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.redis_client:
            self.initialize()

        try:
            key = self._get_key(category, identifier)
            value = self.redis_client.get(key)
            if value:
                logger.debug("cache_hit category=%s key=%s", category, identifier)
                return json.loads(value)
            logger.debug("cache_miss category=%s key=%s", category, identifier)
            return None
        except Exception as e:
            logger.error("cache_get_failed category=%s error=%s", category, e)
            return None

    async def set(self, category: str, identifier: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        if not self.redis_client:
            self.initialize()

        try:
            key = self._get_key(category, identifier)
            config = self.configs.get(category)
            ttl_seconds = ttl or (config.ttl_seconds if config else 300)
            
            serialized = json.dumps(value, default=str)
            self.redis_client.setex(key, ttl_seconds, serialized)
            logger.debug("cache_set category=%s key=%s ttl=%s", category, identifier, ttl_seconds)
            return True
        except Exception as e:
            logger.error("cache_set_failed category=%s error=%s", category, e)
            return False

    async def delete(self, category: str, identifier: str) -> bool:
        """Delete value from cache."""
        if not self.redis_client:
            self.initialize()

        try:
            key = self._get_key(category, identifier)
            self.redis_client.delete(key)
            logger.debug("cache_delete category=%s key=%s", category, identifier)
            return True
        except Exception as e:
            logger.error("cache_delete_failed category=%s error=%s", category, e)
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        if not self.redis_client:
            self.initialize()

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info("cache_invalidated pattern=%s count=%s", pattern, len(keys))
                return len(keys)
            return 0
        except Exception as e:
            logger.error("cache_invalidate_failed pattern=%s error=%s", pattern, e)
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
        cached = await self.get(category, identifier)
        if cached is not None:
            return cached

        value = await fetch_func() if asyncio.iscoroutinefunction(fetch_func) else fetch_func()
        await self.set(category, identifier, value, ttl)
        return value

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.redis_client:
            self.initialize()

        try:
            info = self.redis_client.info()
            return {
                'redis_version': info.get('redis_version'),
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(info),
            }
        except Exception as e:
            logger.error("cache_stats_failed error=%s", e)
            return {}

    def _calculate_hit_rate(self, info: Dict) -> float:
        """Calculate cache hit rate."""
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)

    async def clear_all(self) -> bool:
        """Clear all cache (use with caution)."""
        if not self.redis_client:
            self.initialize()

        try:
            for category in self.configs:
                await self.invalidate_category(category)
            logger.warning("cache_cleared_all_categories")
            return True
        except Exception as e:
            logger.error("cache_clear_failed error=%s", e)
            return False


# Global instance
cache_service = RedisCacheService()


def get_cache_service() -> RedisCacheService:
    """Get cache service instance."""
    return cache_service


# Decorator for caching
def cache_result(category: str, ttl: Optional[int] = None):
    """Decorator to cache function results."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            identifier = f"{func.__name__}:{':'.join(str(arg) for arg in args)}"
            
            result = await cache_service.get_or_set(
                category=category,
                identifier=identifier,
                fetch_func=lambda: func(*args, **kwargs),
                ttl=ttl
            )
            return result
        return wrapper
    return decorator


# Cache invalidation helpers
async def invalidate_dashboard_cache(vendor_id: int):
    """Invalidate dashboard cache for vendor."""
    await cache_service.invalidate_pattern(f"cache:dashboard:{vendor_id}:*")


async def invalidate_analytics_cache(vendor_id: int):
    """Invalidate analytics cache for vendor."""
    await cache_service.invalidate_pattern(f"cache:analytics:{vendor_id}:*")


async def invalidate_session_cache(user_id: int):
    """Invalidate session cache for user."""
    await cache_service.invalidate_pattern(f"cache:session:{user_id}:*")


async def invalidate_menu_cache(vendor_id: int):
    """Invalidate menu cache for vendor."""
    await cache_service.invalidate_pattern(f"cache:menu:{vendor_id}:*")


async def invalidate_orders_cache(vendor_id: int):
    """Invalidate orders cache for vendor."""
    await cache_service.invalidate_pattern(f"cache:orders:{vendor_id}:*")