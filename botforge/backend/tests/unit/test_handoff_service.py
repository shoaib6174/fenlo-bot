"""Tests for HandoffService."""

import sys
from datetime import UTC, datetime
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Pre-mock twilio to avoid ImportError in response_router import chain
if "twilio" not in sys.modules:
    sys.modules["twilio"] = ModuleType("twilio")
    sys.modules["twilio.rest"] = ModuleType("twilio.rest")
    sys.modules["twilio.rest"].Client = MagicMock()

from app.models.conversation import Conversation, Message
from app.modules.handoff.provider import HandoffResult
from app.services.handoff_service import HandoffService


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_llm_router():
    """Create mock LLM router."""
    router = AsyncMock()
    router.complete = AsyncMock(
        return_value={"content": "Customer asked about billing. Bot couldn't help."}
    )
    return router


@pytest.fixture
def service(mock_llm_router):
    return HandoffService(llm_router=mock_llm_router)


@pytest.fixture
def sample_conversation():
    conv_id = uuid4()
    ws_id = uuid4()
    conv = MagicMock(spec=Conversation)
    conv.id = conv_id
    conv.workspace_id = ws_id
    conv.channel = "web"
    conv.status = "active"
    conv.contact_name = "Jane Doe"
    conv.contact_info = {"email": "jane@example.com"}
    conv.lead_score = 50
    conv.metadata_ = {}
    return conv


@pytest.fixture
def sample_workspace():
    ws = MagicMock()
    ws.settings = {
        "handoff": {
            "provider": "generic_webhook",
            "webhook_url": "https://hooks.example.com/escalate",
            "webhook_secret": "secret123",  # pragma: allowlist secret
            "timeout_hours": 12,
        }
    }
    return ws


class TestHandoffServiceEscalate:
    """Test HandoffService.escalate()."""

    @pytest.mark.asyncio
    async def test_escalate_success(
        self, service, mock_session, sample_conversation, sample_workspace
    ):
        """Test successful escalation."""
        conv = sample_conversation
        ws = sample_workspace

        async def mock_get(model, id_):
            if model is Conversation:
                return conv
            return ws

        mock_session.get = AsyncMock(side_effect=mock_get)

        # Mock message query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(spec=Message, role="user", content="Help me", created_at=datetime.now(UTC)),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Mock provider
        with patch("app.services.handoff_service._build_provider") as mock_build:
            mock_provider = AsyncMock()
            mock_provider.escalate = AsyncMock(
                return_value=HandoffResult(success=True, external_ticket_id="TICKET-1")
            )
            mock_build.return_value = mock_provider

            result = await service.escalate(
                conversation_id=conv.id,
                workspace_id=conv.workspace_id,
                reason={"rule": "keyword", "matched": "speak to human"},
                session=mock_session,
            )

        assert result.success is True
        assert result.external_ticket_id == "TICKET-1"
        assert conv.status == "escalated"
        assert "escalated_at" in conv.metadata_
        mock_session.add.assert_called()
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_escalate_conversation_not_found(self, service, mock_session):
        """Test escalation with missing conversation."""
        mock_session.get = AsyncMock(return_value=None)

        result = await service.escalate(
            conversation_id=uuid4(),
            workspace_id=uuid4(),
            reason={"rule": "keyword"},
            session=mock_session,
        )

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_escalate_already_escalated(self, service, mock_session, sample_conversation):
        """Test escalation of already-escalated conversation."""
        sample_conversation.status = "escalated"
        mock_session.get = AsyncMock(return_value=sample_conversation)

        result = await service.escalate(
            conversation_id=sample_conversation.id,
            workspace_id=sample_conversation.workspace_id,
            reason={"rule": "keyword"},
            session=mock_session,
        )

        assert result.success is False
        assert "already escalated" in result.error.lower()

    @pytest.mark.asyncio
    async def test_escalate_no_handoff_config(self, service, mock_session, sample_conversation):
        """Test escalation when handoff is not configured."""
        ws = MagicMock()
        ws.settings = {}

        async def mock_get(model, id_):
            if model is Conversation:
                return sample_conversation
            return ws

        mock_session.get = AsyncMock(side_effect=mock_get)

        result = await service.escalate(
            conversation_id=sample_conversation.id,
            workspace_id=sample_conversation.workspace_id,
            reason={"rule": "keyword"},
            session=mock_session,
        )

        assert result.success is False
        assert "not configured" in result.error.lower()


class TestHandoffServiceForward:
    """Test HandoffService.forward_message()."""

    @pytest.mark.asyncio
    async def test_forward_message_success(self, service, mock_session):
        """Test forwarding a user message."""
        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.workspace_id = uuid4()
        conv.status = "escalated"
        conv.metadata_ = {"external_ticket_id": "TICKET-1"}

        ws = MagicMock()
        ws.settings = {
            "handoff": {
                "webhook_url": "https://hooks.example.com/escalate",
                "webhook_secret": "secret",  # pragma: allowlist secret
            }
        }

        async def mock_get(model, id_):
            if model is Conversation:
                return conv
            return ws

        mock_session.get = AsyncMock(side_effect=mock_get)

        with patch("app.services.handoff_service._build_provider") as mock_build:
            mock_provider = AsyncMock()
            mock_provider.forward_message = AsyncMock(return_value=HandoffResult(success=True))
            mock_build.return_value = mock_provider

            result = await service.forward_message(
                conversation_id=conv.id,
                workspace_id=conv.workspace_id,
                message="I still need help!",
                sender_name="Jane",
                session=mock_session,
            )

        assert result.success is True
        mock_provider.forward_message.assert_called_once_with(
            external_ticket_id="TICKET-1",
            message="I still need help!",
            sender_name="Jane",
        )

    @pytest.mark.asyncio
    async def test_forward_not_escalated(self, service, mock_session):
        """Test forwarding to a non-escalated conversation."""
        conv = MagicMock(spec=Conversation)
        conv.status = "active"
        mock_session.get = AsyncMock(return_value=conv)

        result = await service.forward_message(
            conversation_id=uuid4(),
            workspace_id=uuid4(),
            message="Hello",
            sender_name=None,
            session=mock_session,
        )

        assert result.success is False
        assert "not escalated" in result.error.lower()


