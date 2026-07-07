import logging
import os

import fakeredis
import redis
from redis.exceptions import ConnectionError as RedisConnectionError, ResponseError as RedisResponseError

logger = logging.getLogger("tnt.redis")


def _build_real_client() -> redis.Redis:
    """Construct a Redis client from ENV configuration."""
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return redis.Redis.from_url(redis_url, decode_responses=True)

    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    return redis.Redis(host=host, port=port, db=db, decode_responses=True)


def _init_client():
    force_fake = os.getenv("USE_FAKE_REDIS", "").strip().lower() in {"1", "true", "yes"}
    if force_fake:
        logger.warning("redis_fallback event=force_fake_env")
        return fakeredis.FakeRedis(decode_responses=True)

    client = _build_real_client()
    try:
        client.ping()
        conn_info = client.connection_pool.connection_kwargs
        logger.info(
            "redis_connected host=%s port=%s db=%s",
            conn_info.get("host"),
            conn_info.get("port"),
            conn_info.get("db"),
        )
        return client
    except (RedisConnectionError, OSError, RedisResponseError) as exc:
        logger.warning(
            "redis_unreachable event=fallback_to_fakeredis error=%s",
            exc,
        )
        return fakeredis.FakeRedis(decode_responses=True)


redis_client = _init_client()
