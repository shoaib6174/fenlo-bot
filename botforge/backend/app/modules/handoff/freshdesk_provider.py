"""
Freshdesk handoff provider — creates/updates support tickets via Freshdesk API v2.

Config (from workspace.settings.handoff):
    freshdesk_domain: e.g. "mycompany" → https://mycompany.freshdesk.com
    freshdesk_api_key: API key (used as basic auth username with "X" password)
    freshdesk_default_group_id: Optional default agent group for ticket assignment
"""

import json

import httpx
import structlog

from app.modules.handoff.provider import EscalationPayload, HandoffResult

logger = structlog.get_logger(__name__)

FRESHDESK_TIMEOUT = 15.0


class FreshdeskProvider:
    """
    Freshdesk integration for human handoff.

    API docs: https://developers.freshdesk.com/api/
    Auth: Basic auth with API key as username, "X" as password.
    """

    def __init__(self, domain: str, api_key: str, default_group_id: int | None = None):
        self.base_url = f"https://{domain}.freshdesk.com/api/v2"
        self.api_key = api_key
        self.default_group_id = default_group_id

    def _auth(self) -> tuple[str, str]:
        return (self.api_key, "X")

    async def escalate(self, payload: EscalationPayload) -> HandoffResult:
        """Create a Freshdesk ticket with conversation summary."""
        contact_info = payload.contact_info or {}
        email = contact_info.get("email", f"bot-{payload.conversation_id}@botforge.local")

        description_parts = [
            f"<h3>Escalation Summary</h3><p>{payload.summary}</p>",
            f"<h3>Channel</h3><p>{payload.channel}</p>",
            f"<h3>Escalation Reason</h3><p>{json.dumps(payload.escalation_reason)}</p>",
        ]
        if payload.last_messages:
            msg_lines = "<br>".join(
                f"<b>{m.get('role', 'unknown')}:</b> {m.get('content', '')}"
                for m in payload.last_messages
            )
            description_parts.append(f"<h3>Recent Messages</h3><p>{msg_lines}</p>")

        description_parts.append(
            f"<hr><p><b>Conversation ID:</b> {payload.conversation_id}<br>"
            f"<b>Workspace ID:</b> {payload.workspace_id}<br>"
            f"<b>Reply URL:</b> {payload.reply_url}<br>"
            f"<b>Resolve URL:</b> {payload.resolve_url}</p>"
        )

        ticket_data: dict = {
            "subject": f"[BotForge] Escalation: {payload.contact_name or 'Customer'}",
            "description": "\n".join(description_parts),
            "email": email,
            "priority": 2,  # Medium
            "status": 2,  # Open
            "source": 7,  # Chat
            "tags": ["botforge", "escalation"],
        }

        if self.default_group_id:
            ticket_data["group_id"] = self.default_group_id

        try:
            async with httpx.AsyncClient(timeout=FRESHDESK_TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/tickets",
                    json=ticket_data,
                    auth=self._auth(),
                )

            if response.status_code in (200, 201):
                resp_data = response.json()
                ticket_id = str(resp_data.get("id", ""))
                logger.info(
                    "freshdesk.ticket_created",
                    ticket_id=ticket_id,
                    conversation_id=str(payload.conversation_id),
                )
                return HandoffResult(success=True, external_ticket_id=ticket_id)
            elif response.status_code == 429:
                logger.warning("freshdesk.rate_limited", action="escalate")
                return HandoffResult(
                    success=False,
                    error="Freshdesk rate limit exceeded — please try again in a few minutes",
                )
            else:
                error = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning("freshdesk.create_failed", error=error)
                return HandoffResult(success=False, error=error)

        except httpx.TimeoutException:
            logger.warning("freshdesk.timeout", action="escalate")
            return HandoffResult(success=False, error="Freshdesk request timed out")
        except Exception as e:
            logger.error("freshdesk.error", action="escalate", error=str(e))
            return HandoffResult(success=False, error=str(e))

    async def forward_message(
        self, external_ticket_id: str, message: str, sender_name: str | None = None
    ) -> HandoffResult:
        """Add a private note to an existing Freshdesk ticket."""
        note_body = f"<b>{sender_name or 'Customer'}:</b> {message}"

        try:
            async with httpx.AsyncClient(timeout=FRESHDESK_TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/tickets/{external_ticket_id}/notes",
                    json={"body": note_body, "private": True},
                    auth=self._auth(),
                )

            if response.status_code in (200, 201):
                logger.info(
                    "freshdesk.note_added",
                    ticket_id=external_ticket_id,
                )
                return HandoffResult(success=True, external_ticket_id=external_ticket_id)
            else:
                error = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning("freshdesk.note_failed", error=error)
                return HandoffResult(success=False, error=error)

        except httpx.TimeoutException:
            logger.warning("freshdesk.timeout", action="forward_message")
            return HandoffResult(success=False, error="Freshdesk request timed out")
        except Exception as e:
            logger.error("freshdesk.error", action="forward_message", error=str(e))
            return HandoffResult(success=False, error=str(e))

    async def resolve(
        self, external_ticket_id: str, resolution_note: str | None = None
    ) -> HandoffResult:
        """Close a Freshdesk ticket (set status to Resolved)."""
        update_data: dict = {"status": 4}  # 4 = Resolved in Freshdesk

        try:
            async with httpx.AsyncClient(timeout=FRESHDESK_TIMEOUT) as client:
                # Add resolution note if provided
                if resolution_note:
                    await client.post(
                        f"{self.base_url}/tickets/{external_ticket_id}/notes",
                        json={"body": f"<b>Resolution:</b> {resolution_note}", "private": True},
                        auth=self._auth(),
                    )

                response = await client.put(
                    f"{self.base_url}/tickets/{external_ticket_id}",
                    json=update_data,
                    auth=self._auth(),
                )

            if response.status_code == 200:
                logger.info(
                    "freshdesk.ticket_resolved",
                    ticket_id=external_ticket_id,
                )
                return HandoffResult(success=True, external_ticket_id=external_ticket_id)
            else:
                error = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning("freshdesk.resolve_failed", error=error)
                return HandoffResult(success=False, error=error)

        except httpx.TimeoutException:
            logger.warning("freshdesk.timeout", action="resolve")
            return HandoffResult(success=False, error="Freshdesk request timed out")
        except Exception as e:
            logger.error("freshdesk.error", action="resolve", error=str(e))
            return HandoffResult(success=False, error=str(e))
