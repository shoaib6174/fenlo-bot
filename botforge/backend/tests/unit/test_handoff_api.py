"""Tests for Handoff API endpoints."""

import hashlib
import hmac
import json
import sys
import time
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Pre-mock twilio to avoid ImportError in response_router import chain
if "twilio" not in sys.modules:
    sys.modules["twilio"] = ModuleType("twilio")
    sys.modules["twilio.rest"] = ModuleType("twilio.rest")
    sys.modules["twilio.rest"].Client = MagicMock()

from app.api.handoff import (
    _validate_hmac,
    handoff_escalate_manual,
    handoff_reply,
    handoff_resolve_external,
    handoff_status,
)
from app.models.conversation import Conversation  # noqa: F401
from app.modules.handoff.provider import HandoffResult

# ── Fixtures ────────────────────────────────────────────────────────


WEBHOOK_SECRET = "test-secret-key-123"  # pragma: allowlist secret


@pytest.fixture
def conv_id():
    return uuid4()


@pytest.fixture
def workspace_id():
    return uuid4()


@pytest.fixture
def mock_conversation(conv_id, workspace_id):
    conv = MagicMock(spec=Conversation)
    conv.id = conv_id
    conv.workspace_id = workspace_id
    conv.status = "escalated"
    conv.metadata_ = {
        "escalated_at": "2026-02-15T10:00:00+00:00",
        "handoff_provider": "generic_webhook",
        "external_ticket_id": "EXT-123",
    }
    return conv


@pytest.fixture
def mock_workspace():
    ws = MagicMock()
    ws.settings = {
        "handoff": {
            "provider": "generic_webhook",
            "webhook_url": "https://hooks.example.com/escalate",
            "webhook_secret": WEBHOOK_SECRET,
            "timeout_hours": 12,
        }
    }
    return ws


@pytest.fixture
def mock_session(mock_conversation, mock_workspace):
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    async def mock_get(model, id_val):
        if model.__name__ == "Conversation":
            return mock_conversation
        if model.__name__ == "Workspace":
            return mock_workspace
        return None

    session.get = AsyncMock(side_effect=mock_get)
    return session


def _sign_request(body: bytes, secret: str = WEBHOOK_SECRET) -> tuple[str, str]:
    """Generate HMAC signature and timestamp for a request."""
    ts = str(int(time.time()))
    message = f"{ts}.{body.decode()}"
    sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return sig, ts


def _make_request(body: bytes, signature: str | None = None, timestamp: str | None = None):
    """Create a mock FastAPI Request."""
    request = AsyncMock()
    request.body = AsyncMock(return_value=body)
    headers = {}
    if signature:
        headers["x-webhook-signature"] = signature
    if timestamp:
        headers["x-webhook-timestamp"] = timestamp
    request.headers = headers
    return request


# ── HMAC Validation Tests ───────────────────────────────────────────


