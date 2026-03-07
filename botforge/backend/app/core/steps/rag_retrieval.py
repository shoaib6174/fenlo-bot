"""
RAG Retrieval Step

Retrieves relevant chunks from the knowledge base and adds them to the context.
Only runs if the workspace has RAG enabled.

When no relevant chunks are found, logs a knowledge gap for later review.
Includes a Redis-backed semantic cache (hash-based) with 1-hour TTL.
"""

import hashlib
import json

import structlog
from sqlalchemy import select

from app.core.engine import MessageContext
from app.core.redis import get_resilient_redis
from app.dependencies import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.workspace import Workspace
from app.modules.rag.pipeline import get_rag_pipeline

logger = structlog.get_logger(__name__)

# Cache TTL in seconds (1 hour)
RAG_CACHE_TTL = 3600

# Lazy singleton — avoids loading sentence-transformers until first gap is detected
_gap_detector = None


def _get_gap_detector():
    global _gap_detector
    if _gap_detector is None:
        from app.modules.rag.knowledge_gaps import KnowledgeGapDetector

        _gap_detector = KnowledgeGapDetector()
    return _gap_detector


def _cache_key(workspace_id: str, query: str) -> str:
    """Build deterministic cache key from workspace + normalized query."""
    normalized = query.strip().lower()
    query_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"rag_cache:{workspace_id}:{query_hash}"


class RAGRetrievalStep:
    """
    Pipeline step that retrieves relevant chunks from the knowledge base.

    - Checks if workspace has RAG enabled
    - Retrieves top-5 relevant chunks
    - Adds chunks and citations to context
    - Logs knowledge gaps when no chunks found
    - No-op when disabled (preserves Phase 1 behavior)
    """

    def __init__(self):
        self.rag_pipeline = get_rag_pipeline()  # None if Pinecone not configured

    async def execute(self, context: MessageContext) -> MessageContext:
        """
        Execute RAG retrieval.

        Args:
            context: Message context with user query

        Returns:
            Context with rag_chunks and citations populated (if RAG enabled)
        """
        if self.rag_pipeline is None:
            logger.debug("rag_skipped_no_pinecone_key")
            return context

        try:
            # Get workspace settings to check if RAG is enabled
            async for session in get_db():
                workspace = await session.get(Workspace, context.workspace_id)
                if not workspace:
                    logger.warning("workspace_not_found", workspace_id=str(context.workspace_id))
                    return context

                settings = workspace.settings or {}
                rag_enabled = settings.get("rag_enabled", True)  # Default to True
                kb_id = settings.get("default_kb_id")

                if not rag_enabled:
                    logger.debug("rag_disabled", workspace_id=str(context.workspace_id))
                    return context

                # Auto-detect KB if not explicitly configured
                if not kb_id:
                    result = await session.execute(
                        select(KnowledgeBase.id)
                        .where(KnowledgeBase.workspace_id == context.workspace_id)
                        .order_by(KnowledgeBase.created_at.desc())
                        .limit(1)
                    )
                    row = result.scalar_one_or_none()
                    if not row:
                        logger.debug("no_kb_found", workspace_id=str(context.workspace_id))
                        return context
                    kb_id = str(row)
                    logger.info(
                        "rag_auto_detected_kb",
                        workspace_id=str(context.workspace_id),
                        kb_id=kb_id,
                    )

                # --- Semantic cache lookup ---
                cache = get_resilient_redis()
                cache_k = _cache_key(str(context.workspace_id), context.message)
                try:
                    cached = await cache.get(cache_k)
                    if cached:
                        hit = json.loads(cached)
                        context.rag_chunks = hit["chunks"]
                        context.citations = hit["citations"]
                        context.metadata["rag_cache_hit"] = True
                        logger.info(
                            "rag_cache_hit",
                            workspace_id=str(context.workspace_id),
                            chunk_count=len(hit["chunks"]),
                        )
                        return context
                except Exception as cache_err:
                    logger.debug("rag_cache_read_failed", error=str(cache_err))

                # --- Pinecone retrieve ---
                chunks = await self.rag_pipeline.retrieve(
                    query=context.message, kb_id=kb_id, top_k=5
                )

                if not chunks:
                    logger.info(
                        "no_rag_chunks_found",
                        workspace_id=str(context.workspace_id),
                        query=context.message,
                    )

                    # Log knowledge gap (fire-and-forget, never block chat)
                    # Use original message (before PromptGuard sandwiching)
                    try:
                        raw_query = context.metadata.get("original_message", context.message)
                        detector = _get_gap_detector()
                        await detector.log_gap(
                            query=raw_query,
                            workspace_id=str(context.workspace_id),
                            conversation_id=str(context.conversation_id)
                            if context.conversation_id
                            else None,
                            session=session,
                        )
                        logger.info(
                            "knowledge_gap_logged",
                            workspace_id=str(context.workspace_id),
                            query=context.message,
                        )
                    except Exception as gap_err:
                        logger.warning(
                            "knowledge_gap_logging_failed",
                            error=str(gap_err),
                        )

                    return context

                # Add chunks to context
                context.rag_chunks = [
                    {
                        "text": chunk.chunk_text,
                        "metadata": chunk.metadata,
                        "score": chunk.relevance_score,
                    }
                    for chunk in chunks
                ]

                # Build citations
                context.citations = [
                    {
                        "doc_name": chunk.doc_name,
                        "page_number": chunk.page_number,
                        "chunk_text": chunk.chunk_text[:200],  # Truncate for display
                        "relevance_score": chunk.relevance_score,
                        "document_id": chunk.doc_id,
                    }
                    for chunk in chunks
                ]

                # --- Store in cache ---
                try:
                    payload = json.dumps(
                        {"chunks": context.rag_chunks, "citations": context.citations}
                    )
                    await cache.set(cache_k, payload, ex=RAG_CACHE_TTL)
                except Exception as cache_err:
                    logger.debug("rag_cache_write_failed", error=str(cache_err))

                logger.info(
                    "rag_chunks_retrieved",
                    workspace_id=str(context.workspace_id),
                    chunk_count=len(chunks),
                    top_score=chunks[0].relevance_score if chunks else None,
                )

                return context

        except Exception as e:
            logger.error(
                "rag_retrieval_failed",
                workspace_id=str(context.workspace_id),
                error=str(e),
                exc_info=True,
            )
            # Don't halt pipeline on RAG failure - degrade gracefully
            return context
