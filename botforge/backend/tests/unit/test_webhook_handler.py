"""Unit tests for webhook handler functions (direct calls, not via ASGI)."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.voice.webhook_handler import (
    dispatch_webhook,
    handle_end_of_call_report,
    handle_status_update,
    resolve_workspace_from_webhook,
    validate_vapi_webhook,
)
from app.schemas.voice import WebhookPayload


def _make_payload(event_type: str, call_id: str, assistant_id: str, **extra) -> WebhookPayload:
    """Build a WebhookPayload for testing."""
    message = {
        "type": event_type,
        "assistant": {"id": assistant_id},
        "call": {
            "id": call_id,
            "customer": {"number": "+15551234567"},
            "phoneNumber": {"number": "+15559876543"},
            "type": "inboundPhoneCall",
        },
    }
    if event_type == "status-update":
        message["status"] = extra.get("status", "ringing")
    elif event_type == "end-of-call-report":
        message["transcript"] = extra.get("transcript", "Test transcript")
        message["summary"] = extra.get("summary", "Test summary")
        message["endedReason"] = extra.get("ended_reason", "customer-ended-call")
        message["startedAt"] = "2026-01-15T10:00:00Z"
        message["endedAt"] = "2026-01-15T10:02:00Z"
        if "analysis" in extra:
            message["analysis"] = extra["analysis"]
    return WebhookPayload(message=message)


def _mock_session_with_no_call() -> AsyncMock:
    """Create a mock session that returns no existing CallLog."""
    session = AsyncMock(spec=AsyncSession)
    # execute returns a result that returns None for scalar_one_or_none
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_result)
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
class TestHandleStatusUpdate:
    """Test handle_status_update webhook handler."""

    async def test_creates_call_log_for_new_call(self):
        """First status-update event creates CallLog and Conversation."""
        workspace_id = uuid4()
        payload = _make_payload("status-update", "call-123", "asst-abc", status="ringing")
        session = _mock_session_with_no_call()

        result = await handle_status_update(payload, workspace_id, session)

        assert result["status"] == "created"
        assert result["state"] == "ringing"
        assert session.add.call_count == 2  # Conversation + CallLog

    async def test_returns_error_for_missing_call_id(self):
        """Returns error when call_id is missing."""
        workspace_id = uuid4()
        payload = WebhookPayload(message={"type": "status-update", "status": "ringing"})
        session = AsyncMock()

        result = await handle_status_update(payload, workspace_id, session)

        assert result["status"] == "error"
        assert "no call_id" in result["detail"]

    async def test_returns_error_for_missing_status(self):
        """Returns error when status is missing."""
        workspace_id = uuid4()
        payload = WebhookPayload(
            message={
                "type": "status-update",
                "call": {"id": "call-123", "type": "inboundPhoneCall"},
            }
        )
        session = AsyncMock()

        result = await handle_status_update(payload, workspace_id, session)

        assert result["status"] == "error"
        assert "no status" in result["detail"]

    async def test_transitions_existing_call(self):
        """status-update transitions state of existing call."""
        workspace_id = uuid4()
        payload = _make_payload("status-update", "call-123", "asst-abc", status="in-progress")

        # Mock existing CallLog
        mock_call = MagicMock()
        mock_call.status = "ringing"

        session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_call
        session.execute = AsyncMock(return_value=mock_result)

        result = await handle_status_update(payload, workspace_id, session)

        assert result["status"] == "updated"
        assert result["state"] == "connected"
        assert mock_call.status == "connected"


@pytest.mark.asyncio
class TestHandleEndOfCallReport:
    """Test handle_end_of_call_report webhook handler."""

    async def test_stores_transcript_for_new_call(self):
        """end-of-call-report creates call and stores transcript when no prior CallLog exists."""
        workspace_id = uuid4()
        payload = _make_payload(
            "end-of-call-report",
            "call-456",
            "asst-xyz",
            transcript="Customer: Hello",
            summary="Greeting call",
        )
        session = _mock_session_with_no_call()

        with patch("app.modules.voice.webhook_handler._escalation_engine") as mock_engine:
            mock_engine.evaluate = AsyncMock(return_value=None)
            result = await handle_end_of_call_report(payload, workspace_id, session)

        assert result["status"] == "processed"
        assert result["escalation"] is None

    async def test_stores_sentiment_from_analysis(self):
        """Extracts sentiment from Vapi successEvaluation."""
        workspace_id = uuid4()
        payload = _make_payload(
            "end-of-call-report",
            "call-789",
            "asst-abc",
            analysis={"successEvaluation": "false"},
        )
        session = _mock_session_with_no_call()

        with patch("app.modules.voice.webhook_handler._escalation_engine") as mock_engine:
            mock_engine.evaluate = AsyncMock(return_value=None)
            result = await handle_end_of_call_report(payload, workspace_id, session)

        assert result["status"] == "processed"

    async def test_escalation_updates_call_log(self):
        """Escalation result is appended to CallLog.actions_taken."""
        workspace_id = uuid4()
        payload = _make_payload(
            "end-of-call-report",
            "call-esc",
            "asst-abc",
            transcript="I want to speak to human",
        )
        session = _mock_session_with_no_call()

        escalation_result = {
            "rule_id": str(uuid4()),
            "rule_type": "keyword",
            "action": "escalate",
            "matched": "speak to human",
        }

        # Mock Conversation lookup for escalation
        mock_conv = MagicMock()
        mock_conv.status = "active"

        # session.execute returns different results for different queries
        call_count = 0

        async def side_effect_execute(query, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                # First call: CallLog lookup
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = None
                return mock_result
            else:
                # Subsequent: Conversation lookup
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = mock_conv
                return mock_result

        session.execute = AsyncMock(side_effect=side_effect_execute)

        with (
            patch("app.modules.voice.webhook_handler._escalation_engine") as mock_engine,
            patch("app.modules.voice.webhook_handler.create_event_bus") as mock_bus_factory,
        ):
            mock_engine.evaluate = AsyncMock(return_value=escalation_result)
            mock_bus = AsyncMock()
            mock_bus_factory.return_value = mock_bus

            result = await handle_end_of_call_report(payload, workspace_id, session)

        assert result["escalation"] is not None
        assert result["escalation"]["action"] == "escalate"
        assert mock_conv.status == "escalated"

    async def test_returns_error_for_missing_call_id(self):
        """Returns error when call_id is missing."""
        workspace_id = uuid4()
        payload = WebhookPayload(message={"type": "end-of-call-report"})
        session = AsyncMock()

        result = await handle_end_of_call_report(payload, workspace_id, session)

        assert result["status"] == "error"


@pytest.mark.asyncio
class TestResolveWorkspace:
    """Test workspace resolution from webhook payload."""

    async def test_no_assistant_id_returns_none(self):
        """Returns None when assistant_id is missing."""
        payload = WebhookPayload(message={"type": "status-update"})
        session = AsyncMock()

        result = await resolve_workspace_from_webhook(payload, session)
        assert result is None

    async def test_unknown_assistant_returns_none(self):
        """Returns None when assistant_id not found in channel_configs."""
        payload = _make_payload("status-update", "call-1", "asst-unknown")
        session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await resolve_workspace_from_webhook(payload, session)
        assert result is None


@pytest.mark.asyncio
class TestDispatchWebhook:
    """Test webhook event dispatch."""

    async def test_dispatches_status_update(self):
        """status-update events are dispatched to handle_status_update."""
        workspace_id = uuid4()
        payload = _make_payload("status-update", "call-d1", "asst-d1", status="ringing")
        session = _mock_session_with_no_call()

        result = await dispatch_webhook(payload, workspace_id, session)
        assert result["status"] == "created"

    async def test_dispatches_end_of_call_report(self):
        """end-of-call-report events are dispatched to handle_end_of_call_report."""
        workspace_id = uuid4()
        payload = _make_payload("end-of-call-report", "call-d2", "asst-d2")
        session = _mock_session_with_no_call()

        with patch("app.modules.voice.webhook_handler._escalation_engine") as mock_engine:
            mock_engine.evaluate = AsyncMock(return_value=None)
            result = await dispatch_webhook(payload, workspace_id, session)

        assert result["status"] == "processed"

    async def test_unhandled_event_returns_ignored(self):
        """Unrecognized event types return ignored."""
        workspace_id = uuid4()
        payload = WebhookPayload(message={"type": "unknown-event"})
        session = AsyncMock()

        result = await dispatch_webhook(payload, workspace_id, session)
        assert result["status"] == "ignored"


@pytest.mark.asyncio
class TestValidateWebhook:
    """Test webhook signature validation."""

    async def test_missing_signature_returns_false(self):
        """Returns False when x-vapi-signature header is missing."""
        mock_request = MagicMock()
        mock_request.headers = {}

        result = await validate_vapi_webhook(mock_request, "secret")
        assert result is False

    async def test_valid_signature_returns_true(self):
        """Returns True for valid HMAC-SHA256 signature."""
        import hashlib
        import hmac

        body = b'{"test": true}'
        secret = "test-secret"  # pragma: allowlist secret
        expected_sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        mock_request = MagicMock()
        mock_request.headers = {"x-vapi-signature": expected_sig}
        mock_request.body = AsyncMock(return_value=body)

        result = await validate_vapi_webhook(mock_request, secret)
        assert result is True

    async def test_invalid_signature_returns_false(self):
        """Returns False for invalid signature."""
        mock_request = MagicMock()
        mock_request.headers = {"x-vapi-signature": "bad-sig"}
        mock_request.body = AsyncMock(return_value=b'{"test": true}')

        result = await validate_vapi_webhook(mock_request, "secret")
        assert result is False
