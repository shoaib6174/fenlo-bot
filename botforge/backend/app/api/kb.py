"""
Knowledge Base CRUD API

Endpoints for managing knowledge bases and their documents.

RBAC:
- owner/admin: full CRUD access
- agent: read-only access
- viewer: no access
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db
from app.middleware.rbac import require_role
from app.models.knowledge_base import Document, KnowledgeBase, KnowledgeGap
from app.models.user import User
from app.models.workspace import Workspace
from app.modules.rag.ingestion import enqueue_document_processing
from app.modules.rag.langchain_pipeline import LangChainRAGPipeline
from app.schemas.docs import DocumentResponse
from app.schemas.kb import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
    KnowledgeGapResponse,
)
from app.services.file_storage import FileStorage, LocalStorage, S3Storage
from app.services.file_validator import FileValidationError, FileValidator

router = APIRouter(prefix="/api/v1/kb", tags=["knowledge-base"])
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


@router.post("/", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    kb_data: KnowledgeBaseCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> KnowledgeBase:
    """
    Create a new knowledge base.

    Requires: admin or owner role

    The KB name becomes the Pinecone namespace for vector isolation.
    """
    kb = KnowledgeBase(
        id=uuid4(),
        workspace_id=current_user.workspace_id,
        name=kb_data.name,
        description=kb_data.description,
        doc_count=0,
        chunk_count=0,
        created_at=datetime.now(UTC),
    )

    session.add(kb)
    await session.flush()

    # Auto-set workspace RAG settings if this is the first KB
    workspace = await session.get(Workspace, current_user.workspace_id)
    if workspace:
        updated_settings = dict(workspace.settings or {})
        if not updated_settings.get("default_kb_id"):
            updated_settings["default_kb_id"] = str(kb.id)
            updated_settings["rag_enabled"] = True
            workspace.settings = updated_settings

    await session.commit()
    await session.refresh(kb)

    return kb


@router.get("/", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
) -> list[KnowledgeBase]:
    """
    List all knowledge bases for the current workspace.

    Requires: agent role or higher
    """
    result = await session.execute(
        select(KnowledgeBase)
        .where(KnowledgeBase.workspace_id == current_user.workspace_id)
        .order_by(KnowledgeBase.created_at.desc())
    )
    return list(result.scalars().all())


# ── Knowledge Gap endpoints (before /{kb_id} to avoid route conflict) ──


@router.get("/gaps", response_model=list[KnowledgeGapResponse])
async def list_knowledge_gaps(
    kb_id: UUID | None = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
) -> list[dict]:
    """
    List knowledge gaps for the current workspace.

    Gaps are workspace-scoped (not per-KB). The kb_id param is accepted
    for frontend compatibility but gaps are returned for the whole workspace.

    Requires: agent role or higher
    """
    result = await session.execute(
        select(KnowledgeGap)
        .where(KnowledgeGap.workspace_id == current_user.workspace_id)
        .order_by(KnowledgeGap.occurrence_count.desc())
        .limit(50)
    )
    gaps = result.scalars().all()

    # Map backend status 'open' → frontend status 'active'
    return [
        {
            "id": gap.id,
            "query_text": gap.query_text,
            "occurrence_count": gap.occurrence_count,
            "first_asked_at": gap.created_at,
            "last_asked_at": gap.last_asked_at,
            "status": "active" if gap.status == "open" else gap.status,
            "kb_id": None,
            "workspace_id": gap.workspace_id,
        }
        for gap in gaps
    ]


@router.post("/gaps/{gap_id}/dismiss", status_code=200)
async def dismiss_knowledge_gap(
    gap_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> dict:
    """
    Dismiss a knowledge gap (mark as irrelevant).

    Requires: admin or owner role
    """
    result = await session.execute(
        select(KnowledgeGap).where(
            KnowledgeGap.id == gap_id,
            KnowledgeGap.workspace_id == current_user.workspace_id,
        )
    )
    gap = result.scalar_one_or_none()

    if not gap:
        raise HTTPException(status_code=404, detail="Knowledge gap not found")

    gap.status = "dismissed"
    await session.commit()

    return {"status": "dismissed", "id": str(gap_id)}


@router.post("/gaps/{gap_id}/address", response_model=DocumentResponse)
async def address_knowledge_gap(
    gap_id: UUID,
    kb_id: UUID = Form(...),
    text_content: str | None = Form(None),
    file: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> Document:
    """
    Address a knowledge gap by adding content to a knowledge base.

    Requires: admin or owner role

    Accepts either text_content (creates a .txt document) or a file upload.
    At least one must be provided. The gap is marked as "addressed" and a
    document is created and enqueued for processing.
    """
    if not text_content and not file:
        raise HTTPException(
            status_code=400,
            detail="Either text_content or file must be provided",
        )

    # Verify gap exists and belongs to workspace
    result = await session.execute(
        select(KnowledgeGap).where(
            KnowledgeGap.id == gap_id,
            KnowledgeGap.workspace_id == current_user.workspace_id,
        )
    )
    gap = result.scalar_one_or_none()
    if not gap:
        raise HTTPException(status_code=404, detail="Knowledge gap not found")

    # Verify KB exists and belongs to workspace
    kb_result = await session.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.workspace_id == current_user.workspace_id,
        )
    )
    kb = kb_result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # Build file content and filename
    if text_content:
        short_id = str(gap_id)[:8]
        filename = f"gap-{short_id}.txt"
        file_content = text_content.encode("utf-8")
        file_type = "text/plain"
    else:
        assert file is not None
        file_content = await file.read()
        filename = file.filename or "unknown"

        # Validate uploaded file
        try:
            await file_validator.validate(
                file_content=file_content,
                filename=filename,
            )
        except FileValidationError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        file_type = (
            file_validator.magic.from_buffer(file_content)
            if file_content
            else "application/octet-stream"
        )

    file_size = len(file_content)

    # Create document record
    doc = Document(
        id=uuid4(),
        kb_id=kb_id,
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        chunk_count=0,
        status="processing",
        metadata_={
            "original_filename": filename,
            "source": "knowledge_gap",
            "gap_id": str(gap_id),
            "gap_query": gap.query_text,
        },
        created_at=datetime.now(UTC),
    )

    session.add(doc)

    # Mark gap as addressed
    gap.status = "addressed"

    await session.commit()
    await session.refresh(doc)

    # Save file to storage
    file_storage = get_file_storage()
    try:
        storage_path = await file_storage.save(
            workspace_id=current_user.workspace_id,
            document_id=doc.id,
            filename=filename,
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
        filename=filename,
    )

    return doc


# ── KB CRUD by ID ──────────────────────────────────────────────


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
) -> KnowledgeBase:
    """
    Get a specific knowledge base by ID.

    Requires: agent role or higher
    """
    result = await session.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.workspace_id == current_user.workspace_id,
        )
    )
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    return kb


@router.patch("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: UUID,
    kb_update: KnowledgeBaseUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> KnowledgeBase:
    """
    Update a knowledge base.

    Requires: admin or owner role
    """
    result = await session.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.workspace_id == current_user.workspace_id,
        )
    )
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # Update fields
    if kb_update.name is not None:
        kb.name = kb_update.name
    if kb_update.description is not None:
        kb.description = kb_update.description

    await session.commit()
    await session.refresh(kb)

    return kb


@router.delete("/{kb_id}", status_code=204)
async def delete_knowledge_base(
    kb_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> None:
    """
    Delete a knowledge base and all its documents/vectors.

    Requires: admin or owner role

    This is a hard delete that removes:
    1. All document records from the database
    2. All vector embeddings from Pinecone (entire namespace)
    3. The knowledge base record itself

    WARNING: This operation cannot be undone.
    """
    result = await session.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.workspace_id == current_user.workspace_id,
        )
    )
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # Get all documents in this KB
    docs_result = await session.execute(select(Document).where(Document.kb_id == kb_id))
    documents = docs_result.scalars().all()

    # Delete vectors from Pinecone for each document
    rag_pipeline = get_rag_pipeline()
    file_storage = get_file_storage()

    for doc in documents:
        # Delete vectors
        try:
            await rag_pipeline.delete(doc_id=str(doc.id), kb_id=str(kb.id))
        except Exception as e:
            import structlog

            logger = structlog.get_logger(__name__)
            logger.warning("vector_delete_failed_kb_deletion", doc_id=str(doc.id), error=str(e))

        # Delete file from storage
        storage_path = (doc.metadata_ or {}).get("storage_path")
        if storage_path:
            try:
                await file_storage.delete(storage_path)
            except Exception as e:
                import structlog

                logger = structlog.get_logger(__name__)
                logger.warning("file_delete_failed_kb_deletion", doc_id=str(doc.id), error=str(e))

        # Delete document record
        await session.delete(doc)

    # Delete the KB
    await session.delete(kb)
    await session.commit()
