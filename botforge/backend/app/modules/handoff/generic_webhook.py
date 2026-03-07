"""Generic webhook handoff provider — sends escalations to any HTTP endpoint"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import httpx
import structlog

from app.modules.handoff.provider import EscalationPayload, HandoffResult

logger = structlog.get_logger(__name__)

# Timeout for outbound HTTP calls
WEBHOOK_TIMEOUT = 10.0


class GenericWebhookProvider:
    """
    Sends handoff events to a configurable webhook URL with HMAC signing.

    Config (from workspace.settings.handoff):
        webhook_url: Target URL for POST requests
        webhook_secret: Shared secret for HMAC-SHA256 signing
    """

    def __init__(self, webhook_url: str, webhook_secret: str):
        self.webhook_url = webhook_url
        self.webhook_secret = webhook_secret

    async def escalate(self, payload: EscalationPayload) -> HandoffResult:
        body = {
            "event": "conversation.escalated",
            "conversation_id": str(payload.conversation_id),
            "workspace_id": str(payload.workspace_id),
            "channel": payload.channel,
            "contact": {
                "name": payload.contact_name,
                "info": payload.contact_info,
            },
            "summary": payload.summary,
            "last_messages": payload.last_messages,
            "escalation_reason": payload.escalation_reason,
            "metadata": payload.metadata,
            "reply_url": payload.reply_url,
            "resolve_url": payload.resolve_url,
        }
        return await self._send("conversation.escalated", body)

    async def forward_message(
        self, external_ticket_id: str, message: str, sender_name: str | None = None
    ) -> HandoffResult:
        body = {
            "event": "conversation.message_forwarded",
            "external_ticket_id": external_ticket_id,
            "message": message,
            "sender_name": sender_name,
        }
        return await self._send("conversation.message_forwarded", body)

    async def resolve(
        self, external_ticket_id: str, resolution_note: str | None = None
    ) -> HandoffResult:
        body = {
            "event": "conversation.resolved",
            "external_ticket_id": external_ticket_id,
            "resolution_note": resolution_note,
        }
        return await self._send("conversation.resolved", body)

    async def _send(self, event_type: str, body: dict) -> HandoffResult:
        """Send signed webhook request to configured URL."""
        try:
            raw_body = json.dumps(body, default=str)
            timestamp = str(int(time.time()))
            signature = self._sign(timestamp, raw_body)

            headers = {
                "Content-Type": "application/json",
                "X-BotForge-Event": event_type,
                "X-BotForge-Timestamp": timestamp,
                "X-BotForge-Signature": signature,
            }

            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
                response = await client.post(self.webhook_url, content=raw_body, headers=headers)

            if response.status_code < 300:
                # Try to extract external ticket ID from response
                ticket_id = None
                try:
                    resp_data = response.json()
                    ticket_id = resp_data.get("ticket_id") or resp_data.get("id")
                except Exception:
                    pass

                logger.info(
                    "handoff_webhook.sent",
                    event_type=event_type,
                    status=response.status_code,
                    ticket_id=ticket_id,
                )
                return HandoffResult(
                    success=True,
                    external_ticket_id=str(ticket_id) if ticket_id else None,
                )
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning(
                    "handoff_webhook.failed",
                    event_type=event_type,
                    status=response.status_code,
                    error=error_msg,
                )
                return HandoffResult(success=False, error=error_msg)

        except httpx.TimeoutException:
            logger.warning("handoff_webhook.timeout", event_type=event_type)
            return HandoffResult(success=False, error="Webhook request timed out")
        except Exception as e:
            logger.error("handoff_webhook.error", event_type=event_type, error=str(e))
            return HandoffResult(success=False, error=str(e))

    def _sign(self, timestamp: str, body: str) -> str:
        """Generate HMAC-SHA256 signature for webhook verification."""
        message = f"{timestamp}.{body}"
        return hmac.new(
            self.webhook_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
