"""Tests for FreshdeskProvider and Freshdesk webhook parsing."""

import json
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

# Pre-mock twilio to avoid ImportError
if "twilio" not in sys.modules:
    sys.modules["twilio"] = ModuleType("twilio")
    sys.modules["twilio.rest"] = ModuleType("twilio.rest")
    sys.modules["twilio.rest"].Client = MagicMock()

from app.modules.handoff.freshdesk_provider import FreshdeskProvider
from app.modules.handoff.provider import EscalationPayload, HandoffResult

# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def provider():
    return FreshdeskProvider(
        domain="testcompany",
        api_key="test-api-key",  # pragma: allowlist secret
        default_group_id=12345,
    )


@pytest.fixture
def escalation_payload():
    return EscalationPayload(
        conversation_id=uuid4(),
        workspace_id=uuid4(),
        channel="web",
        contact_name="Jane Doe",
        contact_info={"email": "jane@example.com"},
        summary="Customer asking about billing issue",
        last_messages=[
            {"role": "user", "content": "I was charged twice"},
            {"role": "assistant", "content": "Let me connect you with our team"},
        ],
        escalation_reason={"rule_type": "keyword", "matched": "billing"},
        metadata={"lead_score": 75},
        reply_url="https://app.example.com/api/v1/handoff/reply",
        resolve_url="https://app.example.com/api/v1/handoff/resolve",
    )


