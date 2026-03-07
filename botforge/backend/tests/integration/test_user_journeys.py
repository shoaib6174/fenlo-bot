"""Integration tests for user journeys.

Tests simulate complete user workflows across multiple API endpoints:
- Journey 1: New workspace setup + onboarding
- Journey 2: Daily analytics review
- Journey 3: Escalation handling (inbox)
- Journey 4: GDPR data request (export + purge)
- Journey 5: Voice channel deployment
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.main import app
from app.models.channel import ChannelConfig
from app.models.conversation import Conversation, Message
from app.models.knowledge_base import Document, KnowledgeBase
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.services.auth import create_access_token, hash_password

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def journey_client(db_session: AsyncSession):
    """Test client with DB override for journey tests."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            follow_redirects=True,
        ) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def journey_user(db_session: AsyncSession):
    """Create owner user with workspace for journey tests."""
    user = User(
        id=uuid.uuid4(),
        email="journey@test.com",
        password_hash=hash_password("password123"),
        name="Journey User",
    )
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(
        id=uuid.uuid4(),
        owner_id=user.id,
        name="Journey Workspace",
    )
    db_session.add(workspace)
    await db_session.flush()

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner",
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(user)

    user.workspace_id = workspace.id
    return user


@pytest_asyncio.fixture
async def journey_token(journey_user: User):
    """Auth token for journey user."""
    return create_access_token(
        user_id=journey_user.id,
        workspace_id=journey_user.workspace_id,
        role="owner",
    )


@pytest_asyncio.fixture
async def seeded_analytics_data(db_session: AsyncSession, journey_user: User):
    """Seed conversations + messages for analytics journey tests."""
    workspace_id = journey_user.workspace_id
    base_time = datetime.now(UTC) - timedelta(days=3)

    conversations = []
    for i in range(10):
        conv = Conversation(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            channel=["web", "whatsapp", "voice"][i % 3],
            status="active" if i < 8 else "escalated",
            lead_score=float(i),
            started_at=base_time + timedelta(hours=i),
        )
        db_session.add(conv)
        await db_session.flush()
        conversations.append(conv)

        for j in range(5):
            msg = Message(
                id=uuid.uuid4(),
                conversation_id=conv.id,
                role="user" if j % 2 == 0 else "assistant",
                content=f"Message {j} in conversation {i}",
                sentiment=["positive", "neutral", "negative"][j % 3],
                intent=["faq", "sales", "support"][j % 3],
                quality_score=0.7 + (j * 0.05),
                created_at=base_time + timedelta(hours=i, minutes=j),
            )
            db_session.add(msg)

    await db_session.commit()
    return conversations


@pytest_asyncio.fixture
async def seeded_workspace_data(
    db_session: AsyncSession, journey_user: User, seeded_analytics_data
):
    """Full workspace data: conversations + documents + channels + KBs."""
    workspace_id = journey_user.workspace_id

    kb = KnowledgeBase(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        name="Test KB",
    )
    db_session.add(kb)
    await db_session.flush()

    doc = Document(
        id=uuid.uuid4(),
        kb_id=kb.id,
        workspace_id=workspace_id,
        filename="test.pdf",
        file_type="pdf",
        file_size=1024,
        status="processed",
    )
    db_session.add(doc)

    channel = ChannelConfig(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        channel="widget",
        config={"enabled": True},
        is_active=True,
    )
    db_session.add(channel)
    await db_session.commit()

    return {"kb": kb, "doc": doc, "channel": channel}


