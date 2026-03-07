"""Integration tests for Document Management API.

Tests cover:
- GET /api/v1/docs/ (list documents)
- GET /api/v1/docs/{id} (get single document)
"""

import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.main import app
from app.models.knowledge_base import Document, KnowledgeBase
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.services.auth import create_access_token, hash_password


@pytest_asyncio.fixture
async def docs_client(db_session: AsyncSession):
    """Test client with DB override for docs tests."""

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
async def docs_user(db_session: AsyncSession):
    """Create owner user with workspace for docs tests."""
    user = User(
        id=uuid.uuid4(),
        email="docs@test.com",
        password_hash=hash_password("password123"),
        name="Docs User",
    )
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(
        id=uuid.uuid4(),
        owner_id=user.id,
        name="Docs Workspace",
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
async def docs_token(docs_user: User):
    """Create auth token for docs user."""
    return create_access_token(
        user_id=docs_user.id,
        workspace_id=docs_user.workspace_id,
        role="owner",
    )


@pytest_asyncio.fixture
async def kb_with_doc(db_session: AsyncSession, docs_user: User):
    """Create a KB with one document."""
    kb = KnowledgeBase(
        id=uuid.uuid4(),
        workspace_id=docs_user.workspace_id,
        name="Docs Test KB",
        doc_count=1,
        chunk_count=10,
        created_at=datetime.now(UTC),
    )
    db_session.add(kb)
    await db_session.flush()

    doc = Document(
        id=uuid.uuid4(),
        kb_id=kb.id,
        filename="readme.pdf",
        file_type="pdf",
        file_size=2048,
        chunk_count=10,
        status="ready",
        metadata_={"storage_path": "uploads/readme.pdf"},
        created_at=datetime.now(UTC),
    )
    db_session.add(doc)
    await db_session.commit()

    return kb, doc


@pytest.mark.asyncio
class TestListDocuments:
    """Tests for GET /api/v1/docs/"""

    async def test_list_all_documents(self, docs_client, docs_token, kb_with_doc):
        """List all documents across workspace KBs."""
        response = await docs_client.get(
            "/api/v1/docs/",
            cookies={"access_token": docs_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["documents"]) == 1
        assert data["documents"][0]["filename"] == "readme.pdf"

    async def test_list_documents_by_kb(self, docs_client, docs_token, kb_with_doc):
        """List documents filtered by KB ID."""
        kb, doc = kb_with_doc

        response = await docs_client.get(
            f"/api/v1/docs/?kb_id={kb.id}",
            cookies={"access_token": docs_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["documents"][0]["filename"] == "readme.pdf"

    async def test_list_documents_empty(self, docs_client, docs_token):
        """List documents when none exist."""
        response = await docs_client.get(
            "/api/v1/docs/",
            cookies={"access_token": docs_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["documents"] == []

    async def test_list_documents_nonexistent_kb_returns_404(self, docs_client, docs_token):
        """List documents for non-existent KB returns 404."""
        fake_id = uuid.uuid4()
        response = await docs_client.get(
            f"/api/v1/docs/?kb_id={fake_id}",
            cookies={"access_token": docs_token},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestGetDocument:
    """Tests for GET /api/v1/docs/{doc_id}"""

    async def test_get_document_success(self, docs_client, docs_token, kb_with_doc):
        """Get a specific document by ID."""
        kb, doc = kb_with_doc

        response = await docs_client.get(
            f"/api/v1/docs/{doc.id}",
            cookies={"access_token": docs_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "readme.pdf"
        assert data["status"] == "ready"
        assert data["file_size"] == 2048

    async def test_get_nonexistent_document_returns_404(self, docs_client, docs_token):
        """Get non-existent document returns 404."""
        fake_id = uuid.uuid4()
        response = await docs_client.get(
            f"/api/v1/docs/{fake_id}",
            cookies={"access_token": docs_token},
        )
        assert response.status_code == 404

    async def test_get_document_wrong_workspace_returns_403(
        self, docs_client, db_session, kb_with_doc
    ):
        """Get document from another workspace returns 403."""
        kb, doc = kb_with_doc

        # Create a different user in a different workspace
        other_user = User(
            id=uuid.uuid4(),
            email="other-docs@test.com",
            password_hash=hash_password("password123"),
            name="Other User",
        )
        db_session.add(other_user)
        await db_session.flush()

        other_workspace = Workspace(
            id=uuid.uuid4(),
            owner_id=other_user.id,
            name="Other Workspace",
        )
        db_session.add(other_workspace)
        await db_session.flush()

        other_member = WorkspaceMember(
            workspace_id=other_workspace.id,
            user_id=other_user.id,
            role="owner",
        )
        db_session.add(other_member)
        await db_session.commit()

        other_token = create_access_token(
            user_id=other_user.id,
            workspace_id=other_workspace.id,
            role="owner",
        )

        response = await docs_client.get(
            f"/api/v1/docs/{doc.id}",
            cookies={"access_token": other_token},
        )
        assert response.status_code == 403
