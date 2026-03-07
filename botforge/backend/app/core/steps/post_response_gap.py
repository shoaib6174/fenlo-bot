"""
Post-Response Knowledge Gap Detection Step

Checks if the LLM response indicates a knowledge gap (e.g. "I don't know" phrases)
even when RAG chunks were returned. Complements the no-chunks detection already
handled in RAGRetrievalStep.
"""

import structlog

from app.core.engine import MessageContext
from app.dependencies import get_db
from app.modules.rag.knowledge_gaps import should_trigger_gap_detection

logger = structlog.get_logger(__name__)

# Reuse the same lazy singleton as rag_retrieval.py
_gap_detector = None


def _get_gap_detector():
    global _gap_detector
    if _gap_detector is None:
        from app.modules.rag.knowledge_gaps import KnowledgeGapDetector

        _gap_detector = KnowledgeGapDetector()
    return _gap_detector


class PostResponseGapStep:
    """
    Detect knowledge gaps from LLM responses that admit lack of knowledge.

    Runs after LLMStreamStep (needs context.response).
    Only fires when chunks WERE returned but the response still indicates
    the bot couldn't answer — the no-chunks case is already handled by
    RAGRetrievalStep.
    """

    async def execute(self, context: MessageContext) -> MessageContext:
        # Need both a response and rag_chunks present (no-chunks case handled elsewhere)
        if not context.response or not context.rag_chunks:
            return context

        # Check if the response indicates a gap
        if not should_trigger_gap_detection(context.rag_chunks, context.response):
            return context

        # Log the gap (fire-and-forget, never block the pipeline)
        try:
            raw_query = context.metadata.get("original_message", context.message)
            detector = _get_gap_detector()
            async for session in get_db():
                await detector.log_gap(
                    query=raw_query,
                    workspace_id=str(context.workspace_id),
                    conversation_id=str(context.conversation_id)
                    if context.conversation_id
                    else None,
                    session=session,
                )
            logger.info(
                "post_response_gap_logged",
                workspace_id=str(context.workspace_id),
                query=context.message[:100],
            )
        except Exception as e:
            logger.warning("post_response_gap_logging_failed", error=str(e))

        return context
