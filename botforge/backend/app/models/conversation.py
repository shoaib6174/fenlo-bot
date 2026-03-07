"""Conversation and message models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base


class Conversation(Base):
    """Conversation with a user across any channel"""

    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('web', 'whatsapp', 'telegram', 'voice', 'widget')",
            name="ck_conversation_channel",
        ),
        CheckConstraint(
            "status IN ('active', 'escalated', 'closed')", name="ck_conversation_status"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel = Column(String(20), nullable=False, default="web")  # web, whatsapp, telegram, voice
    external_id = Column(String(255))  # Channel-specific ID (e.g., WhatsApp phone number)
    contact_name = Column(String(255))
    contact_info = Column(JSONB)  # ContactInfo schema: {phone, email, name, source}
    title = Column(String(255))  # Auto-generated from first user message (first 60 chars)
    status = Column(String(20), nullable=False, default="active")  # active, escalated, closed
    metadata_ = Column("metadata", JSONB)  # Channel-specific metadata
    lead_score = Column(Integer, default=0)
    started_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    ended_at = Column(TIMESTAMP(timezone=True))


# Create index after table definition
Index(
    "idx_conversations_workspace",
    Conversation.workspace_id,
    Conversation.started_at.desc(),
)


class Message(Base):
    """Message in a conversation - partitioned by month"""

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="ck_message_role"),
        CheckConstraint(
            "sentiment IS NULL OR sentiment IN ('positive', 'neutral', 'negative')",
            name="ck_message_sentiment",
        ),
        CheckConstraint(
            "feedback IS NULL OR feedback IN ('positive', 'negative')", name="ck_message_feedback"
        ),
        {"postgresql_partition_by": "RANGE (created_at)"},
    )

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(10), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    citations = Column(JSONB)  # [{doc_name, page_number, chunk_text, relevance_score}]
    tokens_used = Column(Integer)
    latency_ms = Column(Integer)
    sentiment = Column(String(20))  # positive, neutral, negative
    quality_score = Column(Float)
    intent = Column(String(30))  # FAQ, booking, sales, support, escalation
    feedback = Column(String(10))  # positive, negative, null
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        primary_key=True,
    )


# Create composite index after table definition for efficient message listing
Index(
    "idx_messages_conversation_time",
    Message.conversation_id,
    Message.created_at.desc(),
)

# Note: Partitions will be created in the migration file
# Example:
# CREATE TABLE messages_2026_02 PARTITION OF messages
#     FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
