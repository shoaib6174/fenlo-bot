"""Integration tests for voice API endpoints (calls, escalation rules)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import ChannelConfig
from app.models.conversation import Conversation
from app.models.user import User
from app.models.voice import CallLog, EscalationRule
from app.models.workspace import Workspace, WorkspaceMember
from app.services.auth import create_access_token, hash_password


async def _create_workspace_with_voice(db_session: AsyncSession) -> tuple:
    """Create workspace + user + voice config. Returns (user_id, workspace_id, token)."""
    user_id = uuid4()
    workspace_id = uuid4()

    user = User(
        id=user_id,
        email=f"voice-api-{uuid4().hex[:6]}@test.com",
        password_hash=hash_password("password"),
        name="Voice API User",
    )
    workspace = Workspace(id=workspace_id, owner_id=user_id, name="Voice API WS")
    member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role="owner")
    channel_config = ChannelConfig(
        id=uuid4(),
        workspace_id=workspace_id,
        channel="voice",
        config={
            "assistant_id": f"asst_{uuid4().hex[:12]}",
            "public_key": "pk-test-12345",
            "voice_enabled": True,
        },
        is_active=True,
    )

    db_session.add_all([user, workspace, member])
    await db_session.flush()
    db_session.add(channel_config)
    await db_session.commit()

    token = create_access_token(user_id=user_id, workspace_id=workspace_id, role="owner")
    return user_id, workspace_id, token


async def _create_call(
    db_session: AsyncSession,
    workspace_id,
    *,
    direction: str = "inbound",
    duration: int | None = 120,
    sentiment: str | None = "neutral",
    actions_taken: list | None = None,
) -> CallLog:
    """Create a CallLog with linked Conversation."""
    conversation = Conversation(
        id=uuid4(),
        workspace_id=workspace_id,
        channel="voice",
        external_id=f"call_{uuid4().hex[:12]}",
        status="active",
        contact_info={"phone": "+15551234567"},
        started_at=datetime.now(UTC),
    )
    db_session.add(conversation)
    await db_session.flush()

    call_log = CallLog(
        id=uuid4(),
        conversation_id=conversation.id,
        vapi_call_id=f"vapi_{uuid4().hex[:12]}",
        direction=direction,
        phone_from="+15551234567",
        phone_to="+15559876543",
        status="ended",
        duration_sec=duration,
        sentiment=sentiment,
        transcript="Test transcript",
        summary="Test summary",
        actions_taken=actions_taken,
        created_at=datetime.now(UTC),
    )
    db_session.add(call_log)
    await db_session.commit()
    await db_session.refresh(call_log)
    return call_log


@pytest.mark.asyncio
class TestVoiceAPI:
    """Test voice call management and escalation rule CRUD endpoints."""

    async def test_list_calls_workspace_scoped(
        self, test_client: AsyncClient, db_session: AsyncSession
    ):
        """GET /calls returns only calls from the current workspace."""
        _, workspace_id, token = await _create_workspace_with_voice(db_session)

        # Create 3 calls
        for _ in range(3):
            await _create_call(db_session, workspace_id)

        response = await test_client.get(
            "/api/v1/voice/calls",
            cookies={"access_token": token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["calls"]) == 3
        assert data["page"] == 1

    async def test_get_call_detail(self, test_client: AsyncClient, db_session: AsyncSession):
        """GET /calls/{call_id} returns full call detail."""
        _, workspace_id, token = await _create_workspace_with_voice(db_session)
        call = await _create_call(db_session, workspace_id, sentiment="positive")

        response = await test_client.get(
            f"/api/v1/voice/calls/{call.id}",
            cookies={"access_token": token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(call.id)
        assert data["transcript"] == "Test transcript"
        assert data["sentiment"] == "positive"

    async def test_call_stats_aggregation(self, test_client: AsyncClient, db_session: AsyncSession):
        """GET /calls/stats returns correct aggregated metrics."""
        _, workspace_id, token = await _create_workspace_with_voice(db_session)

        # Create calls with different sentiments
        await _create_call(db_session, workspace_id, sentiment="positive", duration=60)
        await _create_call(db_session, workspace_id, sentiment="negative", duration=120)
        await _create_call(
            db_session,
            workspace_id,
            sentiment="negative",
            duration=180,
            actions_taken=[{"action": "escalate", "rule_type": "keyword"}],
        )

        response = await test_client.get(
            "/api/v1/voice/calls/stats",
            cookies={"access_token": token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_calls"] == 3
        assert data["avg_duration_sec"] == 120.0
        assert data["sentiment_distribution"]["positive"] == 1
        assert data["sentiment_distribution"]["negative"] == 2
        # 1 out of 3 calls has escalation action
        assert abs(data["escalation_rate"] - 0.333) < 0.01

    async def test_create_escalation_rule(self, test_client: AsyncClient, db_session: AsyncSession):
        """POST /escalation-rules creates a rule with valid condition schema."""
        _, workspace_id, token = await _create_workspace_with_voice(db_session)

        response = await test_client.post(
            "/api/v1/voice/escalation-rules",
            cookies={"access_token": token},
            json={
                "rule_type": "keyword",
                "condition": {"keywords": ["help", "agent"], "match_mode": "any"},
                "action": "escalate",
                "priority": 10,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["rule_type"] == "keyword"
        assert data["action"] == "escalate"
        assert data["priority"] == 10

    async def test_update_escalation_rule(self, test_client: AsyncClient, db_session: AsyncSession):
        """PATCH /escalation-rules/{rule_id} updates rule fields."""
        _, workspace_id, token = await _create_workspace_with_voice(db_session)

        rule = EscalationRule(
            id=uuid4(),
            workspace_id=workspace_id,
            rule_type="keyword",
            condition={"keywords": ["help"]},
            action="log",
            is_active=True,
            priority=5,
        )
        db_session.add(rule)
        await db_session.commit()

        response = await test_client.patch(
            f"/api/v1/voice/escalation-rules/{rule.id}",
            cookies={"access_token": token},
            json={"action": "escalate", "priority": 20},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "escalate"
        assert data["priority"] == 20

    async def test_delete_escalation_rule(self, test_client: AsyncClient, db_session: AsyncSession):
        """DELETE /escalation-rules/{rule_id} removes the rule."""
        _, workspace_id, token = await _create_workspace_with_voice(db_session)

        rule = EscalationRule(
            id=uuid4(),
            workspace_id=workspace_id,
            rule_type="sentiment",
            condition={"threshold": "negative"},
            action="notify",
            is_active=True,
            priority=1,
        )
        db_session.add(rule)
        await db_session.commit()

        response = await test_client.delete(
            f"/api/v1/voice/escalation-rules/{rule.id}",
            cookies={"access_token": token},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

        # Verify rule is gone
        list_resp = await test_client.get(
            "/api/v1/voice/escalation-rules",
            cookies={"access_token": token},
        )
        assert len(list_resp.json()) == 0

    async def test_calls_workspace_isolated(
        self, test_client: AsyncClient, db_session: AsyncSession
    ):
        """Workspace A calls don't appear in workspace B listing."""
        # Create workspace A with calls
        _, ws_a_id, token_a = await _create_workspace_with_voice(db_session)
        await _create_call(db_session, ws_a_id)
        await _create_call(db_session, ws_a_id)

        # Create workspace B (no calls)
        user_b_id = uuid4()
        ws_b_id = uuid4()
        user_b = User(
            id=user_b_id,
            email=f"ws-b-{uuid4().hex[:6]}@test.com",
            password_hash=hash_password("password"),
            name="WS B User",
        )
        ws_b = Workspace(id=ws_b_id, owner_id=user_b_id, name="WS B")
        member_b = WorkspaceMember(workspace_id=ws_b_id, user_id=user_b_id, role="owner")
        db_session.add_all([user_b, ws_b, member_b])
        await db_session.commit()

        token_b = create_access_token(user_id=user_b_id, workspace_id=ws_b_id, role="owner")

        # Workspace A should see 2 calls
        resp_a = await test_client.get(
            "/api/v1/voice/calls",
            cookies={"access_token": token_a},
        )
        assert resp_a.json()["total"] == 2

        # Workspace B should see 0 calls
        resp_b = await test_client.get(
            "/api/v1/voice/calls",
            cookies={"access_token": token_b},
        )
        assert resp_b.json()["total"] == 0
