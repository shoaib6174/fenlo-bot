"""Unit tests for AnalyticsService — aggregation logic."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.analytics_service import AnalyticsService


def _make_cache() -> MagicMock:
    """Create a mock cache manager that always calls compute_fn (bypasses Redis)."""
    cache = MagicMock()

    async def _passthrough(key, fn, ttl=3600):
        return await fn()

    cache.get_or_compute = AsyncMock(side_effect=_passthrough)
    return cache


def _make_row(**kwargs):
    """Create a mock SQLAlchemy row with attribute access."""
    row = MagicMock()
    for k, v in kwargs.items():
        setattr(row, k, v)
    return row


@pytest.mark.asyncio
class TestAnalyticsService:
    """Test analytics aggregation queries."""

    async def test_get_overview_returns_metrics(self):
        """Overview should return totals and sentiment distribution."""
        cache = _make_cache()
        svc = AnalyticsService(cache=cache)

        db = AsyncMock()
        # First call: conversation count
        db.scalar = AsyncMock(return_value=10)
        # Second call: message aggregation
        msg_row = _make_row(
            msg_count=50,
            avg_latency=450.0,
            avg_quality=0.78,
            positive=20,
            neutral=15,
            negative=5,
        )
        mock_result = MagicMock()
        mock_result.one.return_value = msg_row
        db.execute = AsyncMock(return_value=mock_result)

        result = await svc.get_overview(str(uuid4()), date(2026, 1, 1), date(2026, 1, 31), db)

        assert result["total_conversations"] == 10
        assert result["total_messages"] == 50
        assert result["avg_response_time_ms"] == 450.0
        assert result["sentiment_distribution"]["positive"] == 20

    async def test_get_volume_returns_time_series(self):
        """Volume should return list of dated counts."""
        cache = _make_cache()
        svc = AnalyticsService(cache=cache)

        db = AsyncMock()
        rows = [
            _make_row(
                period=datetime(2026, 1, 1, tzinfo=UTC),
                message_count=10,
                conversation_count=3,
            ),
            _make_row(
                period=datetime(2026, 1, 2, tzinfo=UTC),
                message_count=15,
                conversation_count=5,
            ),
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        db.execute = AsyncMock(return_value=mock_result)

        result = await svc.get_volume(str(uuid4()), date(2026, 1, 1), date(2026, 1, 2), "day", db)

        assert len(result) == 2
        assert result[0]["message_count"] == 10
        assert result[1]["conversation_count"] == 5

    async def test_get_channels_returns_breakdown(self):
        """Channels should return per-channel count and quality."""
        cache = _make_cache()
        svc = AnalyticsService(cache=cache)

        db = AsyncMock()
        # First execute: channel counts
        count_rows = [
            _make_row(channel="web", count=20),
            _make_row(channel="whatsapp", count=5),
        ]
        # Second execute: quality per channel
        quality_rows = [
            _make_row(channel="web", avg_quality=0.75),
            _make_row(channel="whatsapp", avg_quality=0.82),
        ]
        mock_result_1 = MagicMock()
        mock_result_1.all.return_value = count_rows
        mock_result_2 = MagicMock()
        mock_result_2.all.return_value = quality_rows
        db.execute = AsyncMock(side_effect=[mock_result_1, mock_result_2])

        result = await svc.get_channels(str(uuid4()), db)

        assert result["web"]["count"] == 20
        assert result["whatsapp"]["avg_quality"] == 0.82

    async def test_get_lead_scores_returns_buckets(self):
        """Lead scores should return 3 buckets."""
        cache = _make_cache()
        svc = AnalyticsService(cache=cache)

        db = AsyncMock()
        row = _make_row(low=10, medium=5, high=3)
        mock_result = MagicMock()
        mock_result.one.return_value = row
        db.execute = AsyncMock(return_value=mock_result)

        result = await svc.get_lead_scores(str(uuid4()), db)

        assert result["buckets"]["0-3"] == 10
        assert result["buckets"]["4-6"] == 5
        assert result["buckets"]["7-10"] == 3

    async def test_get_sentiment_returns_time_series(self):
        """Sentiment should return dated positive/neutral/negative counts."""
        cache = _make_cache()
        svc = AnalyticsService(cache=cache)

        db = AsyncMock()
        rows = [
            _make_row(
                period=datetime(2026, 1, 1, tzinfo=UTC),
                positive=10,
                neutral=8,
                negative=2,
            ),
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        db.execute = AsyncMock(return_value=mock_result)

        result = await svc.get_sentiment(
            str(uuid4()), date(2026, 1, 1), date(2026, 1, 1), "day", db
        )

        assert len(result) == 1
        assert result[0]["positive"] == 10
        assert result[0]["negative"] == 2