class TestHMACValidation:
    """Test HMAC signature validation (7.20)."""

    @pytest.mark.asyncio
    async def test_valid_signature(self, mock_session, conv_id):
        """Valid HMAC signature passes validation."""
        body = json.dumps({"conversation_id": str(conv_id)}).encode()
        sig, ts = _sign_request(body)

        # Should not raise
        await _validate_hmac(conv_id, body, sig, ts, mock_session)

    @pytest.mark.asyncio
    async def test_missing_signature(self, mock_session, conv_id):
        """Missing signature raises 401."""
        body = b'{"test": true}'
        with pytest.raises(Exception) as exc_info:
            await _validate_hmac(conv_id, body, None, str(int(time.time())), mock_session)
        assert exc_info.value.status_code == 401
        assert "Missing signature" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_missing_timestamp(self, mock_session, conv_id):
        """Missing timestamp raises 401."""
        body = b'{"test": true}'
        with pytest.raises(Exception) as exc_info:
            await _validate_hmac(conv_id, body, "somesig", None, mock_session)
        assert exc_info.value.status_code == 401
        assert "Missing signature" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_invalid_timestamp_format(self, mock_session, conv_id):
        """Non-numeric timestamp raises 401."""
        body = b'{"test": true}'
        with pytest.raises(Exception) as exc_info:
            await _validate_hmac(conv_id, body, "somesig", "not-a-number", mock_session)
        assert exc_info.value.status_code == 401
        assert "Invalid timestamp" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_expired_timestamp(self, mock_session, conv_id):
        """Timestamp older than tolerance raises 401."""
        body = b'{"test": true}'
        old_ts = str(int(time.time()) - 600)  # 10 minutes ago
        sig = hmac.new(
            WEBHOOK_SECRET.encode(), f"{old_ts}.{body.decode()}".encode(), hashlib.sha256
        ).hexdigest()
        with pytest.raises(Exception) as exc_info:
            await _validate_hmac(conv_id, body, sig, old_ts, mock_session)
        assert exc_info.value.status_code == 401
        assert "too old" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_wrong_signature(self, mock_session, conv_id):
        """Invalid signature raises 401."""
        body = json.dumps({"conversation_id": str(conv_id)}).encode()
        ts = str(int(time.time()))
        wrong_sig = "deadbeef" * 8
        with pytest.raises(Exception) as exc_info:
            await _validate_hmac(conv_id, body, wrong_sig, ts, mock_session)
        assert exc_info.value.status_code == 401
        assert "Invalid signature" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_conversation_not_found(self, mock_session, conv_id):
        """Unknown conversation_id raises 404."""
        mock_session.get = AsyncMock(return_value=None)
        body = b'{"test": true}'
        sig, ts = _sign_request(body)
        with pytest.raises(Exception) as exc_info:
            await _validate_hmac(uuid4(), body, sig, ts, mock_session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_no_webhook_secret_configured(self, mock_session, mock_workspace, conv_id):
        """Missing webhook_secret in workspace settings raises 401."""
        mock_workspace.settings = {"handoff": {"webhook_url": "https://example.com"}}
        body = json.dumps({"conversation_id": str(conv_id)}).encode()
        sig, ts = _sign_request(body)
        with pytest.raises(Exception) as exc_info:
            await _validate_hmac(conv_id, body, sig, ts, mock_session)
        assert exc_info.value.status_code == 401
        assert "secret not configured" in str(exc_info.value.detail)


# ── POST /reply Tests ───────────────────────────────────────────────


class TestHandoffReply:
    """Test POST /api/v1/handoff/reply (7.16)."""

    @pytest.mark.asyncio
    async def test_reply_success(self, mock_session, conv_id):
        """Valid reply is relayed to user."""
        body_dict = {
            "conversation_id": str(conv_id),
            "message": "Hello, I can help with that!",
            "agent_name": "Agent Smith",
        }
        body = json.dumps(body_dict).encode()
        sig, ts = _sign_request(body)
        request = _make_request(body, sig, ts)

        with patch("app.api.handoff.HandoffService") as MockService:
            svc_instance = MockService.return_value
            svc_instance.handle_agent_reply = AsyncMock(return_value=HandoffResult(success=True))

            result = await handoff_reply(request=request, db=mock_session)

        assert result["status"] == "ok"
        assert result["message"] == "Reply delivered"
        svc_instance.handle_agent_reply.assert_awaited_once_with(
            conversation_id=conv_id,
            message="Hello, I can help with that!",
            agent_name="Agent Smith",
            session=mock_session,
        )

    @pytest.mark.asyncio
    async def test_reply_invalid_json(self, mock_session):
        """Invalid JSON returns 400."""
        request = _make_request(b"not-json", "sig", "123")

        with pytest.raises(Exception) as exc_info:
            await handoff_reply(request=request, db=mock_session)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_reply_service_failure(self, mock_session, conv_id):
        """Service failure returns 400."""
        body_dict = {"conversation_id": str(conv_id), "message": "help"}
        body = json.dumps(body_dict).encode()
        sig, ts = _sign_request(body)
        request = _make_request(body, sig, ts)

        with patch("app.api.handoff.HandoffService") as MockService:
            svc_instance = MockService.return_value
            svc_instance.handle_agent_reply = AsyncMock(
                return_value=HandoffResult(success=False, error="Conversation not escalated")
            )

            with pytest.raises(Exception) as exc_info:
                await handoff_reply(request=request, db=mock_session)
            assert exc_info.value.status_code == 400


# ── POST /resolve Tests ─────────────────────────────────────────────


class TestHandoffResolveExternal:
    """Test POST /api/v1/handoff/resolve (7.17)."""

    @pytest.mark.asyncio
    async def test_resolve_success(self, mock_session, conv_id):
        """Valid resolve request transitions conversation."""
        body_dict = {
            "conversation_id": str(conv_id),
            "resolution_note": "Issue was a billing error, refunded.",
        }
        body = json.dumps(body_dict).encode()
        sig, ts = _sign_request(body)
        request = _make_request(body, sig, ts)

        with patch("app.api.handoff.HandoffService") as MockService:
            svc_instance = MockService.return_value
            svc_instance.resolve = AsyncMock(return_value=HandoffResult(success=True))

            result = await handoff_resolve_external(request=request, db=mock_session)

        assert result["status"] == "ok"
        svc_instance.resolve.assert_awaited_once_with(
            conversation_id=conv_id,
            session=mock_session,
            resolution_note="Issue was a billing error, refunded.",
        )

    @pytest.mark.asyncio
    async def test_resolve_without_note(self, mock_session, conv_id):
        """Resolve works without optional resolution_note."""
        body_dict = {"conversation_id": str(conv_id)}
        body = json.dumps(body_dict).encode()
        sig, ts = _sign_request(body)
        request = _make_request(body, sig, ts)

        with patch("app.api.handoff.HandoffService") as MockService:
            svc_instance = MockService.return_value
            svc_instance.resolve = AsyncMock(return_value=HandoffResult(success=True))

            result = await handoff_resolve_external(request=request, db=mock_session)

        assert result["status"] == "ok"
        svc_instance.resolve.assert_awaited_once_with(
            conversation_id=conv_id,
            session=mock_session,
            resolution_note=None,
        )


# ── GET /status Tests ───────────────────────────────────────────────


class TestHandoffStatus:
    """Test GET /api/v1/handoff/status/{conversation_id} (7.18)."""

    @pytest.mark.asyncio
    async def test_status_escalated(self, mock_session, mock_conversation, conv_id, workspace_id):
        """Returns full handoff state for escalated conversation."""
        from datetime import UTC, datetime

        mock_event = MagicMock()
        mock_event.event_type = "escalated"
        mock_event.actor = "system"
        mock_event.payload = {"reason": {"rule_type": "manual"}}
        mock_event.created_at = datetime(2026, 2, 15, 10, 0, 0, tzinfo=UTC)

        # First execute: conversation query (scalar_one_or_none)
        conv_result = MagicMock()
        conv_result.scalar_one_or_none.return_value = mock_conversation
        # Second execute: events query (scalars().all())
        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [mock_event]
        mock_session.execute = AsyncMock(side_effect=[conv_result, events_result])

        user = MagicMock()
        user.email = "admin@example.com"
        current_user = (user, workspace_id, "admin")

        result = await handoff_status(
            conversation_id=conv_id,
            current_user=current_user,
            db=mock_session,
        )

        assert result.status == "escalated"
        assert result.escalated_at == "2026-02-15T10:00:00+00:00"
        assert result.external_ticket_id == "EXT-123"
        assert len(result.events) == 1
        assert result.events[0]["event_type"] == "escalated"

    @pytest.mark.asyncio
    async def test_status_not_found(self, mock_session, workspace_id):
        """Returns 404 for unknown conversation."""
        conv_result = MagicMock()
        conv_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=conv_result)

        user = MagicMock()
        current_user = (user, workspace_id, "admin")

        with pytest.raises(Exception) as exc_info:
            await handoff_status(
                conversation_id=uuid4(),
                current_user=current_user,
                db=mock_session,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_status_wrong_workspace(self, mock_session, mock_conversation, conv_id):
        """Returns 404 when conversation belongs to different workspace."""
        # select().where() with wrong workspace_id returns None
        conv_result = MagicMock()
        conv_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=conv_result)

        user = MagicMock()
        other_workspace = uuid4()
        current_user = (user, other_workspace, "admin")

        with pytest.raises(Exception) as exc_info:
            await handoff_status(
                conversation_id=conv_id,
                current_user=current_user,
                db=mock_session,
            )
        assert exc_info.value.status_code == 404


