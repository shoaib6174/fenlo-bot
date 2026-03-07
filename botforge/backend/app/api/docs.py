"""
Document Management API

Endpoints for uploading, managing, and processing documents in knowledge bases.

Flow:
1. POST /upload → file validated → stored locally → ARQ job enqueued → status "processing"
2. ARQ worker → parse → chunk → embed → Pinecone → status "ready"
3. On failure → status "failed" → user can retry

RBAC:
- owner/admin: full access
- agent: read-only
- viewer: no access
"""

import io
import zipfile
from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db
from app.middleware.rbac import require_role
from app.models.knowledge_base import Document, KnowledgeBase
from app.models.user import User
from app.modules.rag.ingestion import enqueue_document_processing
from app.modules.rag.langchain_pipeline import LangChainRAGPipeline
from app.schemas.docs import DocumentListResponse, DocumentResponse
from app.services.file_storage import FileStorage, LocalStorage, S3Storage
from app.services.file_validator import FileValidationError, FileValidator

router = APIRouter(prefix="/api/v1/docs", tags=["documents"])
file_validator = FileValidator()


def get_rag_pipeline() -> LangChainRAGPipeline:
    """Get RAG pipeline instance"""
    return LangChainRAGPipeline(
        pinecone_api_key=settings.pinecone_api_key,
        pinecone_environment=settings.pinecone_environment,
        index_name=settings.pinecone_index_name,
    )


def get_file_storage() -> FileStorage:
    """Get file storage instance based on config"""
    if settings.file_storage_backend == "s3":
        return S3Storage(bucket_name=settings.s3_bucket_name)
    return LocalStorage(base_path="uploads")


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    kb_id: UUID = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> Document:
    """
    Upload a document to a knowledge base.

    Requires: admin or owner role

    Steps:
    1. Validate file (magic bytes, size, type)
    2. Store file in local/S3 storage
    3. Create document record with status="processing"
    4. Enqueue ARQ job for processing
    5. Return document ID immediately (async processing)
    """
    # Verify KB exists and belongs to workspace
    result = await session.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.workspace_id == current_user.workspace_id,
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Validate file (magic bytes, size, parse safety, embedded scripts)
    try:
        await file_validator.validate(
            file_content=file_content,
            filename=file.filename or "unknown",
        )
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Detect MIME type from content
    detected_mime = (
        file_validator.magic.from_buffer(file_content)
        if file_content
        else "application/octet-stream"
    )

    # Create document record
    doc = Document(
        id=uuid4(),
        kb_id=kb_id,
        filename=file.filename or "unknown",
        file_type=detected_mime,
        file_size=file_size,
        chunk_count=0,
        status="processing",
        metadata_={"original_filename": file.filename},
        created_at=datetime.now(UTC),
    )

    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    # Save file to storage (enables retry on failure)
    file_storage = get_file_storage()
    try:
        storage_path = await file_storage.save(
            workspace_id=current_user.workspace_id,
            document_id=doc.id,
            filename=file.filename or "unknown",
            content=file_content,
        )
        doc.metadata_ = {**(doc.metadata_ or {}), "storage_path": storage_path}
        await session.commit()
    except Exception as e:
        import structlog

        logger = structlog.get_logger(__name__)
        logger.warning("file_storage_save_failed", doc_id=str(doc.id), error=str(e))

    # Enqueue ARQ job for processing
    await enqueue_document_processing(
        doc_id=str(doc.id),
        kb_id=str(kb_id),
        file_content=file_content,
        filename=file.filename or "unknown",
    )

    return doc


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    kb_id: UUID | None = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
) -> DocumentListResponse:
    """
    List documents in a knowledge base (or all docs if kb_id not provided).

    Requires: agent role or higher
    """
    query = select(Document)

    # If kb_id provided, filter by it (and verify workspace access)
    if kb_id:
        # Verify KB belongs to workspace
        kb_result = await session.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.workspace_id == current_user.workspace_id,
            )
        )
        if not kb_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Knowledge base not found")

        query = query.where(Document.kb_id == kb_id)
    else:
        # Get all docs in workspace's KBs
        kb_result = await session.execute(
            select(KnowledgeBase.id).where(KnowledgeBase.workspace_id == current_user.workspace_id)
        )
        kb_ids = [kb_id for (kb_id,) in kb_result.all()]
        query = query.where(Document.kb_id.in_(kb_ids))

    query = query.order_by(Document.created_at.desc())
    result = await session.execute(query)
    docs = list(result.scalars().all())

    return DocumentListResponse(documents=docs, total=len(docs))


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
) -> Document:
    """
    Get a specific document by ID.

    Requires: agent role or higher
    """
    result = await session.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify workspace access via KB
    kb_result = await session.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == doc.kb_id,
            KnowledgeBase.workspace_id == current_user.workspace_id,
        )
    )
    if not kb_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")

    return doc


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> None:
    """
    Delete a document and its vectors.

    Requires: admin or owner role

    Steps:
    1. Delete vectors from Pinecone
    2. Delete file from storage
    3. Delete document record
    """
    result = await session.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify workspace access
    kb_result = await session.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == doc.kb_id,
            KnowledgeBase.workspace_id == current_user.workspace_id,
        )
    )
    kb = kb_result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete vectors from Pinecone
    rag_pipeline = get_rag_pipeline()
    try:
        await rag_pipeline.delete(doc_id=str(doc.id), kb_id=str(kb.id))
    except Exception as e:
        # Log error but continue with deletion
        import structlog

        logger = structlog.get_logger(__name__)
        logger.warning("vector_delete_failed", doc_id=str(doc.id), error=str(e))

    # Delete file from storage
    file_storage = get_file_storage()
    storage_path = (doc.metadata_ or {}).get("storage_path")
    if storage_path:
        try:
            await file_storage.delete(storage_path)
        except Exception as e:
            # Log error but continue with deletion
            import structlog

            logger = structlog.get_logger(__name__)
            logger.warning("file_delete_failed", doc_id=str(doc.id), error=str(e))

    # Delete document record
    await session.delete(doc)
    await session.commit()

    # Update KB doc count
    kb.doc_count -= 1
    await session.commit()


