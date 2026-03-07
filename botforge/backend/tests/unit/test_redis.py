"""Unit tests for ResilientRedis and InMemoryFallback.

Tests graceful degradation: normal ops, fallback on Redis failure,
degraded mode transitions, recovery detection, in-memory fallback.
"""

import time
from unittest.mock import AsyncMock, patch

import pytest
from redis.exceptions import RedisError

from app.core.redis import InMemoryFallback, ResilientRedis


@pytest.mark.asyncio
class TestInMemoryFallback:
    """Test the in-memory fallback store."""

    async def test_get_missing_key_returns_none(self):
        fb = InMemoryFallback()
        assert await fb.get("nonexistent") is None

    async def test_set_and_get(self):
        fb = InMemoryFallback()
        await fb.set("key1", "value1")
        assert await fb.get("key1") == "value1"

    async def test_set_with_expiry_returns_value_before_expiry(self):
        fb = InMemoryFallback()
        await fb.set("key1", "value1", ex=3600)
        assert await fb.get("key1") == "value1"

    async def test_set_with_expiry_returns_none_after_expiry(self):
        fb = InMemoryFallback()
        # Set with 0 second expiry (already expired)
        fb._store["expired_key"] = ("value", time.time() - 1)
        assert await fb.get("expired_key") is None

    async def test_delete_existing_key(self):
        fb = InMemoryFallback()
        await fb.set("key1", "value1")
        result = await fb.delete("key1")
        assert result == 1
        assert await fb.get("key1") is None

    async def test_delete_missing_key(self):
        fb = InMemoryFallback()
        result = await fb.delete("nonexistent")
        assert result == 0

    async def test_incr_new_key(self):
        fb = InMemoryFallback()
        result = await fb.incr("counter")
        assert result == 1

    async def test_incr_existing_key(self):
        fb = InMemoryFallback()
        await fb.incr("counter")
        await fb.incr("counter")
        result = await fb.incr("counter")
        assert result == 3

    async def test_expire_existing_key(self):
        fb = InMemoryFallback()
        await fb.set("key1", "value1")
        result = await fb.expire("key1", 3600)
        assert result is True

    async def test_expire_missing_key(self):
        fb = InMemoryFallback()
        result = await fb.expire("nonexistent", 3600)
        assert result is False


