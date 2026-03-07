"""
WhatsApp Webhook API — Twilio inbound message + status callback handling.

Implements acknowledge-first pattern: return 200 to Twilio immediately,
process message pipeline asynchronously, send response as separate message.
"""

import asyncio
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context_manager import LoadContextStep, PersistenceStep
from app.core.engine import MessageContext, MessagePipeline
from app.core.event_bus import EventTypes, InProcessEventBus
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
from app.modules.channels.provider import InboundMessage
from app.modules.channels.twilio_whatsapp_provider import TwilioWhatsAppProvider

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/channels/whatsapp", tags=["whatsapp"])

# Module-level event bus instance (matches pattern used elsewhere)
_event_bus = InProcessEventBus()


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def whatsapp_webhook(
    request: Request,
    x_twilio_signature: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
    # Twilio sends webhook as form-encoded POST parameters
    MessageSid: str = Form(...),
    Body: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    NumMedia: str = Form("0"),
) -> Response:
    """
    Receive inbound WhatsApp message from Twilio webhook.

    Implements acknowledge-first pattern:
    1. Validate signature
    2. Check idempotency (Redis dedup by MessageSid)
    3. Return 200 OK to Twilio (within 1 second)
    4. Process message pipeline asynchronously
    5. Send response as separate outbound message

    Twilio webhook docs: https://www.twilio.com/docs/usage/webhooks
    """
    # --- Step 1: Validate Twilio signature (HMAC-SHA1) ---
    provider = TwilioWhatsAppProvider()

    # Get full URL for signature validation (Twilio signs the complete URL)
    url = str(request.url)

    # Get all form parameters for signature validation
    form_data = await request.form()
    params = dict(form_data.items())

    # Load channel config from DB — only match Twilio provider (exclude Meta configs)
    stmt = select(ChannelConfig).where(
        ChannelConfig.channel == "whatsapp",
        ChannelConfig.is_active,
        (ChannelConfig.provider.in_(["twilio"]) | ChannelConfig.provider.is_(None)),
    )
    result = await db.execute(stmt)
    channel_config = result.scalars().first()

    if not x_twilio_signature:
        logger.warning("whatsapp_webhook_missing_signature", message_sid=MessageSid)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Twilio-Signature header",
        )

    if not provider.validate_webhook_signature(
        x_twilio_signature, url, params, config=channel_config
    ):
        logger.warning(
            "whatsapp_webhook_invalid_signature",
            message_sid=MessageSid,
            from_number=From,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Twilio signature",
        )

    # --- Step 2: Check idempotency (Redis dedup by MessageSid) ---
    # Twilio may retry webhooks if we don't respond quickly enough (up to 3 times)
    # Use Redis to deduplicate by MessageSid with 24-hour TTL
    from app.core.redis import get_resilient_redis

    redis = get_resilient_redis()
    idempotency_key = f"twilio_msg:{MessageSid}"
    is_duplicate = await redis.get(idempotency_key)
    if is_duplicate:
        logger.info(
            "whatsapp_webhook_duplicate_ignored",
            message_sid=MessageSid,
            from_number=From,
        )
        # Return 200 OK (already processed)
        return Response(content="OK", status_code=status.HTTP_200_OK)

    # Mark as seen (24-hour TTL)
    await redis.set(idempotency_key, "1", ex=86400)

    # --- Step 3: Return 200 OK to Twilio immediately (acknowledge receipt) ---
    # We MUST respond within 15 seconds or Twilio will retry
    # Fire-and-forget async task to process message pipeline
    asyncio.create_task(
        _process_whatsapp_message_async(
            message_sid=MessageSid,
            body=Body,
            from_number=From,
            to_number=To,
            num_media=NumMedia,
            form_params=params,
        )
    )

    return Response(content="OK", status_code=status.HTTP_200_OK)


