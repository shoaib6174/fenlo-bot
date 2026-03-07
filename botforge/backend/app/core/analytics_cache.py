"""
Analytics cache manager with circuit breaker and request coalescing.

Prevents thundering herd on Redis failures. Lock pool is bounded to
prevent memory leaks (Expert Panel P0 Fix).
"""

import asyncio
import json
import time
from collections.abc import Callable
from typing import Any

import structlog
from redis.exceptions import RedisError

from app.core.redis import get_redis_client

logger = structlog.get_logger(__name__)

# Default cache TTL: 1 hour
DEFAULT_TTL_SEC = 3600


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""


class AnalyticsCacheManager:
    """
    Redis cache manager with circuit breaker and request coalescing.

    Circuit breaker opens after ``failure_threshold`` consecutive Redis failures
    and recovers after ``recovery_timeout`` seconds.  Request coalescing prevents
    duplicate computations when many coroutines request the same key.
    """

    MAX_LOCKS = 500

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout

        # Circuit breaker state
        self._failure_count = 0
        self._circuit_open_since: float | None = None

        # Request coalescing
        self._in_flight: dict[str, asyncio.Lock] = {}
        self._waiters: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Circuit breaker helpers
    # ------------------------------------------------------------------

    def _is_circuit_open(self) -> bool:
        if self._circuit_open_since is None:
            return False
        elapsed = time.monotonic() - self._circuit_open_since
        if elapsed >= self._recovery_timeout:
            # Half-open: allow a probe
            logger.info("analytics_cache.circuit_half_open", elapsed_s=round(elapsed, 1))
            self._circuit_open_since = None
            self._failure_count = 0
            return False
        return True

    def _record_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= self._failure_threshold:
            self._circuit_open_since = time.monotonic()
            logger.warning(
                "analytics_cache.circuit_opened",
                failures=self._failure_count,
            )

    def _record_success(self) -> None:
        if self._failure_count > 0:
            self._failure_count = 0
            self._circuit_open_since = None

    # ------------------------------------------------------------------
    # Low-level Redis operations
    # ------------------------------------------------------------------

    async def _redis_get(self, key: str) -> str | None:
        if self._is_circuit_open():
            raise CircuitBreakerOpen()
        redis = get_redis_client()
        if redis is None:
            raise CircuitBreakerOpen()
        try:
            result = await redis.get(key)
            self._record_success()
            return result
        except RedisError as exc:
            self._record_failure()
            raise exc

    async def _redis_set(self, key: str, value: str, ttl: int) -> None:
        if self._is_circuit_open():
            return  # silently skip
        redis = get_redis_client()
        if redis is None:
            return
        try:
            await redis.set(key, value, ex=ttl)
            self._record_success()
        except RedisError:
            self._record_failure()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get(self, key: str) -> str | None:
        """Get cached value. Returns None on miss or circuit-open."""
        try:
            return await self._redis_get(key)
        except (CircuitBreakerOpen, RedisError):
            return None

    async def set(self, key: str, value: str, ttl: int = DEFAULT_TTL_SEC) -> None:
        """Set cached value. Silently degrades if Redis is down."""
        await self._redis_set(key, value, ttl)

    async def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        ttl: int = DEFAULT_TTL_SEC,
    ) -> Any:
        """
        Get from cache or compute with request coalescing.

        Multiple concurrent requests for the same key share a single computation.
        Lock cleanup uses reference counting to avoid race conditions.
        """
        # Try cache first
        cached = await self.get(key)
        if cached is not None:
            return json.loads(cached)

        # Request coalescing -----------------------------------------------
        if key not in self._in_flight:
            # Evict an unlocked entry if pool is full
            if len(self._in_flight) >= self.MAX_LOCKS:
                for k in list(self._in_flight):
                    if not self._in_flight[k].locked():
                        self._in_flight.pop(k, None)
                        self._waiters.pop(k, None)
                        break
            self._in_flight[key] = asyncio.Lock()
            self._waiters[key] = 0

        self._waiters[key] = self._waiters.get(key, 0) + 1
        lock = self._in_flight[key]

        try:
            async with lock:
                # Double-check cache after acquiring lock
                cached = await self.get(key)
                if cached is not None:
                    return json.loads(cached)

                # Compute value
                value = await compute_fn()

                # Cache the result (graceful degradation)
                await self.set(key, json.dumps(value, default=str), ttl)

                return value
        finally:
            self._waiters[key] -= 1
            if self._waiters[key] <= 0:
                self._in_flight.pop(key, None)
                self._waiters.pop(key, None)


# Singleton
_cache_manager: AnalyticsCacheManager | None = None


def get_analytics_cache() -> AnalyticsCacheManager:
    """Get singleton AnalyticsCacheManager."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = AnalyticsCacheManager()
    return _cache_manager
