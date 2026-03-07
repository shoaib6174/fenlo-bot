"""Tests for handoff auto-resolve ARQ job."""

import sys
from datetime import UTC, datetime, timedelta
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Pre-mock twilio to avoid ImportError
if "twilio" not in sys.modules:
    sys.modules["twilio"] = ModuleType("twilio")
    sys.modules["twilio.rest"] = ModuleType("twilio.rest")
    sys.modules["twilio.rest"].Client = MagicMock()

from app.modules.handoff.provider import HandoffResult

# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def mock_ctx():
    return {
        "database_url": "postgresql+asyncpg://test:test@localhost:5433/test",  # pragma: allowlist secret
        "redis": AsyncMock(),
    }


def _make_conversation(conv_id=None, auto_resolve_at=None, status="escalated"):
    """Create a mock conversation."""
    conv = MagicMock()
    conv.id = conv_id or uuid4()
    conv.workspace_id = uuid4()
    conv.status = status
    conv.metadata_ = {}
    if auto_resolve_at:
        conv.metadata_["auto_resolve_at"] = auto_resolve_at
    return conv


# ── Tests ───────────────────────────────────────────────────────────


class TestCheckHandoffTimeouts:
    """Test check_handoff_timeouts ARQ job (7.29-7.32)."""

    @pytest.mark.asyncio
    async def test_resolves_expired_conversations(self, mock_ctx):
        """Conversations past auto_resolve_at are auto-resolved."""
        from worker import check_handoff_timeouts

        expired_conv = _make_conversation(
            auto_resolve_at=(datetime.now(UTC) - timedelta(hours=1)).isoformat()
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [expired_conv]

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine") as mock_engine_cls,
            patch("app.services.handoff_service.HandoffService") as MockService,
        ):
            mock_engine = AsyncMock()
            mock_engine_cls.return_value = mock_engine

            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=mock_result)

            # Use context manager properly
            mock_engine.__aenter__ = AsyncMock(return_value=mock_engine)
            mock_engine.__aexit__ = AsyncMock(return_value=False)

            with patch("sqlalchemy.ext.asyncio.AsyncSession") as MockSessionCls:
                MockSessionCls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                MockSessionCls.return_value.__aexit__ = AsyncMock(return_value=False)

                svc_instance = MockService.return_value
                svc_instance.resolve = AsyncMock(return_value=HandoffResult(success=True))

                result = await check_handoff_timeouts(mock_ctx)

        assert result["status"] == "success"
        assert result["resolved"] == 1
        svc_instance.resolve.assert_awaited_once()
        # Verify auto=True was passed
        call_kwargs = svc_instance.resolve.call_args
        assert call_kwargs.kwargs.get("auto") is True

    @pytest.mark.asyncio
    async def test_skips_not_yet_expired(self, mock_ctx):
        """Conversations not yet past timeout are skipped."""
        from worker import check_handoff_timeouts

        future_conv = _make_conversation(
            auto_resolve_at=(datetime.now(UTC) + timedelta(hours=12)).isoformat()
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [future_conv]

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine") as mock_engine_cls,
            patch("app.services.handoff_service.HandoffService") as MockService,
        ):
            mock_engine = AsyncMock()
            mock_engine_cls.return_value = mock_engine

            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=mock_result)

            with patch("sqlalchemy.ext.asyncio.AsyncSession") as MockSessionCls:
                MockSessionCls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                MockSessionCls.return_value.__aexit__ = AsyncMock(return_value=False)

                svc_instance = MockService.return_value
                svc_instance.resolve = AsyncMock()

                result = await check_handoff_timeouts(mock_ctx)

        assert result["status"] == "success"
        assert result["resolved"] == 0
        svc_instance.resolve.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_conversations_without_timeout(self, mock_ctx):
        """Conversations without auto_resolve_at are skipped."""
        from worker import check_handoff_timeouts

        conv_no_timeout = _make_conversation()  # No auto_resolve_at

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [conv_no_timeout]

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine") as mock_engine_cls,
            patch("app.services.handoff_service.HandoffService"),
        ):
            mock_engine = AsyncMock()
            mock_engine_cls.return_value = mock_engine

            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=mock_result)

            with patch("sqlalchemy.ext.asyncio.AsyncSession") as MockSessionCls:
                MockSessionCls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                MockSessionCls.return_value.__aexit__ = AsyncMock(return_value=False)

                result = await check_handoff_timeouts(mock_ctx)

        assert result["status"] == "success"
        assert result["resolved"] == 0

    @pytest.mark.asyncio
    async def test_handles_no_db_url(self):
        """Returns error when no database URL in context."""
        from worker import check_handoff_timeouts

        result = await check_handoff_timeouts({})

        assert result["status"] == "failed"
        assert "No database URL" in result["error"]

    @pytest.mark.asyncio
    async def test_handles_resolve_failure(self, mock_ctx):
        """Counts errors when resolve fails."""
        from worker import check_handoff_timeouts

        expired_conv = _make_conversation(
            auto_resolve_at=(datetime.now(UTC) - timedelta(hours=2)).isoformat()
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [expired_conv]

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine") as mock_engine_cls,
            patch("app.services.handoff_service.HandoffService") as MockService,
        ):
            mock_engine = AsyncMock()
            mock_engine_cls.return_value = mock_engine

            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=mock_result)

            with patch("sqlalchemy.ext.asyncio.AsyncSession") as MockSessionCls:
                MockSessionCls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                MockSessionCls.return_value.__aexit__ = AsyncMock(return_value=False)

                svc_instance = MockService.return_value
                svc_instance.resolve = AsyncMock(
                    return_value=HandoffResult(success=False, error="DB error")
                )

                result = await check_handoff_timeouts(mock_ctx)

        assert result["status"] == "success"
        assert result["resolved"] == 0
        assert result["errors"] == 1