async def _process_whatsapp_message_async(
    message_sid: str,
    body: str,
    from_number: str,
    to_number: str,
    num_media: str,
    form_params: dict[str, Any],
) -> None:
    """
    Process WhatsApp message asynchronously after acknowledging webhook.

    Steps:
    1. Extract message using TwilioWhatsAppProvider.process_inbound()
    2. Find or create conversation by external_id (phone number)
    3. Run message through ConversationEngine pipeline
    4. Send response via TwilioWhatsAppProvider.send_message()

    Args:
        message_sid: Twilio MessageSid
        body: Message text content
        from_number: Sender phone number (with "whatsapp:" prefix)
        to_number: Recipient phone number (our sandbox number)
        num_media: Number of media attachments
        form_params: Full webhook payload for metadata extraction
    """
    from app.dependencies import AsyncSessionLocal

    # Get new DB session for async task (separate from request session)
    async with AsyncSessionLocal() as db:
        try:
            logger.info(
                "whatsapp_message_processing_started",
                message_sid=message_sid,
                from_number=from_number,
            )

            # --- Step 1: Extract message using provider ---
            provider = TwilioWhatsAppProvider()

            # Build payload dict for process_inbound
            payload = {
                "MessageSid": message_sid,
                "Body": body,
                "From": from_number,
                "To": to_number,
                "NumMedia": num_media,
            }

            # Add media URLs if present
            for key, value in form_params.items():
                if key.startswith("MediaUrl"):
                    payload[key] = value

            # Placeholder config (will be fetched later when we know workspace)
            # For now, just extract the message
            temp_config = ChannelConfig(
                workspace_id="00000000-0000-0000-0000-000000000000",  # Placeholder
                channel="whatsapp",
                config={},
                is_active=True,
            )

            inbound_message: InboundMessage = await provider.process_inbound(payload, temp_config)

            # --- Step 2: Find or create conversation by external_id (phone number) ---
            sender_phone = inbound_message.sender_id

            # Look up conversation by external_id = phone number
            # Note: We need to find the workspace first by looking up the WhatsApp channel config
            # For now, we'll query for active Twilio whatsapp channel configs
            stmt = select(ChannelConfig).where(
                ChannelConfig.channel == "whatsapp",
                ChannelConfig.is_active,
                (ChannelConfig.provider.in_(["twilio"]) | ChannelConfig.provider.is_(None)),
            )
            result = await db.execute(stmt)
            whatsapp_configs = result.scalars().all()

            if not whatsapp_configs:
                logger.error(
                    "whatsapp_no_active_config",
                    message_sid=message_sid,
                    from_number=from_number,
                )
                return

            # Use the first active config (TODO: support multiple workspaces)
            channel_config = whatsapp_configs[0]
            workspace_id = channel_config.workspace_id

            # Look for existing conversation with this phone number
            stmt = select(Conversation).where(
                Conversation.workspace_id == workspace_id,
                Conversation.channel == "whatsapp",
                Conversation.external_id == sender_phone,
            )
            result = await db.execute(stmt)
            conversation = result.scalar_one_or_none()

            # Create conversation if not found
            if not conversation:
                conversation = Conversation(
                    workspace_id=workspace_id,
                    channel="whatsapp",
                    external_id=sender_phone,
                    contact_name=f"WhatsApp: {sender_phone}",
                )
                db.add(conversation)
                await db.flush()

                logger.info(
                    "whatsapp_conversation_created",
                    conversation_id=str(conversation.id),
                    phone=sender_phone,
                    workspace_id=str(workspace_id),
                )

            # --- Step 3: Run message through pipeline ---
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

            # Synchronous mode — no WebSocket streamer, collect full response
            context.metadata["llm_router"] = LLMRouter()
            context.metadata["synchronous"] = True

            # Run pipeline with 12-second timeout
            try:
                async with asyncio.timeout(12):
                    result = await pipeline.process(context)

                response_content = result.response or ""

                logger.info(
                    "whatsapp_pipeline_completed",
                    conversation_id=str(conversation.id),
                    message_sid=message_sid,
                    response_length=len(response_content),
                )

            except TimeoutError:
                logger.warning(
                    "whatsapp_pipeline_timeout",
                    conversation_id=str(conversation.id),
                    message_sid=message_sid,
                )
                response_content = "Sorry, I'm taking longer than usual to process your message. Please try again in a moment."

            # --- Step 4: Send response via Twilio ---
            if not response_content:
                response_content = (
                    "I received your message but couldn't generate a response. Please try again."
                )

            # Update channel config with recipient phone for send_message
            channel_config.config["recipient_phone"] = sender_phone

            send_result = await provider.send_message(
                conversation_id=conversation.id,
                message=response_content,
                config=channel_config,
            )

            if send_result.success:
                logger.info(
                    "whatsapp_response_sent",
                    conversation_id=str(conversation.id),
                    message_sid=message_sid,
                    response_message_sid=send_result.provider_message_id,
                )
            else:
                logger.error(
                    "whatsapp_response_send_failed",
                    conversation_id=str(conversation.id),
                    message_sid=message_sid,
                    error=send_result.error,
                )

        except Exception as e:
            logger.error(
                "whatsapp_message_processing_failed",
                message_sid=message_sid,
                from_number=from_number,
                error=str(e),
                exc_info=True,
            )


