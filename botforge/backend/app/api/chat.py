"""
Chat API routes - WebSocket streaming, SSE fallback, and HTTP endpoints.

Provides:
- WebSocket streaming for real-time chat
- SSE fallback for environments without WebSocket support
- HTTP endpoints for conversation management
- Message feedback endpoints
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, get_current_user_from_token
from app.core.context_manager import LoadContextStep, PersistenceStep
from app.core.engine import MessageContext, MessagePipeline
from app.core.llm_router import LLMRouter
from app.core.prompt_guard import PromptGuardStep
from app.core.response_streamer import LLMStreamStep, ResponseStreamer
from app.core.steps.analytics import IntentClassifierStep, QualityScorerStep, SentimentAnalysisStep
from app.core.steps.booking import BookingEnrichmentStep
from app.core.steps.escalation_step import EscalationStep
from app.core.steps.handoff_guard import HandoffGuardStep
from app.core.steps.lead_scoring import LeadScoringStep
from app.core.steps.post_response_gap import PostResponseGapStep
from app.core.steps.rag_retrieval import RAGRetrievalStep
from app.dependencies import get_db, get_llm_router
from app.middleware.rbac import require_role
from app.models.conversation import Conversation, Message

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


# Request/Response Schemas
class SendMessageRequest(BaseModel):
    """Request body for POST /send"""

    message: str
    conversation_id: uuid.UUID | None = None


class SendMessageResponse(BaseModel):
    """Response for POST /send"""

    conversation_id: uuid.UUID
    assistant_message: str
    metadata: dict


class ConversationListItem(BaseModel):
    """Conversation list item"""

    id: uuid.UUID
    title: str
    lead_score: int | None
    started_at: datetime
    message_count: int


class MessageItem(BaseModel):
    """Message in conversation history"""

    id: uuid.UUID
    role: str
    content: str
    sentiment: str | None
    intent: str | None
    quality_score: float | None
    feedback: str | None
    citations: list[dict] | None = None
    created_at: datetime


class FeedbackRequest(BaseModel):
    """Request body for feedback"""

    feedback: Literal["positive", "negative"]


class DebugMetadata(BaseModel):
    """Debug metadata for a conversation"""

    conversation_id: uuid.UUID
    messages: list[dict]
    rag_chunks: list[dict] | None
    confidence_scores: list[float] | None
    intents: list[str] | None


@router.websocket("/stream")
async def websocket_chat(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for real-time chat streaming.

    Authentication via query parameter (not cookie, since WebSocket doesn't support cookies well).

    Protocol:
    1. Client connects with JWT token in query string
    2. Client sends JSON: {"message": "user message", "conversation_id": "uuid" (optional)}
    3. Server streams events:
       - {"event": "typing", "data": {"is_typing": true}}
       - {"event": "token", "data": {"token": "word"}}
       - {"event": "done", "data": {"conversation_id": "...", "metadata": {...}}}
       - {"event": "error", "data": {"message": "...", "code": "..."}}
    """
    await websocket.accept()
    streamer = ResponseStreamer(websocket)
    llm_router = websocket.app.state.llm_router

    # Track for graceful shutdown
    from app.main import active_websockets

    active_websockets.add(websocket)

    try:
        # Authenticate user from token
        user = await get_current_user_from_token(token, db)

        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_text = data.get("message")
            conversation_id = data.get("conversation_id")

            if not message_text:
                await streamer.send_error("Message is required", "missing_message")
                continue

            # Convert conversation_id string to UUID if provided
            if conversation_id:
                try:
                    conversation_id = uuid.UUID(conversation_id)
                except ValueError:
                    await streamer.send_error(
                        "Invalid conversation ID format", "invalid_conversation_id"
                    )
                    continue

            # Process message through pipeline
            try:
                # Build pipeline (llm_router injected via dependency)
                pipeline = MessagePipeline(
                    [
                        HandoffGuardStep(db),
                        LoadContextStep(db),
                        PromptGuardStep(),
                        RAGRetrievalStep(),  # Retrieve relevant chunks from KB
                        LLMStreamStep(),
                        PostResponseGapStep(),
                        SentimentAnalysisStep(),
                        IntentClassifierStep(),
                        BookingEnrichmentStep(db),
                        QualityScorerStep(),
                        LeadScoringStep(),
                        EscalationStep(db),
                        PersistenceStep(db),
                    ]
                )

                # Create context
                context = MessageContext(
                    workspace_id=user.workspace_id,
                    user_id=user.id,
                    conversation_id=conversation_id,
                    message=message_text,
                )

                # Attach streamer and router to metadata
                context.metadata["streamer"] = streamer
                context.metadata["llm_router"] = llm_router

                # Process message
                result = await pipeline.process(context)

                # Send done event (include citations so frontend gets them atomically)
                done_metadata = {
                    "sentiment": result.sentiment,
                    "intent": result.intent,
                    "quality_score": result.quality_score,
                    "tokens_used": result.tokens_used,
                    "provider_used": result.provider_used,
                }
                if result.citations:
                    done_metadata["citations"] = result.citations
                if result.metadata.get("booking_config"):
                    done_metadata["booking_config"] = result.metadata["booking_config"]

                await streamer.send_done(
                    conversation_id=result.conversation_id,
                    metadata=done_metadata,
                )

            except Exception as e:
                await streamer.send_error(str(e), "processing_error")

    except WebSocketDisconnect:
        # Client disconnected
        pass
    except Exception as e:
        try:
            await streamer.send_error(str(e), "server_error")
        except Exception as send_err:
            # Failed to send error over WebSocket - log but don't fail
            import logging

            logging.getLogger(__name__).exception("Failed to send WebSocket error: %s", send_err)
    finally:
        active_websockets.discard(websocket)
        try:
            await websocket.close()
        except Exception as close_err:
            # WebSocket already closed or connection lost
            import logging

            logging.getLogger(__name__).debug("WebSocket close failed: %s", close_err)


