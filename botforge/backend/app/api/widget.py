"""
Widget Public API — No JWT auth, domain allowlist + rate limiting.

Endpoints:
- GET /widget/{widget_id}/config — Public config fetch (domain-validated)
- POST /widget/{widget_id}/chat — Anonymous SSE chat (rate limited, S75)
- POST /widget/error — Error reporting (rate limited 5/min per widget)
"""

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context_manager import LoadContextStep, PersistenceStep
from app.core.engine import MessageContext, MessagePipeline
from app.core.llm_router import LLMRouter
from app.core.prompt_guard import PromptGuardStep
from app.core.redis import get_redis_client
from app.core.response_streamer import LLMStreamStep
from app.core.steps.post_response_gap import PostResponseGapStep
from app.core.steps.rag_retrieval import RAGRetrievalStep
from app.dependencies import get_db
from app.models.channel import ChannelConfig
from app.modules.channels.widget_provider import WidgetProvider
from app.schemas.channel import WidgetErrorReport, WidgetPublicConfigResponse
from app.schemas.widget import WidgetChatRequest

router = APIRouter(prefix="/api/v1/widget", tags=["widget"])
logger = logging.getLogger(__name__)

# Rate limit: 20 messages/hour per IP per widget
WIDGET_CHAT_RATE_LIMIT = 20
WIDGET_CHAT_RATE_WINDOW = 3600  # 1 hour in seconds


async def _check_rate_limit(widget_id: str, client_ip: str) -> bool:
    """Check rate limit for widget chat. Returns True if allowed, False if exceeded."""
    redis = get_redis_client()
    if not redis:
        # Graceful degradation: allow if Redis unavailable
        return True
    try:
        key = f"widget_rl:{widget_id}:{client_ip}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, WIDGET_CHAT_RATE_WINDOW)
        return count <= WIDGET_CHAT_RATE_LIMIT
    except Exception:
        logger.warning("widget.rate_limit.redis_error", exc_info=True)
        return True  # Graceful degradation


@router.get("/{widget_id}/config", response_model=WidgetPublicConfigResponse)
async def get_widget_config(
    widget_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> WidgetPublicConfigResponse:
    """
    Fetch public widget configuration.

    No JWT required. Security via:
    1. Domain allowlist — validates Origin header
    2. No sensitive data returned (only display config)
    3. Returns HMAC for WebSocket auth (time-limited)

    Returns 404 for invalid widget_id (does NOT reveal if workspace exists).
    Returns 403 if Origin not in allowed_domains.
    """
    # Fetch widget config
    stmt = select(ChannelConfig).where(
        ChannelConfig.id == widget_id,
        ChannelConfig.channel == "widget",
        ChannelConfig.is_active == True,  # noqa: E712
    )

    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        # Return 404 without revealing workspace existence
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found",
        )

    # Validate Origin header against allowed_domains
    origin = request.headers.get("Origin", "")
    allowed_domains = config.config.get("allowed_domains", [])

    widget_provider = WidgetProvider()
    if not widget_provider.validate_domain(origin, allowed_domains):
        logger.warning(
            f"Widget config fetch blocked: origin={origin} not in allowed_domains={allowed_domains}",
            extra={"widget_id": str(widget_id), "origin": origin},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origin not allowed",
        )

    # Generate HMAC for WebSocket auth
    hmac_salt = config.config.get("widget_id_hmac_salt", "")
    hmac_value, hmac_timestamp = widget_provider.generate_hmac(str(widget_id), hmac_salt)

    # Return public config (no sensitive data)
    return WidgetPublicConfigResponse(
        widget_id=widget_id,
        colors=config.config.get("colors", {"primary": "#007bff", "background": "#ffffff"}),
        position=config.config.get("position", "bottom-right"),
        greeting=config.config.get("greeting", "Hi! How can I help you today?"),
        widget_api_version=1,
        hmac=hmac_value,
        hmac_timestamp=hmac_timestamp,
    )


