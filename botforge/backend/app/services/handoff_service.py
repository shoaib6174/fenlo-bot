"""
Handoff Service — orchestrates human handoff lifecycle.

Manages: escalation, message forwarding, agent reply relay, resolution.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.llm_router import LLMRouter
from app.models.conversation import Conversation, Message
from app.models.handoff import HandoffEvent
from app.modules.handoff.generic_webhook import GenericWebhookProvider
from app.modules.handoff.provider import EscalationPayload, HandoffProvider, HandoffResult

logger = structlog.get_logger(__name__)

# Default auto-resolve timeout
DEFAULT_TIMEOUT_HOURS = 24

# Max messages to include in summary context
SUMMARY_MESSAGE_LIMIT = 20

_SUMMARY_PROMPT = """Summarize this customer support conversation in 2-3 sentences.
Focus on: what the customer wants, what was attempted, and why escalation is needed.

Conversation:
{messages}

Summary:"""


def _build_provider(handoff_config: dict) -> HandoffProvider:
    """Resolve handoff provider from workspace config."""
    provider_type = handoff_config.get("provider", "generic_webhook")

    if provider_type == "freshdesk":
        from app.modules.handoff.freshdesk_provider import FreshdeskProvider

        domain = handoff_config.get("freshdesk_domain")
        api_key = handoff_config.get("freshdesk_api_key")
        if not domain or not api_key:
            raise ValueError("Freshdesk domain and API key are required")
        return FreshdeskProvider(
            domain=domain,
            api_key=api_key,
            default_group_id=handoff_config.get("freshdesk_default_group_id"),
        )

    # Default: generic webhook
    webhook_url = handoff_config.get("webhook_url")
    webhook_secret = handoff_config.get("webhook_secret", "")
    if not webhook_url:
        raise ValueError("Handoff webhook_url not configured")

    return GenericWebhookProvider(
        webhook_url=webhook_url,
        webhook_secret=webhook_secret,
    )


class HandoffService:
    """Orchestrates the human handoff lifecycle."""

    def __init__(self, llm_router: LLMRouter | None = None):
        self.llm_router = llm_router

    async def escalate(
        self,
        conversation_id: UUID,
        workspace_id: UUID,
        reason: dict,
        session: AsyncSession,
    ) -> HandoffResult:
        """
        Escalate a conversation to a human agent.

        1. Load conversation + recent messages
        2. Generate LLM summary
        3. Set conversation status to 'escalated'
        4. Send to external system via provider
        5. Log handoff event

        Args:
            conversation_id: Conversation to escalate
            workspace_id: Workspace for config lookup
            reason: Escalation reason dict (rule_type, matched, etc.)
            session: Database session

        Returns:
            HandoffResult from the provider
        """
        from app.models.workspace import Workspace

        # Load conversation
        conv = await session.get(Conversation, conversation_id)
        if not conv:
            return HandoffResult(success=False, error="Conversation not found")

        if conv.status == "escalated":
            return HandoffResult(success=False, error="Conversation already escalated")

        # Load workspace for handoff config
        workspace = await session.get(Workspace, workspace_id)
        if not workspace:
            return HandoffResult(success=False, error="Workspace not found")

        ws_settings = workspace.settings or {}
        handoff_config = ws_settings.get("handoff", {})

        provider_type = handoff_config.get("provider", "generic_webhook")
        if provider_type == "freshdesk":
            if not handoff_config.get("freshdesk_domain") or not handoff_config.get(
                "freshdesk_api_key"
            ):
                return HandoffResult(
                    success=False, error="Freshdesk domain and API key are required"
                )
        else:
            if not handoff_config.get("webhook_url"):
                return HandoffResult(
                    success=False, error="Handoff not configured for this workspace"
                )

        # Get recent messages for summary
        messages = await self._get_recent_messages(conversation_id, session)

        # Generate LLM summary
        summary = await self._generate_summary(messages)

        # Build payload
        timeout_hours = handoff_config.get("timeout_hours", DEFAULT_TIMEOUT_HOURS)
        base_url = settings.frontend_url.rstrip("/")

        payload = EscalationPayload(
            conversation_id=conversation_id,
            workspace_id=workspace_id,
            channel=conv.channel or "web",
            contact_name=conv.contact_name,
            contact_info=conv.contact_info,
            summary=summary,
            last_messages=[{"role": m.role, "content": m.content[:500]} for m in messages[-5:]],
            escalation_reason=reason,
            metadata={
                "lead_score": conv.lead_score,
            },
            reply_url=f"{base_url}/api/v1/handoff/reply",
            resolve_url=f"{base_url}/api/v1/handoff/resolve",
        )

        # Send to provider
        try:
            provider = _build_provider(handoff_config)
        except ValueError as e:
            return HandoffResult(success=False, error=str(e))

        result = await provider.escalate(payload)

        if result.success:
            # Update conversation status
            conv.status = "escalated"
            metadata = conv.metadata_ or {}
            metadata["escalated_at"] = datetime.now(UTC).isoformat()
            metadata["handoff_provider"] = handoff_config.get("provider", "generic_webhook")
            metadata["escalation_reason"] = reason
            if result.external_ticket_id:
                metadata["external_ticket_id"] = result.external_ticket_id
            metadata["auto_resolve_at"] = (
                datetime.now(UTC) + timedelta(hours=timeout_hours)
            ).isoformat()
            conv.metadata_ = metadata

            # Log event
            event = HandoffEvent(
                id=uuid4(),
                conversation_id=conversation_id,
                workspace_id=workspace_id,
                event_type="escalated",
                actor="system",
                payload={
                    "reason": reason,
                    "external_ticket_id": result.external_ticket_id,
                    "summary": summary[:500],
                },
                created_at=datetime.now(UTC),
            )
            session.add(event)
            await session.commit()

            logger.info(
                "handoff.escalated",
                conversation_id=str(conversation_id),
                external_ticket_id=result.external_ticket_id,
            )

        return result

    async def forward_message(
        self,
        conversation_id: UUID,
        workspace_id: UUID,
        message: str,
        sender_name: str | None,
        session: AsyncSession,
    ) -> HandoffResult:
        """
        Forward a user message to the external system.

        Called by HandoffGuardStep when a user sends a message
        to an escalated conversation.
        """
        conv = await session.get(Conversation, conversation_id)
        if not conv or conv.status != "escalated":
            return HandoffResult(success=False, error="Conversation not escalated")

        metadata = conv.metadata_ or {}
        external_ticket_id = metadata.get("external_ticket_id")

        from app.models.workspace import Workspace

        workspace = await session.get(Workspace, workspace_id)
        handoff_config = (workspace.settings or {}).get("handoff", {}) if workspace else {}

        try:
            provider = _build_provider(handoff_config)
        except ValueError as e:
            return HandoffResult(success=False, error=str(e))

        result = await provider.forward_message(
            external_ticket_id=external_ticket_id or str(conversation_id),
            message=message,
            sender_name=sender_name,
        )

        if result.success:
            event = HandoffEvent(
                id=uuid4(),
                conversation_id=conversation_id,
                workspace_id=workspace_id,
                event_type="message_forwarded",
                payload={"message": message[:500]},
                created_at=datetime.now(UTC),
            )
            session.add(event)
            await session.commit()

        return result

    async def handle_agent_reply(
        self,
        conversation_id: UUID,
        message: str,
        agent_name: str | None,
        session: AsyncSession,
    ) -> HandoffResult:
        """
        Relay an agent's reply to the user on the original channel.

        Called by POST /api/v1/handoff/reply.
        """
        conv = await session.get(Conversation, conversation_id)
        if not conv:
            return HandoffResult(success=False, error="Conversation not found")

        if conv.status != "escalated":
            return HandoffResult(success=False, error="Conversation not escalated")

        # Relay via the channel response router (lazy import to avoid twilio dep)
        from app.modules.channels.response_router import send_channel_response

        send_result = await send_channel_response(
            conversation_id=conversation_id,
            message=message,
            db=session,
        )

        if send_result.success:
            # Store as assistant message
            msg = Message(
                id=uuid4(),
                conversation_id=conversation_id,
                role="assistant",
                content=message,
                created_at=datetime.now(UTC),
            )
            session.add(msg)

            event = HandoffEvent(
                id=uuid4(),
                conversation_id=conversation_id,
                workspace_id=conv.workspace_id,
                event_type="agent_replied",
                actor=agent_name,
                payload={"message": message[:500]},
                created_at=datetime.now(UTC),
            )
            session.add(event)
            await session.commit()

            logger.info(
                "handoff.agent_replied",
                conversation_id=str(conversation_id),
                agent=agent_name,
            )
            return HandoffResult(success=True)

        return HandoffResult(success=False, error=send_result.error)

    async def resolve(
        self,
        conversation_id: UUID,
        session: AsyncSession,
        *,
        resolution_note: str | None = None,
        auto: bool = False,
    ) -> HandoffResult:
        """
        Resolve an escalated conversation — bot resumes.

        Args:
            conversation_id: Conversation to resolve
            session: Database session
            resolution_note: Optional note from agent
            auto: Whether this is an auto-resolve (timeout)
        """
        conv = await session.get(Conversation, conversation_id)
        if not conv:
            return HandoffResult(success=False, error="Conversation not found")

        if conv.status != "escalated":
            return HandoffResult(success=False, error="Conversation not escalated")

        # Update conversation status back to active
        conv.status = "active"
        metadata = conv.metadata_ or {}
        metadata["resolved_at"] = datetime.now(UTC).isoformat()
        metadata.pop("auto_resolve_at", None)
        conv.metadata_ = metadata

        event_type = "auto_resolved" if auto else "resolved"
        event = HandoffEvent(
            id=uuid4(),
            conversation_id=conversation_id,
            workspace_id=conv.workspace_id,
            event_type=event_type,
            actor="system" if auto else None,
            payload={"resolution_note": resolution_note} if resolution_note else None,
            created_at=datetime.now(UTC),
        )
        session.add(event)
        await session.commit()

        # Notify user (lazy import to avoid twilio dep)
        from app.modules.channels.response_router import send_channel_response

        resolve_msg = (
            "Our team will follow up with you separately. The bot is back online — feel free to ask anything!"
            if auto
            else "Your conversation has been resolved by our team. The bot is back online — feel free to ask anything!"
        )
        await send_channel_response(
            conversation_id=conversation_id,
            message=resolve_msg,
            db=session,
        )

        # Notify external system
        try:
            from app.models.workspace import Workspace

            workspace = await session.get(Workspace, conv.workspace_id)
            handoff_config = (workspace.settings or {}).get("handoff", {}) if workspace else {}
            provider = _build_provider(handoff_config)
            external_id = metadata.get("external_ticket_id", str(conversation_id))
            await provider.resolve(external_id, resolution_note)
        except Exception as e:
            logger.warning(
                "handoff.resolve_notify_failed",
                conversation_id=str(conversation_id),
                error=str(e),
            )

        logger.info(
            "handoff.resolved",
            conversation_id=str(conversation_id),
            auto=auto,
        )
        return HandoffResult(success=True)

    async def _get_recent_messages(
        self, conversation_id: UUID, session: AsyncSession
    ) -> list[Message]:
        """Fetch recent messages for summarization."""
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(SUMMARY_MESSAGE_LIMIT)
        )
        messages = list(result.scalars().all())
        messages.reverse()  # chronological order
        return messages

    async def _generate_summary(self, messages: list[Message]) -> str:
        """Generate an LLM summary of the conversation."""
        if not messages:
            return "No conversation history available."

        # Format messages for the LLM
        formatted = "\n".join(f"{m.role.capitalize()}: {m.content[:300]}" for m in messages)

        if not self.llm_router:
            # Fallback: simple truncated transcript
            return formatted[:500]

        try:
            result = await self.llm_router.complete(
                messages=[
                    {
                        "role": "user",
                        "content": _SUMMARY_PROMPT.format(messages=formatted[:2000]),
                    }
                ],
                stream=False,
                max_tokens=150,
            )
            return result.get("content", formatted[:500])
        except Exception as e:
            logger.warning("handoff.summary_failed", error=str(e))
            return formatted[:500]