@router.post("/{doc_id}/retry", response_model=DocumentResponse)
async def retry_document_processing(
    doc_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> Document:
    """
    Retry processing a failed document.

    Requires: admin or owner role

    Steps:
    1. Verify document status is "failed"
    2. Clean up any partial vectors (RAGPipeline.cleanup_partial_vectors())
    3. Reset status to "processing"
    4. Re-enqueue ARQ job
    """
    result = await session.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify workspace access
    kb_result = await session.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == doc.kb_id,
            KnowledgeBase.workspace_id == current_user.workspace_id,
        )
    )
    if not kb_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")

    if doc.status != "failed":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry document with status '{doc.status}'. Only failed documents can be retried.",
        )

    # Clean up partial vectors
    rag_pipeline = get_rag_pipeline()
    try:
        kb_result_retry = await session.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == doc.kb_id)
        )
        kb_for_retry = kb_result_retry.scalar_one()
        await rag_pipeline.cleanup_partial_vectors(doc_id=str(doc.id), kb_id=str(kb_for_retry.id))
    except Exception as e:
        import structlog

        logger = structlog.get_logger(__name__)
        logger.warning("partial_vector_cleanup_failed", doc_id=str(doc.id), error=str(e))

    # Reset status
    doc.status = "processing"
    await session.commit()

    # Re-enqueue ARQ job
    file_storage = get_file_storage()
    storage_path = (doc.metadata_ or {}).get("storage_path")
    if storage_path:
        try:
            # Read file from storage
            file_content = await file_storage.retrieve(storage_path)

            # Enqueue processing job
            await enqueue_document_processing(
                doc_id=str(doc.id),
                kb_id=str(doc.kb_id),
                file_content=file_content,
                filename=doc.filename,
            )
        except Exception as e:
            doc.status = "failed"
            await session.commit()
            raise HTTPException(
                status_code=500, detail=f"Failed to re-enqueue document: {e}"
            ) from e
    else:
        doc.status = "failed"
        doc.metadata_ = doc.metadata_ or {}
        doc.metadata_["error"] = "No stored file found for retry"
        await session.commit()
        raise HTTPException(
            status_code=400, detail="Document file not found in storage. Please re-upload."
        )

    return doc


# --- Batch upload ---

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv"}
_batch_logger = structlog.get_logger("docs.batch")


@router.post("/upload-batch")
async def upload_batch(
    kb_id: UUID = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    Upload a ZIP file containing multiple documents.

    Extracts the ZIP, validates each file, creates Document records,
    and enqueues individual processing jobs.
    """
    # Verify KB exists and belongs to workspace
    result = await session.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.workspace_id == current_user.workspace_id,
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    zip_bytes = await file.read()
    if len(zip_bytes) > 50 * 1024 * 1024:  # 50 MB limit
        raise HTTPException(status_code=400, detail="ZIP file exceeds 50 MB limit")

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as e:
        raise HTTPException(status_code=400, detail="Invalid ZIP file") from e

    results: list[dict] = []
    file_storage = get_file_storage()

    for info in zf.infolist():
        if info.is_dir():
            continue
        fname = info.filename.split("/")[-1]  # strip directory paths
        if not fname or fname.startswith("."):
            continue

        ext = "." + fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        if ext not in _ALLOWED_EXTENSIONS:
            results.append(
                {"filename": fname, "status": "skipped", "reason": f"unsupported type: {ext}"}
            )
            continue

        content = zf.read(info.filename)
        if len(content) == 0:
            results.append({"filename": fname, "status": "skipped", "reason": "empty file"})
            continue

        # Create document record
        doc = Document(
            id=uuid4(),
            kb_id=kb_id,
            filename=fname,
            file_type=ext.lstrip("."),
            file_size=len(content),
            chunk_count=0,
            status="processing",
            metadata_={"original_filename": fname, "batch_upload": True},
            created_at=datetime.now(UTC),
        )
        session.add(doc)
        await session.flush()

        # Save to storage
        try:
            storage_path = await file_storage.save(
                workspace_id=current_user.workspace_id,
                document_id=doc.id,
                filename=fname,
                content=content,
            )
            doc.metadata_ = {**(doc.metadata_ or {}), "storage_path": storage_path}
        except Exception as e:
            _batch_logger.warning("batch_storage_save_failed", filename=fname, error=str(e))

        # Enqueue processing
        await enqueue_document_processing(
            doc_id=str(doc.id),
            kb_id=str(kb_id),
            file_content=content,
            filename=fname,
        )
        results.append({"filename": fname, "status": "processing", "document_id": str(doc.id)})

    await session.commit()
    _batch_logger.info("batch_upload_complete", total=len(results), kb_id=str(kb_id))

    return {"documents": results, "total": len(results)}
