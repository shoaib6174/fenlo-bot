"""Handoff provider interface for external system integration"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID


@dataclass
class HandoffResult:
    """Result of a handoff provider operation"""

    success: bool
    external_ticket_id: str | None = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class EscalationPayload:
    """Data sent to external system when escalating a conversation"""

    conversation_id: UUID
    workspace_id: UUID
    channel: str
    contact_name: str | None
    contact_info: dict | None
    summary: str
    last_messages: list[dict]
    escalation_reason: dict
    metadata: dict  # sentiment, intent, lead_score, etc.
    reply_url: str
    resolve_url: str


class HandoffProvider(Protocol):
    """
    Abstract interface for handoff provider implementations.

    All handoff providers (GenericWebhook, Freshdesk, future Zendesk/Slack)
    implement this Protocol.
    """

    async def escalate(self, payload: EscalationPayload) -> HandoffResult:
        """
        Notify external system of a new escalation.

        Creates a ticket/alert in the external system with conversation context.

        Args:
            payload: Escalation data including summary, contact info, reason

        Returns:
            HandoffResult with external ticket ID on success
        """
        ...

    async def forward_message(
        self, external_ticket_id: str, message: str, sender_name: str | None = None
    ) -> HandoffResult:
        """
        Forward a user message to an already-escalated conversation.

        Args:
            external_ticket_id: ID of the ticket in the external system
            message: User's message content
            sender_name: Optional sender display name

        Returns:
            HandoffResult indicating delivery success
        """
        ...

    async def resolve(
        self, external_ticket_id: str, resolution_note: str | None = None
    ) -> HandoffResult:
        """
        Notify external system that a conversation has been resolved.

        Args:
            external_ticket_id: ID of the ticket in the external system
            resolution_note: Optional note about the resolution

        Returns:
            HandoffResult indicating success
        """
        ...
