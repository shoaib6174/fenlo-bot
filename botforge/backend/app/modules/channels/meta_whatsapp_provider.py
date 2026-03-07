"""
Meta WhatsApp Cloud API Channel Provider — Inbound webhook handling, HMAC validation, message delivery.

Handles WhatsApp messages via Meta's Graph API with signature validation, message extraction,
and response delivery. Uses acknowledge-first pattern for webhook handling.
"""

import hashlib
import hmac
from typing import Any
from uuid import UUID

import httpx
import structlog

from app.config import settings
from app.models.channel import ChannelConfig
from app.modules.channels.provider import ChannelProvider, ChannelSendResult, InboundMessage

logger = structlog.get_logger(__name__)


class MetaWhatsAppProvider(ChannelProvider):
    """Meta WhatsApp Cloud API channel provider with signature validation and message handling."""

    @staticmethod
    def _get_credentials(config: ChannelConfig | None = None) -> tuple[str, str, str, str]:
        """
        Get Meta credentials from channel config (DB/UI), falling back to env vars.

        Returns:
            Tuple of (access_token, phone_number_id, app_secret, api_version)
        """
        cfg = config.config if config and config.config else {}
        access_token = cfg.get("access_token") or settings.meta_whatsapp_access_token
        phone_number_id = cfg.get("phone_number_id") or settings.meta_whatsapp_phone_number_id
        app_secret = cfg.get("app_secret") or settings.meta_whatsapp_app_secret
        api_version = cfg.get("api_version") or settings.meta_whatsapp_api_version
        return access_token, phone_number_id, app_secret, api_version

    async def send_message(
        self, conversation_id: UUID, message: str, config: ChannelConfig
    ) -> ChannelSendResult:
        """
        Send WhatsApp message via Meta Graph API.

        Args:
            conversation_id: BotForge conversation ID (for logging/tracking)
            message: Message content to send
            config: Channel configuration with Meta credentials

        Returns:
            ChannelSendResult with success status and Meta message ID (wamid)
        """
        try:
            access_token, phone_number_id, _, api_version = self._get_credentials(config)

            to_number = config.config.get("recipient_phone")
            if not to_number:
                logger.error(
                    "meta_send_failed_no_recipient",
                    conversation_id=str(conversation_id),
                    config_id=str(config.id),
                )
                return ChannelSendResult(
                    success=False,
                    error="Recipient phone number not found in config",
                    should_retry=False,
                )

            formatted_message = await self.format_message(message, config.config)

            url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_number,
                "type": "text",
                "text": {"preview_url": False, "body": formatted_message},
            }

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

            wamid = data.get("messages", [{}])[0].get("id", "")

            logger.info(
                "meta_message_sent",
                conversation_id=str(conversation_id),
                wamid=wamid,
                to_number=to_number,
            )

            return ChannelSendResult(
                success=True,
                provider_message_id=wamid,
                error=None,
                should_retry=False,
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                "meta_send_http_error",
                conversation_id=str(conversation_id),
                status_code=e.response.status_code,
                response_body=e.response.text,
                exc_info=True,
            )
            should_retry = e.response.status_code >= 500
            return ChannelSendResult(
                success=False,
                provider_message_id=None,
                error=f"HTTP {e.response.status_code}: {e.response.text}",
                should_retry=should_retry,
            )

        except Exception as e:
            logger.error(
                "meta_send_failed",
                conversation_id=str(conversation_id),
                error=str(e),
                exc_info=True,
            )
            should_retry = "timeout" in str(e).lower() or "connection" in str(e).lower()
            return ChannelSendResult(
                success=False,
                provider_message_id=None,
                error=str(e),
                should_retry=should_retry,
            )

    async def validate_config(self, config: dict) -> bool:
        """
        Validate Meta WhatsApp Cloud API configuration.

        Checks DB config first (access_token, phone_number_id, app_secret), falls back to env vars.

        Args:
            config: Channel config dict from DB

        Returns:
            True if Meta credentials are available (DB or env vars)
        """
        access_token = (config.get("access_token") or "").strip() or (
            settings.meta_whatsapp_access_token or ""
        ).strip()
        phone_number_id = (config.get("phone_number_id") or "").strip() or (
            settings.meta_whatsapp_phone_number_id or ""
        ).strip()
        app_secret = (config.get("app_secret") or "").strip() or (
            settings.meta_whatsapp_app_secret or ""
        ).strip()

        return bool(access_token and phone_number_id and app_secret)

    async def process_inbound(self, payload: dict, config: ChannelConfig) -> InboundMessage:
        """
        Process inbound WhatsApp message from Meta webhook.

        Meta webhook payload structure:
        {
            "entry": [{
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"display_phone_number": "...", "phone_number_id": "..."},
                        "contacts": [{"profile": {"name": "..."}, "wa_id": "..."}],
                        "messages": [{
                            "from": "15551234567",
                            "id": "wamid.xxx",
                            "timestamp": "...",
                            "text": {"body": "Hello"},
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }

        Args:
            payload: Meta webhook payload dict
            config: Channel configuration

        Returns:
            InboundMessage with extracted content and sender info

        Raises:
            ValueError: If payload is malformed or missing required fields
        """
        if not isinstance(payload, dict):
            raise ValueError("Invalid payload: must be a dict")

        entries = payload.get("entry")
        if not entries or not isinstance(entries, list):
            raise ValueError("Invalid payload: 'entry' is required and must be a list")

        changes = entries[0].get("changes")
        if not changes or not isinstance(changes, list):
            raise ValueError("Invalid payload: 'entry[0].changes' is required")

        value = changes[0].get("value", {})
        messages = value.get("messages")
        if not messages or not isinstance(messages, list):
            raise ValueError("Invalid payload: no messages found in webhook")

        msg = messages[0]
        wamid = msg.get("id")
        if not wamid:
            raise ValueError("Invalid payload: message 'id' (wamid) is required")

        sender = msg.get("from", "")
        if not sender:
            raise ValueError("Invalid payload: message 'from' is required")

        msg_type = msg.get("type", "text")
        if msg_type == "text":
            body = msg.get("text", {}).get("body", "").strip()
        else:
            body = f"[{msg_type} message]"

        if not body:
            raise ValueError("Invalid payload: message body is empty")

        metadata: dict[str, Any] = {}
        contacts = value.get("contacts", [])
        if contacts:
            contact = contacts[0]
            profile_name = contact.get("profile", {}).get("name")
            if profile_name:
                metadata["contact_name"] = profile_name

        metadata["message_type"] = msg_type

        return InboundMessage(
            content=body,
            sender_id=sender,
            provider_message_id=wamid,
            metadata=metadata,
        )

    async def format_message(self, content: str, config: dict) -> str:
        """
        Format message for WhatsApp delivery via Meta Cloud API.

        Plain text passthrough (same as Twilio provider).

        Args:
            content: Raw message content
            config: Channel config (unused for now)

        Returns:
            Formatted message string (plain text)
        """
        return content

    # --- Meta-Specific Methods (not in ChannelProvider Protocol) ---

    def validate_webhook_signature(
        self,
        signature_header: str,
        raw_body: bytes,
        config: ChannelConfig | None = None,
    ) -> bool:
        """
        Validate Meta webhook request signature using HMAC-SHA256.

        Meta signs webhook requests with HMAC-SHA256(app_secret, raw_body).
        The signature is sent in the X-Hub-Signature-256 header as "sha256=<hex>".

        Args:
            signature_header: Value from X-Hub-Signature-256 header (e.g. "sha256=abc123...")
            raw_body: Raw request body bytes
            config: Optional channel config to read app_secret from DB

        Returns:
            True if signature is valid, False otherwise
        """
        if not signature_header or not raw_body:
            return False

        try:
            _, _, app_secret, _ = self._get_credentials(config)
            if not app_secret:
                logger.error("meta_webhook_validation_no_app_secret")
                return False

            # Strip "sha256=" prefix
            if not signature_header.startswith("sha256="):
                return False
            expected_hash = signature_header[7:]

            computed_hash = hmac.new(
                app_secret.encode("utf-8"),
                raw_body,
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(computed_hash, expected_hash)

        except Exception as e:
            logger.error("meta_webhook_signature_validation_error", error=str(e))
            return False