@router.post("/status", status_code=status.HTTP_200_OK)
async def whatsapp_status_callback(
    request: Request,
    x_twilio_signature: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
    # Twilio status callback form params
    MessageSid: str = Form(...),
    MessageStatus: str = Form(...),
    To: str = Form(""),
    From: str = Form(""),
    AccountSid: str = Form(""),
    ErrorCode: str | None = Form(None),
    ErrorMessage: str | None = Form(None),
) -> Response:
    """
    Receive delivery status callbacks from Twilio for outbound WhatsApp messages.

    Twilio sends: queued, sent, delivered, failed, undelivered, read.
    Always returns 200 to prevent Twilio retries.
    """
    # --- Step 1: Validate Twilio signature ---
    provider = TwilioWhatsAppProvider()
    url = str(request.url)
    form_data = await request.form()
    params = dict(form_data.items())

    # Load channel config from DB — only match Twilio provider (exclude Meta configs)
    stmt = select(ChannelConfig).where(
        ChannelConfig.channel == "whatsapp",
        ChannelConfig.is_active,
        (ChannelConfig.provider.in_(["twilio"]) | ChannelConfig.provider.is_(None)),
    )
    result = await db.execute(stmt)
    channel_config = result.scalars().first()

    if not x_twilio_signature:
        logger.warning("whatsapp_status_missing_signature", message_sid=MessageSid)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Twilio-Signature header",
        )

    if not provider.validate_webhook_signature(
        x_twilio_signature, url, params, config=channel_config
    ):
        logger.warning(
            "whatsapp_status_invalid_signature",
            message_sid=MessageSid,
            status=MessageStatus,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Twilio signature",
        )

    # --- Step 2: Redis idempotency check (MessageSid + status combo) ---
    from app.core.redis import get_resilient_redis

    redis = get_resilient_redis()
    idempotency_key = f"twilio_status:{MessageSid}:{MessageStatus}"
    is_duplicate = await redis.get(idempotency_key)
    if is_duplicate:
        logger.debug(
            "whatsapp_status_duplicate_ignored",
            message_sid=MessageSid,
            status=MessageStatus,
        )
        return Response(content="OK", status_code=status.HTTP_200_OK)

    await redis.set(idempotency_key, "1", ex=86400)

    workspace_id = channel_config.workspace_id if channel_config else None

    # --- Step 4: Log delivery status ---
    delivery_log = MessageDeliveryLog(
        workspace_id=workspace_id,
        provider_message_id=MessageSid,
        channel="whatsapp",
        status=MessageStatus,
        error_code=ErrorCode,
        error_message=ErrorMessage,
        raw_payload=params,
    )
    db.add(delivery_log)
    await db.commit()

    logger.info(
        "whatsapp_status_logged",
        message_sid=MessageSid,
        status=MessageStatus,
        error_code=ErrorCode,
        workspace_id=str(workspace_id) if workspace_id else None,
    )

    # --- Step 5: Publish event for webhook outbox ---
    asyncio.create_task(
        _event_bus.publish(
            EventTypes.MESSAGE_DELIVERY_STATUS,
            {
                "workspace_id": str(workspace_id) if workspace_id else None,
                "provider_message_id": MessageSid,
                "channel": "whatsapp",
                "status": MessageStatus,
                "error_code": ErrorCode,
            },
        )
    )

    return Response(content="OK", status_code=status.HTTP_200_OK)