@router.post(
    "/send", response_model=SendMessageResponse, dependencies=[Depends(require_role("agent"))]
)
async def send_message(
    payload: SendMessageRequest,
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm_router: LLMRouter = Depends(get_llm_router),
):
    """
    Synchronous chat endpoint (alternative to WebSocket).

    Processes message and returns complete response (no streaming).
    RBAC: owner/admin/agent can access chat; viewer cannot.
    """
    user, workspace_id, role = current_user

    # Build pipeline (llm_router injected via dependency)
    pipeline = MessagePipeline(
        [
            HandoffGuardStep(db),
            LoadContextStep(db),
            PromptGuardStep(),
            RAGRetrievalStep(),  # Retrieve relevant chunks from KB
            LLMStreamStep(),  # Will not stream, just process
            PostResponseGapStep(),
            SentimentAnalysisStep(),
            IntentClassifierStep(),
            BookingEnrichmentStep(db),
            QualityScorerStep(),
            LeadScoringStep(),
            EscalationStep(db),
            PersistenceStep(db),
        ]
    )

    # Create context
    context = MessageContext(
        workspace_id=workspace_id,
        user_id=user.id,
        conversation_id=payload.conversation_id,
        message=payload.message,
    )

    # Attach router (but no streamer for synchronous)
    context.metadata["llm_router"] = llm_router
    context.metadata["synchronous"] = True

    # Process message
    result = await pipeline.process(context)

    response_metadata = {
        "sentiment": result.sentiment,
        "intent": result.intent,
        "quality_score": result.quality_score,
        "tokens_used": result.tokens_used,
        "provider_used": result.provider_used,
    }
    if result.citations:
        response_metadata["citations"] = result.citations

    return SendMessageResponse(
        conversation_id=result.conversation_id,
        assistant_message=result.response,
        metadata=response_metadata,
    )


# --- SSE fallback endpoint ---