def _mock_response(status_code: int, json_data: dict | None = None):
    """Create a mock httpx.Response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.text = json.dumps(json_data or {})
    response.json.return_value = json_data or {}
    return response


# ── FreshdeskProvider.escalate() tests ──────────────────────────────


class TestFreshdeskEscalate:
    """Test FreshdeskProvider.escalate() (7.23)."""

    @pytest.mark.asyncio
    async def test_escalate_creates_ticket(self, provider, escalation_payload):
        """Successful escalation creates a Freshdesk ticket."""
        mock_resp = _mock_response(201, {"id": 42})

        with patch("app.modules.handoff.freshdesk_provider.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await provider.escalate(escalation_payload)

        assert result.success is True
        assert result.external_ticket_id == "42"

        # Verify the ticket data sent
        call_kwargs = client_instance.post.call_args
        assert "testcompany.freshdesk.com/api/v2/tickets" in call_kwargs.args[0]
        ticket_data = call_kwargs.kwargs["json"]
        assert "[BotForge]" in ticket_data["subject"]
        assert ticket_data["email"] == "jane@example.com"
        assert ticket_data["priority"] == 2
        assert ticket_data["group_id"] == 12345

    @pytest.mark.asyncio
    async def test_escalate_http_error(self, provider, escalation_payload):
        """HTTP error returns failure result."""
        mock_resp = _mock_response(422, {"errors": [{"field": "email"}]})

        with patch("app.modules.handoff.freshdesk_provider.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await provider.escalate(escalation_payload)

        assert result.success is False
        assert "422" in result.error

    @pytest.mark.asyncio
    async def test_escalate_timeout(self, provider, escalation_payload):
        """Timeout returns failure result."""
        with patch("app.modules.handoff.freshdesk_provider.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await provider.escalate(escalation_payload)

        assert result.success is False
        assert "timed out" in result.error

    @pytest.mark.asyncio
    async def test_escalate_no_email_uses_fallback(self, provider, escalation_payload):
        """Missing email uses a generated fallback."""
        escalation_payload.contact_info = {}
        mock_resp = _mock_response(201, {"id": 99})

        with patch("app.modules.handoff.freshdesk_provider.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await provider.escalate(escalation_payload)

        assert result.success is True
        call_kwargs = client_instance.post.call_args
        ticket_data = call_kwargs.kwargs["json"]
        assert "@botforge.local" in ticket_data["email"]


# ── FreshdeskProvider.forward_message() tests ───────────────────────


class TestFreshdeskForwardMessage:
    """Test FreshdeskProvider.forward_message() (7.24)."""

    @pytest.mark.asyncio
    async def test_forward_adds_note(self, provider):
        """Forward creates a private note on the ticket."""
        mock_resp = _mock_response(201, {"id": 1001})

        with patch("app.modules.handoff.freshdesk_provider.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await provider.forward_message("42", "I still need help", "Jane")

        assert result.success is True
        call_kwargs = client_instance.post.call_args
        assert "/tickets/42/notes" in call_kwargs.args[0]
        note_data = call_kwargs.kwargs["json"]
        assert note_data["private"] is True
        assert "Jane" in note_data["body"]


# ── FreshdeskProvider.resolve() tests ───────────────────────────────


class TestFreshdeskResolve:
    """Test FreshdeskProvider.resolve() (7.25)."""

    @pytest.mark.asyncio
    async def test_resolve_closes_ticket(self, provider):
        """Resolve updates ticket status to Resolved (4)."""
        mock_resp_note = _mock_response(201, {})
        mock_resp_update = _mock_response(200, {})

        with patch("app.modules.handoff.freshdesk_provider.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(return_value=mock_resp_note)
            client_instance.put = AsyncMock(return_value=mock_resp_update)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await provider.resolve("42", "Issue fixed")

        assert result.success is True
        # Verify note was added with resolution
        note_call = client_instance.post.call_args
        assert "/tickets/42/notes" in note_call.args[0]
        # Verify ticket status update
        update_call = client_instance.put.call_args
        assert "/tickets/42" in update_call.args[0]
        assert update_call.kwargs["json"]["status"] == 4

    @pytest.mark.asyncio
    async def test_resolve_without_note(self, provider):
        """Resolve without note skips note creation."""
        mock_resp = _mock_response(200, {})

        with patch("app.modules.handoff.freshdesk_provider.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.put = AsyncMock(return_value=mock_resp)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await provider.resolve("42")

        assert result.success is True
        client_instance.post.assert_not_awaited()


# ── Provider Registry tests ─────────────────────────────────────────


class TestProviderRegistry:
    """Test provider resolution from workspace settings (7.27)."""

    def test_builds_generic_webhook(self):
        """Generic webhook provider is default."""
        from app.services.handoff_service import _build_provider

        config = {
            "provider": "generic_webhook",
            "webhook_url": "https://hooks.example.com",
            "webhook_secret": "secret",  # pragma: allowlist secret
        }
        provider = _build_provider(config)
        from app.modules.handoff.generic_webhook import GenericWebhookProvider

        assert isinstance(provider, GenericWebhookProvider)

    def test_builds_freshdesk(self):
        """Freshdesk provider is built from config."""
        from app.services.handoff_service import _build_provider

        config = {
            "provider": "freshdesk",
            "freshdesk_domain": "mycompany",
            "freshdesk_api_key": "api-key-123",  # pragma: allowlist secret
            "freshdesk_default_group_id": 42,
        }
        provider = _build_provider(config)
        assert isinstance(provider, FreshdeskProvider)
        assert provider.default_group_id == 42

    def test_freshdesk_missing_config_raises(self):
        """Missing Freshdesk config raises ValueError."""
        from app.services.handoff_service import _build_provider

        config = {"provider": "freshdesk"}
        with pytest.raises(ValueError, match="domain and API key"):
            _build_provider(config)


# ── Freshdesk Webhook Parsing tests (7.26) ──────────────────────────


class TestFreshdeskWebhookParsing:
    """Test Freshdesk webhook payload parsing in handoff API."""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        return session

    @pytest.fixture
    def conv_id(self):
        return uuid4()

    @pytest.fixture
    def mock_workspace_with_token(self):
        ws = MagicMock()
        ws.settings = {
            "handoff": {
                "provider": "freshdesk",
                "freshdesk_domain": "test",
                "freshdesk_api_key": "key",  # pragma: allowlist secret
                "freshdesk_webhook_token": "fd-token-123",  # pragma: allowlist secret
            }
        }
        return ws

    def _make_request(self, body: dict, token: str | None = None):
        request = AsyncMock()
        raw = json.dumps(body).encode()
        request.body = AsyncMock(return_value=raw)
        headers = {}
        if token:
            headers["x-freshdesk-token"] = token
        request.headers = headers
        return request

    @pytest.mark.asyncio
    async def test_agent_reply_webhook(self, mock_session, conv_id, mock_workspace_with_token):
        """Freshdesk agent reply note is forwarded to user."""
        from app.api.handoff import freshdesk_webhook
        from app.models.conversation import Conversation

        conv = MagicMock(spec=Conversation)
        conv.id = conv_id
        conv.workspace_id = uuid4()
        conv.status = "escalated"

        async def mock_get(model, id_val):
            if model.__name__ == "Conversation":
                return conv
            if model.__name__ == "Workspace":
                return mock_workspace_with_token
            return None

        mock_session.get = AsyncMock(side_effect=mock_get)

        body = {
            "ticket": {
                "status": 3,  # Pending (not resolved)
                "custom_fields": {"cf_conversation_id": str(conv_id)},
            },
            "note": {"body": "<p>Hi, I can help with that billing issue.</p>"},
            "agent": {"name": "Agent Smith"},
        }
        request = self._make_request(body, "fd-token-123")

        with patch("app.api.handoff.HandoffService") as MockService:
            svc = MockService.return_value
            svc.handle_agent_reply = AsyncMock(return_value=HandoffResult(success=True))

            result = await freshdesk_webhook(request=request, db=mock_session)

        assert result["action"] == "replied"
        svc.handle_agent_reply.assert_awaited_once()
        # Verify HTML was stripped
        call_args = svc.handle_agent_reply.call_args
        assert "<p>" not in call_args.kwargs["message"]

    @pytest.mark.asyncio
    async def test_ticket_resolved_webhook(self, mock_session, conv_id, mock_workspace_with_token):
        """Freshdesk ticket resolved triggers conversation resolve."""
        from app.api.handoff import freshdesk_webhook
        from app.models.conversation import Conversation

        conv = MagicMock(spec=Conversation)
        conv.id = conv_id
        conv.workspace_id = uuid4()
        conv.status = "escalated"

        async def mock_get(model, id_val):
            if model.__name__ == "Conversation":
                return conv
            if model.__name__ == "Workspace":
                return mock_workspace_with_token
            return None

        mock_session.get = AsyncMock(side_effect=mock_get)

        body = {
            "ticket": {
                "status": 4,  # Resolved
                "custom_fields": {"cf_conversation_id": str(conv_id)},
            },
        }
        request = self._make_request(body, "fd-token-123")

        with patch("app.api.handoff.HandoffService") as MockService:
            svc = MockService.return_value
            svc.resolve = AsyncMock(return_value=HandoffResult(success=True))

            result = await freshdesk_webhook(request=request, db=mock_session)

        assert result["action"] == "resolved"
        svc.resolve.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_conversation_id_ignored(self, mock_session):
        """Webhook without conversation_id is ignored."""
        from app.api.handoff import freshdesk_webhook

        body = {"ticket": {"status": 2, "custom_fields": {}}}
        request = self._make_request(body)

        result = await freshdesk_webhook(request=request, db=mock_session)
        assert result["status"] == "ignored"