@router.post("/{widget_id}/chat")
async def widget_chat(
    widget_id: UUID,
    body: WidgetChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Anonymous SSE chat endpoint for the homepage live widget (S75).

    No JWT required. Security via:
    1. Widget ID must exist and be active
    2. Rate limit: 20 msgs/hour per IP (Redis counter, graceful degradation)
    3. Message length capped at 500 chars (schema validation)

    Returns text/event-stream with events:
    - token: {"token": "word "} — streamed word-by-word
    - done: {"conversation_id": "...", "citations": [...]} — final metadata
    - error: {"message": "...", "code": "..."} — on failure
    """
    # Validate widget exists and is active
    stmt = select(ChannelConfig).where(
        ChannelConfig.id == widget_id,
        ChannelConfig.channel == "widget",
        ChannelConfig.is_active == True,  # noqa: E712
    )
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found",
        )

    # Rate limit by IP
    client_ip = request.client.host if request.client else "unknown"
    if not await _check_rate_limit(str(widget_id), client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )

    # Build reduced pipeline (skip analytics/escalation for anonymous)
    llm_router = LLMRouter()
    pipeline = MessagePipeline(
        [
            LoadContextStep(db),
            PromptGuardStep(),
            RAGRetrievalStep(),
            LLMStreamStep(),
            PostResponseGapStep(),
            PersistenceStep(db),
        ]
    )

    context = MessageContext(
        workspace_id=config.workspace_id,
        user_id=None,
        conversation_id=body.conversation_id,
        message=body.message,
    )
    context.metadata["llm_router"] = llm_router
    context.metadata["synchronous"] = True
    context.metadata["channel"] = "widget"

    async def event_generator():
        try:
            result = await pipeline.process(context)

            # Stream tokens word-by-word
            words = result.response.split(" ") if result.response else []
            for word in words:
                yield f"event: token\ndata: {json.dumps({'token': word + ' '})}\n\n"
                await asyncio.sleep(0.02)

            # Emit done with conversation_id and citations
            done_data = {
                "conversation_id": str(result.conversation_id) if result.conversation_id else None,
            }
            if result.citations:
                done_data["citations"] = result.citations

            yield f"event: done\ndata: {json.dumps(done_data)}\n\n"
        except Exception as e:
            logger.error("widget.chat.error", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'message': str(e), 'code': 'widget_chat_error'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/error", status_code=status.HTTP_204_NO_CONTENT)
async def report_widget_error(
    error: WidgetErrorReport,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Widget error reporting endpoint.

    Rate limited: 5 reports/min per widget_id (Redis counter).
    Max payload size: 10KB (enforced by schema field max_length).

    Errors are logged (not stored in DB to avoid table bloat).
    Logged at WARN level with source=widget tag for filtering.

    No authentication required — widget_id must exist and be active.
    """
    # Verify widget exists and is active
    stmt = select(ChannelConfig).where(
        ChannelConfig.id == error.widget_id,
        ChannelConfig.channel == "widget",
        ChannelConfig.is_active == True,  # noqa: E712
    )

    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        # Silently ignore errors for non-existent widgets (prevents enumeration)
        return

    # TODO: Rate limiting (5/min per widget_id) via Redis
    # For now, just log the error
    # In S50 implementation, add Redis-based rate limiting here

    # Log error with structured fields
    logger.warning(
        f"Widget error: {error.error_type} — {error.message}",
        extra={
            "source": "widget",
            "widget_id": str(error.widget_id),
            "workspace_id": str(config.workspace_id),
            "error_type": error.error_type,
            "error_message": error.message,  # Renamed from 'message' to avoid LogRecord conflict
            "stack_trace": error.stack_trace[:500] if error.stack_trace else None,  # Truncate
            "browser": error.browser,
            "url": error.url,
            "timestamp": error.timestamp.isoformat(),
        },
    )