@router.get("/stream-sse")
async def stream_sse(
    token: str = Query(..., description="JWT auth token"),
    message: str = Query(..., description="User message"),
    conversation_id: str | None = Query(None, description="Conversation UUID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Server-Sent Events fallback for chat streaming.

    For environments where WebSocket is not available.
    Returns text/event-stream with token-by-token delivery.
    """
    from app.api.auth import get_current_user_from_token

    user = await get_current_user_from_token(token, db)
    llm_router = LLMRouter()

    conv_uuid = None
    if conversation_id:
        try:
            conv_uuid = uuid.UUID(conversation_id)
        except ValueError:
            pass

    # Build pipeline (synchronous mode — we collect full response, then emit SSE)
    pipeline = MessagePipeline(
        [
            HandoffGuardStep(db),
            LoadContextStep(db),
            PromptGuardStep(),
            RAGRetrievalStep(),
            LLMStreamStep(),
            PostResponseGapStep(),
            SentimentAnalysisStep(),
            IntentClassifierStep(),
            BookingEnrichmentStep(db),
            QualityScorerStep(),
            LeadScoringStep(),
            EscalationStep(db),
            PersistenceStep(db),
        ]
    )

    context = MessageContext(
        workspace_id=user.workspace_id,
        user_id=user.id,
        conversation_id=conv_uuid,
        message=message,
    )
    context.metadata["llm_router"] = llm_router
    context.metadata["synchronous"] = True

    async def event_generator():
        try:
            result = await pipeline.process(context)

            # Emit tokens (split response into words for SSE streaming feel)
            words = result.response.split(" ") if result.response else []
            for word in words:
                yield f"event: token\ndata: {json.dumps({'token': word + ' '})}\n\n"
                await asyncio.sleep(0.02)  # slight delay for streaming effect

            # Emit done
            done_data = {
                "conversation_id": str(result.conversation_id) if result.conversation_id else None,
                "sentiment": result.sentiment,
                "intent": result.intent,
                "quality_score": result.quality_score,
                "tokens_used": result.tokens_used,
            }
            if result.citations:
                done_data["citations"] = result.citations

            yield f"event: done\ndata: {json.dumps(done_data)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e), 'code': 'sse_error'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations", dependencies=[Depends(require_role("agent"))])
async def list_conversations(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    channel: str | None = Query(
        None, description="Filter by channel (whatsapp, widget, voice, web)"
    ),
    status: str | None = Query(None, description="Filter by status (active, escalated, resolved)"),
    min_lead_score: int | None = Query(None, ge=0, le=100, description="Minimum lead score"),
):
    """
    List conversations for the authenticated user's workspace.

    Returns conversations sorted by most recent first.
    Supports filtering by channel, status, and lead score.
    RBAC: owner/admin/agent can access.
    """
    user, workspace_id, role = current_user

    # Correlated scalar subquery to get message count per conversation
    message_count_subq = (
        select(func.count(Message.id))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )

    # Build query with filters
    query = select(Conversation, message_count_subq.label("message_count")).where(
        Conversation.workspace_id == workspace_id
    )

    # Apply filters
    if channel:
        query = query.where(Conversation.channel == channel)

    if status:
        query = query.where(Conversation.status == status)

    if min_lead_score is not None:
        query = query.where(Conversation.lead_score >= min_lead_score)

    # Order and paginate
    query = query.order_by(desc(Conversation.started_at)).limit(limit).offset(offset)

    result = await db.execute(query)
    rows = result.all()

    # Build response items from single query result
    items = [
        ConversationListItem(
            id=conv.id,
            title=conv.contact_name or "Conversation",
            lead_score=conv.lead_score,
            started_at=conv.started_at,
            message_count=message_count,
        )
        for conv, message_count in rows
    ]

    return {"conversations": items, "total": len(items)}


@router.get(
    "/conversations/{conversation_id}/messages", dependencies=[Depends(require_role("agent"))]
)
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get message history for a conversation.

    RBAC: owner/admin/agent can access.
    """
    user, workspace_id, role = current_user
    # Verify conversation belongs to user's workspace
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == workspace_id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get messages
    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = messages_result.scalars().all()

    return {
        "conversation_id": conversation_id,
        "messages": [
            MessageItem(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                sentiment=msg.sentiment,
                intent=msg.intent,
                quality_score=msg.quality_score,
                feedback=msg.feedback,
                citations=msg.citations,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
    }


@router.get("/conversations/{conversation_id}/debug", dependencies=[Depends(require_role("admin"))])
async def get_conversation_debug(
    conversation_id: uuid.UUID,
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Debug view for a conversation.

    Shows RAG chunks, confidence scores, intent classification, etc.
    RBAC: owner/admin only (not agent/viewer).
    """
    user, workspace_id, role = current_user
    # Verify conversation belongs to user's workspace
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == workspace_id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get messages with metadata
    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = messages_result.scalars().all()

    debug_data = {
        "conversation_id": str(conversation_id),
        "conversation": {
            "status": conversation.status,
            "channel": conversation.channel,
            "lead_score": conversation.lead_score,
            "started_at": conversation.started_at.isoformat() if conversation.started_at else None,
            "message_count": len(messages),
        },
        "messages": [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "sentiment": msg.sentiment,
                "intent": msg.intent,
                "quality_score": msg.quality_score,
                "tokens_used": msg.tokens_used,
                "latency_ms": msg.latency_ms,
                "citations": msg.citations or [],
                "feedback": msg.feedback,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ],
        "confidence_scores": [msg.quality_score for msg in messages if msg.quality_score],
        "intents": [msg.intent for msg in messages if msg.intent],
    }

    return debug_data


@router.post("/messages/{message_id}/feedback", dependencies=[Depends(require_role("agent"))])
async def submit_feedback(
    message_id: uuid.UUID,
    payload: FeedbackRequest,
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit thumbs up/down feedback for a message.

    RBAC: owner/admin/agent can submit feedback.
    """
    user, workspace_id, role = current_user

    # Get message and verify workspace
    result = await db.execute(select(Message).where(Message.id == message_id))
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Verify message belongs to user's workspace via conversation
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == message.conversation_id,
            Conversation.workspace_id == workspace_id,
        )
    )
    conversation = conv_result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=403, detail="Access denied")

    # Update feedback
    message.feedback = payload.feedback
    await db.commit()

    return {"message": "Feedback recorded", "message_id": message_id, "feedback": payload.feedback}


@router.get(
    "/conversations/{conversation_id}/handoff-context",
    dependencies=[Depends(require_role("agent"))],
)
async def get_handoff_context(
    conversation_id: uuid.UUID,
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get enriched handoff context for agent takeover.

    Returns comprehensive context including:
    - Recent messages (last 20)
    - RAG citations and context
    - Sentiment timeline
    - Intent history
    - Quality scores
    - Lead score
    - Escalation reason

    RBAC: owner/admin/agent can access.
    """
    user, workspace_id, role = current_user

    # Verify conversation belongs to user's workspace
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == workspace_id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Assemble handoff context
    from app.modules.channels.handoff import assemble_handoff_context

    context = await assemble_handoff_context(conversation_id, db)

    return context


class AgentReplyRequest(BaseModel):
    """Request body for agent reply"""

    message: str


class AgentReplyResponse(BaseModel):
    """Response for agent reply"""

    status: Literal["sent", "queued"]
    provider_message_id: str | None


@router.post(
    "/conversations/{conversation_id}/reply", dependencies=[Depends(require_role("agent"))]
)
async def agent_reply(
    conversation_id: uuid.UUID,
    payload: AgentReplyRequest,
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentReplyResponse:
    """
    Send agent reply through the original channel.

    Routes the reply through the correct channel (Widget, WhatsApp, Web)
    using the channel response router. Message is persisted with
    role="assistant", sender_type="agent".

    On send failure with should_retry=True, message is queued in WebhookOutbox
    for retry delivery.

    RBAC: owner/admin/agent can send replies.
    """
    user, workspace_id, role = current_user

    # Verify conversation belongs to user's workspace
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
        message=payload.message,
        db=db,
    )

    # Persist message as assistant message from agent
    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=payload.message,
    )
    db.add(assistant_message)
    await db.commit()

    # Determine response status
    if send_result.success:
        return AgentReplyResponse(
            status="sent",
            provider_message_id=send_result.provider_message_id,
        )
    elif send_result.should_retry:
        return AgentReplyResponse(
            status="queued",
            provider_message_id=None,
        )
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message: {send_result.error}",
        )
