"""Channel Response Router — Route agent replies through the original channel.

Centralizes response delivery across all channels (Widget, WhatsApp, Web) with
retry-on-failure logic via WebhookOutbox. Implements Spec Panel Review A-03.

Usage:
    result = await send_channel_response(conversation_id, "Thanks!", db)
    if not result.success:
        logger.error("send_failed", error=result.error)
"""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventTypes, create_event_bus
from app.models.channel import ChannelConfig
from app.models.conversation import Conversation
from app.modules.channels.meta_whatsapp_provider import MetaWhatsAppProvider
from app.modules.channels.provider import ChannelProvider, ChannelSendResult
from app.modules.channels.telegram_provider import TelegramProvider
from app.modules.channels.twilio_whatsapp_provider import TwilioWhatsAppProvider
from app.modules.channels.widget_provider import WidgetProvider

logger = structlog.get_logger(__name__)


# --- Provider Registry ---
# Compound keys for provider-specific routing: "channel:provider"
# Fallback keys without provider for backwards compatibility.

_PROVIDER_REGISTRY: dict[str, ChannelProvider] = {
    "whatsapp": TwilioWhatsAppProvider(),  # default fallback
    "whatsapp:twilio": TwilioWhatsAppProvider(),
    "whatsapp:meta": MetaWhatsAppProvider(),
    "web": WidgetProvider(),  # Widget provider handles web channel
    "telegram": TelegramProvider(),
    # "voice": VapiProvider(),  # TODO: implement
}

# Channel mapping: Conversation.channel → ChannelConfig.channel
# (Conversation uses 'web', but ChannelConfig uses 'widget')
_CHANNEL_CONFIG_MAP: dict[str, str] = {
    "web": "widget",
    "whatsapp": "whatsapp",
    "telegram": "telegram",
    "voice": "voice",
}


async def send_channel_response(
    conversation_id: UUID,
    message: str,
    db: AsyncSession,
) -> ChannelSendResult:
    """Route agent reply through the original channel.

    Flow:
    1. Look up conversation's channel + config
    2. Resolve ChannelProvider from registry
    3. Call provider.send_message(conversation_id, message, config)
    4. On failure with should_retry=True → publish WEBHOOK_DELIVERY_REQUIRED event
    5. Return result

    Args:
        conversation_id: Target conversation UUID
        message: Agent reply content
        db: Database session

    Returns:
        ChannelSendResult with success status, provider_message_id, error details

    Raises:
        ValueError: If conversation not found or channel not supported
    """
    # Step 1: Look up conversation
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        error_msg = f"Conversation {conversation_id} not found"
        logger.error("response_router.conversation_not_found", conversation_id=str(conversation_id))
        return ChannelSendResult(
            success=False,
            error=error_msg,
            should_retry=False,
        )

    channel = conversation.channel
    workspace_id = conversation.workspace_id

    # Step 2: Map conversation channel to config channel and look up channel config
    # (Conversation uses 'web', but ChannelConfig uses 'widget')
    config_channel = _CHANNEL_CONFIG_MAP.get(channel, channel)

    stmt = select(ChannelConfig).where(
        ChannelConfig.workspace_id == workspace_id,
        ChannelConfig.channel == config_channel,
        ChannelConfig.is_active,
    )
    result = await db.execute(stmt)
    channel_config = result.scalar_one_or_none()

    if not channel_config:
        error_msg = f"No active channel config for {channel} (config: {config_channel}) in workspace {workspace_id}"
        logger.error(
            "response_router.no_channel_config",
            channel=channel,
            config_channel=config_channel,
            workspace_id=str(workspace_id),
        )
        return ChannelSendResult(
            success=False,
            error=error_msg,
            should_retry=False,
        )

    # Step 3: Resolve provider (provider-aware: "whatsapp:meta" or "whatsapp:twilio")
    provider_key = f"{channel}:{channel_config.provider}" if channel_config.provider else channel
    provider = _PROVIDER_REGISTRY.get(provider_key) or _PROVIDER_REGISTRY.get(channel)

    if not provider:
        error_msg = f"Channel '{channel}' not supported"
        logger.error("response_router.unsupported_channel", channel=channel)
        return ChannelSendResult(
            success=False,
            error=error_msg,
            should_retry=False,
        )

    # Step 4: Send message through provider
    logger.info(
        "response_router.sending",
        conversation_id=str(conversation_id),
        channel=channel,
        message_length=len(message),
    )

    send_result = await provider.send_message(
        conversation_id=conversation_id,
        message=message,
        config=channel_config,
    )

    if not send_result.success and send_result.should_retry:
        # Step 5: Queue in WebhookOutbox via event bus
        logger.warning(
            "response_router.send_failed_queueing",
            conversation_id=str(conversation_id),
            channel=channel,
            error=send_result.error,
        )

        from app.config import settings

        event_bus = create_event_bus(settings)
        await event_bus.publish(
            EventTypes.WEBHOOK_DELIVERY_REQUIRED,
            {
                "workspace_id": str(workspace_id),
                "conversation_id": str(conversation_id),
                "channel": channel,
                "message": message,
                "retry_count": 0,
            },
        )

    return send_result
