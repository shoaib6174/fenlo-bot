"""Unit tests for usage tracker.

Spec: docs/plans/phase-1-engine.md (Section 1.13)
"""

from unittest.mock import AsyncMock, Mock

import pytest

from app.core.event_bus import InProcessEventBus
from app.services.usage_tracker import UsageTracker


@pytest.fixture
def event_bus():
    """Create event bus instance."""
    return InProcessEventBus()


@pytest.fixture
def tracker(event_bus):
    """Create UsageTracker instance."""
    return UsageTracker(event_bus=event_bus)


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


class TestUsageTracker:
    """Test usage tracking functionality."""

    async def test_tracks_llm_tokens(self, tracker, mock_db):
        """Test that LLM tokens are tracked."""
        await tracker.track_llm_usage(
            db=mock_db,
            workspace_id="ws-123",
            tokens_in=100,
            tokens_out=200,
            provider="groq",
        )

        # Verify DB was called
        assert mock_db.execute.called
        assert mock_db.commit.called

    async def test_atomic_increment_uses_on_conflict(self, tracker, mock_db):
        """Test that usage increment uses ON CONFLICT DO UPDATE."""
        await tracker.track_llm_usage(
            db=mock_db,
            workspace_id="ws-123",
            tokens_in=100,
            tokens_out=200,
            provider="groq",
        )

        # Check that query uses ON CONFLICT pattern
        call_args = str(mock_db.execute.call_args)
        assert "ON CONFLICT" in call_args

    def test_calculates_cost_groq(self, tracker):
        """Test cost calculation for Groq provider."""
        cost = tracker._estimate_cost(
            tokens_in=1_000_000,  # 1M tokens
            tokens_out=1_000_000,
            provider="groq",
        )

        # Groq: $0.05/1M input + $0.05/1M output = $0.10
        assert cost == pytest.approx(0.10, abs=0.001)

    def test_calculates_cost_openai(self, tracker):
        """Test cost calculation for OpenAI GPT-4o-mini."""
        cost = tracker._estimate_cost(
            tokens_in=1_000_000,  # 1M tokens
            tokens_out=1_000_000,
            provider="openai",
        )

        # OpenAI: $0.15/1M input + $0.60/1M output = $0.75
        assert cost == pytest.approx(0.75, abs=0.001)

    async def test_workspace_isolation(self, tracker, mock_db):
        """Test that usage is isolated per workspace."""
        await tracker.track_llm_usage(
            db=mock_db,
            workspace_id="ws-123",
            tokens_in=100,
            tokens_out=200,
            provider="groq",
        )

        await tracker.track_llm_usage(
            db=mock_db,
            workspace_id="ws-456",
            tokens_in=150,
            tokens_out=250,
            provider="groq",
        )

        # Verify two separate DB calls
        assert mock_db.execute.call_count == 2

    async def test_tracks_vector_query(self, tracker, mock_db):
        """Test tracking of vector/RAG queries."""
        await tracker.track_vector_query(
            db=mock_db,
            workspace_id="ws-123",
        )

        assert mock_db.execute.called
        assert mock_db.commit.called

    async def test_tracks_document_storage(self, tracker, mock_db):
        """Test tracking of document uploads."""
        await tracker.track_document_storage(
            db=mock_db,
            workspace_id="ws-123",
            bytes_added=1024 * 1024,  # 1MB
        )

        assert mock_db.execute.called
        assert mock_db.commit.called

    def test_cost_estimation_zero_tokens(self, tracker):
        """Test cost estimation with zero tokens."""
        cost = tracker._estimate_cost(
            tokens_in=0,
            tokens_out=0,
            provider="groq",
        )

        assert cost == 0.0

    async def test_get_current_usage(self, tracker, mock_db):
        """Test getting current usage for a workspace."""
        from datetime import date

        from app.models.workspace import WorkspaceUsage

        usage = WorkspaceUsage(
            workspace_id="ws-123",
            period=date.today().replace(day=1),
            llm_tokens_in=100,
            llm_tokens_out=200,
            vector_queries=5,
            documents_stored=3,
            storage_bytes=1024,
            api_calls=50,
            estimated_cost=0.15,
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=usage)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await tracker.get_current_usage(
            db=mock_db,
            workspace_id="ws-123",
        )

        assert result.llm_tokens_in == 100
        assert result.llm_tokens_out == 200
        assert result.api_calls == 50
