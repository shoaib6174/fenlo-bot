"""
Telegram Bot Channel Provider — Bot API integration for message handling.

Uses Telegram Bot API (HTTP-based, no SDK). Handles inbound message processing,
outbound message delivery, and webhook registration.

Telegram Bot API docs: https://core.telegram.org/bots/api
"""

from uuid import UUID

import httpx
import structlog

from app.models.channel import ChannelConfig
from app.modules.channels.provider import ChannelProvider, ChannelSendResult, InboundMessage

logger = structlog.get_logger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramProvider(ChannelProvider):
    """Telegram Bot channel provider using Bot API (HTTP, no SDK)."""

    @staticmethod
    def _get_bot_token(config: ChannelConfig | None = None) -> str:
        """Get bot token from channel config."""
        cfg = config.config if config and config.config else {}
        return cfg.get("bot_token", "")

    @staticmethod
    def _get_chat_id(config: ChannelConfig | None = None) -> str:
        """Get recipient chat_id from channel config."""
        cfg = config.config if config and config.config else {}
        return str(cfg.get("recipient_chat_id", ""))

    async def send_message(
        self, conversation_id: UUID, message: str, config: ChannelConfig
    ) -> ChannelSendResult:
        """Send a message via Telegram Bot API sendMessage."""
        try:
            bot_token = self._get_bot_token(config)
            chat_id = self._get_chat_id(config)

            if not bot_token:
                return ChannelSendResult(
                    success=False,
                    error="Bot token not configured",
                    should_retry=False,
                )
            if not chat_id:
                return ChannelSendResult(
                    success=False,
                    error="Recipient chat_id not found in config",
                    should_retry=False,
                )

            formatted = await self.format_message(message, config.config)

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": formatted,
                        "parse_mode": "Markdown",
                    },
                )

            if response.status_code == 200:
                data = response.json()
                msg_id = str(data.get("result", {}).get("message_id", ""))
                logger.info(
                    "telegram_message_sent",
                    conversation_id=str(conversation_id),
                    message_id=msg_id,
                )
                return ChannelSendResult(
                    success=True,
                    provider_message_id=msg_id,
                )
            else:
                error_msg = response.text[:200]
                should_retry = response.status_code >= 500
                logger.error(
                    "telegram_send_failed",
                    status=response.status_code,
                    error=error_msg,
                )
                return ChannelSendResult(
                    success=False,
                    error=f"Telegram API error {response.status_code}: {error_msg}",
                    should_retry=should_retry,
                )

        except Exception as e:
            logger.error("telegram_send_exception", error=str(e), exc_info=True)
            should_retry = "timeout" in str(e).lower() or "connection" in str(e).lower()
            return ChannelSendResult(
                success=False,
                error=str(e),
                should_retry=should_retry,
            )

    async def validate_config(self, config: dict) -> bool:
        """Validate Telegram bot configuration by calling getMe."""
        bot_token = config.get("bot_token", "").strip()
        if not bot_token:
            return False

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{TELEGRAM_API_BASE}/bot{bot_token}/getMe",
                )
            if response.status_code == 200:
                data = response.json()
                return data.get("ok", False)
            return False
        except Exception:
            return False

    async def process_inbound(self, payload: dict, config: ChannelConfig) -> InboundMessage:
        """
        Process inbound Telegram update.

        Telegram update structure:
        {
            "update_id": 123456789,
            "message": {
                "message_id": 123,
                "from": {"id": 12345, "first_name": "John"},
                "chat": {"id": 12345, "type": "private"},
                "text": "Hello bot"
            }
        }
        """
        if not isinstance(payload, dict):
            raise ValueError("Invalid payload: must be a dict")

        message = payload.get("message", {})
        if not message:
            raise ValueError("Invalid payload: 'message' field required")

        text = message.get("text", "").strip()
        if not text:
            raise ValueError("Invalid payload: message text is empty")

        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))
        if not chat_id:
            raise ValueError("Invalid payload: chat.id is required")

        message_id = str(message.get("message_id", ""))
        update_id = str(payload.get("update_id", ""))

        from_user = message.get("from", {})
        metadata = {
            "first_name": from_user.get("first_name", ""),
            "username": from_user.get("username", ""),
            "chat_type": chat.get("type", "private"),
        }

        return InboundMessage(
            content=text,
            sender_id=chat_id,
            provider_message_id=update_id or message_id,
            metadata=metadata,
        )

    async def format_message(self, content: str, config: dict) -> str:
        """Format message for Telegram (Markdown passthrough)."""
        return content

    # --- Telegram-Specific Methods ---

    async def register_webhook(self, bot_token: str, webhook_url: str) -> bool:
        """Register webhook URL with Telegram Bot API."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{TELEGRAM_API_BASE}/bot{bot_token}/setWebhook",
                    json={"url": webhook_url},
                )
            if response.status_code == 200:
                data = response.json()
                return data.get("ok", False)
            return False
        except Exception as e:
            logger.error("telegram_webhook_register_failed", error=str(e))
            return False

    async def get_bot_info(self, bot_token: str) -> dict | None:
        """Get bot info via getMe API call."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{TELEGRAM_API_BASE}/bot{bot_token}/getMe",
                )
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return data.get("result", {})
            return None
        except Exception:
            return None
