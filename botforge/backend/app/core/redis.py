"""
Redis wrapper with graceful degradation fallback.
Spec: docs/plans/phase-0-scaffold.md (Section 0a.4b)

Redis is used for 6 critical functions:
- Rate limiting
- Session cache
- Semantic cache
- Event bus
- ARQ job queue
- WebSocket pub/sub

When Redis is down, each function falls back appropriately.
"""

import time
from typing import Any

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings

logger = structlog.get_logger()

# Singleton Redis client
_redis_client: Redis | None = None


def get_redis_client() -> Redis | None:
    """
    Get singleton Redis client.
    Returns None if Redis is not configured or connection failed.
    """
    global _redis_client
    if _redis_client is None:
        if not settings.redis_url:
            logger.warning("redis.not_configured")
            return None
        try:
            _redis_client = Redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        except Exception as e:
            logger.error("redis.connection_failed", error=str(e))
            return None
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection on shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("redis.closed")


class InMemoryFallback:
    """
    In-memory fallback for Redis operations.
    Used when Redis is unavailable.
    """

    def __init__(self):
        self._store: dict[str, tuple[Any, float | None]] = {}
        self._counters: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        """Get value from in-memory store."""
        if key not in self._store:
            return None
        value, expiry = self._store[key]
        if expiry and time.time() > expiry:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        """Set value in in-memory store with optional expiry."""
        expiry = time.time() + ex if ex else None
        self._store[key] = (value, expiry)
        return True

    async def delete(self, key: str) -> int:
        """Delete key from in-memory store."""
        if key in self._store:
            del self._store[key]
            return 1
        return 0

    async def incr(self, key: str) -> int:
        """Increment counter in memory."""
        self._counters[key] = self._counters.get(key, 0) + 1
        return self._counters[key]

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiry on existing key."""
        if key in self._store:
            value, _ = self._store[key]
            self._store[key] = (value, time.time() + seconds)
            return True
        return False


class ResilientRedis:
    """
    Redis wrapper with automatic fallback on connection failure.

    When Redis is unavailable:
    - Rate limiting → in-memory per-process counter
    - Session cache → DB query (slower but works)
    - Semantic cache → cache miss, queries hit LLM
    - ARQ queue → in-memory queue (risk: lost on crash)
    - WebSocket pub/sub → in-process only
    - Event bus → in-process event bus
    """

    def __init__(self):
        self.redis: Redis | None = None
        self.fallback = InMemoryFallback()
        self.degraded = False
        self._last_degraded_log = 0

    def _get_redis(self) -> Redis | None:
        """Lazy-load Redis client."""
        if self.redis is None:
            self.redis = get_redis_client()
        return self.redis

    def _log_degraded_mode(self, reason: str) -> None:
        """Log degraded mode transition (rate-limited to once per minute)."""
        now = time.time()
        if not self.degraded:
            logger.warning("redis.degraded_mode", reason=reason)
            self.degraded = True
            self._last_degraded_log = now
        elif now - self._last_degraded_log > 300:  # Every 5 minutes
            logger.warning("redis.still_degraded", duration_s=int(now - self._last_degraded_log))
            self._last_degraded_log = now

    def _log_recovered(self) -> None:
        """Log recovery from degraded mode."""
        if self.degraded:
            logger.info("redis.recovered")
            self.degraded = False

    async def get(self, key: str) -> str | None:
        """Get value with fallback to in-memory."""
        redis = self._get_redis()
        if redis is None:
            return await self.fallback.get(key)

        try:
            result = await redis.get(key)
            self._log_recovered()
            return result
        except RedisError as e:
            self._log_degraded_mode(f"get_failed: {e}")
            return await self.fallback.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        """Set value with fallback to in-memory."""
        redis = self._get_redis()
        if redis is None:
            return await self.fallback.set(key, value, ex)

        try:
            await redis.set(key, value, ex=ex)
            self._log_recovered()
            return True
        except RedisError as e:
            self._log_degraded_mode(f"set_failed: {e}")
            return await self.fallback.set(key, value, ex)

    async def delete(self, key: str) -> int:
        """Delete key with fallback to in-memory."""
        redis = self._get_redis()
        if redis is None:
            return await self.fallback.delete(key)

        try:
            result = await redis.delete(key)
            self._log_recovered()
            return result
        except RedisError as e:
            self._log_degraded_mode(f"delete_failed: {e}")
            return await self.fallback.delete(key)

    async def incr(self, key: str) -> int:
        """Increment counter with fallback to in-memory."""
        redis = self._get_redis()
        if redis is None:
            return await self.fallback.incr(key)

        try:
            result = await redis.incr(key)
            self._log_recovered()
            return result
        except RedisError as e:
            self._log_degraded_mode(f"incr_failed: {e}")
            return await self.fallback.incr(key)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiry with fallback to in-memory."""
        redis = self._get_redis()
        if redis is None:
            return await self.fallback.expire(key, seconds)

        try:
            result = await redis.expire(key, seconds)
            self._log_recovered()
            return bool(result)
        except RedisError as e:
            self._log_degraded_mode(f"expire_failed: {e}")
            return await self.fallback.expire(key, seconds)

    async def ping(self) -> bool:
        """Check if Redis is available."""
        redis = self._get_redis()
        if redis is None:
            return False

        try:
            await redis.ping()
            self._log_recovered()
            return True
        except RedisError:
            self._log_degraded_mode("ping_failed")
            return False


# Singleton instance
_resilient_redis: ResilientRedis | None = None


def get_resilient_redis() -> ResilientRedis:
    """Get singleton ResilientRedis instance."""
    global _resilient_redis
    if _resilient_redis is None:
        _resilient_redis = ResilientRedis()
    return _resilient_redis