# ── Journey 1: Onboarding ────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestJourney1Onboarding:
    """Simulate onboarding wizard flow."""

    async def test_onboarding_progress_starts_at_zero(self, journey_client, journey_token):
        """GET /onboarding/progress returns initial state."""
        response = await journey_client.get(
            "/api/v1/onboarding/progress",
            cookies={"access_token": journey_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["completion_pct"] == 0
        assert data["current_step"] == "personality"
        assert data["completed_at"] is None

    async def test_complete_steps_in_order(self, journey_client, journey_token):
        """Steps advance in sequence: personality → first_document → test_chat → deploy_channel."""
        steps = ["personality", "first_document", "test_chat", "deploy_channel"]
        for step in steps:
            response = await journey_client.put(
                f"/api/v1/onboarding/step/{step}",
                cookies={"access_token": journey_token},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["step"] == step

    async def test_complete_onboarding_sets_completed_at(self, journey_client, journey_token):
        """POST /onboarding/complete marks onboarding as done."""
        # Complete all steps first
        for step in ["personality", "first_document", "test_chat", "deploy_channel"]:
            await journey_client.put(
                f"/api/v1/onboarding/step/{step}",
                cookies={"access_token": journey_token},
            )

        response = await journey_client.post(
            "/api/v1/onboarding/complete",
            cookies={"access_token": journey_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["completed_at"] is not None
        assert data["completion_pct"] == 100

    async def test_settings_update_for_personality(self, journey_client, journey_token):
        """PUT /settings updates bot personality (part of step 1)."""
        response = await journey_client.put(
            "/api/v1/settings",
            cookies={"access_token": journey_token},
            json={"system_prompt": "You are a helpful assistant", "bot_name": "TestBot"},
        )
        assert response.status_code == 200

    async def test_skip_onboarding(self, journey_client, journey_token):
        """POST /onboarding/skip allows skipping."""
        response = await journey_client.post(
            "/api/v1/onboarding/skip",
            cookies={"access_token": journey_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ── Journey 2: Analytics Review ───────────────────────────────────────────────


@pytest.mark.asyncio
class TestJourney2AnalyticsReview:
    """Simulate admin reviewing analytics dashboard."""

    async def test_analytics_overview_with_data(
        self, journey_client, journey_token, seeded_analytics_data
    ):
        """GET /analytics/overview returns aggregated metrics."""
        response = await journey_client.get(
            "/api/v1/analytics/overview",
            cookies={"access_token": journey_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_conversations"] == 10
        assert data["total_messages"] == 50
        assert "sentiment_distribution" in data

    async def test_analytics_volume(self, journey_client, journey_token, seeded_analytics_data):
        """GET /analytics/volume returns time series."""
        response = await journey_client.get(
            "/api/v1/analytics/volume",
            cookies={"access_token": journey_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "date" in data[0]
        assert "message_count" in data[0]

    async def test_analytics_top_questions(
        self, journey_client, journey_token, seeded_analytics_data
    ):
        """GET /analytics/top-questions returns ranked questions."""
        response = await journey_client.get(
            "/api/v1/analytics/top-questions?limit=5",
            cookies={"access_token": journey_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_analytics_sentiment(self, journey_client, journey_token, seeded_analytics_data):
        """GET /analytics/sentiment returns sentiment breakdown."""
        response = await journey_client.get(
            "/api/v1/analytics/sentiment",
            cookies={"access_token": journey_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_analytics_channels(self, journey_client, journey_token, seeded_analytics_data):
        """GET /analytics/channels returns per-channel breakdown."""
        response = await journey_client.get(
            "/api/v1/analytics/channels",
            cookies={"access_token": journey_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    async def test_csv_export(self, journey_client, journey_token, seeded_analytics_data):
        """GET /export/conversations/csv returns CSV file."""
        response = await journey_client.get(
            "/api/v1/export/conversations/csv",
            cookies={"access_token": journey_token},
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        content = response.text
        assert "conversation_id" in content  # CSV header


# ── Journey 3: Escalation Handling ────────────────────────────────────────────


@pytest.mark.asyncio
class TestJourney3EscalationHandling:
    """Simulate agent handling escalated conversations via inbox."""

    async def test_inbox_list_escalated(self, journey_client, journey_token, seeded_analytics_data):
        """GET /inbox/conversations?status=escalated returns escalated items."""
        response = await journey_client.get(
            "/api/v1/inbox/conversations?status=escalated",
            cookies={"access_token": journey_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # We seeded 2 escalated conversations
        assert len(data) == 2

    async def test_inbox_get_conversation_detail(
        self, journey_client, journey_token, seeded_analytics_data
    ):
        """GET /inbox/conversations/{id} returns full conversation."""
        # Get escalated conversation ID
        list_resp = await journey_client.get(
            "/api/v1/inbox/conversations?status=escalated",
            cookies={"access_token": journey_token},
        )
        conversations = list_resp.json()
        if not conversations:
            pytest.skip("No escalated conversations seeded")

        conv_id = conversations[0]["id"]
        response = await journey_client.get(
            f"/api/v1/inbox/conversations/{conv_id}",
            cookies={"access_token": journey_token},
        )
        assert response.status_code == 200


# ── Journey 4: GDPR Data Request ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestJourney4GDPRRequest:
    """Simulate GDPR export and purge flow."""

    async def test_storage_usage_shows_counts(
        self, journey_client, journey_token, journey_user, seeded_workspace_data
    ):
        """GET /admin/storage/{workspace_id} returns record counts."""
        response = await journey_client.get(
            f"/api/v1/admin/storage/{journey_user.workspace_id}",
            cookies={"access_token": journey_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["conversations_count"] == 10
        assert data["messages_count"] == 50
        assert data["documents_count"] == 1
        assert data["channels_count"] == 1
        assert data["knowledge_bases_count"] == 1

    async def test_workspace_export_returns_zip(
        self, journey_client, journey_token, journey_user, seeded_workspace_data
    ):
        """POST /admin/export/{workspace_id} returns ZIP file."""
        response = await journey_client.post(
            f"/api/v1/admin/export/{journey_user.workspace_id}",
            cookies={"access_token": journey_token},
        )
        assert response.status_code == 200
        assert "application/zip" in response.headers.get("content-type", "")
        assert len(response.content) > 0

    async def test_purge_deletes_all_data(
        self, journey_client, journey_token, journey_user, seeded_workspace_data
    ):
        """DELETE /admin/workspace/{workspace_id}/data purges everything."""
        response = await journey_client.delete(
            f"/api/v1/admin/workspace/{journey_user.workspace_id}/data",
            cookies={"access_token": journey_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted_records"]["messages"] >= 50
        assert data["deleted_records"]["conversations"] >= 10
        assert data["deleted_records"]["documents"] >= 1

    async def test_storage_empty_after_purge(
        self, journey_client, journey_token, journey_user, seeded_workspace_data
    ):
        """Storage shows zero counts after purge."""
        # Purge first
        await journey_client.delete(
            f"/api/v1/admin/workspace/{journey_user.workspace_id}/data",
            cookies={"access_token": journey_token},
        )

        # Check storage
        response = await journey_client.get(
            f"/api/v1/admin/storage/{journey_user.workspace_id}",
            cookies={"access_token": journey_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["conversations_count"] == 0
        assert data["messages_count"] == 0
        assert data["documents_count"] == 0


# ── Journey 5: Voice Channel ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestJourney5VoiceChannel:
    """Simulate voice channel setup flow."""

    async def test_create_channel_config(self, journey_client, journey_token):
        """POST /channels creates a voice channel config."""
        response = await journey_client.post(
            "/api/v1/channels",
            cookies={"access_token": journey_token},
            json={
                "channel": "voice",
                "config": {"vapi_assistant_id": "test_assistant"},
                "is_active": True,
            },
        )
        assert response.status_code in (200, 201)

    async def test_list_channels(self, journey_client, journey_token):
        """GET /channels returns channel list."""
        # Create a channel first
        await journey_client.post(
            "/api/v1/channels",
            cookies={"access_token": journey_token},
            json={"channel": "widget", "config": {}, "is_active": True},
        )

        response = await journey_client.get(
            "/api/v1/channels",
            cookies={"access_token": journey_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
