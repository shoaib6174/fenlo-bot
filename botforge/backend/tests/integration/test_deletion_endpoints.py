"""Integration tests for AX.12 deletion and retry endpoints.

Tests cover:
- DELETE /api/v1/docs/{id}: delete a single document
- DELETE /api/v1/kb/{id}: delete KB and cascade to documents
- POST /api/v1/docs/{id}/retry: retry failed document processing
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.main import app
from app.models.knowledge_base import Document, KnowledgeBase
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.services.auth import create_access_token, hash_password


@pytest_asyncio.fixture
async def deletion_client(db_session: AsyncSession):
    """Test client with DB override for deletion tests."""

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
async def owner_user(db_session: AsyncSession):
    """Create owner user with workspace."""
    user = User(
        id=uuid.uuid4(),
        email="owner@deletion-test.com",
        password_hash=hash_password("password123"),
        name="Owner User",
    )
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(
        id=uuid.uuid4(),
        owner_id=user.id,
        name="Deletion Test Workspace",
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

    # Attach workspace_id for convenience
    user.workspace_id = workspace.id
    return user


@pytest_asyncio.fixture
async def owner_token(owner_user: User):
    """Create auth token for owner user."""
    return create_access_token(
        user_id=owner_user.id,
        workspace_id=owner_user.workspace_id,
        role="owner",
    )


@pytest_asyncio.fixture
async def kb_with_docs(db_session: AsyncSession, owner_user: User):
    """Create a knowledge base with 2 documents."""
    kb = KnowledgeBase(
        id=uuid.uuid4(),
        workspace_id=owner_user.workspace_id,
        name="Test KB",
        doc_count=2,
    )
    db_session.add(kb)
    await db_session.flush()

    doc1 = Document(
        id=uuid.uuid4(),
        kb_id=kb.id,
        filename="test1.pdf",
        file_type="pdf",
        file_size=1024,
        chunk_count=5,
        status="ready",
        metadata_={"storage_path": "uploads/test1.pdf"},
    )
    doc2 = Document(
        id=uuid.uuid4(),
        kb_id=kb.id,
        filename="test2.pdf",
        file_type="pdf",
        file_size=2048,
        chunk_count=10,
        status="ready",
        metadata_={"storage_path": "uploads/test2.pdf"},
    )
    db_session.add_all([doc1, doc2])
    await db_session.commit()

    return kb, doc1, doc2


# Mock external services (Pinecone, file storage) for all tests
@pytest.fixture(autouse=True)
def mock_external_services():
    """Mock RAG pipeline and file storage to avoid external calls."""
    mock_rag = AsyncMock()
    mock_storage = AsyncMock()

    with (
        patch("app.api.docs.get_rag_pipeline", return_value=mock_rag),
        patch("app.api.docs.get_file_storage", return_value=mock_storage),
        patch("app.api.kb.get_rag_pipeline", return_value=mock_rag),
        patch("app.api.kb.get_file_storage", return_value=mock_storage),
    ):
        yield mock_rag, mock_storage


# ─── DELETE /api/v1/docs/{id} ───────────────────────────────────────────


@pytest.mark.asyncio
class TestDeleteDocument:
    """Tests for DELETE /api/v1/docs/{id}"""

    async def test_delete_document_success(
        self, deletion_client, owner_token, kb_with_docs, db_session
    ):
        """Happy path: delete document removes DB row and returns 204."""
        kb, doc1, doc2 = kb_with_docs

        response = await deletion_client.delete(
            f"/api/v1/docs/{doc1.id}",
            cookies={"access_token": owner_token},
        )

        assert response.status_code == 204

        # Verify document is gone from DB
        result = await db_session.execute(select(Document).where(Document.id == doc1.id))
        assert result.scalar_one_or_none() is None

        # Verify other document still exists
        result = await db_session.execute(select(Document).where(Document.id == doc2.id))
        assert result.scalar_one_or_none() is not None

    async def test_delete_nonexistent_document_returns_404(self, deletion_client, owner_token):
        """Error: deleting non-existent document returns 404."""
        fake_id = uuid.uuid4()
        response = await deletion_client.delete(
            f"/api/v1/docs/{fake_id}",
            cookies={"access_token": owner_token},
        )
        assert response.status_code == 404

    async def test_delete_document_calls_rag_and_storage(
        self, deletion_client, owner_token, kb_with_docs, db_session, mock_external_services
    ):
        """Delete calls Pinecone delete and file storage delete."""
        mock_rag, mock_storage = mock_external_services
        kb, doc1, doc2 = kb_with_docs

        response = await deletion_client.delete(
            f"/api/v1/docs/{doc1.id}",
            cookies={"access_token": owner_token},
        )

        assert response.status_code == 204
        mock_rag.delete.assert_called_once_with(doc_id=str(doc1.id), kb_id=str(kb.id))
        mock_storage.delete.assert_called_once_with("uploads/test1.pdf")

    async def test_delete_document_decrements_kb_doc_count(
        self, deletion_client, owner_token, kb_with_docs, db_session
    ):
        """Deleting a document decrements the KB's doc_count."""
        kb, doc1, doc2 = kb_with_docs
        assert kb.doc_count == 2

        await deletion_client.delete(
            f"/api/v1/docs/{doc1.id}",
            cookies={"access_token": owner_token},
        )

        await db_session.refresh(kb)
        assert kb.doc_count == 1

    async def test_delete_document_continues_on_rag_failure(
        self, deletion_client, owner_token, kb_with_docs, db_session, mock_external_services
    ):
        """Delete continues and removes DB row even if Pinecone delete fails."""
        mock_rag, mock_storage = mock_external_services
        mock_rag.delete.side_effect = Exception("Pinecone unavailable")
        kb, doc1, doc2 = kb_with_docs

        response = await deletion_client.delete(
            f"/api/v1/docs/{doc1.id}",
            cookies={"access_token": owner_token},
        )

        assert response.status_code == 204
        result = await db_session.execute(select(Document).where(Document.id == doc1.id))
        assert result.scalar_one_or_none() is None

    async def test_delete_document_wrong_workspace_returns_403(
        self, deletion_client, db_session, kb_with_docs
    ):
        """Error: deleting document from another workspace returns 403."""
        kb, doc1, doc2 = kb_with_docs

        # Create a different user in a different workspace
        other_user = User(
            id=uuid.uuid4(),
            email="other@deletion-test.com",
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

        response = await deletion_client.delete(
            f"/api/v1/docs/{doc1.id}",
            cookies={"access_token": other_token},
        )
        assert response.status_code == 403


# ─── DELETE /api/v1/kb/{id} ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestDeleteKnowledgeBase:
    """Tests for DELETE /api/v1/kb/{id}"""

    async def test_delete_kb_cascades_to_documents(
        self, deletion_client, owner_token, kb_with_docs, db_session
    ):
        """Happy path: deleting KB removes all its documents."""
        kb, doc1, doc2 = kb_with_docs

        response = await deletion_client.delete(
            f"/api/v1/kb/{kb.id}",
            cookies={"access_token": owner_token},
        )

        assert response.status_code == 204

        # Verify KB is gone
        result = await db_session.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb.id))
        assert result.scalar_one_or_none() is None

        # Verify all documents are gone
        result = await db_session.execute(select(Document).where(Document.kb_id == kb.id))
        assert result.scalars().all() == []

    async def test_delete_kb_calls_rag_and_storage_for_each_doc(
        self, deletion_client, owner_token, kb_with_docs, db_session, mock_external_services
    ):
        """Deleting KB calls Pinecone and storage delete for every document."""
        mock_rag, mock_storage = mock_external_services
        kb, doc1, doc2 = kb_with_docs

        response = await deletion_client.delete(
            f"/api/v1/kb/{kb.id}",
            cookies={"access_token": owner_token},
        )

        assert response.status_code == 204
        assert mock_rag.delete.call_count == 2
        assert mock_storage.delete.call_count == 2

    async def test_delete_empty_kb_succeeds(
        self, deletion_client, owner_token, db_session, owner_user
    ):
        """Deleting a KB with 0 documents succeeds."""
        empty_kb = KnowledgeBase(
            id=uuid.uuid4(),
            workspace_id=owner_user.workspace_id,
            name="Empty KB",
            doc_count=0,
        )
        db_session.add(empty_kb)
        await db_session.commit()

        response = await deletion_client.delete(
            f"/api/v1/kb/{empty_kb.id}",
            cookies={"access_token": owner_token},
        )

        assert response.status_code == 204
        result = await db_session.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == empty_kb.id)
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_kb_continues_on_partial_rag_failure(
        self, deletion_client, owner_token, kb_with_docs, db_session, mock_external_services
    ):
        """KB deletion continues even if some document vector deletes fail."""
        mock_rag, mock_storage = mock_external_services
        call_count = 0

        async def flaky_delete(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Pinecone timeout")

        mock_rag.delete.side_effect = flaky_delete
        kb, doc1, doc2 = kb_with_docs

        response = await deletion_client.delete(
            f"/api/v1/kb/{kb.id}",
            cookies={"access_token": owner_token},
        )

        assert response.status_code == 204
        result = await db_session.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb.id))
        assert result.scalar_one_or_none() is None

    async def test_delete_nonexistent_kb_returns_404(self, deletion_client, owner_token):
        """Error: deleting non-existent KB returns 404."""
        fake_id = uuid.uuid4()
        response = await deletion_client.delete(
            f"/api/v1/kb/{fake_id}",
            cookies={"access_token": owner_token},
        )
        assert response.status_code == 404


