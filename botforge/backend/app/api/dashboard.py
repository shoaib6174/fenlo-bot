"""
Dashboard API routes - summary statistics and recent activity.

Provides:
- Dashboard summary with workspace statistics
- Recent conversations overview
- Feature availability flags
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.dependencies import get_db
from app.models.conversation import Conversation, Message
from app.models.knowledge_base import Document, KnowledgeBase, KnowledgeGap
from app.models.workspace import Workspace

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


# Response Schemas
class RecentConversation(BaseModel):
    """Recent conversation summary"""

    id: str
    first_message: str
    last_message_at: datetime
    message_count: int
    sentiment: Literal["positive", "neutral", "negative"] | None = None
    lead_score: int | None = None


class FeatureFlags(BaseModel):
    """Feature availability flags"""

    rag_enabled: bool
    voice_enabled: bool
    channels_enabled: bool
    analytics_enabled: bool


class DashboardSummary(BaseModel):
    """Dashboard summary response"""

    conversations_count: int
    messages_count: int
    documents_count: int
    knowledge_gaps_count: int
    avg_quality_score: float | None = None
    recent_conversations: list[RecentConversation]
    features: FeatureFlags


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get dashboard summary with workspace statistics.

    Returns:
    - Conversation, message, document, and knowledge gap counts
    - Average quality score across messages
    - Recent 5 conversations with preview
    - Feature availability flags

    Accessible by: any authenticated user
    """
    user, workspace_id, role = current_user

    # Query conversations count
    conversations_count_stmt = select(func.count(Conversation.id)).where(
        Conversation.workspace_id == workspace_id
    )
    conversations_count = await db.scalar(conversations_count_stmt) or 0

    # Query messages count
    messages_count_stmt = (
        select(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.workspace_id == workspace_id)
    )
    messages_count = await db.scalar(messages_count_stmt) or 0

    # Query documents count (across all knowledge bases in workspace)
    documents_count_stmt = (
        select(func.count(Document.id))
        .join(KnowledgeBase, Document.kb_id == KnowledgeBase.id)
        .where(KnowledgeBase.workspace_id == workspace_id)
    )
    documents_count = await db.scalar(documents_count_stmt) or 0

    # Query knowledge gaps count (unresolved only)
    knowledge_gaps_count_stmt = select(func.count(KnowledgeGap.id)).where(
        KnowledgeGap.workspace_id == workspace_id, KnowledgeGap.status == "open"
    )
    knowledge_gaps_count = await db.scalar(knowledge_gaps_count_stmt) or 0

    # Calculate average quality score (from assistant messages only)
    avg_quality_score_stmt = (
        select(func.avg(Message.quality_score))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.workspace_id == workspace_id,
            Message.role == "assistant",
            Message.quality_score.isnot(None),
        )
    )
    avg_quality_score = await db.scalar(avg_quality_score_stmt)

    # Get recent 5 conversations with first message and metadata
    # Subquery to get first message per conversation
    first_message_subq = (
        select(
            Message.conversation_id,
            func.min(Message.created_at).label("first_message_at"),
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    # Subquery to get message count per conversation
    message_count_subq = (
        select(
            Message.conversation_id,
            func.count(Message.id).label("message_count"),
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    # Main query for recent conversations
    recent_conversations_stmt = (
        select(
            Conversation.id,
            Message.content.label("first_message"),
            Conversation.started_at.label("last_message_at"),
            message_count_subq.c.message_count,
            Message.sentiment,
            Conversation.lead_score,
        )
        .join(first_message_subq, Conversation.id == first_message_subq.c.conversation_id)
        .join(
            Message,
            (Message.conversation_id == Conversation.id)
            & (Message.created_at == first_message_subq.c.first_message_at),
        )
        .outerjoin(message_count_subq, Conversation.id == message_count_subq.c.conversation_id)
        .where(Conversation.workspace_id == workspace_id)
        .order_by(Conversation.started_at.desc())
        .limit(5)
    )

    result = await db.execute(recent_conversations_stmt)
    recent_conversations_rows = result.all()

    recent_conversations = [
        RecentConversation(
            id=str(row.id),
            first_message=row.first_message[:100] if row.first_message else "",
            last_message_at=row.last_message_at,
            message_count=row.message_count or 0,
            sentiment=row.sentiment,
            lead_score=row.lead_score,
        )
        for row in recent_conversations_rows
    ]

    # Get workspace settings for feature flags
    workspace_stmt = select(Workspace).where(Workspace.id == workspace_id)
    workspace_result = await db.execute(workspace_stmt)
    workspace = workspace_result.scalar_one_or_none()

    if not workspace:
        # Fallback if workspace not found (shouldn't happen)
        features = FeatureFlags(
            rag_enabled=False,
            voice_enabled=False,
            channels_enabled=False,
            analytics_enabled=False,
        )
    else:
        workspace_features = workspace.features or {}
        features = FeatureFlags(
            rag_enabled=workspace_features.get("rag_enabled", False),
            voice_enabled=workspace_features.get("voice_enabled", False),
            channels_enabled=workspace_features.get("channels_enabled", False),
            analytics_enabled=workspace_features.get("analytics_enabled", False),
        )

    return DashboardSummary(
        conversations_count=conversations_count,
        messages_count=messages_count,
        documents_count=documents_count,
        knowledge_gaps_count=knowledge_gaps_count,
        avg_quality_score=float(avg_quality_score) if avg_quality_score else None,
        recent_conversations=recent_conversations,
        features=features,
    )
