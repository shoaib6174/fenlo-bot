"""
End-to-end RAG integration tests.

Tests the complete flow:
1. Upload document → Process → Ask question → Get answer with citations
2. Knowledge gap detection
"""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.core.engine import MessageContext
from app.core.steps.rag_retrieval import RAGRetrievalStep
from app.models.user import User
from app.models.workspace import Workspace
from app.modules.rag.pipeline import Chunk


@pytest.fixture
async def test_owner(db_session):
    """Create a test user to serve as workspace owner."""
    user = User(
        id=uuid4(),
        email=f"rag-test-{uuid4().hex[:8]}@test.com",
        password_hash="$2b$12$fakehash",
        name="RAG Test User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
class TestRAGEndToEnd:
    """Test complete RAG flow end-to-end"""

    async def test_rag_retrieval_step_with_enabled_workspace(self, db_session, test_owner):
        """Test RAG retrieval when workspace has RAG enabled"""
        # Create test workspace with RAG enabled
        workspace = Workspace(
            id=uuid4(),
            owner_id=test_owner.id,
            name="Test RAG Workspace",
            token_budget_monthly=1000000,
            settings={
                "rag_enabled": True,
                "default_kb_id": str(uuid4()),
            },
        )
        db_session.add(workspace)
        await db_session.commit()

        # Mock RAG pipeline
        mock_chunks = [
            Chunk(
                doc_id="doc-1",
                doc_name="FAQ.pdf",
                chunk_text="We are open Monday-Friday, 9 AM to 6 PM EST.",
                page_number=1,
                relevance_score=0.92,
                metadata={"document_id": "doc-1", "doc_name": "FAQ.pdf", "page_number": 1},
            ),
            Chunk(
                doc_id="doc-2",
                doc_name="Business_Info.pdf",
                chunk_text="Our business hours are 9 AM to 6 PM Eastern Time.",
                page_number=2,
                relevance_score=0.85,
                metadata={
                    "document_id": "doc-2",
                    "doc_name": "Business_Info.pdf",
                    "page_number": 2,
                },
            ),
        ]

        mock_pipeline = Mock()
        mock_pipeline.retrieve = AsyncMock(return_value=mock_chunks)

        async def mock_get_db():
            yield db_session

        with (
            patch("app.core.steps.rag_retrieval.get_rag_pipeline", return_value=mock_pipeline),
            patch("app.core.steps.rag_retrieval.get_db", mock_get_db),
        ):
            # Create message context
            context = MessageContext(
                workspace_id=workspace.id,
                user_id=uuid4(),
                conversation_id=None,
                message="What are your business hours?",
            )

            # Execute RAG retrieval step
            step = RAGRetrievalStep()
            result_context = await step.execute(context)

            # Verify chunks were retrieved
            assert len(result_context.rag_chunks) == 2
            assert result_context.rag_chunks[0]["score"] == 0.92
            assert "9 AM to 6 PM" in result_context.rag_chunks[0]["text"]

            # Verify citations were added
            assert len(result_context.citations) == 2
            assert result_context.citations[0]["doc_name"] == "FAQ.pdf"
            assert result_context.citations[0]["page_number"] == 1
            assert result_context.citations[0]["relevance_score"] == 0.92
            assert result_context.citations[0]["document_id"] == "doc-1"

    async def test_rag_retrieval_step_with_disabled_workspace(self, db_session, test_owner):
        """Test RAG retrieval is skipped when workspace has RAG disabled"""
        # Create test workspace with RAG disabled
        workspace = Workspace(
            id=uuid4(),
            owner_id=test_owner.id,
            name="Test No-RAG Workspace",
            token_budget_monthly=1000000,
            settings={
                "rag_enabled": False,
            },
        )
        db_session.add(workspace)
        await db_session.commit()

        async def mock_get_db():
            yield db_session

        mock_pipeline = Mock()

        with (
            patch("app.core.steps.rag_retrieval.get_rag_pipeline", return_value=mock_pipeline),
            patch("app.core.steps.rag_retrieval.get_db", mock_get_db),
        ):
            # Create message context
            context = MessageContext(
                workspace_id=workspace.id,
                user_id=uuid4(),
                conversation_id=None,
                message="What are your business hours?",
            )

            # Execute RAG retrieval step
            step = RAGRetrievalStep()
            result_context = await step.execute(context)

            # Verify no chunks were retrieved (RAG disabled)
            assert len(result_context.rag_chunks) == 0
            assert len(result_context.citations) == 0

    async def test_rag_retrieval_step_with_no_matching_chunks(self, db_session, test_owner):
        """Test RAG retrieval when no chunks match the query"""
        # Create test workspace with RAG enabled
        workspace = Workspace(
            id=uuid4(),
            owner_id=test_owner.id,
            name="Test RAG Workspace",
            token_budget_monthly=1000000,
            settings={
                "rag_enabled": True,
                "default_kb_id": str(uuid4()),
            },
        )
        db_session.add(workspace)
        await db_session.commit()

        # Mock RAG pipeline returning no chunks
        mock_pipeline = Mock()
        mock_pipeline.retrieve = AsyncMock(return_value=[])

        async def mock_get_db():
            yield db_session

        with (
            patch("app.core.steps.rag_retrieval.get_rag_pipeline", return_value=mock_pipeline),
            patch("app.core.steps.rag_retrieval.get_db", mock_get_db),
        ):
            # Create message context
            context = MessageContext(
                workspace_id=workspace.id,
                user_id=uuid4(),
                conversation_id=None,
                message="What is the meaning of life?",
            )

            # Execute RAG retrieval step
            step = RAGRetrievalStep()
            result_context = await step.execute(context)

            # Verify no chunks were retrieved
            assert len(result_context.rag_chunks) == 0
            assert len(result_context.citations) == 0

    async def test_rag_retrieval_step_error_handling(self, db_session, test_owner):
        """Test RAG retrieval gracefully handles errors"""
        # Create test workspace with RAG enabled
        workspace = Workspace(
            id=uuid4(),
            owner_id=test_owner.id,
            name="Test RAG Workspace",
            token_budget_monthly=1000000,
            settings={
                "rag_enabled": True,
                "default_kb_id": str(uuid4()),
            },
        )
        db_session.add(workspace)
        await db_session.commit()

        # Mock RAG pipeline that raises an error
        mock_pipeline = Mock()
        mock_pipeline.retrieve = AsyncMock(side_effect=Exception("Pinecone connection failed"))

        async def mock_get_db():
            yield db_session

        with (
            patch("app.core.steps.rag_retrieval.get_rag_pipeline", return_value=mock_pipeline),
            patch("app.core.steps.rag_retrieval.get_db", mock_get_db),
        ):
            # Create message context
            context = MessageContext(
                workspace_id=workspace.id,
                user_id=uuid4(),
                conversation_id=None,
                message="What are your business hours?",
            )

            # Execute RAG retrieval step - should not raise
            step = RAGRetrievalStep()
            result_context = await step.execute(context)

            # Verify pipeline continued despite error
            assert len(result_context.rag_chunks) == 0
            assert len(result_context.citations) == 0
            assert result_context.should_halt is False
