"""
Twilio WhatsApp Channel Provider — Inbound webhook handling, HMAC validation, message delivery.

Handles WhatsApp messages via Twilio API with signature validation, message extraction,
and response delivery. Uses acknowledge-first pattern for webhook handling.
"""

import base64
import hashlib
import hmac
from typing import Any
from uuid import UUID

import structlog
from twilio.rest import Client as TwilioClient

from app.config import settings
from app.models.channel import ChannelConfig
from app.modules.channels.provider import ChannelProvider, ChannelSendResult, InboundMessage

logger = structlog.get_logger(__name__)


class TwilioWhatsAppProvider(ChannelProvider):
    """Twilio WhatsApp channel provider with signature validation and message handling."""

    @staticmethod
    def _get_credentials(config: ChannelConfig | None = None) -> tuple[str, str, str]:
        """
        Get Twilio credentials from channel config (DB/UI), falling back to env vars.

        Returns:
            Tuple of (account_sid, auth_token, phone)
        """
        cfg = config.config if config and config.config else {}
        account_sid = cfg.get("account_sid") or settings.twilio_account_sid
        auth_token = cfg.get("auth_token") or settings.twilio_auth_token
        phone = cfg.get("phone") or settings.twilio_sandbox_phone
        return account_sid, auth_token, phone

    async def send_message(
        self, conversation_id: UUID, message: str, config: ChannelConfig
    ) -> ChannelSendResult:
        """
        Send WhatsApp message via Twilio REST API.

        Args:
            conversation_id: BotForge conversation ID (for logging/tracking)
            message: Message content to send
            config: Channel configuration with Twilio credentials

        Returns:
            ChannelSendResult with success status and Twilio MessageSid
        """
        try:
            # Extract config — DB config first, env vars as fallback
            account_sid, auth_token, from_number = self._get_credentials(config)

            # Get recipient from config metadata (set during conversation creation)
            # recipient_phone is stored in config.config dict when conversation is created
            to_number = config.config.get("recipient_phone")
            if not to_number:
                logger.error(
                    "twilio_send_failed_no_recipient",
                    conversation_id=str(conversation_id),
                    config_id=str(config.id),
                )
                return ChannelSendResult(
                    success=False,
                    error="Recipient phone number not found in config",
                    should_retry=False,
                )

            # Initialize Twilio client
            client = TwilioClient(account_sid, auth_token)

            # Format message for WhatsApp (plain text)
            formatted_message = await self.format_message(message, config.config)

            # Send message via Twilio
            twilio_message = client.messages.create(
                body=formatted_message,
                from_=f"whatsapp:{from_number}",
                to=f"whatsapp:{to_number}",
            )

            logger.info(
                "twilio_message_sent",
                conversation_id=str(conversation_id),
                message_sid=twilio_message.sid,
                to_number=to_number,
            )

            return ChannelSendResult(
                success=True,
                provider_message_id=twilio_message.sid,
                error=None,
                should_retry=False,
            )

        except Exception as e:
            logger.error(
                "twilio_send_failed",
                conversation_id=str(conversation_id),
                error=str(e),
                exc_info=True,
            )

            # Determine if we should retry based on error type
            should_retry = "timeout" in str(e).lower() or "connection" in str(e).lower()

            return ChannelSendResult(
                success=False,
                provider_message_id=None,
                error=str(e),
                should_retry=should_retry,
            )

    async def validate_config(self, config: dict) -> bool:
        """
        Validate Twilio WhatsApp configuration.

        Checks DB config first (account_sid, auth_token, phone), falls back to env vars.

        Args:
            config: Channel config dict from DB

        Returns:
            True if Twilio credentials are available (DB or env vars)
        """
        account_sid = (config.get("account_sid") or "").strip() or (
            settings.twilio_account_sid or ""
        ).strip()
        auth_token = (config.get("auth_token") or "").strip() or (
            settings.twilio_auth_token or ""
        ).strip()
        phone = (config.get("phone") or "").strip() or (settings.twilio_sandbox_phone or "").strip()

        return bool(account_sid and auth_token and phone)

    async def process_inbound(self, payload: dict, config: ChannelConfig) -> InboundMessage:
        """
        Process inbound WhatsApp message from Twilio webhook.

        Twilio webhook payload structure:
        {
            "MessageSid": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "Body": "Hello from WhatsApp",
            "From": "whatsapp:+1234567890",
            "To": "whatsapp:+14155238886",
            "NumMedia": "0",
            "MediaUrl0": "https://..." (if NumMedia > 0)
        }

        Args:
            payload: Twilio webhook payload dict
            config: Channel configuration

        Returns:
            InboundMessage with extracted content and sender info

        Raises:
            ValueError: If payload is malformed or missing required fields
        """
        if not isinstance(payload, dict):
            raise ValueError("Invalid payload: must be a dict")

        # Extract required fields
        message_sid = payload.get("MessageSid")
        if not message_sid:
            raise ValueError("Invalid payload: 'MessageSid' is required")

        body = payload.get("Body", "").strip()
        if not body:
            raise ValueError("Invalid payload: 'Body' must be a non-empty string")

        from_number = payload.get("From", "")
        if not from_number:
            raise ValueError("Invalid payload: 'From' is required")

        # Remove "whatsapp:" prefix if present
        sender_phone = from_number.replace("whatsapp:", "").strip()
        if not sender_phone:
            raise ValueError("Invalid payload: 'From' must contain a phone number")

        # Extract metadata (media URLs if present)
        metadata: dict[str, Any] = {}
        num_media = int(payload.get("NumMedia", "0"))
        if num_media > 0:
            media_urls = []
            for i in range(num_media):
                media_url = payload.get(f"MediaUrl{i}")
                if media_url:
                    media_urls.append(media_url)
            if media_urls:
                metadata["media_urls"] = media_urls

        return InboundMessage(
            content=body,
            sender_id=sender_phone,  # Phone number without "whatsapp:" prefix
            provider_message_id=message_sid,
            metadata=metadata,
        )

    async def format_message(self, content: str, config: dict) -> str:
        """
        Format message for WhatsApp delivery.

        WhatsApp supports plain text and some basic formatting (bold, italic).
        For now, we send plain text as-is. Future enhancement: support WhatsApp
        formatting codes (*bold*, _italic_, ~strikethrough~).

        Args:
            content: Raw message content
            config: Channel config (unused for now)

        Returns:
            Formatted message string (plain text)
        """
        return content

    # --- Twilio-Specific Methods (not in ChannelProvider Protocol) ---

    def validate_webhook_signature(
        self,
        signature: str,
        url: str,
        params: dict[str, str],
        config: ChannelConfig | None = None,
    ) -> bool:
        """
        Validate Twilio webhook request signature using HMAC-SHA1.

        Twilio signs webhook requests with HMAC-SHA1(auth_token, url + sorted_params).
        The signature is sent in the X-Twilio-Signature header.

        Args:
            signature: Value from X-Twilio-Signature header
            url: Full request URL (including protocol and any query params)
            params: All POST parameters from the request body
            config: Optional channel config to read auth_token from DB

        Returns:
            True if signature is valid, False otherwise
        """
        if not signature or not url:
            return False

        try:
            # Get auth token from DB config first, then env vars
            _, auth_token, _ = self._get_credentials(config)
            if not auth_token:
                logger.error("twilio_webhook_validation_no_auth_token")
                return False

            # Build the signature data: URL + sorted POST params
            data = url
            for key in sorted(params.keys()):
                data += key + params[key]

            # Compute HMAC-SHA1
            computed_signature = base64.b64encode(
                hmac.new(
                    auth_token.encode("utf-8"),
                    data.encode("utf-8"),
                    hashlib.sha1,
                ).digest()
            ).decode("utf-8")

            # Constant-time comparison to prevent timing attacks
            return hmac.compare_digest(computed_signature, signature)

        except Exception as e:
            logger.error("twilio_webhook_signature_validation_error", error=str(e))
            return False