class TestHandoffServiceReply:
    """Test HandoffService.handle_agent_reply()."""

    @pytest.mark.asyncio
    async def test_agent_reply_success(self, service, mock_session):
        """Test relaying agent reply to user."""
        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.workspace_id = uuid4()
        conv.status = "escalated"
        mock_session.get = AsyncMock(return_value=conv)

        with patch("app.modules.channels.response_router.send_channel_response") as mock_send:
            mock_send.return_value = MagicMock(success=True)

            result = await service.handle_agent_reply(
                conversation_id=conv.id,
                message="We've fixed the billing issue.",
                agent_name="Agent Smith",
                session=mock_session,
            )

        assert result.success is True
        mock_send.assert_called_once()
        # Should have added a Message + HandoffEvent
        assert mock_session.add.call_count == 2

    @pytest.mark.asyncio
    async def test_agent_reply_not_escalated(self, service, mock_session):
        """Test replying to non-escalated conversation."""
        conv = MagicMock(spec=Conversation)
        conv.status = "active"
        mock_session.get = AsyncMock(return_value=conv)

        result = await service.handle_agent_reply(
            conversation_id=uuid4(),
            message="Hello",
            agent_name=None,
            session=mock_session,
        )

        assert result.success is False


class TestHandoffServiceResolve:
    """Test HandoffService.resolve()."""

    @pytest.mark.asyncio
    async def test_resolve_success(self, service, mock_session):
        """Test resolving an escalated conversation."""
        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.workspace_id = uuid4()
        conv.status = "escalated"
        conv.metadata_ = {"external_ticket_id": "TICKET-1"}
        mock_session.get = AsyncMock(return_value=conv)

        ws = MagicMock()
        ws.settings = {
            "handoff": {
                "webhook_url": "https://hooks.example.com/escalate",
                "webhook_secret": "secret",  # pragma: allowlist secret
            }
        }

        # mock_session.get needs to return both conversation and workspace
        call_count = 0

        async def mock_get(model, id_):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return conv
            return ws

        mock_session.get = AsyncMock(side_effect=mock_get)

        with patch("app.modules.channels.response_router.send_channel_response") as mock_send:
            mock_send.return_value = MagicMock(success=True)

            with patch("app.services.handoff_service._build_provider") as mock_build:
                mock_provider = AsyncMock()
                mock_provider.resolve = AsyncMock(return_value=HandoffResult(success=True))
                mock_build.return_value = mock_provider

                result = await service.resolve(
                    conversation_id=conv.id,
                    session=mock_session,
                    resolution_note="Fixed via email",
                )

        assert result.success is True
        assert conv.status == "active"
        assert "resolved_at" in conv.metadata_

    @pytest.mark.asyncio
    async def test_auto_resolve(self, service, mock_session):
        """Test auto-resolve sends different message."""
        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.workspace_id = uuid4()
        conv.status = "escalated"
        conv.metadata_ = {}
        mock_session.get = AsyncMock(return_value=conv)

        ws = MagicMock()
        ws.settings = {
            "handoff": {"webhook_url": "https://example.com", "webhook_secret": "s"}
        }  # pragma: allowlist secret

        call_count = 0

        async def mock_get(model, id_):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return conv
            return ws

        mock_session.get = AsyncMock(side_effect=mock_get)

        with patch("app.modules.channels.response_router.send_channel_response") as mock_send:
            mock_send.return_value = MagicMock(success=True)

            with patch("app.services.handoff_service._build_provider") as mock_build:
                mock_build.return_value = AsyncMock()

                result = await service.resolve(
                    conversation_id=conv.id,
                    session=mock_session,
                    auto=True,
                )

        assert result.success is True
        # Verify auto-resolve message was sent
        call_args = mock_send.call_args
        msg = call_args.kwargs.get("message", call_args[1].get("message", ""))
        assert "follow up" in msg.lower()


class TestSummaryGeneration:
    """Test LLM summary generation."""

    @pytest.mark.asyncio
    async def test_summary_with_llm(self, service):
        """Test summary generation uses LLM router."""
        messages = [
            MagicMock(spec=Message, role="user", content="What are your prices?"),
            MagicMock(spec=Message, role="assistant", content="I'm not sure about pricing."),
        ]

        summary = await service._generate_summary(messages)

        assert "billing" in summary.lower() or "couldn't help" in summary.lower()
        service.llm_router.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_summary_without_llm(self):
        """Test fallback summary when no LLM router."""
        service_no_llm = HandoffService(llm_router=None)
        messages = [
            MagicMock(spec=Message, role="user", content="Help me with billing"),
        ]

        summary = await service_no_llm._generate_summary(messages)

        assert "billing" in summary.lower()

    @pytest.mark.asyncio
    async def test_summary_empty_messages(self, service):
        """Test summary with no messages."""
        summary = await service._generate_summary([])
        assert "no conversation" in summary.lower()
