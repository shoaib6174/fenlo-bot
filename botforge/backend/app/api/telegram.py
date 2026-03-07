"""
Telegram Webhook API — Bot API inbound message handling.

Implements acknowledge-first pattern: return 200 to Telegram immediately,
process message pipeline asynchronously, send response via Bot API.
"""

import asyncio
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context_manager import LoadContextStep, PersistenceStep
from app.core.engine import MessageContext, MessagePipeline
from app.core.llm_router import LLMRouter
from app.core.prompt_guard import PromptGuardStep
from app.core.response_streamer import LLMStreamStep
from app.core.steps.analytics import IntentClassifierStep, QualityScorerStep, SentimentAnalysisStep
from app.core.steps.booking import BookingEnrichmentStep
from app.core.steps.escalation_step import EscalationStep
from app.core.steps.handoff_guard import HandoffGuardStep
from app.core.steps.lead_scoring import LeadScoringStep
from app.core.steps.post_response_gap import PostResponseGapStep
from app.core.steps.rag_retrieval import RAGRetrievalStep
from app.dependencies import get_db
from app.models.channel import ChannelConfig
from app.models.conversation import Conversation
from app.modules.channels.telegram_provider import TelegramProvider

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/channels/telegram", tags=["telegram"])


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Receive inbound Telegram update via Bot API webhook.

    Flow:
    1. Parse JSON body
    2. Check idempotency (Redis dedup by update_id)
    3. Return 200 OK immediately
    4. Process message pipeline asynchronously
    5. Send response via sendMessage API
    """
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    # Only handle message updates (skip edited_message, channel_post, etc.)
    message = payload.get("message")
    if not message or not message.get("text"):
        return JSONResponse({"ok": True})

    update_id = str(payload.get("update_id", ""))
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not chat_id:
        return JSONResponse({"ok": True})

    # --- Idempotency check (Redis dedup by update_id) ---
    from app.core.redis import get_resilient_redis

    redis = get_resilient_redis()
    idempotency_key = f"telegram_update:{update_id}"
    is_duplicate = await redis.get(idempotency_key)
    if is_duplicate:
        logger.info("telegram_webhook_duplicate", update_id=update_id)
        return JSONResponse({"ok": True})

    await redis.set(idempotency_key, "1", ex=86400)

    # --- Find channel config ---
    stmt = select(ChannelConfig).where(
        ChannelConfig.channel == "telegram",
        ChannelConfig.is_active,
    )
    result = await db.execute(stmt)
    channel_config = result.scalars().first()

    if not channel_config:
        logger.warning("telegram_webhook_no_config", chat_id=chat_id)
        return JSONResponse({"ok": True})

    # --- Acknowledge and process async ---
    asyncio.create_task(
        _process_telegram_message(
            payload=payload,
            channel_config_id=str(channel_config.id),
            workspace_id=str(channel_config.workspace_id),
            bot_token=channel_config.config.get("bot_token", ""),
        )
    )

    return JSONResponse({"ok": True})


async def _process_telegram_message(
    payload: dict[str, Any],
    channel_config_id: str,
    workspace_id: str,
    bot_token: str,
) -> None:
    """Process Telegram message through pipeline and send response."""
    from uuid import UUID

    from app.dependencies import AsyncSessionLocal

    provider = TelegramProvider()

    async with AsyncSessionLocal() as db:
        try:
            # Load channel config
            stmt = select(ChannelConfig).where(ChannelConfig.id == UUID(channel_config_id))
            result = await db.execute(stmt)
            channel_config = result.scalar_one_or_none()

            if not channel_config:
                logger.error("telegram_process_no_config", config_id=channel_config_id)
                return

            # Parse inbound message
            inbound = await provider.process_inbound(payload, channel_config)
            chat_id = inbound.sender_id
            text = inbound.content

            logger.info(
                "telegram_message_received",
                chat_id=chat_id,
                text_length=len(text),
                username=inbound.metadata.get("username", ""),
            )

            # Find or create conversation
            ws_id = UUID(workspace_id)
            stmt = select(Conversation).where(
                Conversation.workspace_id == ws_id,
                Conversation.channel == "telegram",
                Conversation.metadata["sender_id"].astext == chat_id,
                Conversation.status.in_(["active", "pending"]),
            )
            result = await db.execute(stmt)
            conversation = result.scalar_one_or_none()

            if not conversation:
                conversation = Conversation(
                    workspace_id=ws_id,
                    channel="telegram",
                    status="active",
                    metadata={
                        "sender_id": chat_id,
                        "first_name": inbound.metadata.get("first_name", ""),
                        "username": inbound.metadata.get("username", ""),
                    },
                )
                db.add(conversation)
                await db.flush()
                logger.info("telegram_conversation_created", conversation_id=str(conversation.id))

            # Build pipeline
            llm_router = LLMRouter()

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
                workspace_id=ws_id,
                user_id=None,
                conversation_id=conversation.id,
                message=text,
            )
            context.metadata["llm_router"] = llm_router
            context.metadata["channel"] = "telegram"

            msg_result = await pipeline.process(context)

            # Send response via Telegram
            if msg_result.response:
                # Update config with recipient chat_id for response
                channel_config.config["recipient_chat_id"] = chat_id
                send_result = await provider.send_message(
                    conversation_id=conversation.id,
                    message=msg_result.response,
                    config=channel_config,
                )

                if not send_result.success:
                    logger.error(
                        "telegram_response_failed",
                        error=send_result.error,
                        chat_id=chat_id,
                    )

        except Exception as e:
            logger.error("telegram_process_error", error=str(e), exc_info=True)
