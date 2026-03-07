"""Stretch tests for voice module — Vapi Provider, webhook signature, conversation-update."""

import hashlib
import hmac
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.voice.webhook_handler import (
    handle_conversation_update,
    validate_vapi_webhook,
)
from app.schemas.voice import WebhookPayload

# --- Vapi Provider Unit Tests (5 tests) ---
# The `vapi` SDK is not installed in the test env, so we mock the module.

_mock_vapi_module = MagicMock()
_mock_vapi_module.AsyncVapi = MagicMock()
_mock_vapi_module.types = MagicMock()
_mock_vapi_module.types.Server = MagicMock()


def _get_provider_class():
    """Import VapiProvider with mocked vapi SDK."""
    with patch.dict(
        sys.modules, {"vapi": _mock_vapi_module, "vapi.types": _mock_vapi_module.types}
    ):
        # Force reimport
        if "app.modules.voice.vapi_provider" in sys.modules:
            del sys.modules["app.modules.voice.vapi_provider"]
        from app.modules.voice.vapi_provider import VapiProvider

        return VapiProvider


@pytest.mark.asyncio
class TestVapiProvider:
    """Unit tests for VapiProvider with mocked Vapi SDK."""

    async def test_create_assistant_returns_id(self):
        """create_assistant returns dict with assistant id."""
        VapiProvider = _get_provider_class()

        mock_client = MagicMock()
        mock_assistant = SimpleNamespace(id="asst_123", name="Test Bot", created_at="2026-01-01")
        mock_client.assistants.create = AsyncMock(return_value=mock_assistant)

        provider = VapiProvider.__new__(VapiProvider)
        provider._client = mock_client

        result = await provider.create_assistant(name="Test Bot", first_message="Hello!")

        assert result["id"] == "asst_123"
        assert result["name"] == "Test Bot"
        mock_client.assistants.create.assert_called_once()

    async def test_create_assistant_with_system_prompt(self):
        """create_assistant passes model config when system_prompt provided."""
        VapiProvider = _get_provider_class()

        mock_client = MagicMock()
        mock_assistant = SimpleNamespace(id="asst_456", name="Prompted Bot", created_at=None)
        mock_client.assistants.create = AsyncMock(return_value=mock_assistant)

        provider = VapiProvider.__new__(VapiProvider)
        provider._client = mock_client

        result = await provider.create_assistant(
            name="Prompted Bot",
            first_message="Hi!",
            system_prompt="You are helpful.",
            webhook_url="https://example.com/webhook",
        )

        assert result["id"] == "asst_456"
        call_kwargs = mock_client.assistants.create.call_args[1]
        assert "model" in call_kwargs
        assert call_kwargs["model"]["messages"][0]["content"] == "You are helpful."

    async def test_validate_keys_valid(self):
        """validate_keys returns True when list succeeds."""
        VapiProvider = _get_provider_class()

        mock_client = MagicMock()
        mock_client.assistants.list = AsyncMock(return_value=[])

        provider = VapiProvider.__new__(VapiProvider)
        provider._client = mock_client

        assert await provider.validate_keys() is True

    async def test_validate_keys_invalid(self):
        """validate_keys returns False when list raises."""
        VapiProvider = _get_provider_class()

        mock_client = MagicMock()
        mock_client.assistants.list = AsyncMock(side_effect=Exception("Unauthorized"))

        provider = VapiProvider.__new__(VapiProvider)
        provider._client = mock_client

        assert await provider.validate_keys() is False

    async def test_delete_assistant(self):
        """delete_assistant calls SDK delete."""
        VapiProvider = _get_provider_class()

        mock_client = MagicMock()
        mock_client.assistants.delete = AsyncMock()

        provider = VapiProvider.__new__(VapiProvider)
        provider._client = mock_client

        await provider.delete_assistant("asst_789")
        mock_client.assistants.delete.assert_called_once_with(id="asst_789")


# --- Webhook Signature Validation Tests (3 tests) ---


@pytest.mark.asyncio
class TestWebhookSignature:
    """Tests for HMAC-SHA256 webhook signature validation."""

    async def test_valid_signature(self):
        """Valid HMAC signature passes validation."""
        secret = "test-webhook-secret"  # pragma: allowlist secret
        body = b'{"message": {"type": "status-update"}}'
        expected_sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        request = MagicMock()
        request.headers = {"x-vapi-signature": expected_sig}
        request.body = AsyncMock(return_value=body)

        result = await validate_vapi_webhook(request, secret)
        assert result is True

    async def test_missing_signature(self):
        """Missing x-vapi-signature header fails."""
        request = MagicMock()
        request.headers = {}
        request.body = AsyncMock(return_value=b"body")

        result = await validate_vapi_webhook(request, "secret")
        assert result is False

    async def test_tampered_signature(self):
        """Tampered body with wrong signature fails."""
        secret = "test-webhook-secret"  # pragma: allowlist secret
        body = b'{"message": {"type": "status-update"}}'
        wrong_sig = hmac.new(secret.encode(), b"tampered", hashlib.sha256).hexdigest()

        request = MagicMock()
        request.headers = {"x-vapi-signature": wrong_sig}
        request.body = AsyncMock(return_value=body)

        result = await validate_vapi_webhook(request, secret)
        assert result is False


