"""Tests for document ingestion service."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.knowledge_base import Document, KnowledgeBase
from app.modules.rag.ingestion import (
    DocumentIngestionService,
    process_document_job,
)


@pytest.fixture
def mock_rag_pipeline():
    """Mock RAG pipeline."""
    pipeline = AsyncMock()
    pipeline.ingest = AsyncMock(return_value=10)  # Returns chunk count
    pipeline.cleanup_partial_vectors = AsyncMock()
    pipeline.delete = AsyncMock()
    return pipeline


@pytest.fixture
def mock_file_storage():
    """Mock file storage."""
    storage = AsyncMock()
    storage.save = AsyncMock(return_value="/storage/path/file.pdf")
    storage.retrieve = AsyncMock(return_value=b"file content")
    storage.delete = AsyncMock()
    return storage


@pytest.fixture
def mock_redis_pool():
    """Mock Redis ARQ pool."""
    with patch("app.modules.rag.ingestion.create_pool") as mock_create:
        pool = AsyncMock()
        pool.enqueue_job = AsyncMock()
        mock_create.return_value = pool
        yield pool


@pytest.fixture
def ingestion_service(mock_rag_pipeline, mock_file_storage):
    """Create DocumentIngestionService instance."""
    return DocumentIngestionService(
        redis_url="redis://localhost:6379",
        rag_pipeline=mock_rag_pipeline,
        file_storage=mock_file_storage,
    )


class TestDocumentIngestionService:
    """Test DocumentIngestionService class."""

    async def test_upload_document_creates_record(
        self, ingestion_service, mock_file_storage, mock_redis_pool
    ):
        """Test uploading document creates database record."""
        mock_db = AsyncMock()

        doc = await ingestion_service.upload_document(
            db=mock_db,
            kb_id=uuid.uuid4(),
            workspace_id=uuid.uuid4(),
            filename="test.pdf",
            file_type="application/pdf",
            file_size=1024,
            content=b"pdf content",
            metadata={"author": "John Doe"},
        )

        assert doc.filename == "test.pdf"
        assert doc.file_type == "application/pdf"
        assert doc.file_size == 1024
        assert doc.status == "processing"
        assert doc.metadata_.get("author") == "John Doe"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()

    async def test_upload_document_saves_to_storage(
        self, ingestion_service, mock_file_storage, mock_redis_pool
    ):
        """Test uploading document saves file to storage."""
        mock_db = AsyncMock()
        workspace_id = uuid.uuid4()
        kb_id = uuid.uuid4()

        await ingestion_service.upload_document(
            db=mock_db,
            kb_id=kb_id,
            workspace_id=workspace_id,
            filename="test.pdf",
            file_type="application/pdf",
            file_size=1024,
            content=b"pdf content",
        )

        mock_file_storage.save.assert_called_once()
        call_args = mock_file_storage.save.call_args[1]
        assert call_args["workspace_id"] == workspace_id
        assert call_args["filename"] == "test.pdf"
        assert call_args["content"] == b"pdf content"

    async def test_upload_document_enqueues_job(self, ingestion_service, mock_redis_pool):
        """Test uploading document enqueues ARQ processing job."""
        mock_db = AsyncMock()

        await ingestion_service.upload_document(
            db=mock_db,
            kb_id=uuid.uuid4(),
            workspace_id=uuid.uuid4(),
            filename="test.pdf",
            file_type="application/pdf",
            file_size=1024,
            content=b"pdf content",
        )

        mock_redis_pool.enqueue_job.assert_called_once()
        call_args = mock_redis_pool.enqueue_job.call_args[1]
        assert call_args["filename"] == "test.pdf"
        assert call_args["content"] == b"pdf content"

    async def test_upload_document_handles_file_like_content(
        self, ingestion_service, mock_redis_pool
    ):
        """Test uploading document handles file-like objects."""
        import io

        mock_db = AsyncMock()
        file_like = io.BytesIO(b"file content")

        await ingestion_service.upload_document(
            db=mock_db,
            kb_id=uuid.uuid4(),
            workspace_id=uuid.uuid4(),
            filename="test.pdf",
            file_type="application/pdf",
            file_size=1024,
            content=file_like,
        )

        # Should read content from file-like object
        mock_redis_pool.enqueue_job.assert_called_once()
        call_args = mock_redis_pool.enqueue_job.call_args[1]
        assert call_args["content"] == b"file content"

    async def test_get_document_status_returns_document(self, ingestion_service):
        """Test getting document status returns document."""
        mock_db = AsyncMock()
        doc_id = uuid.uuid4()

        mock_doc = Document(
            id=doc_id,
            kb_id=uuid.uuid4(),
            filename="test.pdf",
            file_type="application/pdf",
            file_size=1024,
            status="ready",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_db.execute.return_value = mock_result

        result = await ingestion_service.get_document_status(mock_db, doc_id)

        assert result == mock_doc
        assert result.status == "ready"

    async def test_get_document_status_returns_none_when_not_found(self, ingestion_service):
        """Test getting document status returns None when not found."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await ingestion_service.get_document_status(mock_db, uuid.uuid4())

        assert result is None

    async def test_retry_failed_document_cleans_up_vectors(
        self, ingestion_service, mock_rag_pipeline, mock_redis_pool, mock_file_storage
    ):
        """Test retrying failed document cleans up partial vectors."""
        mock_db = AsyncMock()
        doc_id = uuid.uuid4()
        kb_id = uuid.uuid4()

        mock_doc = Document(
            id=doc_id,
            kb_id=kb_id,
            filename="test.pdf",
            file_type="application/pdf",
            file_size=1024,
            status="failed",
            metadata_={"storage_path": "/storage/path/file.pdf", "error": "Parse error"},
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_db.execute.return_value = mock_result

        await ingestion_service.retry_failed_document(mock_db, doc_id)

        mock_rag_pipeline.cleanup_partial_vectors.assert_called_once_with(str(doc_id), str(kb_id))
        assert mock_doc.status == "processing"
        assert "error" not in mock_doc.metadata_
        mock_redis_pool.enqueue_job.assert_called_once()

    async def test_retry_failed_document_raises_when_not_found(self, ingestion_service):
        """Test retrying non-existent document raises ValueError."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await ingestion_service.retry_failed_document(mock_db, uuid.uuid4())

    async def test_retry_failed_document_raises_when_not_failed(self, ingestion_service):
        """Test retrying non-failed document raises ValueError."""
        mock_db = AsyncMock()
        doc_id = uuid.uuid4()

        mock_doc = Document(
            id=doc_id,
            kb_id=uuid.uuid4(),
            filename="test.pdf",
            file_type="application/pdf",
            file_size=1024,
            status="ready",  # Not failed
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not in failed state"):
            await ingestion_service.retry_failed_document(mock_db, doc_id)

    async def test_delete_document_removes_vectors_and_file(
        self, ingestion_service, mock_rag_pipeline, mock_file_storage
    ):
        """Test deleting document removes vectors and file from storage."""
        mock_db = AsyncMock()
        doc_id = uuid.uuid4()
        kb_id = uuid.uuid4()

        mock_doc = Document(
            id=doc_id,
            kb_id=kb_id,
            filename="test.pdf",
            file_type="application/pdf",
            file_size=1024,
            status="ready",
            chunk_count=10,
            metadata_={"storage_path": "/storage/path/file.pdf"},
        )

        mock_kb = KnowledgeBase(
            id=kb_id,
            workspace_id=uuid.uuid4(),
            name="Test KB",
            doc_count=5,
            chunk_count=50,
        )

        # Mock document query
        mock_doc_result = MagicMock()
        mock_doc_result.scalar_one_or_none.return_value = mock_doc

        # Mock KB query
        mock_kb_result = MagicMock()
        mock_kb_result.scalar_one_or_none.return_value = mock_kb

        mock_db.execute.side_effect = [mock_doc_result, mock_kb_result]

        await ingestion_service.delete_document(mock_db, doc_id)

        mock_rag_pipeline.delete.assert_called_once_with(str(doc_id), str(kb_id))
        mock_file_storage.delete.assert_called_once_with("/storage/path/file.pdf")
        mock_db.delete.assert_called_once_with(mock_doc)
        assert mock_kb.doc_count == 4
        assert mock_kb.chunk_count == 40

    async def test_delete_document_handles_storage_error_gracefully(
        self, ingestion_service, mock_file_storage
    ):
        """Test deleting document continues even if storage deletion fails."""
        mock_db = AsyncMock()
        doc_id = uuid.uuid4()
        kb_id = uuid.uuid4()

        mock_doc = Document(
            id=doc_id,
            kb_id=kb_id,
            filename="test.pdf",
            file_type="application/pdf",
            file_size=1024,
            status="ready",
            chunk_count=5,
            metadata_={"storage_path": "/storage/path/file.pdf"},
        )

        mock_doc_result = MagicMock()
        mock_doc_result.scalar_one_or_none.return_value = mock_doc
        mock_kb_result = MagicMock()
        mock_kb_result.scalar_one_or_none.return_value = None
        mock_db.execute.side_effect = [mock_doc_result, mock_kb_result]

        mock_file_storage.delete.side_effect = Exception("Storage error")

        # Should not raise despite storage error
        await ingestion_service.delete_document(mock_db, doc_id)

        mock_db.delete.assert_called_once_with(mock_doc)

    async def test_delete_document_raises_when_not_found(self, ingestion_service):
        """Test deleting non-existent document raises ValueError."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await ingestion_service.delete_document(mock_db, uuid.uuid4())


class TestProcessDocumentJob:
    """Test ARQ worker job function."""

    async def test_process_document_job_success(self):
        """Test successful document processing job."""
        mock_rag_pipeline = AsyncMock()
        mock_rag_pipeline.ingest = AsyncMock(return_value=15)  # 15 chunks

        doc_id = str(uuid.uuid4())
        kb_id = str(uuid.uuid4())

        mock_doc = Document(
            id=uuid.UUID(doc_id),
            kb_id=uuid.UUID(kb_id),
            filename="test.pdf",
            file_type="application/pdf",
            file_size=1024,
            status="processing",
            chunk_count=0,
        )

        mock_kb = KnowledgeBase(
            id=uuid.UUID(kb_id),
            workspace_id=uuid.uuid4(),
            name="Test KB",
            doc_count=1,
            chunk_count=10,
        )

        with patch("sqlalchemy.ext.asyncio.create_async_engine"):
            with patch("sqlalchemy.orm.sessionmaker") as mock_sessionmaker:
                mock_db = AsyncMock()

                # Mock document and KB queries
                mock_doc_result = MagicMock()
                mock_doc_result.scalar_one_or_none.return_value = mock_doc
                mock_kb_result = MagicMock()
                mock_kb_result.scalar_one_or_none.return_value = mock_kb

                mock_db.execute.side_effect = [mock_doc_result, mock_kb_result]
                mock_db.__aenter__ = AsyncMock(return_value=mock_db)
                mock_db.__aexit__ = AsyncMock()

                mock_session = MagicMock()
                mock_session.return_value = mock_db
                mock_sessionmaker.return_value = mock_session

                ctx = {
                    "rag_pipeline": mock_rag_pipeline,
                    "database_url": "postgresql://test",
                }

                result = await process_document_job(
                    ctx=ctx,
                    doc_id=doc_id,
                    kb_id=kb_id,
                    filename="test.pdf",
                    content=b"pdf content",
                    metadata={},
                )

                assert result["status"] == "success"
                assert result["chunk_count"] == 15
                assert mock_doc.status == "ready"
                assert mock_doc.chunk_count == 15
                assert mock_kb.chunk_count == 25  # 10 + 15

    async def test_process_document_job_handles_error(self):
        """Test document processing job handles errors gracefully."""
        mock_rag_pipeline = AsyncMock()
        mock_rag_pipeline.ingest = AsyncMock(side_effect=Exception("Parse error"))
        mock_rag_pipeline.cleanup_partial_vectors = AsyncMock()

        doc_id = str(uuid.uuid4())
        kb_id = str(uuid.uuid4())

        mock_doc = Document(
            id=uuid.UUID(doc_id),
            kb_id=uuid.UUID(kb_id),
            filename="test.pdf",
            file_type="application/pdf",
            file_size=1024,
            status="processing",
            metadata_={},
        )

        with patch("sqlalchemy.ext.asyncio.create_async_engine"):
            with patch("sqlalchemy.orm.sessionmaker") as mock_sessionmaker:
                mock_db = AsyncMock()
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = mock_doc
                mock_db.execute.return_value = mock_result
                mock_db.__aenter__ = AsyncMock(return_value=mock_db)
                mock_db.__aexit__ = AsyncMock(return_value=False)

                mock_session = MagicMock()
                mock_session.return_value = mock_db
                mock_sessionmaker.return_value = mock_session

                ctx = {
                    "rag_pipeline": mock_rag_pipeline,
                    "database_url": "postgresql://test",
                }

                result = await process_document_job(
                    ctx=ctx,
                    doc_id=doc_id,
                    kb_id=kb_id,
                    filename="test.pdf",
                    content=b"pdf content",
                    metadata={},
                )

                assert result["status"] == "error"
                assert "Parse error" in result["error"]
                assert mock_doc.status == "failed"
                assert mock_doc.metadata_.get("error") == "Parse error"
                mock_rag_pipeline.cleanup_partial_vectors.assert_called_once()
