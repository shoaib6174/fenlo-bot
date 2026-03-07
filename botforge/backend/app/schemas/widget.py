"""Widget chat schemas for anonymous SSE endpoint (S75)."""

from uuid import UUID

from pydantic import BaseModel, Field


class WidgetChatRequest(BaseModel):
    """Request body for anonymous widget chat via SSE."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="User message (max 500 chars for anonymous users)",
    )
    conversation_id: UUID | None = Field(
        None,
        description="Conversation ID for multi-turn (None for first message)",
    )