# --- Conversation Update Handler Tests (3 tests) ---


async def _create_voice_fixtures(db_session: AsyncSession):
    """Create workspace + user + conversation + call_log for voice tests."""
    from datetime import UTC, datetime

    from app.models.conversation import Conversation
    from app.models.user import User
    from app.models.voice import CallLog
    from app.models.workspace import Workspace, WorkspaceMember
    from app.services.auth import hash_password

    user_id = uuid4()
    workspace_id = uuid4()
    call_id = f"call_{uuid4().hex[:12]}"

    user = User(
        id=user_id,
        email=f"voice-{uuid4().hex[:6]}@test.com",
        password_hash=hash_password("password"),
        name="Voice Test User",
    )
    workspace = Workspace(id=workspace_id, owner_id=user_id, name="Voice WS")
    member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role="owner")

    db_session.add_all([user, workspace, member])
    await db_session.flush()

    conv = Conversation(
        id=uuid4(),
        workspace_id=workspace_id,
        channel="voice",
        external_id=call_id,
        status="active",
        started_at=datetime.now(UTC),
    )
    db_session.add(conv)
    await db_session.flush()

    call_log = CallLog(
        id=uuid4(),
        conversation_id=conv.id,
        vapi_call_id=call_id,
        direction="web",
        phone_from="web",
        phone_to="assistant",
        status="connected",
        created_at=datetime.now(UTC),
    )
    db_session.add(call_log)
    await db_session.flush()

    return workspace_id, call_id, call_log


@pytest.mark.asyncio
class TestConversationUpdateHandler:
    """Tests for conversation-update webhook handler."""

    async def test_updates_transcript(self, db_session: AsyncSession):
        """conversation-update stores partial transcript on CallLog."""
        workspace_id, call_id, call_log = await _create_voice_fixtures(db_session)

        payload = WebhookPayload(
            message={
                "type": "conversation-update",
                "call": {"id": call_id},
                "messages": [
                    {"role": "user", "content": "Hello, I need help"},
                    {"role": "assistant", "content": "How can I help you today?"},
                ],
            }
        )

        result = await handle_conversation_update(payload, workspace_id, db_session)

        assert result["status"] == "updated"
        assert result["message_count"] == 2
        assert "Hello, I need help" in call_log.transcript
        assert "How can I help you today?" in call_log.transcript

    async def test_no_call_id_returns_error(self, db_session: AsyncSession):
        """Missing call_id returns error."""
        payload = WebhookPayload(
            message={
                "type": "conversation-update",
                "messages": [{"role": "user", "content": "Hello"}],
            }
        )

        result = await handle_conversation_update(payload, uuid4(), db_session)
        assert result["status"] == "error"

    async def test_no_messages_returns_ignored(self, db_session: AsyncSession):
        """Empty messages list returns ignored."""
        payload = WebhookPayload(
            message={
                "type": "conversation-update",
                "call": {"id": "call_test123"},
                "messages": [],
            }
        )

        result = await handle_conversation_update(payload, uuid4(), db_session)
        assert result["status"] == "ignored"


# --- WebhookPayload Schema Tests (2 tests) ---


class TestWebhookPayloadSchema:
    """Tests for WebhookPayload property extractors."""

    def test_conversation_messages_extraction(self):
        """conversation_messages extracts role/content from messages array."""
        payload = WebhookPayload(
            message={
                "type": "conversation-update",
                "messages": [
                    {"role": "user", "content": "Hi"},
                    {"role": "assistant", "content": "Hello!"},
                ],
            }
        )

        messages = payload.conversation_messages
        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "Hi"}
        assert messages[1] == {"role": "assistant", "content": "Hello!"}

    def test_conversation_messages_from_artifact(self):
        """conversation_messages falls back to artifact.messages."""
        payload = WebhookPayload(
            message={
                "type": "conversation-update",
                "artifact": {
                    "messages": [
                        {"role": "user", "content": "Test from artifact"},
                    ]
                },
            }
        )

        messages = payload.conversation_messages
        assert len(messages) == 1
        assert messages[0]["content"] == "Test from artifact"
