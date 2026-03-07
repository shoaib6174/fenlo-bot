"""Tests for HandoffGuardStep and EscalationStep."""

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Pre-mock twilio to avoid ImportError
if "twilio" not in sys.modules:
    sys.modules["twilio"] = ModuleType("twilio")
    sys.modules["twilio.rest"] = ModuleType("twilio.rest")
    sys.modules["twilio.rest"].Client = MagicMock()

import pytest

from app.core.engine import MessageContext
from app.core.steps.escalation_step import EscalationStep
from app.core.steps.handoff_guard import HandoffGuardStep
from app.modules.handoff.provider import HandoffResult

# ── HandoffGuardStep tests ──


class TestHandoffGuardStep:
    """Test HandoffGuardStep."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def context(self):
        return MessageContext(
            workspace_id=uuid4(),
            user_id=uuid4(),
            conversation_id=uuid4(),
            message="I need more help please",
        )

    @pytest.mark.asyncio
    async def test_passthrough_when_not_escalated(self, mock_db, context):
        """Test that non-escalated conversations pass through."""
        mock_result = MagicMock()
        mock_result.first.return_value = MagicMock(
            status="active", workspace_id=context.workspace_id
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        step = HandoffGuardStep(mock_db)
        result = await step.execute(context)

        assert result.should_halt is False
        assert result.response is None

    @pytest.mark.asyncio
    async def test_passthrough_when_no_conversation(self, mock_db):
        """Test that contexts without conversation_id pass through."""
        context = MessageContext(
            workspace_id=uuid4(),
            user_id=uuid4(),
            conversation_id=None,
            message="Hello",
        )
        step = HandoffGuardStep(mock_db)
        result = await step.execute(context)

        assert result.should_halt is False

    @pytest.mark.asyncio
    async def test_halts_when_escalated(self, mock_db, context):
        """Test that escalated conversations halt the pipeline."""
        mock_result = MagicMock()
        mock_result.first.return_value = MagicMock(
            status="escalated", workspace_id=context.workspace_id
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.handoff_service.HandoffService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.forward_message = AsyncMock(return_value=HandoffResult(success=True))
            mock_svc_cls.return_value = mock_svc

            step = HandoffGuardStep(mock_db)
            result = await step.execute(context)

        assert result.should_halt is True
        assert result.halt_reason == "conversation_escalated"
        assert "forwarded" in result.response.lower()
        # Should have persisted user message
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_halts_even_if_forward_fails(self, mock_db, context):
        """Test that pipeline halts even if forwarding fails."""
        mock_result = MagicMock()
        mock_result.first.return_value = MagicMock(
            status="escalated", workspace_id=context.workspace_id
        )
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.handoff_service.HandoffService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.forward_message = AsyncMock(side_effect=Exception("Network error"))
            mock_svc_cls.return_value = mock_svc

            step = HandoffGuardStep(mock_db)
            result = await step.execute(context)

        assert result.should_halt is True
        assert result.response is not None


# ── EscalationStep tests ──


class TestEscalationStep:
    """Test EscalationStep."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def context(self):
        ctx = MessageContext(
            workspace_id=uuid4(),
            user_id=uuid4(),
            conversation_id=uuid4(),
            message="I want to speak to a human",
        )
        ctx.response = "I understand your frustration."
        ctx.sentiment = "negative"
        ctx.intent = "escalation"
        ctx.quality_score = 0.3
        ctx.metadata["llm_router"] = AsyncMock()
        return ctx

    @pytest.mark.asyncio
    async def test_no_escalation_when_no_rules_match(self, mock_db, context):
        """Test that no escalation happens when rules don't match."""
        with patch.object(EscalationStep, "__init__", lambda self, db: None):
            step = EscalationStep.__new__(EscalationStep)
            step.db = mock_db
            step.engine = AsyncMock()
            step.engine.evaluate = AsyncMock(return_value=None)

            result = await step.execute(context)

        assert "connecting you" not in (result.response or "")

    @pytest.mark.asyncio
    async def test_escalation_triggered(self, mock_db, context):
        """Test that matching rules trigger handoff."""
        with patch.object(EscalationStep, "__init__", lambda self, db: None):
            step = EscalationStep.__new__(EscalationStep)
            step.db = mock_db
            step.engine = AsyncMock()
            step.engine.evaluate = AsyncMock(
                return_value={
                    "rule_id": str(uuid4()),
                    "rule_type": "keyword",
                    "action": "escalate",
                    "matched": "speak to a human",
                }
            )

            with patch("app.services.handoff_service.HandoffService") as mock_svc_cls:
                mock_svc = AsyncMock()
                mock_svc.escalate = AsyncMock(return_value=HandoffResult(success=True))
                mock_svc_cls.return_value = mock_svc

                result = await step.execute(context)

        assert "connecting you" in result.response.lower()
        mock_svc.escalate.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_escalate_action_ignored(self, mock_db, context):
        """Test that 'notify' or 'log' actions don't trigger handoff."""
        with patch.object(EscalationStep, "__init__", lambda self, db: None):
            step = EscalationStep.__new__(EscalationStep)
            step.db = mock_db
            step.engine = AsyncMock()
            step.engine.evaluate = AsyncMock(
                return_value={
                    "rule_type": "keyword",
                    "action": "notify",
                    "matched": "some keyword",
                }
            )

            result = await step.execute(context)

        assert "connecting you" not in result.response

    @pytest.mark.asyncio
    async def test_skips_when_no_response(self, mock_db):
        """Test that step skips when there's no response."""
        ctx = MessageContext(
            workspace_id=uuid4(),
            user_id=uuid4(),
            conversation_id=uuid4(),
            message="Hello",
        )
        step = EscalationStep(mock_db)
        result = await step.execute(ctx)
        assert result.response is None

    @pytest.mark.asyncio
    async def test_error_doesnt_block_pipeline(self, mock_db, context):
        """Test that errors in escalation don't halt the pipeline."""
        with patch.object(EscalationStep, "__init__", lambda self, db: None):
            step = EscalationStep.__new__(EscalationStep)
            step.db = mock_db
            step.engine = AsyncMock()
            step.engine.evaluate = AsyncMock(side_effect=Exception("DB error"))

            result = await step.execute(context)

        # Response should be unchanged
        assert result.response == "I understand your frustration."
