"""
Public API — Share-token authenticated read-only endpoints.

No JWT auth required. Workspace identified by share_token UUID.
Rate limited per IP to prevent abuse.

Endpoints:
- GET /public/{share_token}/dashboard — Read-only dashboard summary
- GET /public/{share_token}/analytics/overview — Analytics overview
- GET /public/{share_token}/analytics/volume — Volume time series
- GET /public/{share_token}/analytics/sentiment — Sentiment over time
- GET /public/{share_token}/analytics/top-questions — Top questions
- GET /public/{share_token}/widget-id — Get widget_id for chat embedding
- GET /public/{share_token}/info — Basic workspace info (name, branding)
- GET /public/{share_token}/conversations — List conversations
- GET /public/{share_token}/conversations/{conversation_id} — Conversation with messages
- GET /public/{share_token}/kb — Knowledge bases with documents + gaps
- POST /public/{share_token}/regenerate — Regenerate share token (auth required)
"""

import logging
import uuid as uuid_mod
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.analytics_cache import get_analytics_cache
from app.dependencies import get_db
from app.models.channel import ChannelConfig
from app.models.conversation import Conversation, Message
from app.models.knowledge_base import Document, KnowledgeBase, KnowledgeGap
from app.models.workspace import Workspace
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/v1/public", tags=["public"])
logger = logging.getLogger(__name__)


async def _get_workspace_by_token(share_token: UUID, db: AsyncSession) -> Workspace:
    """Look up workspace by share_token. Raises 404 if not found or disabled."""
    stmt = select(Workspace).where(
        Workspace.share_token == share_token,
        Workspace.share_enabled.is_(True),
    )
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or disabled share link",
        )
    return workspace


# ------------------------------------------------------------------
# Workspace Info
# ------------------------------------------------------------------


@router.get("/{share_token}/info")
async def public_workspace_info(
    share_token: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Basic workspace info for public pages (name, branding)."""
    workspace = await _get_workspace_by_token(share_token, db)
    settings = workspace.settings or {}
    return {
        "name": workspace.name,
        "brand_name": settings.get("brand_name", workspace.name),
        "logo_url": settings.get("logo_url", ""),
        "accent_color": settings.get("accent_color", "#0ea5e9"),
    }


# ------------------------------------------------------------------
# Dashboard Summary (read-only)
# ------------------------------------------------------------------


@router.get("/{share_token}/dashboard")
async def public_dashboard(
    share_token: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Read-only dashboard summary — same data as authenticated endpoint."""
    workspace = await _get_workspace_by_token(share_token, db)
    workspace_id = workspace.id

    # Conversations count
    conversations_count = (
        await db.scalar(
            select(func.count(Conversation.id)).where(Conversation.workspace_id == workspace_id)
        )
        or 0
    )

    # Messages count
    messages_count = (
        await db.scalar(
            select(func.count(Message.id))
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.workspace_id == workspace_id)
        )
        or 0
    )

    # Documents count
    documents_count = (
        await db.scalar(
            select(func.count(Document.id))
            .join(KnowledgeBase, Document.kb_id == KnowledgeBase.id)
            .where(KnowledgeBase.workspace_id == workspace_id)
        )
        or 0
    )

    # Knowledge gaps count
    knowledge_gaps_count = (
        await db.scalar(
            select(func.count(KnowledgeGap.id)).where(
                KnowledgeGap.workspace_id == workspace_id,
                KnowledgeGap.status == "open",
            )
        )
        or 0
    )

    # Average quality score
    avg_quality_score = await db.scalar(
        select(func.avg(Message.quality_score))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.workspace_id == workspace_id,
            Message.role == "assistant",
            Message.quality_score.isnot(None),
        )
    )

    # Recent 5 conversations (preview only)
    recent_stmt = (
        select(
            Conversation.id,
            Conversation.started_at,
            Conversation.lead_score,
        )
        .where(Conversation.workspace_id == workspace_id)
        .order_by(Conversation.started_at.desc())
        .limit(5)
    )
    result = await db.execute(recent_stmt)
    recent = [
        {
            "id": str(row.id),
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "lead_score": row.lead_score,
        }
        for row in result.all()
    ]

    return {
        "workspace_name": workspace.name,
        "conversations_count": conversations_count,
        "messages_count": messages_count,
        "documents_count": documents_count,
        "knowledge_gaps_count": knowledge_gaps_count,
        "avg_quality_score": float(avg_quality_score) if avg_quality_score else None,
        "recent_conversations": recent,
    }


