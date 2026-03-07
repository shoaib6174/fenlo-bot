"""Handoff Context Assembly — Enriched data for agent takeover.

Assembles comprehensive context when a conversation is escalated to a human agent.
Includes citations, sentiment timeline, intent history, quality scores, and lead score.

Implements Spec Panel Review E-02 data assembly rules:
- recent_messages: Last 20 messages (all roles)
- rag_context: Top 5 RAG chunks by relevance, deduplicated
- quality_scores: Per-message scores, null for user messages
- sentiment_timeline: Sentiment labels, null if no analysis
- lead_score: Current cumulative score
- escalation_reason: Human-readable trigger string

Usage:
    context = await assemble_handoff_context(conversation_id, db)
    # Returns dict with all context data
"""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message

logger = structlog.get_logger(__name__)


async def assemble_handoff_context(
    conversation_id: UUID,
    db: AsyncSession,
    message_limit: int = 20,
    rag_chunk_limit: int = 5,
) -> dict:
    """Assemble enriched handoff context for agent takeover.

    Args:
        conversation_id: Target conversation UUID
        db: Database session
        message_limit: Number of recent messages to include (default: 20)
        rag_chunk_limit: Max RAG chunks to include (default: 5)

    Returns:
        Dictionary with handoff context data:
        - conversation_id: str
        - channel: str
        - contact: dict (phone/email, name if available)
        - lead_score: int
        - escalation_reason: str | None
        - message_count: int
        - sentiment_timeline: list[dict] ({timestamp, sentiment})
        - intent_history: list[dict] ({timestamp, intent})
        - rag_contexts: list[dict] ({source, content, score})
        - quality_scores: list[dict] ({timestamp, score})
        - recent_messages: list[dict]

    Raises:
        ValueError: If conversation not found
    """
    # Look up conversation
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise ValueError(f"Conversation {conversation_id} not found")

    # Get recent messages (last N, ordered by created_at DESC)
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(message_limit)
    )
    result = await db.execute(stmt)
    recent_messages_raw = result.scalars().all()

    # Reverse to chronological order (oldest first)
    recent_messages_raw = list(reversed(recent_messages_raw))

    # Build recent_messages array
    recent_messages = []
    sentiment_timeline = []
    intent_history = []
    quality_scores = []

    for msg in recent_messages_raw:
        recent_messages.append(
            {
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "sentiment": msg.sentiment,
                "intent": msg.intent,
                "quality_score": msg.quality_score,
            }
        )
        timestamp = msg.created_at.isoformat() if msg.created_at else None
        sentiment_timeline.append({"timestamp": timestamp, "sentiment": msg.sentiment})
        intent_history.append({"timestamp": timestamp, "intent": msg.intent})
        quality_scores.append({"timestamp": timestamp, "score": msg.quality_score})

    # Extract RAG context from message citations column
    rag_context = []
    seen_chunks = set()  # Deduplication by (doc_name, chunk_text) tuple

    for msg in recent_messages_raw:
        if not msg.citations or not isinstance(msg.citations, list):
            continue

        for citation in msg.citations:
            if not isinstance(citation, dict):
                continue

            doc_name = citation.get("doc_name")
            chunk_text = citation.get("chunk")
            relevance = citation.get("relevance", 0.0)

            if not doc_name or not chunk_text:
                continue

            # Deduplicate by (doc_name, first 100 chars of chunk)
            dedup_key = (doc_name, chunk_text[:100])
            if dedup_key in seen_chunks:
                continue

            seen_chunks.add(dedup_key)
            rag_context.append(
                {
                    "source": doc_name,
                    "content": chunk_text,
                    "score": relevance,
                }
            )

            # Stop at limit
            if len(rag_context) >= rag_chunk_limit:
                break

        if len(rag_context) >= rag_chunk_limit:
            break

    # Sort RAG context by relevance (highest first)
    rag_context.sort(key=lambda x: x["score"], reverse=True)

    # Build escalation reason from metadata
    escalation_reason = None
    if conversation.metadata_ and "escalation_trigger" in conversation.metadata_:
        trigger = conversation.metadata_["escalation_trigger"]
        if isinstance(trigger, dict):
            rule_type = trigger.get("rule_type", "unknown")
            matched = trigger.get("matched", "")
            escalation_reason = f"{rule_type}: {matched}"
        elif isinstance(trigger, str):
            escalation_reason = trigger

    # Build contact info
    contact = {}
    if conversation.contact_info:
        contact = dict(conversation.contact_info)
    if conversation.contact_name:
        contact["name"] = conversation.contact_name
    if conversation.external_id:
        # For WhatsApp: external_id is phone number
        if conversation.channel == "whatsapp":
            contact["phone"] = conversation.external_id

    # Get total message count
    stmt = select(Message.id).where(Message.conversation_id == conversation_id)
    result = await db.execute(stmt)
    message_count = len(result.scalars().all())

    # Assemble final context
    context = {
        "conversation_id": str(conversation.id),
        "channel": conversation.channel,
        "contact": contact,
        "lead_score": conversation.lead_score or 0,
        "escalation_reason": escalation_reason,
        "message_count": message_count,
        "sentiment_timeline": sentiment_timeline,
        "intent_history": intent_history,
        "rag_contexts": rag_context,
        "quality_scores": quality_scores,
        "recent_messages": recent_messages,
    }

    logger.info(
        "handoff.context_assembled",
        conversation_id=str(conversation_id),
        channel=conversation.channel,
        message_count=message_count,
        rag_chunk_count=len(rag_context),
        lead_score=conversation.lead_score,
    )

    return context
