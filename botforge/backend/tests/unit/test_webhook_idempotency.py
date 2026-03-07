"""Unit tests for webhook idempotency (Redis SET NX dedup)."""

import hashlib
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.voice.idempotency import check_idempotency


@pytest.mark.asyncio
class TestWebhookIdempotency:
    """Test webhook deduplication behavior."""

    async def test_first_event_returns_false(self):
        """New event returns False (not a duplicate — process it)."""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)  # SET NX succeeded — new key

        with patch("app.modules.voice.idempotency.get_redis_client", return_value=mock_redis):
            result = await check_idempotency("status-update", "call-123", "2026-01-01T00:00:00Z")

        assert result is False
        mock_redis.set.assert_called_once()

    async def test_duplicate_event_returns_true(self):
        """Duplicate event returns True (already processed — skip it)."""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=None)  # SET NX failed — key exists

        with patch("app.modules.voice.idempotency.get_redis_client", return_value=mock_redis):
            result = await check_idempotency("status-update", "call-123", "2026-01-01T00:00:00Z")

        assert result is True

    async def test_different_events_not_deduped(self):
        """Different event types produce different idempotency keys."""
        call_log = []
        mock_redis = AsyncMock()

        async def track_set(key, value, ex=None, nx=None):
            call_log.append(key)
            return True

        mock_redis.set = track_set

        with patch("app.modules.voice.idempotency.get_redis_client", return_value=mock_redis):
            await check_idempotency("status-update", "call-123", "ts1")
            await check_idempotency("end-of-call-report", "call-123", "ts1")

        assert len(call_log) == 2
        assert call_log[0] != call_log[1]

    async def test_idempotency_key_generation(self):
        """Key is SHA-256 hash of event_type:event_id:timestamp."""
        expected_hash = hashlib.sha256(b"status-update:call-999:ts-abc").hexdigest()
        expected_key = f"voice:idem:{expected_hash}"

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)

        with patch("app.modules.voice.idempotency.get_redis_client", return_value=mock_redis):
            await check_idempotency("status-update", "call-999", "ts-abc")

        mock_redis.set.assert_called_once_with(expected_key, "1", ex=86400, nx=True)

    async def test_redis_failure_allows_processing(self):
        """Redis error returns False (graceful degradation — allow processing)."""
        from redis.exceptions import RedisError

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(side_effect=RedisError("connection lost"))

        with patch("app.modules.voice.idempotency.get_redis_client", return_value=mock_redis):
            result = await check_idempotency("status-update", "call-123", "ts1")

        assert result is False
