"""
Handoff Guard Step — short-circuits the pipeline for escalated conversations.

When a conversation is in 'escalated' status, this step:
1. Forwards the user's message to the external system
2. Stores the message in DB
3. Sets should_halt = True to skip the rest of the pipeline
"""

from datetime import UTC, datetime
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.engine import MessageContext
from app.models.conversation import Conversation, Message

logger = structlog.get_logger(__name__)


class HandoffGuardStep:
    """
    First step in pipeline. Checks if conversation is escalated.

    If escalated: forwards message to external system, persists it, halts pipeline.
    If not escalated: passes through unchanged.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, context: MessageContext) -> MessageContext:
        if not context.conversation_id:
            return context

        # Check conversation status
        result = await self.db.execute(
            select(Conversation.status, Conversation.workspace_id).where(
                Conversation.id == context.conversation_id
            )
        )
        row = result.first()

        if not row or row.status != "escalated":
            return context

        # Conversation is escalated — forward message and halt
        logger.info(
            "handoff_guard.escalated_conversation",
            conversation_id=str(context.conversation_id),
        )

        # Persist user message
        msg = Message(
            id=uuid4(),
            conversation_id=context.conversation_id,
            role="user",
            content=context.message,
            created_at=datetime.now(UTC),
        )
        self.db.add(msg)
        await self.db.commit()

        # Forward to external system (fire-and-forget, don't block)
        try:
            from app.services.handoff_service import HandoffService

            service = HandoffService()
            await service.forward_message(
                conversation_id=context.conversation_id,
                workspace_id=context.workspace_id,
                message=context.message,
                sender_name=None,
                session=self.db,
            )
        except Exception as e:
            logger.warning(
                "handoff_guard.forward_failed",
                conversation_id=str(context.conversation_id),
                error=str(e),
            )

        # Set response and halt
        context.response = (
            "Your message has been forwarded to our support team. They'll respond shortly."
        )
        context.should_halt = True
        context.halt_reason = "conversation_escalated"

        return context
