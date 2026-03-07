"""Integration tests for Dashboard API endpoints.

Tests cover:
- GET /api/v1/dashboard/summary (real data with conversations/messages/docs)
"""

import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.main import app
from app.models.conversation import Conversation, Message
from app.models.knowledge_base import KnowledgeBase, KnowledgeGap
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.services.auth import create_access_token, hash_password


@pytest_asyncio.fixture
async def dash_client(db_session: AsyncSession):
    """Test client with DB override for dashboard tests."""

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
async def dash_user(db_session: AsyncSession):
    """Create a user with workspace for dashboard tests."""
    user = User(
        id=uuid.uuid4(),
        email="dash@test.com",
        password_hash=hash_password("password123"),
        name="Dashboard User",
    )
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(
        id=uuid.uuid4(),
        owner_id=user.id,
        name="Dashboard Workspace",
        features={"rag_enabled": True},
        settings={},
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
async def dash_token(dash_user: User):
    """Create a token for querying actual DB data."""
    return create_access_token(
        user_id=dash_user.id,
        workspace_id=dash_user.workspace_id,
        role="owner",
    )


@pytest.mark.asyncio
class TestDashboardSummary:
    """Tests for GET /api/v1/dashboard/summary"""

    async def test_empty_workspace(self, dash_client, dash_token):
        """With no data returns all zeros."""
        response = await dash_client.get(
            "/api/v1/dashboard/summary",
            cookies={"access_token": dash_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["conversations_count"] == 0
        assert data["messages_count"] == 0
        assert data["documents_count"] == 0
        assert data["knowledge_gaps_count"] == 0
        assert data["avg_quality_score"] is None
        assert data["recent_conversations"] == []
        assert data["features"]["rag_enabled"] is True

    async def test_with_data(self, dash_client, dash_token, dash_user, db_session):
        """With conversations, messages, docs, and gaps."""
        workspace_id = dash_user.workspace_id

        # Create a conversation
        conv = Conversation(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            channel="web",
            status="active",
            started_at=datetime.now(UTC),
        )
        db_session.add(conv)
        await db_session.flush()

        # Create messages
        msg1 = Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role="user",
            content="Hello, how are you?",
            created_at=datetime.now(UTC),
        )
        msg2 = Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            role="assistant",
            content="I'm fine, thank you!",
            quality_score=0.9,
            sentiment="positive",
            created_at=datetime.now(UTC),
        )
        db_session.add_all([msg1, msg2])

        # Create a KB with a document
        kb = KnowledgeBase(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            name="Test KB",
            doc_count=1,
            chunk_count=5,
            created_at=datetime.now(UTC),
        )
        db_session.add(kb)
        await db_session.flush()

        from app.models.knowledge_base import Document

        doc = Document(
            id=uuid.uuid4(),
            kb_id=kb.id,
            filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            chunk_count=5,
            status="ready",
        )
        db_session.add(doc)

        # Create knowledge gap
        gap = KnowledgeGap(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            query_text="What is the return policy?",
            occurrence_count=3,
            status="open",
            created_at=datetime.now(UTC),
            last_asked_at=datetime.now(UTC),
        )
        db_session.add(gap)
        await db_session.commit()

        response = await dash_client.get(
            "/api/v1/dashboard/summary",
            cookies={"access_token": dash_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["conversations_count"] == 1
        assert data["messages_count"] == 2
        assert data["documents_count"] == 1
        assert data["knowledge_gaps_count"] == 1
        assert data["avg_quality_score"] == 0.9
        assert len(data["recent_conversations"]) == 1
        assert data["recent_conversations"][0]["message_count"] == 2

    async def test_unauthenticated_returns_401(self, dash_client):
        """Unauthenticated request returns 401."""
        response = await dash_client.get("/api/v1/dashboard/summary")
        assert response.status_code == 401
