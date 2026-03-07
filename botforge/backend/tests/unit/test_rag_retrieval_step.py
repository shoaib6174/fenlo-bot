"""Unit tests for RAG retrieval step."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.core.engine import MessageContext
from app.core.steps.rag_retrieval import RAGRetrievalStep
from app.modules.rag.pipeline import Chunk


@pytest.mark.asyncio
class TestRAGRetrievalStep:
    """Test RAG retrieval pipeline step"""

    async def test_rag_retrieval_with_enabled_workspace(self):
        """Test RAG retrieval when workspace has RAG enabled"""
        workspace_id = uuid4()
        kb_id = str(uuid4())

        # Mock workspace with RAG enabled
        mock_workspace = Mock()
        mock_workspace.settings = {
            "rag_enabled": True,
            "default_kb_id": kb_id,
        }

        # Mock database session
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_workspace)
        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        # Mock get_db to yield session
        async def mock_get_db():
            yield mock_session

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

        with (
            patch("app.core.steps.rag_retrieval.get_db", mock_get_db),
            patch("app.core.steps.rag_retrieval.get_rag_pipeline", return_value=mock_pipeline),
        ):
            # Create message context
            context = MessageContext(
                workspace_id=workspace_id,
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

            # Verify retrieve was called with correct parameters
            mock_pipeline.retrieve.assert_called_once_with(
                query="What are your business hours?", kb_id=kb_id, top_k=5
            )

    async def test_rag_retrieval_with_disabled_workspace(self):
        """Test RAG retrieval is skipped when workspace has RAG disabled"""
        workspace_id = uuid4()

        # Mock workspace with RAG disabled
        mock_workspace = Mock()
        mock_workspace.settings = {
            "rag_enabled": False,
        }

        # Mock database session
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_workspace)

        # Mock get_db
        async def mock_get_db():
            yield mock_session

        # Mock RAG pipeline (should not be called)
        mock_pipeline = Mock()
        mock_pipeline.retrieve = AsyncMock()

        with (
            patch("app.core.steps.rag_retrieval.get_db", mock_get_db),
            patch("app.core.steps.rag_retrieval.get_rag_pipeline", return_value=mock_pipeline),
        ):
            # Create message context
            context = MessageContext(
                workspace_id=workspace_id,
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

            # Verify retrieve was NOT called
            mock_pipeline.retrieve.assert_not_called()

    async def test_rag_retrieval_with_no_matching_chunks(self):
        """Test RAG retrieval when no chunks match the query"""
        workspace_id = uuid4()
        kb_id = str(uuid4())

        # Mock workspace with RAG enabled
        mock_workspace = Mock()
        mock_workspace.settings = {
            "rag_enabled": True,
            "default_kb_id": kb_id,
        }

        # Mock database session
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_workspace)

        # Mock get_db
        async def mock_get_db():
            yield mock_session

        # Mock RAG pipeline returning no chunks
        mock_pipeline = Mock()
        mock_pipeline.retrieve = AsyncMock(return_value=[])

        with (
            patch("app.core.steps.rag_retrieval.get_db", mock_get_db),
            patch("app.core.steps.rag_retrieval.get_rag_pipeline", return_value=mock_pipeline),
        ):
            # Create message context
            context = MessageContext(
                workspace_id=workspace_id,
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

    async def test_rag_retrieval_error_handling(self):
        """Test RAG retrieval gracefully handles errors"""
        workspace_id = uuid4()
        kb_id = str(uuid4())

        # Mock workspace with RAG enabled
        mock_workspace = Mock()
        mock_workspace.settings = {
            "rag_enabled": True,
            "default_kb_id": kb_id,
        }

        # Mock database session
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_workspace)

        # Mock get_db
        async def mock_get_db():
            yield mock_session

        # Mock RAG pipeline that raises an error
        mock_pipeline = Mock()
        mock_pipeline.retrieve = AsyncMock(side_effect=Exception("Pinecone connection failed"))

        with (
            patch("app.core.steps.rag_retrieval.get_db", mock_get_db),
            patch("app.core.steps.rag_retrieval.get_rag_pipeline", return_value=mock_pipeline),
        ):
            # Create message context
            context = MessageContext(
                workspace_id=workspace_id,
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
