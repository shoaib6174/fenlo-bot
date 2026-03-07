"""
WhatsApp Webhook API — Meta Cloud API inbound message + status callback handling.

Implements acknowledge-first pattern: return 200 to Meta immediately,
process message pipeline asynchronously, send response as separate message.
"""

import asyncio

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.context_manager import LoadContextStep, PersistenceStep
from app.core.engine import MessageContext, MessagePipeline
from app.core.llm_router import LLMRouter
from app.core.prompt_guard import PromptGuardStep
from app.core.response_streamer import LLMStreamStep
from app.core.steps.analytics import IntentClassifierStep, QualityScorerStep, SentimentAnalysisStep
from app.core.steps.escalation_step import EscalationStep
from app.core.steps.handoff_guard import HandoffGuardStep
from app.core.steps.lead_scoring import LeadScoringStep
from app.core.steps.post_response_gap import PostResponseGapStep
from app.core.steps.rag_retrieval import RAGRetrievalStep
from app.dependencies import get_db
from app.models.channel import ChannelConfig, MessageDeliveryLog
from app.models.conversation import Conversation
from app.modules.channels.meta_whatsapp_provider import MetaWhatsAppProvider

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/channels/whatsapp-meta", tags=["whatsapp-meta"])


@router.get("/webhook")
async def meta_webhook_verify(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
) -> PlainTextResponse:
    """
    Meta webhook verification handshake.

    When configuring a webhook URL in Meta's App Dashboard, Meta sends a GET request
    with hub.mode=subscribe, hub.verify_token, and hub.challenge.
    We must return hub.challenge if the verify_token matches our configured value.
    """
    if hub_mode != "subscribe":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid hub.mode",
        )

    # Check verify_token against config
    expected_token = settings.meta_whatsapp_verify_token
    if not expected_token or hub_verify_token != expected_token:
        logger.warning(
            "meta_webhook_verify_failed",
            hub_mode=hub_mode,
            token_match=False,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify token mismatch",
        )

    logger.info("meta_webhook_verified")
    return PlainTextResponse(content=hub_challenge or "", status_code=status.HTTP_200_OK)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def meta_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Receive inbound WhatsApp messages and status updates from Meta webhook.

    Implements acknowledge-first pattern:
    1. Validate X-Hub-Signature-256 signature (HMAC-SHA256)
    2. Check idempotency (Redis dedup by wamid)
    3. Return 200 OK to Meta immediately
    4. Process message pipeline asynchronously
    5. Send response as separate outbound message
    """
    raw_body = await request.body()
    payload = await request.json()

    # --- Step 1: Validate Meta signature (HMAC-SHA256) ---
    provider = MetaWhatsAppProvider()

    # Load channel config from DB
    stmt = select(ChannelConfig).where(
        ChannelConfig.channel == "whatsapp",
        ChannelConfig.provider == "meta",
        ChannelConfig.is_active,
    )
    result = await db.execute(stmt)
    channel_config = result.scalars().first()

    if not x_hub_signature_256:
        logger.warning("meta_webhook_missing_signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Hub-Signature-256 header",
        )

    if not provider.validate_webhook_signature(
        x_hub_signature_256, raw_body, config=channel_config
    ):
        logger.warning("meta_webhook_invalid_signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Meta signature",
        )

    # --- Determine event type ---
    # Meta sends both messages and status updates through the same endpoint
    entries = payload.get("entry", [])
    if not entries:
        return Response(content="OK", status_code=status.HTTP_200_OK)

    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})

            # Handle inbound messages
            messages = value.get("messages", [])
            if messages:
                for msg in messages:
                    wamid = msg.get("id", "")
                    if not wamid:
                        continue

                    # Redis idempotency dedup
                    from app.core.redis import get_resilient_redis

                    redis = get_resilient_redis()
                    idempotency_key = f"meta_msg:{wamid}"
                    is_duplicate = await redis.get(idempotency_key)
                    if is_duplicate:
                        logger.info("meta_webhook_duplicate_ignored", wamid=wamid)
                        continue

                    await redis.set(idempotency_key, "1", ex=86400)

                    # Fire-and-forget async processing
                    asyncio.create_task(_process_meta_message_async(payload=payload))

            # Handle status updates
            statuses = value.get("statuses", [])
            if statuses:
                for status_update in statuses:
                    asyncio.create_task(
                        _process_meta_status_async(status_update=status_update, db_url=None)
                    )

    return Response(content="OK", status_code=status.HTTP_200_OK)


async def _process_meta_message_async(payload: dict) -> None:
    """
    Process Meta WhatsApp message asynchronously after acknowledging webhook.

    Steps:
    1. Extract message using MetaWhatsAppProvider.process_inbound()
    2. Find or create conversation by external_id (phone number)
    3. Run message through ConversationEngine pipeline
    4. Send response via MetaWhatsAppProvider.send_message()
    """
    from app.dependencies import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            provider = MetaWhatsAppProvider()

            # Placeholder config for message extraction
            temp_config = ChannelConfig(
                workspace_id="00000000-0000-0000-0000-000000000000",
                channel="whatsapp",
                provider="meta",
                config={},
                is_active=True,
            )

            inbound_message = await provider.process_inbound(payload, temp_config)
            sender_phone = inbound_message.sender_id

            logger.info(
                "meta_message_processing_started",
                wamid=inbound_message.provider_message_id,
                from_number=sender_phone,
            )

            # Find Meta whatsapp channel config
            stmt = select(ChannelConfig).where(
                ChannelConfig.channel == "whatsapp",
                ChannelConfig.provider == "meta",
                ChannelConfig.is_active,
            )
            result = await db.execute(stmt)
            whatsapp_configs = result.scalars().all()

            if not whatsapp_configs:
                logger.error(
                    "meta_no_active_config",
                    wamid=inbound_message.provider_message_id,
                    from_number=sender_phone,
                )
                return

            channel_config = whatsapp_configs[0]
            workspace_id = channel_config.workspace_id

            # Look for existing conversation
            stmt = select(Conversation).where(
                Conversation.workspace_id == workspace_id,
                Conversation.channel == "whatsapp",
                Conversation.external_id == sender_phone,
            )
            result = await db.execute(stmt)
            conversation = result.scalar_one_or_none()

            if not conversation:
                contact_name = inbound_message.metadata.get(
                    "contact_name", f"WhatsApp: {sender_phone}"
                )
                conversation = Conversation(
                    workspace_id=workspace_id,
                    channel="whatsapp",
                    external_id=sender_phone,
                    contact_name=contact_name,
                )
                db.add(conversation)
                await db.flush()

                logger.info(
                    "meta_conversation_created",
                    conversation_id=str(conversation.id),
                    phone=sender_phone,
                    workspace_id=str(workspace_id),
                )

            # Run message through pipeline
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
                    QualityScorerStep(),
                    LeadScoringStep(),
                    EscalationStep(db),
                    PersistenceStep(db),
                ]
            )

            context = MessageContext(
                conversation_id=conversation.id,
                workspace_id=workspace_id,
                user_id=None,
                message=inbound_message.content,
            )

            context.metadata["llm_router"] = LLMRouter()
            context.metadata["synchronous"] = True

            try:
                async with asyncio.timeout(12):
                    result = await pipeline.process(context)
                response_content = result.response or ""

                logger.info(
                    "meta_pipeline_completed",
                    conversation_id=str(conversation.id),
                    wamid=inbound_message.provider_message_id,
                    response_length=len(response_content),
                )

            except TimeoutError:
                logger.warning(
                    "meta_pipeline_timeout",
                    conversation_id=str(conversation.id),
                    wamid=inbound_message.provider_message_id,
                )
                response_content = "Sorry, I'm taking longer than usual to process your message. Please try again in a moment."

            if not response_content:
                response_content = (
                    "I received your message but couldn't generate a response. Please try again."
                )

            # Send response via Meta API
            channel_config.config["recipient_phone"] = sender_phone

            send_result = await provider.send_message(
                conversation_id=conversation.id,
                message=response_content,
                config=channel_config,
            )

            if send_result.success:
                logger.info(
                    "meta_response_sent",
                    conversation_id=str(conversation.id),
                    wamid=inbound_message.provider_message_id,
                    response_wamid=send_result.provider_message_id,
                )
            else:
                logger.error(
                    "meta_response_send_failed",
                    conversation_id=str(conversation.id),
                    wamid=inbound_message.provider_message_id,
                    error=send_result.error,
                )

        except Exception as e:
            logger.error(
                "meta_message_processing_failed",
                error=str(e),
                exc_info=True,
            )


async def _process_meta_status_async(status_update: dict, db_url: str | None = None) -> None:
    """
    Process Meta WhatsApp delivery status update.

    Meta status updates: sent, delivered, read, failed.
    """
    from app.dependencies import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            wamid = status_update.get("id", "")
            msg_status = status_update.get("status", "")
            recipient = status_update.get("recipient_id", "")

            # Extract error info if present
            errors = status_update.get("errors", [])
            error_code = errors[0].get("code", "") if errors else None
            error_message = errors[0].get("title", "") if errors else None

            # Find workspace from meta channel config
            stmt = select(ChannelConfig).where(
                ChannelConfig.channel == "whatsapp",
                ChannelConfig.provider == "meta",
                ChannelConfig.is_active,
            )
            result = await db.execute(stmt)
            channel_config = result.scalars().first()
            workspace_id = channel_config.workspace_id if channel_config else None

            delivery_log = MessageDeliveryLog(
                workspace_id=workspace_id,
                provider_message_id=wamid,
                channel="whatsapp",
                status=msg_status,
                error_code=str(error_code) if error_code else None,
                error_message=error_message,
                raw_payload=status_update,
            )
            db.add(delivery_log)
            await db.commit()

            logger.info(
                "meta_status_logged",
                wamid=wamid,
                status=msg_status,
                recipient=recipient,
                error_code=error_code,
            )

        except Exception as e:
            logger.error(
                "meta_status_processing_failed",
                error=str(e),
                exc_info=True,
            )
