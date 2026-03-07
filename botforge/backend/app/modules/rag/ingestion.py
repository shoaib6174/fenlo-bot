"""Document ingestion service.

Flow: Upload → Validate → Store → Enqueue ARQ job
ARQ Worker: Parse → Chunk → Embed → Store in Pinecone
Status: processing → ready / failed
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, BinaryIO

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import Document, KnowledgeBase
from app.services.file_storage import FileStorage

if TYPE_CHECKING:
    from app.modules.rag.langchain_pipeline import LangChainRAGPipeline


class DocumentIngestionService:
    """Service for document upload, validation, and ingestion orchestration"""

    def __init__(
        self,
        redis_url: str,
        rag_pipeline: LangChainRAGPipeline,
        file_storage: FileStorage,
    ):
        """Initialize ingestion service.

        Args:
            redis_url: Redis connection URL for ARQ
            rag_pipeline: RAG pipeline for embeddings
            file_storage: File storage backend
        """
        self.redis_settings = RedisSettings.from_dsn(redis_url)
        self.rag_pipeline = rag_pipeline
        self.file_storage = file_storage

    async def upload_document(
        self,
        db: AsyncSession,
        kb_id: uuid.UUID,
        workspace_id: uuid.UUID,
        filename: str,
        file_type: str,
        file_size: int,
        content: bytes | BinaryIO,
        metadata: dict | None = None,
    ) -> Document:
        """Upload and enqueue document for processing.

        Args:
            db: Database session
            kb_id: Knowledge base ID
            workspace_id: Workspace ID for file storage organization
            filename: Original filename
            file_type: MIME type
            file_size: File size in bytes
            content: File content (bytes or file-like object)
            metadata: Optional document metadata

        Returns:
            Created Document record with status='processing'
        """
        # Create document record
        doc = Document(
            id=uuid.uuid4(),
            kb_id=kb_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            status="processing",
            metadata_=metadata or {},
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        # Save file to storage
        content_bytes = content if isinstance(content, bytes) else content.read()
        storage_path = await self.file_storage.save(
            workspace_id=workspace_id,
            document_id=doc.id,
            filename=filename,
            content=content_bytes,
        )

        # Update document with storage path
        doc.metadata_ = doc.metadata_ or {}
        doc.metadata_["storage_path"] = storage_path
        await db.commit()

        # Enqueue ARQ job for background processing
        redis = await create_pool(self.redis_settings)
        await redis.enqueue_job(
            "process_document",
            doc_id=str(doc.id),
            kb_id=str(kb_id),
            filename=filename,
            content=content_bytes,
            metadata=metadata or {},
        )

        return doc

    async def get_document_status(self, db: AsyncSession, doc_id: uuid.UUID) -> Document | None:
        """Get document processing status.

        Args:
            db: Database session
            doc_id: Document ID

        Returns:
            Document record or None if not found
        """
        result = await db.execute(select(Document).where(Document.id == doc_id))
        return result.scalar_one_or_none()

    async def retry_failed_document(self, db: AsyncSession, doc_id: uuid.UUID) -> Document:
        """Retry processing a failed document.

        Args:
            db: Database session
            doc_id: Document ID

        Returns:
            Updated Document record with status='processing'
        """
        result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()

        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        if doc.status != "failed":
            raise ValueError(f"Document {doc_id} is not in failed state")

        # Clean up partial vectors from failed attempt
        await self.rag_pipeline.cleanup_partial_vectors(str(doc.id), str(doc.kb_id))

        # Retrieve file content from storage
        storage_path = doc.metadata_.get("storage_path")
        if not storage_path:
            raise ValueError(f"Document {doc_id} has no storage path")

        content = await self.file_storage.retrieve(storage_path)

        # Reset status and re-enqueue
        doc.status = "processing"
        doc.processed_at = None
        if "error" in doc.metadata_:
            del doc.metadata_["error"]
        await db.commit()

        # Re-enqueue ARQ job
        redis = await create_pool(self.redis_settings)
        await redis.enqueue_job(
            "process_document",
            doc_id=str(doc.id),
            kb_id=str(doc.kb_id),
            filename=doc.filename,
            content=content,
            metadata=doc.metadata_ or {},
        )

        return doc

    async def delete_document(self, db: AsyncSession, doc_id: uuid.UUID) -> None:
        """Delete document and its vectors.

        Args:
            db: Database session
            doc_id: Document ID
        """
        result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()

        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        # Delete vectors from Pinecone
        await self.rag_pipeline.delete(str(doc.id), str(doc.kb_id))

        # Delete file from storage
        storage_path = doc.metadata_.get("storage_path")
        if storage_path:
            try:
                await self.file_storage.delete(storage_path)
            except Exception as e:
                # Log error but don't fail the whole operation
                import structlog

                logger = structlog.get_logger(__name__)
                logger.warning(
                    "file_storage.delete_failed",
                    doc_id=str(doc_id),
                    storage_path=storage_path,
                    error=str(e),
                )

        # Update KB counts
        kb_result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == doc.kb_id))
        kb = kb_result.scalar_one_or_none()
        if kb:
            kb.doc_count = max(0, kb.doc_count - 1)
            kb.chunk_count = max(0, kb.chunk_count - doc.chunk_count)

        # Delete document record
        await db.delete(doc)
        await db.commit()


async def enqueue_document_processing(
    doc_id: str,
    kb_id: str,
    file_content: bytes,
    filename: str,
    redis_url: str | None = None,
) -> None:
    """Helper function to enqueue document processing job.

    Args:
        doc_id: Document ID
        kb_id: Knowledge base ID
        file_content: File content bytes
        filename: Original filename
        redis_url: Optional Redis URL (defaults to config)
    """
    from app.config import settings

    redis_settings = RedisSettings.from_dsn(redis_url or settings.redis_url)

    redis = await create_pool(redis_settings)
    await redis.enqueue_job(
        "process_document",
        doc_id=doc_id,
        kb_id=kb_id,
        filename=filename,
        content=file_content,
        metadata={},
    )


async def process_document_job(
    ctx: dict,
    doc_id: str,
    kb_id: str,
    filename: str,
    content: bytes,
    metadata: dict,
) -> dict:
    """ARQ worker job: Parse, chunk, embed, and store document.

    This runs in the ARQ worker process, separate from the API server.

    Args:
        ctx: ARQ context (contains redis, db connection, etc.)
        doc_id: Document ID
        kb_id: Knowledge base ID
        filename: Original filename
        content: File content bytes
        metadata: Document metadata

    Returns:
        Job result with status and chunk count
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    # Get dependencies from context
    rag_pipeline: LangChainRAGPipeline = ctx.get("rag_pipeline")
    database_url: str = ctx.get("database_url")

    # Create DB session for worker
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as db:
            # Update status to processing
            result = await db.execute(select(Document).where(Document.id == uuid.UUID(doc_id)))
            doc = result.scalar_one_or_none()

            if not doc:
                return {"status": "error", "error": "Document not found"}

            # Ingest document
            chunk_count = await rag_pipeline.ingest(
                content=content,
                filename=filename,
                kb_id=kb_id,
                doc_id=doc_id,
                metadata=metadata,
            )

            # Update document status
            doc.status = "ready"
            doc.chunk_count = chunk_count
            doc.processed_at = datetime.now(UTC)

            # Update KB counts
            kb_result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == uuid.UUID(kb_id))
            )
            kb = kb_result.scalar_one_or_none()
            if kb:
                kb.chunk_count += chunk_count

            await db.commit()

            return {"status": "success", "chunk_count": chunk_count}

    except Exception as e:
        # On failure: clean up partial vectors and mark as failed
        async with async_session() as db:
            result = await db.execute(select(Document).where(Document.id == uuid.UUID(doc_id)))
            doc = result.scalar_one_or_none()

            if doc:
                # Clean up partial vectors
                await rag_pipeline.cleanup_partial_vectors(doc_id, kb_id)

                # Mark as failed
                doc.status = "failed"
                doc.metadata_ = doc.metadata_ or {}
                doc.metadata_["error"] = str(e)
                doc.processed_at = datetime.now(UTC)
                await db.commit()

        return {"status": "error", "error": str(e)}
