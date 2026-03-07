"""
Context Manager - Loads conversation history and manages system prompts.

Handles:
- Loading last 20 messages from a conversation
- Auto-creating conversations on first message
- System prompt injection
- Message pair persistence
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.engine import MessageContext, PipelineStep
from app.models.conversation import Conversation, Message


class ContextManager:
    """
    Manages conversation context and history.

    Features:
    - Load last 20 messages for context window
    - Auto-create conversation on first message
    - System prompt injection from workspace settings
    - Message pair persistence to database
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize context manager with database session.

        Args:
            db: SQLAlchemy async session
        """
        self.db = db

    async def load_context(
        self,
        workspace_id: UUID,
        conversation_id: UUID | None,
        channel: str = "web",
    ) -> tuple[UUID, list[dict[str, Any]], str, int]:
        """
        Load conversation history and system prompt.

        If conversation_id is None, creates a new conversation.
        Otherwise, loads the last 20 messages from the conversation.

        Args:
            workspace_id: Workspace identifier
            conversation_id: Optional conversation ID (None creates new)

        Returns:
            Tuple of (conversation_id, history, system_prompt, existing_lead_score)
            - conversation_id: The conversation UUID (newly created or existing)
            - history: List of message dicts with 'role' and 'content'
            - system_prompt: Default system prompt for the workspace
            - existing_lead_score: Current lead score for the conversation
        """
        # Auto-create conversation if this is the first message
        existing_lead_score = 0
        if conversation_id is None:
            conversation_id = await self._create_conversation(workspace_id, channel)
            history = []
        else:
            # Load last 20 messages for context
            history = await self._load_history(conversation_id)
            # Load existing lead score for cumulative scoring
            score_result = await self.db.execute(
                select(Conversation.lead_score).where(Conversation.id == conversation_id)
            )
            existing_lead_score = score_result.scalar_one_or_none() or 0

        # Load system prompt from workspace settings (falls back to default)
        system_prompt = await self._load_system_prompt(workspace_id)

        return conversation_id, history, system_prompt, existing_lead_score

    async def save_message_pair(
        self,
        conversation_id: UUID,
        user_message: str,
        assistant_message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Save user-assistant message pair to database.

        Args:
            conversation_id: Conversation identifier
            user_message: User's message content
            assistant_message: Assistant's response content
            metadata: Optional metadata (sentiment, quality_score, tokens_used, etc.)

        Raises:
            ValueError: If conversation_id does not exist in the database
        """
        # App-layer FK validation (Message table is partitioned, so DB-level FK not possible)
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} does not exist")

        metadata = metadata or {}
        now = datetime.now(UTC)

        # Generate title from first user message (first 60 chars)
        if conversation.title is None:
            conversation.title = user_message[:60] + ("..." if len(user_message) > 60 else "")

        # Save user message
        user_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role="user",
            content=user_message,
            created_at=now,
        )
        self.db.add(user_msg)

        # Save assistant message with metadata (offset by 1ms to ensure deterministic ordering)
        assistant_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_message,
            created_at=now + timedelta(milliseconds=1),
            sentiment=metadata.get("sentiment"),
            quality_score=metadata.get("quality_score"),
            intent=metadata.get("intent"),
            tokens_used=metadata.get("tokens_used"),
            latency_ms=metadata.get("latency_ms"),
            citations=metadata.get("citations"),
        )
        self.db.add(assistant_msg)

        await self.db.flush()

    async def _create_conversation(self, workspace_id: UUID, channel: str = "web") -> UUID:
        """
        Create a new conversation.

        Args:
            workspace_id: Workspace identifier

        Returns:
            New conversation UUID
        """
        conversation = Conversation(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            channel=channel,
            status="active",
            started_at=datetime.now(UTC),
        )
        self.db.add(conversation)
        await self.db.flush()
        return conversation.id

    async def _load_history(self, conversation_id: UUID) -> list[dict[str, Any]]:
        """
        Load last 20 messages from conversation.

        Args:
            conversation_id: Conversation identifier

        Returns:
            List of message dicts with 'role' and 'content'
        """
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(20)
        )
        result = await self.db.execute(query)
        messages = result.scalars().all()

        # Reverse to get chronological order (oldest first)
        history = [{"role": msg.role, "content": msg.content} for msg in reversed(messages)]
        return history

    _DEFAULT_PROMPT = (
        "You are a helpful AI assistant. Answer questions clearly and concisely. "
        "If you don't know something, say so honestly. Be professional and friendly."
    )

    async def _load_system_prompt(self, workspace_id: UUID) -> str:
        """Load system_prompt from workspace settings, falling back to default."""
        from app.models.workspace import Workspace

        result = await self.db.execute(
            select(Workspace.settings).where(Workspace.id == workspace_id)
        )
        settings = result.scalar_one_or_none()
        if settings and isinstance(settings, dict):
            prompt = settings.get("system_prompt", "").strip()
            if prompt:
                return prompt
        return self._DEFAULT_PROMPT

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt (kept for backward compatibility)."""
        return self._DEFAULT_PROMPT


class LoadContextStep(PipelineStep):
    """
    Pipeline step that loads conversation context.

    This is typically the first step in the pipeline.
    It loads conversation history and system prompt,
    and auto-creates conversations for new chats.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize step with database session.

        Args:
            db: SQLAlchemy async session
        """
        self.context_manager = ContextManager(db)

    async def execute(self, context: MessageContext) -> MessageContext:
        """
        Load conversation context and history.

        Args:
            context: Current message context

        Returns:
            Updated context with conversation_id, history, and system_prompt
        """
        (
            conversation_id,
            history,
            system_prompt,
            existing_lead_score,
        ) = await self.context_manager.load_context(
            workspace_id=context.workspace_id,
            conversation_id=context.conversation_id,
            channel=context.metadata.get("channel", "web"),
        )

        # Update context
        context.conversation_id = conversation_id
        context.conversation_history = history
        context.system_prompt = system_prompt
        context.metadata["existing_lead_score"] = existing_lead_score

        return context


class PersistenceStep(PipelineStep):
    """
    Pipeline step that persists message pairs to database.

    This should run after the response has been generated.
    It saves both the user message and assistant response.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize step with database session.

        Args:
            db: SQLAlchemy async session
        """
        self.context_manager = ContextManager(db)

    async def execute(self, context: MessageContext) -> MessageContext:
        """
        Save message pair to database.

        Args:
            context: Current message context with response

        Returns:
            Unchanged context (persistence is side-effect)
        """
        if context.response and context.conversation_id:
            metadata = {
                "sentiment": context.sentiment,
                "quality_score": context.quality_score,
                "intent": context.intent,
                "tokens_used": context.tokens_used,
                "citations": context.citations,
            }

            # Use original message (before PromptGuard sandwiching) for persistence
            user_message = context.metadata.get("original_message", context.message)

            await self.context_manager.save_message_pair(
                conversation_id=context.conversation_id,
                user_message=user_message,
                assistant_message=context.response,
                metadata=metadata,
            )

            # Update conversation-level lead score if calculated
            if context.lead_score is not None:
                await self.context_manager.db.execute(
                    update(Conversation)
                    .where(Conversation.id == context.conversation_id)
                    .values(lead_score=context.lead_score)
                )
                await self.context_manager.db.flush()

        return context
