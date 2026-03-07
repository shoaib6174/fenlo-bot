"""Unit tests for token budget guard.

Spec: docs/plans/phase-1-engine.md (Section 1.14)
"""

from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.event_bus import InProcessEventBus
from app.core.token_budget import TokenBudgetGuard
from app.models.workspace import Workspace, WorkspaceUsage


@pytest.fixture
def event_bus():
    """Create event bus instance."""
    return InProcessEventBus()


@pytest.fixture
def token_guard(event_bus):
    """Create TokenBudgetGuard instance."""
    return TokenBudgetGuard(event_bus=event_bus)


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


class TestTokenBudget:
    """Test token budget guard functionality."""

    async def test_under_budget_allows(self, token_guard, mock_db):
        """Test that requests under budget are allowed."""
        # Mock _get_current_usage to return 500K usage
        current_period = date.today().replace(day=1)
        usage = WorkspaceUsage(
            workspace_id="ws-123",
            period=current_period,
            llm_tokens_in=250_000,
            llm_tokens_out=250_000,
            vector_queries=0,
            documents_stored=0,
            storage_bytes=0,
            api_calls=0,
            estimated_cost=0.0,
        )

        # Mock workspace with default budget
        workspace = Workspace(
            id="ws-123",
            name="Test Workspace",
            settings={"token_budget_monthly": 1_000_000},
        )

        # Mock database queries - first for usage, second for workspace
        mock_result_usage = Mock()
        mock_result_usage.scalar_one_or_none = Mock(return_value=usage)

        mock_result_workspace = Mock()
        mock_result_workspace.scalar_one_or_none = Mock(return_value=workspace)

        mock_db.execute = AsyncMock(side_effect=[mock_result_usage, mock_result_workspace])
        mock_db.flush = AsyncMock()

        allowed, message = await token_guard.check_budget(
            db=mock_db, workspace_id="ws-123", estimated_tokens=1000
        )

        assert allowed is True
        assert message is None

    async def test_over_budget_blocks(self, token_guard, mock_db):
        """Test that requests over budget are blocked."""
        # Mock usage at 1M tokens (budget exhausted)
        current_period = date.today().replace(day=1)
        usage = WorkspaceUsage(
            workspace_id="ws-123",
            period=current_period,
            llm_tokens_in=500_000,
            llm_tokens_out=500_000,  # Total 1M
            vector_queries=0,
            documents_stored=0,
            storage_bytes=0,
            api_calls=0,
            estimated_cost=0.0,
        )

        workspace = Workspace(
            id="ws-123",
            name="Test Workspace",
            settings={"token_budget_monthly": 1_000_000},
        )

        mock_result_usage = Mock()
        mock_result_usage.scalar_one_or_none = Mock(return_value=usage)
        mock_result_workspace = Mock()
        mock_result_workspace.scalar_one_or_none = Mock(return_value=workspace)

        mock_db.execute = AsyncMock(side_effect=[mock_result_usage, mock_result_workspace])
        mock_db.flush = AsyncMock()

        allowed, message = await token_guard.check_budget(
            db=mock_db, workspace_id="ws-123", estimated_tokens=1000
        )

        assert allowed is False
        assert message is not None
        assert "budget exhausted" in message.lower()

    async def test_emits_warning_at_80_percent(self, token_guard, mock_db, event_bus):
        """Test that warning event is emitted at 80%."""
        # Mock usage at 80% (800K of 1M)
        current_period = date.today().replace(day=1)
        usage = WorkspaceUsage(
            workspace_id="ws-123",
            period=current_period,
            llm_tokens_in=400_000,
            llm_tokens_out=400_000,
            vector_queries=0,
            documents_stored=0,
            storage_bytes=0,
            api_calls=0,
            estimated_cost=0.0,
        )

        workspace = Workspace(
            id="ws-123",
            name="Test Workspace",
            settings={"token_budget_monthly": 1_000_000},
        )

        mock_result_usage = Mock()
        mock_result_usage.scalar_one_or_none = Mock(return_value=usage)
        mock_result_workspace = Mock()
        mock_result_workspace.scalar_one_or_none = Mock(return_value=workspace)

        mock_db.execute = AsyncMock(side_effect=[mock_result_usage, mock_result_workspace])
        mock_db.flush = AsyncMock()

        # Subscribe to warning event
        warnings_received = []

        async def handler(event_type: str, data: dict):
            warnings_received.append(data)

        await event_bus.subscribe("token.budget_warning", handler)

        await token_guard.check_budget(db=mock_db, workspace_id="ws-123", estimated_tokens=1000)

        assert len(warnings_received) == 1
        assert warnings_received[0]["workspace_id"] == "ws-123"

    async def test_default_budget_1m_tokens(self, token_guard, mock_db):
        """Test that default budget is 1M tokens."""
        current_period = date.today().replace(day=1)
        usage = WorkspaceUsage(
            workspace_id="ws-123",
            period=current_period,
            llm_tokens_in=0,
            llm_tokens_out=0,
            vector_queries=0,
            documents_stored=0,
            storage_bytes=0,
            api_calls=0,
            estimated_cost=0.0,
        )

        # Workspace with no settings - should use default
        workspace = Workspace(
            id="ws-123",
            name="Test Workspace",
            settings=None,
        )

        mock_result_usage = Mock()
        mock_result_usage.scalar_one_or_none = Mock(return_value=usage)
        mock_result_workspace = Mock()
        mock_result_workspace.scalar_one_or_none = Mock(return_value=workspace)

        mock_db.execute = AsyncMock(side_effect=[mock_result_usage, mock_result_workspace])
        mock_db.flush = AsyncMock()

        # Budget check should use default 1M
        allowed, _ = await token_guard.check_budget(
            db=mock_db, workspace_id="ws-123", estimated_tokens=1000
        )

        assert allowed is True  # Well under 1M budget
