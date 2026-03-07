"""Integration tests for Knowledge Base CRUD API.

Tests cover:
- POST /api/v1/kb/ (create KB)
- GET /api/v1/kb/ (list KBs)
- GET /api/v1/kb/{id} (get single KB)
- PATCH /api/v1/kb/{id} (update KB)
- GET /api/v1/kb/gaps (list knowledge gaps)
- POST /api/v1/kb/gaps/{id}/dismiss (dismiss gap)
"""

import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.main import app
from app.models.knowledge_base import KnowledgeBase, KnowledgeGap
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.services.auth import create_access_token, hash_password


@pytest_asyncio.fixture
async def kb_client(db_session: AsyncSession):
    """Test client with DB override for KB tests."""

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
async def kb_user(db_session: AsyncSession):
    """Create owner user with workspace for KB tests."""
    user = User(
        id=uuid.uuid4(),
        email="kb@test.com",
        password_hash=hash_password("password123"),
        name="KB User",
    )
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(
        id=uuid.uuid4(),
        owner_id=user.id,
        name="KB Test Workspace",
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
async def kb_token(kb_user: User):
    """Create auth token for KB user."""
    return create_access_token(
        user_id=kb_user.id,
        workspace_id=kb_user.workspace_id,
        role="owner",
    )


@pytest.mark.asyncio
class TestCreateKB:
    """Tests for POST /api/v1/kb/"""

    async def test_create_kb_success(self, kb_client, kb_token):
        """Create a new knowledge base."""
        response = await kb_client.post(
            "/api/v1/kb/",
            json={"name": "My KB", "description": "Test description"},
            cookies={"access_token": kb_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My KB"
        assert data["description"] == "Test description"
        assert data["doc_count"] == 0
        assert data["chunk_count"] == 0

    async def test_create_kb_without_description(self, kb_client, kb_token):
        """Create KB without optional description."""
        response = await kb_client.post(
            "/api/v1/kb/",
            json={"name": "Minimal KB"},
            cookies={"access_token": kb_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Minimal KB"
        assert data["description"] is None


@pytest.mark.asyncio
class TestListKBs:
    """Tests for GET /api/v1/kb/"""

    async def test_list_empty(self, kb_client, kb_token):
        """List KBs when none exist returns empty list."""
        response = await kb_client.get(
            "/api/v1/kb/",
            cookies={"access_token": kb_token},
        )

        assert response.status_code == 200
        assert response.json() == []

    async def test_list_returns_workspace_kbs(self, kb_client, kb_token, kb_user, db_session):
        """List KBs returns only KBs for the user's workspace."""
        kb1 = KnowledgeBase(
            id=uuid.uuid4(),
            workspace_id=kb_user.workspace_id,
            name="KB Alpha",
            doc_count=0,
            chunk_count=0,
            created_at=datetime.now(UTC),
        )
        kb2 = KnowledgeBase(
            id=uuid.uuid4(),
            workspace_id=kb_user.workspace_id,
            name="KB Beta",
            doc_count=0,
            chunk_count=0,
            created_at=datetime.now(UTC),
        )
        db_session.add_all([kb1, kb2])
        await db_session.commit()

        response = await kb_client.get(
            "/api/v1/kb/",
            cookies={"access_token": kb_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


@pytest.mark.asyncio
class TestGetKB:
    """Tests for GET /api/v1/kb/{kb_id}"""

    async def test_get_kb_success(self, kb_client, kb_token, kb_user, db_session):
        """Get a specific KB by ID."""
        kb = KnowledgeBase(
            id=uuid.uuid4(),
            workspace_id=kb_user.workspace_id,
            name="Fetch Me",
            doc_count=3,
            chunk_count=15,
            created_at=datetime.now(UTC),
        )
        db_session.add(kb)
        await db_session.commit()

        response = await kb_client.get(
            f"/api/v1/kb/{kb.id}",
            cookies={"access_token": kb_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Fetch Me"
        assert data["doc_count"] == 3

    async def test_get_nonexistent_kb_returns_404(self, kb_client, kb_token):
        """Getting non-existent KB returns 404."""
        fake_id = uuid.uuid4()
        response = await kb_client.get(
            f"/api/v1/kb/{fake_id}",
            cookies={"access_token": kb_token},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestUpdateKB:
    """Tests for PATCH /api/v1/kb/{kb_id}"""

    async def test_update_kb_name(self, kb_client, kb_token, kb_user, db_session):
        """Update KB name."""
        kb = KnowledgeBase(
            id=uuid.uuid4(),
            workspace_id=kb_user.workspace_id,
            name="Old Name",
            doc_count=0,
            chunk_count=0,
            created_at=datetime.now(UTC),
        )
        db_session.add(kb)
        await db_session.commit()

        response = await kb_client.patch(
            f"/api/v1/kb/{kb.id}",
            json={"name": "New Name"},
            cookies={"access_token": kb_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"

    async def test_update_nonexistent_kb_returns_404(self, kb_client, kb_token):
        """Updating non-existent KB returns 404."""
        fake_id = uuid.uuid4()
        response = await kb_client.patch(
            f"/api/v1/kb/{fake_id}",
            json={"name": "Updated"},
            cookies={"access_token": kb_token},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestKnowledgeGaps:
    """Tests for GET /api/v1/kb/gaps and POST /api/v1/kb/gaps/{id}/dismiss"""

    async def test_list_gaps_empty(self, kb_client, kb_token):
        """List gaps when none exist returns empty list."""
        response = await kb_client.get(
            "/api/v1/kb/gaps",
            cookies={"access_token": kb_token},
        )

        assert response.status_code == 200
        assert response.json() == []

    async def test_list_gaps_returns_workspace_gaps(self, kb_client, kb_token, kb_user, db_session):
        """List gaps returns gaps for the user's workspace."""
        gap = KnowledgeGap(
            id=uuid.uuid4(),
            workspace_id=kb_user.workspace_id,
            query_text="What is your refund policy?",
            occurrence_count=5,
            status="open",
            created_at=datetime.now(UTC),
            last_asked_at=datetime.now(UTC),
        )
        db_session.add(gap)
        await db_session.commit()

        response = await kb_client.get(
            "/api/v1/kb/gaps",
            cookies={"access_token": kb_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["query_text"] == "What is your refund policy?"
        # Backend 'open' maps to frontend 'active'
        assert data[0]["status"] == "active"

    async def test_dismiss_gap_success(self, kb_client, kb_token, kb_user, db_session):
        """Dismiss a knowledge gap."""
        gap = KnowledgeGap(
            id=uuid.uuid4(),
            workspace_id=kb_user.workspace_id,
            query_text="Dismissed question",
            occurrence_count=1,
            status="open",
            created_at=datetime.now(UTC),
            last_asked_at=datetime.now(UTC),
        )
        db_session.add(gap)
        await db_session.commit()

        response = await kb_client.post(
            f"/api/v1/kb/gaps/{gap.id}/dismiss",
            cookies={"access_token": kb_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "dismissed"

    async def test_dismiss_nonexistent_gap_returns_404(self, kb_client, kb_token):
        """Dismissing non-existent gap returns 404."""
        fake_id = uuid.uuid4()
        response = await kb_client.post(
            f"/api/v1/kb/gaps/{fake_id}/dismiss",
            cookies={"access_token": kb_token},
        )
        assert response.status_code == 404
