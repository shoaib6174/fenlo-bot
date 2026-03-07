"""Handoff event model for tracking human handoff lifecycle"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base


class HandoffEvent(Base):
    """Audit trail for human handoff lifecycle events"""

    __tablename__ = "handoff_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('escalated', 'message_forwarded', 'agent_replied', "
            "'resolved', 'auto_resolved')",
            name="ck_handoff_event_type",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type = Column(String(30), nullable=False)
    actor = Column(String(255))  # agent name/email or "system" for auto-resolve
    payload = Column(JSONB)  # event-specific data (reason, message excerpt, etc.)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


Index(
    "idx_handoff_events_conversation",
    HandoffEvent.conversation_id,
    HandoffEvent.created_at.desc(),
)