# ------------------------------------------------------------------
# Analytics (read-only)
# ------------------------------------------------------------------


def _default_range() -> tuple[date, date]:
    return date.today() - timedelta(days=30), date.today()


def _get_service() -> AnalyticsService:
    return AnalyticsService(cache=get_analytics_cache())


@router.get("/{share_token}/analytics/overview")
async def public_analytics_overview(
    share_token: UUID,
    db: AsyncSession = Depends(get_db),
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
):
    workspace = await _get_workspace_by_token(share_token, db)
    start, end = start_date or _default_range()[0], end_date or _default_range()[1]
    svc = _get_service()
    return await svc.get_overview(str(workspace.id), start, end, db)


@router.get("/{share_token}/analytics/volume")
async def public_analytics_volume(
    share_token: UUID,
    db: AsyncSession = Depends(get_db),
    period: str = Query("day", pattern="^(day|week|month)$"),
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
):
    workspace = await _get_workspace_by_token(share_token, db)
    start, end = start_date or _default_range()[0], end_date or _default_range()[1]
    svc = _get_service()
    return await svc.get_volume(str(workspace.id), start, end, period, db)


@router.get("/{share_token}/analytics/sentiment")
async def public_analytics_sentiment(
    share_token: UUID,
    db: AsyncSession = Depends(get_db),
    period: str = Query("day", pattern="^(day|week|month)$"),
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
):
    workspace = await _get_workspace_by_token(share_token, db)
    start, end = start_date or _default_range()[0], end_date or _default_range()[1]
    svc = _get_service()
    return await svc.get_sentiment(str(workspace.id), start, end, period, db)


@router.get("/{share_token}/analytics/top-questions")
async def public_analytics_top_questions(
    share_token: UUID,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
):
    workspace = await _get_workspace_by_token(share_token, db)
    svc = _get_service()
    return await svc.get_top_questions(str(workspace.id), limit, db)


# ------------------------------------------------------------------
# Conversations (read-only)
# ------------------------------------------------------------------


