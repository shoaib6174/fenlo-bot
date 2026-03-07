"""
Unified Inbox API — Multi-channel conversation inbox with handoff support.

Provides filtered conversation listing, message detail, handoff context,
and agent reply routing for the unified inbox UI.
"""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.dependencies import get_db
from app.middleware.rbac import require_role
from app.models.conversation import Conversation, Message
from app.models.voice import CallLog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/inbox", tags=["inbox"])


@router.get("/conversations", dependencies=[Depends(require_role("agent"))])
async def list_inbox_conversations(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    channel: str | None = Query(None),
    status: str | None = Query(None),
    min_lead_score: int | None = Query(None, ge=0, le=100),
):
    """
    List conversations for the unified inbox with channel badges, lead scores,
    and last message preview.

    Supports filtering by channel, status, and minimum lead score.
    Returns paginated results sorted by most recent activity.
    """
    user, workspace_id, role = current_user

    # Subquery: last message timestamp per conversation
    last_msg_subq = (
        select(func.max(Message.created_at))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )

    # Build base query
    query = select(Conversation, last_msg_subq.label("last_message_at")).where(
        Conversation.workspace_id == workspace_id
    )

    # Apply filters
    if channel and channel != "all":
        query = query.where(Conversation.channel == channel)
    if status and status != "all":
        query = query.where(Conversation.status == status)
    if min_lead_score is not None:
        query = query.where(Conversation.lead_score >= min_lead_score)

    # Count total before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Order by last activity, paginate
    offset = (page - 1) * per_page
    query = query.order_by(desc("last_message_at")).limit(per_page).offset(offset)

    result = await db.execute(query)
    rows = result.all()

    # Collect voice conversation IDs to batch-fetch call logs
    voice_conv_ids = [conv.id for conv, _ in rows if conv.channel == "voice"]

    # Batch-fetch call logs for voice conversations
    call_log_map: dict = {}
    if voice_conv_ids:
        cl_result = await db.execute(
            select(CallLog)
            .where(CallLog.conversation_id.in_(voice_conv_ids))
            .order_by(CallLog.created_at.desc())
        )
        for cl in cl_result.scalars().all():
            # Keep first (most recent) call log per conversation
            if cl.conversation_id not in call_log_map:
                call_log_map[cl.conversation_id] = cl

    items = []
    for conv, last_message_at in rows:
        item = {
            "id": str(conv.id),
            "workspace_id": str(conv.workspace_id),
            "channel": conv.channel,
            "contact_name": conv.contact_name,
            "contact_identifier": conv.external_id or "",
            "status": conv.status,
            "lead_score": conv.lead_score or 0,
            "last_message_at": last_message_at.isoformat()
            if last_message_at
            else conv.started_at.isoformat(),
            "last_message_preview": None,
            "created_at": conv.started_at.isoformat(),
            "updated_at": None,
        }

        # Enrich voice conversations with call log summary
        if conv.channel == "voice" and conv.id in call_log_map:
            cl = call_log_map[conv.id]
            item["call_log"] = {
                "id": str(cl.id),
                "status": cl.status,
                "direction": cl.direction,
                "duration_sec": cl.duration_sec,
                "phone_from": cl.phone_from or "",
                "phone_to": cl.phone_to or "",
                "summary": cl.summary,
                "sentiment": cl.sentiment,
            }
            # Use call log created_at as fallback for last_message_at
            if not last_message_at:
                item["last_message_at"] = cl.created_at.isoformat()

        items.append(item)

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/conversations/{conversation_id}", dependencies=[Depends(require_role("agent"))])
async def get_inbox_conversation(
    conversation_id: uuid.UUID,
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get conversation detail with messages for the inbox panel."""
    user, workspace_id, role = current_user

    # Fetch conversation
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == workspace_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Fetch messages
    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    response = {
        "id": str(conversation.id),
        "workspace_id": str(conversation.workspace_id),
        "channel": conversation.channel,
        "contact_name": conversation.contact_name,
        "contact_identifier": conversation.external_id or "",
        "status": conversation.status,
        "lead_score": conversation.lead_score or 0,
        "last_message_at": messages[-1].created_at.isoformat()
        if messages
        else conversation.started_at.isoformat(),
        "last_message_preview": messages[-1].content[:100] if messages else None,
        "created_at": conversation.started_at.isoformat(),
        "updated_at": None,
        "messages": [
            {
                "id": str(msg.id),
                "conversation_id": str(msg.conversation_id),
                "role": msg.role,
                "content": msg.content,
                "sentiment": msg.sentiment,
                "intent": msg.intent,
                "quality_score": msg.quality_score,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ],
    }

    # Enrich voice conversations with call log data (including transcript)
    if conversation.channel == "voice":
        cl_result = await db.execute(
            select(CallLog)
            .where(CallLog.conversation_id == conversation_id)
            .order_by(CallLog.created_at.desc())
        )
        call_logs = cl_result.scalars().all()
        if call_logs:
            cl = call_logs[0]  # Most recent call
            response["call_log"] = {
                "id": str(cl.id),
                "vapi_call_id": cl.vapi_call_id,
                "status": cl.status,
                "direction": cl.direction,
                "duration_sec": cl.duration_sec,
                "phone_from": cl.phone_from or "",
                "phone_to": cl.phone_to or "",
                "recording_url": cl.recording_url,
                "transcript": cl.transcript,
                "summary": cl.summary,
                "sentiment": cl.sentiment,
                "actions_taken": cl.actions_taken,
                "created_at": cl.created_at.isoformat(),
            }
            # Use call log created_at as fallback for last_message_at
            if not messages:
                response["last_message_at"] = cl.created_at.isoformat()

    return response


@router.get("/handoff/{conversation_id}", dependencies=[Depends(require_role("agent"))])
async def get_inbox_handoff(
    conversation_id: uuid.UUID,
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get enriched handoff context for agent takeover."""
    user, workspace_id, role = current_user

    # Verify conversation belongs to workspace
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == workspace_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    from app.modules.channels.handoff import assemble_handoff_context

    context = await assemble_handoff_context(conversation_id, db)
    return context


@router.post("/reply/{conversation_id}", dependencies=[Depends(require_role("agent"))])
async def inbox_reply(
    conversation_id: uuid.UUID,
    payload: dict,
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send agent reply through the original channel."""
    user, workspace_id, role = current_user

    content = payload.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    # Verify conversation belongs to workspace
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == workspace_id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Route reply through channel
    from app.modules.channels.response_router import send_channel_response

    send_result = await send_channel_response(
        conversation_id=conversation_id,
        message=content,
        db=db,
    )

    # Check send result BEFORE persisting — don't save orphan messages on failure
    if not send_result.success and not send_result.should_retry:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message: {send_result.error}",
        )

    # Persist message only after successful send (or retryable failure)
    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=content,
    )
    db.add(assistant_message)
    await db.commit()