# ── POST /escalate Tests ────────────────────────────────────────────


class TestHandoffEscalateManual:
    """Test POST /api/v1/handoff/escalate/{conversation_id} (7.19)."""

    @pytest.mark.asyncio
    async def test_manual_escalate_success(self, mock_session, conv_id, workspace_id):
        """Manual escalation triggers HandoffService.escalate()."""
        conv = MagicMock(spec=Conversation)
        conv.id = conv_id
        conv.workspace_id = workspace_id
        conv.status = "active"
        conv_result = MagicMock()
        conv_result.scalar_one_or_none.return_value = conv
        mock_session.execute = AsyncMock(return_value=conv_result)

        user = MagicMock()
        user.email = "admin@example.com"
        current_user = (user, workspace_id, "admin")

        with patch("app.api.handoff.HandoffService") as MockService:
            svc_instance = MockService.return_value
            svc_instance.escalate = AsyncMock(
                return_value=HandoffResult(success=True, external_ticket_id="EXT-456")
            )

            result = await handoff_escalate_manual(
                conversation_id=conv_id,
                current_user=current_user,
                db=mock_session,
            )

        assert result["status"] == "ok"
        assert result["external_ticket_id"] == "EXT-456"
        svc_instance.escalate.assert_awaited_once_with(
            conversation_id=conv_id,
            workspace_id=workspace_id,
            reason={"rule_type": "manual", "triggered_by": "admin@example.com"},
            session=mock_session,
        )

    @pytest.mark.asyncio
    async def test_manual_escalate_already_escalated(
        self, mock_session, mock_conversation, conv_id, workspace_id
    ):
        """Returns 409 if conversation is already escalated."""
        mock_conversation.status = "escalated"
        conv_result = MagicMock()
        conv_result.scalar_one_or_none.return_value = mock_conversation
        mock_session.execute = AsyncMock(return_value=conv_result)

        user = MagicMock()
        user.email = "admin@example.com"
        current_user = (user, workspace_id, "admin")

        with pytest.raises(Exception) as exc_info:
            await handoff_escalate_manual(
                conversation_id=conv_id,
                current_user=current_user,
                db=mock_session,
            )
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_manual_escalate_not_found(self, mock_session, workspace_id):
        """Returns 404 for unknown conversation."""
        conv_result = MagicMock()
        conv_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=conv_result)

        user = MagicMock()
        current_user = (user, workspace_id, "admin")

        with pytest.raises(Exception) as exc_info:
            await handoff_escalate_manual(
                conversation_id=uuid4(),
                current_user=current_user,
                db=mock_session,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_manual_escalate_service_failure(self, mock_session, conv_id, workspace_id):
        """Returns 400 when service fails."""
        conv = MagicMock(spec=Conversation)
        conv.id = conv_id
        conv.workspace_id = workspace_id
        conv.status = "active"
        conv_result = MagicMock()
        conv_result.scalar_one_or_none.return_value = conv
        mock_session.execute = AsyncMock(return_value=conv_result)

        user = MagicMock()
        user.email = "admin@example.com"
        current_user = (user, workspace_id, "admin")

        with patch("app.api.handoff.HandoffService") as MockService:
            svc_instance = MockService.return_value
            svc_instance.escalate = AsyncMock(
                return_value=HandoffResult(
                    success=False, error="Handoff not configured for this workspace"
                )
            )

            with pytest.raises(Exception) as exc_info:
                await handoff_escalate_manual(
                    conversation_id=conv_id,
                    current_user=current_user,
                    db=mock_session,
                )
            assert exc_info.value.status_code == 400