@router.get("/{share_token}/conversations")
async def public_conversations(
    share_token: UUID,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
):
    """List recent conversations (read-only)."""
    workspace = await _get_workspace_by_token(share_token, db)

    # Subquery for message count
    msg_count_sub = (
        select(
            Message.conversation_id,
            func.count(Message.id).label("message_count"),
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    stmt = (
        select(
            Conversation.id,
            Conversation.title,
            Conversation.channel,
            Conversation.status,
            Conversation.started_at,
            Conversation.lead_score,
            func.coalesce(msg_count_sub.c.message_count, 0).label("message_count"),
        )
        .outerjoin(msg_count_sub, Conversation.id == msg_count_sub.c.conversation_id)
        .where(Conversation.workspace_id == workspace.id)
        .order_by(Conversation.started_at.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "id": str(row.id),
            "title": row.title,
            "channel": row.channel,
            "status": row.status,
            "message_count": row.message_count,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "lead_score": row.lead_score,
        }
        for row in rows
    ]


@router.get("/{share_token}/conversations/{conversation_id}")
async def public_conversation_detail(
    share_token: UUID,
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single conversation with its messages (read-only)."""
    workspace = await _get_workspace_by_token(share_token, db)

    # Verify conversation belongs to this workspace
    conv_stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.workspace_id == workspace.id,
    )
    conv_result = await db.execute(conv_stmt)
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # Fetch messages
    msg_stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    msg_result = await db.execute(msg_stmt)
    messages = msg_result.scalars().all()

    return {
        "id": str(conversation.id),
        "title": conversation.title,
        "channel": conversation.channel,
        "status": conversation.status,
        "started_at": conversation.started_at.isoformat() if conversation.started_at else None,
        "lead_score": conversation.lead_score,
        "messages": [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "citations": msg.citations,
                "sentiment": msg.sentiment,
                "quality_score": msg.quality_score,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in messages
        ],
    }


# ------------------------------------------------------------------
# Knowledge Base (read-only)
# ------------------------------------------------------------------


@router.get("/{share_token}/kb")
async def public_knowledge_base(
    share_token: UUID,
    db: AsyncSession = Depends(get_db),
):
    """List knowledge bases with documents and gaps (read-only)."""
    workspace = await _get_workspace_by_token(share_token, db)

    # Fetch all KBs for workspace
    kb_stmt = (
        select(KnowledgeBase)
        .where(KnowledgeBase.workspace_id == workspace.id)
        .order_by(KnowledgeBase.created_at.desc())
    )
    kb_result = await db.execute(kb_stmt)
    kbs = kb_result.scalars().all()

    result = []
    for kb in kbs:
        # Documents for this KB
        doc_stmt = (
            select(Document).where(Document.kb_id == kb.id).order_by(Document.created_at.desc())
        )
        doc_result = await db.execute(doc_stmt)
        docs = doc_result.scalars().all()

        # Knowledge gaps for this workspace (gaps are workspace-level)
        gap_stmt = (
            select(KnowledgeGap)
            .where(
                KnowledgeGap.workspace_id == workspace.id,
                KnowledgeGap.status == "open",
            )
            .order_by(KnowledgeGap.occurrence_count.desc())
        )
        gap_result = await db.execute(gap_stmt)
        gaps = gap_result.scalars().all()

        result.append(
            {
                "id": str(kb.id),
                "name": kb.name,
                "description": kb.description,
                "created_at": kb.created_at.isoformat() if kb.created_at else None,
                "documents": [
                    {
                        "id": str(doc.id),
                        "filename": doc.filename,
                        "file_type": doc.file_type,
                        "file_size": doc.file_size,
                        "status": doc.status,
                        "chunk_count": doc.chunk_count,
                        "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    }
                    for doc in docs
                ],
                "gaps": [
                    {
                        "id": str(gap.id),
                        "query_text": gap.query_text,
                        "occurrence_count": gap.occurrence_count,
                        "status": gap.status,
                        "last_asked_at": (
                            gap.last_asked_at.isoformat() if gap.last_asked_at else None
                        ),
                    }
                    for gap in gaps
                ],
            }
        )

    return result


# ------------------------------------------------------------------
# Widget ID (for embedding chat on public pages)
# ------------------------------------------------------------------


@router.get("/{share_token}/widget-id")
async def public_widget_id(
    share_token: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the widget channel ID for embedding chat on public pages."""
    workspace = await _get_workspace_by_token(share_token, db)
    stmt = select(ChannelConfig).where(
        ChannelConfig.workspace_id == workspace.id,
        ChannelConfig.channel == "widget",
        ChannelConfig.is_active.is_(True),
    )
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active widget channel configured",
        )
    return {"widget_id": str(channel.id)}


# ------------------------------------------------------------------
# Share Token Management (authenticated)
# ------------------------------------------------------------------


@router.get("/share-token")
async def get_share_token(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current workspace's share token and status."""
    _, workspace_id, _ = current_user
    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {
        "share_token": str(workspace.share_token),
        "share_enabled": workspace.share_enabled,
    }


@router.post("/share-token/regenerate")
async def regenerate_share_token(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate the share token (invalidates all existing public links)."""
    _, workspace_id, role = current_user
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    workspace.share_token = uuid_mod.uuid4()
    await db.commit()
    await db.refresh(workspace)

    return {
        "share_token": str(workspace.share_token),
        "share_enabled": workspace.share_enabled,
    }


@router.post("/share-token/toggle")
async def toggle_share_enabled(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable public share links."""
    _, workspace_id, role = current_user
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    workspace.share_enabled = not workspace.share_enabled
    await db.commit()
    await db.refresh(workspace)

    return {
        "share_token": str(workspace.share_token),
        "share_enabled": workspace.share_enabled,
    }
