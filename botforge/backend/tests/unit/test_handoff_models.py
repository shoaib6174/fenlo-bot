"""Tests for handoff models and providers."""

import hashlib
import hmac
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.handoff import HandoffEvent
from app.modules.handoff.generic_webhook import GenericWebhookProvider
from app.modules.handoff.provider import EscalationPayload, HandoffResult

# ── HandoffEvent model tests ──


class TestHandoffEvent:
    """Test HandoffEvent model."""

    def test_create_handoff_event(self):
        """Test creating a HandoffEvent instance."""
        event = HandoffEvent(
            id=uuid4(),
            conversation_id=uuid4(),
            workspace_id=uuid4(),
            event_type="escalated",
            actor="system",
            payload={"reason": "keyword", "matched": "speak to human"},
            created_at=datetime.now(UTC),
        )
        assert event.event_type == "escalated"
        assert event.actor == "system"
        assert event.payload["reason"] == "keyword"

    def test_handoff_event_all_event_types(self):
        """Test that all valid event types can be used."""
        valid_types = [
            "escalated",
            "message_forwarded",
            "agent_replied",
            "resolved",
            "auto_resolved",
        ]
        for event_type in valid_types:
            event = HandoffEvent(
                id=uuid4(),
                conversation_id=uuid4(),
                workspace_id=uuid4(),
                event_type=event_type,
            )
            assert event.event_type == event_type

    def test_handoff_event_optional_fields(self):
        """Test HandoffEvent with minimal required fields."""
        event = HandoffEvent(
            id=uuid4(),
            conversation_id=uuid4(),
            workspace_id=uuid4(),
            event_type="escalated",
        )
        assert event.actor is None
        assert event.payload is None


# ── HandoffResult dataclass tests ──


class TestHandoffResult:
    """Test HandoffResult dataclass."""

    def test_success_result(self):
        result = HandoffResult(success=True, external_ticket_id="TICKET-123")
        assert result.success is True
        assert result.external_ticket_id == "TICKET-123"
        assert result.error is None

    def test_failure_result(self):
        result = HandoffResult(success=False, error="Connection refused")
        assert result.success is False
        assert result.external_ticket_id is None

    def test_default_metadata(self):
        result = HandoffResult(success=True)
        assert result.metadata == {}


# ── EscalationPayload dataclass tests ──


class TestEscalationPayload:
    """Test EscalationPayload dataclass."""

    def test_create_payload(self):
        conv_id = uuid4()
        ws_id = uuid4()
        payload = EscalationPayload(
            conversation_id=conv_id,
            workspace_id=ws_id,
            channel="whatsapp",
            contact_name="John Doe",
            contact_info={"phone": "+1234567890"},
            summary="User asked about pricing but bot couldn't help.",
            last_messages=[{"role": "user", "content": "What are your prices?"}],
            escalation_reason={"rule": "keyword", "matched": "speak to agent"},
            metadata={"sentiment": "negative", "intent": "sales", "lead_score": 72},
            reply_url="https://example.com/api/v1/handoff/reply",
            resolve_url="https://example.com/api/v1/handoff/resolve",
        )
        assert payload.conversation_id == conv_id
        assert payload.channel == "whatsapp"
        assert payload.contact_name == "John Doe"


# ── GenericWebhookProvider tests ──


class TestGenericWebhookProvider:
    """Test GenericWebhookProvider."""

    @pytest.fixture
    def provider(self):
        return GenericWebhookProvider(
            webhook_url="https://hooks.example.com/botforge",
            webhook_secret="test-secret-key",  # pragma: allowlist secret
        )

    @pytest.fixture
    def sample_payload(self):
        return EscalationPayload(
            conversation_id=uuid4(),
            workspace_id=uuid4(),
            channel="web",
            contact_name="Jane Smith",
            contact_info={"email": "jane@example.com"},
            summary="Customer needs help with billing.",
            last_messages=[
                {"role": "user", "content": "I need help with my invoice"},
                {"role": "assistant", "content": "I'm not sure about billing details."},
            ],
            escalation_reason={"rule": "intent", "matched": "escalation"},
            metadata={"sentiment": "neutral", "intent": "support"},
            reply_url="https://botforge.example.com/api/v1/handoff/reply",
            resolve_url="https://botforge.example.com/api/v1/handoff/resolve",
        )

    def test_sign(self, provider):
        """Test HMAC signature generation."""
        timestamp = "1700000000"
        body = '{"event": "test"}'
        sig = provider._sign(timestamp, body)

        # Verify independently
        message = f"{timestamp}.{body}"
        expected = hmac.new(b"test-secret-key", message.encode(), hashlib.sha256).hexdigest()
        assert sig == expected

    @pytest.mark.asyncio
    async def test_escalate_success(self, provider, sample_payload):
        """Test successful escalation webhook."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"ticket_id": "EXT-42"}
        mock_response.text = '{"ticket_id": "EXT-42"}'

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await provider.escalate(sample_payload)

        assert result.success is True
        assert result.external_ticket_id == "EXT-42"

        # Verify the POST was called with correct URL
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert (
            call_args.kwargs.get("headers", call_args[1].get("headers", {})).get("X-BotForge-Event")
            == "conversation.escalated"
        )

    @pytest.mark.asyncio
    async def test_escalate_http_error(self, provider, sample_payload):
        """Test escalation webhook with HTTP error."""
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await provider.escalate(sample_payload)

        assert result.success is False
        assert "500" in result.error

    @pytest.mark.asyncio
    async def test_escalate_timeout(self, provider, sample_payload):
        """Test escalation webhook timeout."""
        import httpx

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("timed out")
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await provider.escalate(sample_payload)

        assert result.success is False
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_forward_message(self, provider):
        """Test forwarding a user message."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.text = "{}"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await provider.forward_message(
                external_ticket_id="EXT-42",
                message="I still need help!",
                sender_name="Jane",
            )

        assert result.success is True

        # Verify body contains message
        call_args = mock_client.post.call_args
        sent_body = json.loads(call_args.kwargs.get("content", call_args[1].get("content", "")))
        assert sent_body["event"] == "conversation.message_forwarded"
        assert sent_body["message"] == "I still need help!"
        assert sent_body["external_ticket_id"] == "EXT-42"

    @pytest.mark.asyncio
    async def test_resolve(self, provider):
        """Test resolving a conversation."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.text = "{}"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await provider.resolve(
                external_ticket_id="EXT-42",
                resolution_note="Issue resolved via email",
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_webhook_includes_signature_headers(self, provider, sample_payload):
        """Test that all webhook requests include HMAC signature headers."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.text = "{}"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await provider.escalate(sample_payload)

        call_args = mock_client.post.call_args
        headers = call_args.kwargs.get("headers", call_args[1].get("headers", {}))
        assert "X-BotForge-Signature" in headers
        assert "X-BotForge-Timestamp" in headers
        assert headers["Content-Type"] == "application/json"