# ─── POST /api/v1/docs/{id}/retry ──────────────────────────────────────


@pytest.mark.asyncio
class TestRetryDocument:
    """Tests for POST /api/v1/docs/{id}/retry"""

    async def test_retry_reenqueues_failed_document(
        self, deletion_client, owner_token, kb_with_docs, db_session
    ):
        """Happy path: retry re-enqueues ARQ job for failed document."""
        kb, doc1, doc2 = kb_with_docs

        # Set doc1 to failed status
        doc1.status = "failed"
        await db_session.commit()

        with patch(
            "app.api.docs.enqueue_document_processing", new_callable=AsyncMock
        ) as mock_enqueue:
            mock_enqueue.return_value = None

            response = await deletion_client.post(
                f"/api/v1/docs/{doc1.id}/retry",
                cookies={"access_token": owner_token},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processing"
            assert data["id"] == str(doc1.id)

    async def test_retry_nonexistent_document_returns_404(self, deletion_client, owner_token):
        """Error: retrying non-existent document returns 404."""
        fake_id = uuid.uuid4()
        response = await deletion_client.post(
            f"/api/v1/docs/{fake_id}/retry",
            cookies={"access_token": owner_token},
        )
        assert response.status_code == 404

    async def test_retry_non_failed_document_returns_400(
        self, deletion_client, owner_token, kb_with_docs
    ):
        """Error: retrying a non-failed document returns 400."""
        kb, doc1, doc2 = kb_with_docs
        # doc1 has status "ready", not "failed"

        response = await deletion_client.post(
            f"/api/v1/docs/{doc1.id}/retry",
            cookies={"access_token": owner_token},
        )

        assert response.status_code == 400
        body = response.json()
        # Handle both direct HTTPException format and standard error format
        if "detail" in body:
            assert "failed" in body["detail"].lower() or "retry" in body["detail"].lower()
        elif "error" in body:
            assert (
                "failed" in body["error"]["message"].lower()
                or "retry" in body["error"]["message"].lower()
            )
        else:
            pytest.fail(f"Unexpected 400 response format: {body}")