@pytest.mark.asyncio
class TestResilientRedis:
    """Test ResilientRedis wrapper with fallback behavior."""

    def _make_resilient_redis(self, redis_mock=None):
        """Create a ResilientRedis with an optional mock Redis client.

        When redis_mock is None, we patch _get_redis to return None
        so it doesn't try to connect to real Redis.
        """
        rr = ResilientRedis()
        if redis_mock is not None:
            rr.redis = redis_mock
            # Also patch _get_redis to return the mock directly
            rr._get_redis = lambda: redis_mock
        else:
            # Patch _get_redis to return None (no Redis available)
            rr._get_redis = lambda: None
        return rr

    # --- No Redis available (None) -> fallback ---

    async def test_get_without_redis_uses_fallback(self):
        rr = self._make_resilient_redis(redis_mock=None)
        await rr.fallback.set("key", "fallback_value")
        result = await rr.get("key")
        assert result == "fallback_value"

    async def test_set_without_redis_uses_fallback(self):
        rr = self._make_resilient_redis(redis_mock=None)
        result = await rr.set("key", "value")
        assert result is True
        assert await rr.fallback.get("key") == "value"

    async def test_delete_without_redis_uses_fallback(self):
        rr = self._make_resilient_redis(redis_mock=None)
        await rr.fallback.set("key", "value")
        result = await rr.delete("key")
        assert result == 1

    async def test_incr_without_redis_uses_fallback(self):
        rr = self._make_resilient_redis(redis_mock=None)
        result = await rr.incr("counter")
        assert result == 1

    async def test_expire_without_redis_uses_fallback(self):
        rr = self._make_resilient_redis(redis_mock=None)
        await rr.fallback.set("key", "val")
        result = await rr.expire("key", 60)
        assert result is True

    async def test_ping_without_redis_returns_false(self):
        rr = self._make_resilient_redis(redis_mock=None)
        assert await rr.ping() is False

    # --- Redis available and working ---

    async def test_get_with_working_redis(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="redis_value")
        rr = self._make_resilient_redis(redis_mock=mock_redis)
        result = await rr.get("key")
        assert result == "redis_value"
        mock_redis.get.assert_awaited_once_with("key")

    async def test_set_with_working_redis(self):
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        rr = self._make_resilient_redis(redis_mock=mock_redis)
        result = await rr.set("key", "value", ex=60)
        assert result is True
        mock_redis.set.assert_awaited_once_with("key", "value", ex=60)

    async def test_delete_with_working_redis(self):
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=1)
        rr = self._make_resilient_redis(redis_mock=mock_redis)
        result = await rr.delete("key")
        assert result == 1

    async def test_incr_with_working_redis(self):
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=5)
        rr = self._make_resilient_redis(redis_mock=mock_redis)
        result = await rr.incr("counter")
        assert result == 5

    async def test_expire_with_working_redis(self):
        mock_redis = AsyncMock()
        mock_redis.expire = AsyncMock(return_value=True)
        rr = self._make_resilient_redis(redis_mock=mock_redis)
        result = await rr.expire("key", 60)
        assert result is True

    async def test_ping_with_working_redis(self):
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        rr = self._make_resilient_redis(redis_mock=mock_redis)
        assert await rr.ping() is True

    # --- Redis errors -> fallback ---

    async def test_get_falls_back_on_redis_error(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=RedisError("connection refused"))
        rr = self._make_resilient_redis(redis_mock=mock_redis)
        await rr.fallback.set("key", "fallback_value")
        result = await rr.get("key")
        assert result == "fallback_value"

    async def test_set_falls_back_on_redis_error(self):
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(side_effect=RedisError("connection refused"))
        rr = self._make_resilient_redis(redis_mock=mock_redis)
        result = await rr.set("key", "value")
        assert result is True
        assert await rr.fallback.get("key") == "value"

    async def test_delete_falls_back_on_redis_error(self):
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(side_effect=RedisError("connection refused"))
        rr = self._make_resilient_redis(redis_mock=mock_redis)
        await rr.fallback.set("key", "value")
        result = await rr.delete("key")
        assert result == 1

    async def test_incr_falls_back_on_redis_error(self):
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=RedisError("connection refused"))
        rr = self._make_resilient_redis(redis_mock=mock_redis)
        result = await rr.incr("counter")
        assert result == 1

    async def test_expire_falls_back_on_redis_error(self):
        mock_redis = AsyncMock()
        mock_redis.expire = AsyncMock(side_effect=RedisError("connection refused"))
        rr = self._make_resilient_redis(redis_mock=mock_redis)
        await rr.fallback.set("key", "val")
        result = await rr.expire("key", 60)
        assert result is True

    async def test_ping_returns_false_on_redis_error(self):
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=RedisError("connection refused"))
        rr = self._make_resilient_redis(redis_mock=mock_redis)
        assert await rr.ping() is False

    # --- Degraded mode transitions ---

    async def test_enters_degraded_mode_on_error(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=RedisError("fail"))
        rr = self._make_resilient_redis(redis_mock=mock_redis)
        assert rr.degraded is False
        await rr.get("key")
        assert rr.degraded is True

    async def test_recovers_from_degraded_mode_on_success(self):
        mock_redis = AsyncMock()
        # First call fails, second succeeds
        mock_redis.get = AsyncMock(side_effect=[RedisError("fail"), "value"])
        rr = self._make_resilient_redis(redis_mock=mock_redis)

        await rr.get("key")  # fails -> degraded
        assert rr.degraded is True

        await rr.get("key")  # succeeds -> recovered
        assert rr.degraded is False

    async def test_degraded_mode_log_rate_limiting(self):
        """Degraded log only emits once until 5-min window passes."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=RedisError("fail"))
        rr = self._make_resilient_redis(redis_mock=mock_redis)

        await rr.get("key1")  # first failure -> logs degraded
        assert rr.degraded is True
        first_log_time = rr._last_degraded_log

        await rr.get("key2")  # second failure -> no new log
        assert rr._last_degraded_log == first_log_time


@pytest.mark.asyncio
class TestRedisSingletons:
    """Test module-level singleton functions."""

    async def test_get_resilient_redis_returns_instance(self):
        from app.core.redis import get_resilient_redis

        rr = get_resilient_redis()
        assert isinstance(rr, ResilientRedis)

    async def test_get_resilient_redis_returns_same_instance(self):
        from app.core.redis import get_resilient_redis

        rr1 = get_resilient_redis()
        rr2 = get_resilient_redis()
        assert rr1 is rr2

    async def test_get_redis_client_returns_none_when_no_url(self):
        from app.core.redis import get_redis_client

        with patch("app.core.redis.settings") as mock_settings:
            mock_settings.redis_url = ""
            # Reset singleton
            import app.core.redis as redis_module

            redis_module._redis_client = None
            result = get_redis_client()
            assert result is None

    async def test_close_redis_when_not_connected(self):
        """close_redis should not fail when no connection exists."""
        import app.core.redis as redis_module
        from app.core.redis import close_redis

        old = redis_module._redis_client
        redis_module._redis_client = None
        await close_redis()  # should not raise
        redis_module._redis_client = old
