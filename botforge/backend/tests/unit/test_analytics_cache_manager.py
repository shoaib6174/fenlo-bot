"""Unit tests for AnalyticsCacheManager — circuit breaker and request coalescing."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.core.analytics_cache import AnalyticsCacheManager


@pytest.mark.asyncio
class TestAnalyticsCacheManager:
    """Test circuit breaker, cache operations, and request coalescing."""

    async def test_cache_hit_returns_cached_data(self):
        """Cache hit should return deserialized data without calling compute."""
        mgr = AnalyticsCacheManager()
        cached = json.dumps({"count": 42})

        with patch("app.core.analytics_cache.get_redis_client") as mock_redis:
            client = AsyncMock()
            client.get = AsyncMock(return_value=cached)
            mock_redis.return_value = client

            compute_fn = AsyncMock(return_value={"count": 999})
            result = await mgr.get_or_compute("test:key", compute_fn)

        assert result == {"count": 42}
        compute_fn.assert_not_awaited()

    async def test_cache_miss_triggers_computation(self):
        """Cache miss should call compute_fn and cache the result."""
        mgr = AnalyticsCacheManager()

        with patch("app.core.analytics_cache.get_redis_client") as mock_redis:
            client = AsyncMock()
            client.get = AsyncMock(return_value=None)
            client.set = AsyncMock()
            mock_redis.return_value = client

            compute_fn = AsyncMock(return_value={"count": 42})
            result = await mgr.get_or_compute("test:key", compute_fn)

        assert result == {"count": 42}
        compute_fn.assert_awaited_once()
        client.set.assert_awaited_once()

    async def test_circuit_breaker_opens_after_threshold(self):
        """After 5 consecutive failures, circuit should open."""
        mgr = AnalyticsCacheManager(failure_threshold=3, recovery_timeout=60.0)

        with patch("app.core.analytics_cache.get_redis_client") as mock_redis:
            client = AsyncMock()
            from redis.exceptions import RedisError

            client.get = AsyncMock(side_effect=RedisError("connection lost"))
            mock_redis.return_value = client

            # Trigger failures to open the circuit
            for _ in range(3):
                result = await mgr.get("some:key")
                assert result is None

        assert mgr._is_circuit_open()

    async def test_circuit_breaker_recovers_after_timeout(self):
        """Circuit should recover (half-open) after recovery timeout."""
        mgr = AnalyticsCacheManager(failure_threshold=2, recovery_timeout=0.1)

        with patch("app.core.analytics_cache.get_redis_client") as mock_redis:
            client = AsyncMock()
            from redis.exceptions import RedisError

            client.get = AsyncMock(side_effect=RedisError("down"))
            mock_redis.return_value = client

            # Open the circuit
            for _ in range(2):
                await mgr.get("key")

            assert mgr._is_circuit_open()

            # Wait for recovery
            await asyncio.sleep(0.15)
            assert not mgr._is_circuit_open()

    async def test_request_coalescing_prevents_duplicate_queries(self):
        """Concurrent requests for the same key should share one computation."""
        mgr = AnalyticsCacheManager()
        call_count = 0

        async def slow_compute():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            return {"value": call_count}

        # Use a dict to simulate Redis storage — after set(), get() returns the value
        store: dict[str, str] = {}

        async def mock_get(key):
            return store.get(key)

        async def mock_set(key, value, ex=None):
            store[key] = value

        with patch("app.core.analytics_cache.get_redis_client") as mock_redis:
            client = AsyncMock()
            client.get = AsyncMock(side_effect=mock_get)
            client.set = AsyncMock(side_effect=mock_set)
            mock_redis.return_value = client

            # Launch 5 concurrent requests for same key
            results = await asyncio.gather(
                *[mgr.get_or_compute("coalesce:key", slow_compute) for _ in range(5)]
            )

        # Only 1 computation should have happened (coalescing)
        assert call_count == 1
        # All results should be the same
        assert all(r == {"value": 1} for r in results)

    async def test_lock_pool_bounded(self):
        """Lock pool should not grow beyond MAX_LOCKS."""
        mgr = AnalyticsCacheManager()
        mgr.MAX_LOCKS = 5

        with patch("app.core.analytics_cache.get_redis_client") as mock_redis:
            client = AsyncMock()
            client.get = AsyncMock(return_value=None)
            client.set = AsyncMock()
            mock_redis.return_value = client

            # Create entries for more keys than MAX_LOCKS
            for i in range(10):
                await mgr.get_or_compute(f"key:{i}", AsyncMock(return_value={"i": i}))

        # After all computations, locks should be cleaned up
        assert len(mgr._in_flight) <= mgr.MAX_LOCKS

    async def test_fallback_to_compute_when_redis_unavailable(self):
        """When Redis is None, should fall through to compute_fn."""
        mgr = AnalyticsCacheManager()

        with patch("app.core.analytics_cache.get_redis_client", return_value=None):
            compute_fn = AsyncMock(return_value={"fallback": True})
            result = await mgr.get_or_compute("key", compute_fn)

        assert result == {"fallback": True}
        compute_fn.assert_awaited_once()

    async def test_set_silently_degrades_on_circuit_open(self):
        """Set should not raise when circuit is open."""
        mgr = AnalyticsCacheManager(failure_threshold=1, recovery_timeout=60.0)

        with patch("app.core.analytics_cache.get_redis_client") as mock_redis:
            client = AsyncMock()
            from redis.exceptions import RedisError

            client.get = AsyncMock(side_effect=RedisError("down"))
            mock_redis.return_value = client

            # Open circuit
            await mgr.get("key")
            assert mgr._is_circuit_open()

            # Set should silently degrade
            await mgr.set("key", "value", ttl=60)  # No exception
