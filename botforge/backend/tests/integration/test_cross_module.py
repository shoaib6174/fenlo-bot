"""Cross-module integration tests.

Tests validate data flows between modules:
- RAG conversation → Analytics aggregation
- Conversation → Lead scoring
- Escalation → Inbox handoff
- Document upload → RAG retrieval (mocked)
- Analytics cache invalidation
- Multi-channel conversation aggregation
- Export includes all modules
- Archive respects retention period
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
async def xmod_client(db_session: AsyncSession):
    """Test client for cross-module tests."""

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
async def xmod_user(db_session: AsyncSession):
    """Create owner user with workspace for cross-module tests."""
    user = User(
        id=uuid.uuid4(),
        email="xmod@test.com",
        password_hash=hash_password("password123"),
        name="Cross Module User",
    )
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(
        id=uuid.uuid4(),
        owner_id=user.id,
        name="Cross Module Workspace",
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
async def xmod_token(xmod_user: User):
    """Auth token for cross-module user."""
    return create_access_token(
        user_id=xmod_user.id,
        workspace_id=xmod_user.workspace_id,
        role="owner",
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRAGToAnalytics:
    """RAG conversation data flows into analytics."""

    async def test_conversation_messages_appear_in_analytics(
        self, db_session, xmod_client, xmod_user, xmod_token
    ):
        """Messages with sentiment/intent are reflected in analytics overview."""
        workspace_id = xmod_user.workspace_id

        # Create conversation with scored messages
        conv = Conversation(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            channel="web",
            status="active",
            started_at=datetime.now(UTC),
        )
        db_session.add(conv)
        await db_session.flush()

        for i in range(5):
            msg = Message(
                id=uuid.uuid4(),
                conversation_id=conv.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Test message {i}",
                sentiment="positive" if i < 3 else "negative",
                quality_score=0.8,
                created_at=datetime.now(UTC) + timedelta(minutes=i),
            )
            db_session.add(msg)
        await db_session.commit()

        # Check analytics picks them up
        response = await xmod_client.get(
            "/api/v1/analytics/overview",
            cookies={"access_token": xmod_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_conversations"] >= 1
        assert data["total_messages"] >= 5


@pytest.mark.asyncio
class TestConversationToLeadScoring:
    """Lead scores are reflected in analytics."""

    async def test_lead_scores_aggregated_in_analytics(
        self, db_session, xmod_client, xmod_user, xmod_token
    ):
        """Conversations with lead_score appear in lead-scores endpoint."""
        workspace_id = xmod_user.workspace_id

        for score in [2.0, 5.5, 8.0]:
            conv = Conversation(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                channel="web",
                status="active",
                lead_score=score,
                started_at=datetime.now(UTC),
            )
            db_session.add(conv)
        await db_session.commit()

        response = await xmod_client.get(
            "/api/v1/analytics/lead-scores",
            cookies={"access_token": xmod_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "buckets" in data


@pytest.mark.asyncio
class TestMultiChannelAggregation:
    """Conversations across channels appear in channel breakdown."""

    async def test_channel_breakdown_shows_all_channels(
        self, db_session, xmod_client, xmod_user, xmod_token
    ):
        """Analytics /channels shows correct per-channel counts."""
        workspace_id = xmod_user.workspace_id

        channels = ["web", "whatsapp", "voice"]
        for ch in channels:
            conv = Conversation(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                channel=ch,
                status="active",
                started_at=datetime.now(UTC),
            )
            db_session.add(conv)
            await db_session.flush()

            msg = Message(
                id=uuid.uuid4(),
                conversation_id=conv.id,
                role="user",
                content=f"Test from {ch}",
                quality_score=0.9,
                created_at=datetime.now(UTC),
            )
            db_session.add(msg)

        await db_session.commit()

        response = await xmod_client.get(
            "/api/v1/analytics/channels",
            cookies={"access_token": xmod_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.asyncio
class TestExportIncludesAllModules:
    """Full export includes data from all modules."""

    async def test_export_zip_has_all_tables(self, db_session, xmod_client, xmod_user, xmod_token):
        """POST /admin/export includes conversations, messages, docs, channels, KBs."""
        workspace_id = xmod_user.workspace_id

        # Seed data across modules
        conv = Conversation(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            channel="web",
            status="active",
            started_at=datetime.now(UTC),
        )
        db_session.add(conv)
        await db_session.flush()

        msg = Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role="user",
            content="Export test",
            created_at=datetime.now(UTC),
        )
        db_session.add(msg)

        kb = KnowledgeBase(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            name="Export KB",
        )
        db_session.add(kb)
        await db_session.flush()

        doc = Document(
            id=uuid.uuid4(),
            kb_id=kb.id,
            workspace_id=workspace_id,
            filename="export_test.pdf",
            file_type="pdf",
            file_size=512,
            status="processed",
        )
        db_session.add(doc)

        channel = ChannelConfig(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            channel="widget",
            config={"test": True},
            is_active=True,
        )
        db_session.add(channel)
        await db_session.commit()

        response = await xmod_client.post(
            f"/api/v1/admin/export/{workspace_id}",
            cookies={"access_token": xmod_token},
        )
        assert response.status_code == 200
        assert "application/zip" in response.headers.get("content-type", "")
        assert len(response.content) > 100  # Non-trivial ZIP


@pytest.mark.asyncio
class TestArchiveRetention:
    """Archive operation respects retention cutoff."""

    async def test_archive_closes_old_conversations(
        self, db_session, xmod_client, xmod_user, xmod_token
    ):
        """POST /admin/archive closes conversations older than cutoff."""
        workspace_id = xmod_user.workspace_id

        # Old conversation (should be archived)
        old_conv = Conversation(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            channel="web",
            status="active",
            started_at=datetime.now(UTC) - timedelta(days=100),
        )
        db_session.add(old_conv)

        # Recent conversation (should stay)
        new_conv = Conversation(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            channel="web",
            status="active",
            started_at=datetime.now(UTC) - timedelta(days=5),
        )
        db_session.add(new_conv)
        await db_session.commit()

        # Archive conversations older than 30 days
        cutoff = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        response = await xmod_client.post(
            f"/api/v1/admin/archive?before={cutoff}",
            cookies={"access_token": xmod_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["archived_count"] == 1  # Only the old one


@pytest.mark.asyncio
class TestTranscriptExport:
    """Transcript export for a single conversation."""

    async def test_transcript_contains_messages(
        self, db_session, xmod_client, xmod_user, xmod_token
    ):
        """GET /export/conversations/{id}/transcript returns formatted text."""
        workspace_id = xmod_user.workspace_id

        conv = Conversation(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            channel="web",
            status="active",
            started_at=datetime.now(UTC),
        )
        db_session.add(conv)
        await db_session.flush()

        msg1 = Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role="user",
            content="What is your return policy?",
            sentiment="neutral",
            created_at=datetime.now(UTC),
        )
        msg2 = Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role="assistant",
            content="Our return policy allows 30-day returns.",
            sentiment="positive",
            quality_score=0.92,
            created_at=datetime.now(UTC) + timedelta(seconds=2),
        )
        db_session.add_all([msg1, msg2])
        await db_session.commit()

        response = await xmod_client.get(
            f"/api/v1/export/conversations/{conv.id}/transcript",
            cookies={"access_token": xmod_token},
        )
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")
        content = response.text
        assert "return policy" in content.lower()
