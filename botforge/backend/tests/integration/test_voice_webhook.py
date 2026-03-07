"""Integration tests for voice webhook endpoint."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import ChannelConfig
from app.models.conversation import Conversation
from app.models.user import User
from app.models.voice import CallLog, EscalationRule
from app.models.workspace import Workspace, WorkspaceMember
from app.services.auth import hash_password


async def _create_voice_workspace(db_session: AsyncSession) -> tuple:
    """Create a workspace with voice configured. Returns (workspace_id, assistant_id)."""
    user_id = uuid4()
    workspace_id = uuid4()
    assistant_id = f"asst_{uuid4().hex[:12]}"

    user = User(
        id=user_id,
        email=f"voice-{uuid4().hex[:6]}@test.com",
        password_hash=hash_password("password"),
        name="Voice Test User",
    )
    workspace = Workspace(id=workspace_id, owner_id=user_id, name="Voice WS")
    member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role="owner")
    channel_config = ChannelConfig(
        id=uuid4(),
        workspace_id=workspace_id,
        channel="voice",
        config={"assistant_id": assistant_id, "voice_enabled": True},
        is_active=True,
    )

    db_session.add_all([user, workspace, member])
    await db_session.flush()
    db_session.add(channel_config)
    await db_session.commit()

    return workspace_id, assistant_id


def _build_webhook_body(event_type: str, call_id: str, assistant_id: str, **extra) -> dict:
    """Build a Vapi webhook payload matching WebhookPayload schema expectations."""
    message = {
        "type": event_type,
        "assistant": {"id": assistant_id},
        "call": {
            "id": call_id,
            "assistantId": assistant_id,
            "customer": {"number": "+15551234567"},
            "phoneNumber": {"number": "+15559876543"},
            "type": "inboundPhoneCall",
        },
    }

    if event_type == "status-update":
        message["status"] = extra.get("status", "ringing")
    elif event_type == "end-of-call-report":
        message["transcript"] = extra.get("transcript", "Hello, this is a test call.")
        message["summary"] = extra.get("summary", "Test call summary")
        message["recordingUrl"] = extra.get("recording_url")
        message["endedReason"] = extra.get("ended_reason", "customer-ended-call")
        # duration_sec computed from startedAt/endedAt
        duration = extra.get("duration", 120)
        message["startedAt"] = "2026-01-15T10:00:00Z"
        message["endedAt"] = f"2026-01-15T10:{duration // 60:02d}:{duration % 60:02d}Z"
        if "analysis" in extra:
            message["analysis"] = extra["analysis"]

    return {"message": message}


@pytest.mark.asyncio
class TestVoiceWebhook:
    """Test voice webhook processing (status-update, end-of-call-report)."""

    async def test_status_update_creates_call_log(
        self, test_client: AsyncClient, db_session: AsyncSession
    ):
        """status-update event creates a CallLog and Conversation."""
        workspace_id, assistant_id = await _create_voice_workspace(db_session)
        call_id = f"call_{uuid4().hex[:12]}"

        body = _build_webhook_body("status-update", call_id, assistant_id, status="ringing")

        with patch("app.modules.voice.idempotency.get_redis_client", return_value=None):
            response = await test_client.post("/api/v1/voice/webhook", json=body)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        assert data["state"] == "ringing"

        # Verify CallLog was created
        result = await db_session.execute(select(CallLog).where(CallLog.vapi_call_id == call_id))
        call_log = result.scalar_one_or_none()
        assert call_log is not None
        assert call_log.status == "ringing"
        assert call_log.direction == "inbound"

    async def test_end_of_call_report_stores_transcript(
        self, test_client: AsyncClient, db_session: AsyncSession
    ):
        """end-of-call-report stores transcript, summary, duration."""
        workspace_id, assistant_id = await _create_voice_workspace(db_session)
        call_id = f"call_{uuid4().hex[:12]}"

        body = _build_webhook_body(
            "end-of-call-report",
            call_id,
            assistant_id,
            transcript="Customer: I need help.\nAssistant: How can I help?",
            summary="Customer requested help",
            duration=90,
        )

        with patch("app.modules.voice.idempotency.get_redis_client", return_value=None):
            response = await test_client.post("/api/v1/voice/webhook", json=body)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"

        # Verify call log has transcript
        result = await db_session.execute(select(CallLog).where(CallLog.vapi_call_id == call_id))
        call_log = result.scalar_one_or_none()
        assert call_log is not None
        assert "I need help" in call_log.transcript
        assert call_log.summary == "Customer requested help"
        assert call_log.duration_sec == 90

    async def test_duplicate_webhook_skipped(
        self, test_client: AsyncClient, db_session: AsyncSession
    ):
        """Duplicate webhook events are skipped via idempotency."""
        workspace_id, assistant_id = await _create_voice_workspace(db_session)
        call_id = f"call_{uuid4().hex[:12]}"

        body = _build_webhook_body("status-update", call_id, assistant_id, status="ringing")

        # Mock Redis to simulate duplicate on second call
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(side_effect=[True, None])  # First: new, second: dup

        with patch("app.modules.voice.idempotency.get_redis_client", return_value=mock_redis):
            resp1 = await test_client.post("/api/v1/voice/webhook", json=body)
            resp2 = await test_client.post("/api/v1/voice/webhook", json=body)

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "already_processed"

    async def test_invalid_signature_rejected(
        self, test_client: AsyncClient, db_session: AsyncSession
    ):
        """Webhook with invalid signature returns 401."""
        workspace_id, assistant_id = await _create_voice_workspace(db_session)
        call_id = f"call_{uuid4().hex[:12]}"

        body = _build_webhook_body("status-update", call_id, assistant_id)

        with (
            patch("app.api.voice.settings") as mock_settings,
            patch("app.modules.voice.idempotency.get_redis_client", return_value=None),
        ):
            mock_settings.vapi_webhook_secret = "test-secret"  # pragma: allowlist secret
            mock_settings.backend_url = "http://test"

            response = await test_client.post(
                "/api/v1/voice/webhook",
                json=body,
                headers={"x-vapi-signature": "invalid-sig"},
            )

        assert response.status_code == 401

    async def test_escalation_triggered_on_keyword(
        self, test_client: AsyncClient, db_session: AsyncSession
    ):
        """end-of-call-report triggers keyword escalation rule."""
        workspace_id, assistant_id = await _create_voice_workspace(db_session)

        # Create an escalation rule
        rule = EscalationRule(
            id=uuid4(),
            workspace_id=workspace_id,
            rule_type="keyword",
            condition={"keywords": ["speak to human"], "match_mode": "any"},
            action="escalate",
            is_active=True,
            priority=10,
        )
        db_session.add(rule)
        await db_session.commit()

        call_id = f"call_{uuid4().hex[:12]}"
        body = _build_webhook_body(
            "end-of-call-report",
            call_id,
            assistant_id,
            transcript="I want to speak to human please",
        )

        with patch("app.modules.voice.idempotency.get_redis_client", return_value=None):
            response = await test_client.post("/api/v1/voice/webhook", json=body)

        assert response.status_code == 200
        data = response.json()
        assert data.get("escalation") is not None
        assert data["escalation"]["rule_type"] == "keyword"
        assert data["escalation"]["action"] == "escalate"

        # Verify conversation was escalated
        result = await db_session.execute(select(CallLog).where(CallLog.vapi_call_id == call_id))
        call_log = result.scalar_one()
        conv_result = await db_session.execute(
            select(Conversation).where(Conversation.id == call_log.conversation_id)
        )
        conversation = conv_result.scalar_one()
        assert conversation.status == "escalated"

    async def test_call_state_transitions_correctly(
        self, test_client: AsyncClient, db_session: AsyncSession
    ):
        """Multiple status-update events transition call state correctly."""
        workspace_id, assistant_id = await _create_voice_workspace(db_session)
        call_id = f"call_{uuid4().hex[:12]}"

        with patch("app.modules.voice.idempotency.get_redis_client", return_value=None):
            # Event 1: ringing
            body1 = _build_webhook_body("status-update", call_id, assistant_id, status="ringing")
            resp1 = await test_client.post("/api/v1/voice/webhook", json=body1)
            assert resp1.json()["state"] == "ringing"

            # Event 2: in-progress (connected)
            body2 = _build_webhook_body(
                "status-update", call_id, assistant_id, status="in-progress"
            )
            resp2 = await test_client.post("/api/v1/voice/webhook", json=body2)
            assert resp2.json()["state"] == "connected"

        # Verify final state in DB
        result = await db_session.execute(select(CallLog).where(CallLog.vapi_call_id == call_id))
        call_log = result.scalar_one()
        assert call_log.status == "connected"

    async def test_webhook_resolves_workspace_from_assistant_id(
        self, test_client: AsyncClient, db_session: AsyncSession
    ):
        """Webhook resolves workspace via assistantId → channel_configs lookup."""
        workspace_id, assistant_id = await _create_voice_workspace(db_session)
        call_id = f"call_{uuid4().hex[:12]}"

        body = _build_webhook_body("status-update", call_id, assistant_id, status="ringing")

        with patch("app.modules.voice.idempotency.get_redis_client", return_value=None):
            response = await test_client.post("/api/v1/voice/webhook", json=body)

        assert response.status_code == 200

        # Verify the call was linked to the correct workspace
        result = await db_session.execute(select(CallLog).where(CallLog.vapi_call_id == call_id))
        call_log = result.scalar_one()

        conv_result = await db_session.execute(
            select(Conversation).where(Conversation.id == call_log.conversation_id)
        )
        conversation = conv_result.scalar_one()
        assert conversation.workspace_id == workspace_id
