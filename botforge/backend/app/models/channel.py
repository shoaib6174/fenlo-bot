"""Channel configuration and webhook models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base


class ChannelConfig(Base):
    """Channel configuration (WhatsApp, Telegram, etc.)"""

    __tablename__ = "channel_configs"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('whatsapp', 'telegram', 'voice', 'widget')",
            name="ck_channel_config_channel",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel = Column(String(20), nullable=False)  # whatsapp, telegram, voice, widget
    provider = Column(
        String(20), nullable=True
    )  # twilio, meta (for whatsapp); NULL defaults to twilio
    config = Column(
        JSONB, nullable=False
    )  # ChannelConfigWhatsApp schema or other channel-specific config
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class WebhookAction(Base):
    """Webhook action configuration"""

    __tablename__ = "webhook_actions"
    __table_args__ = (
        CheckConstraint(
            "action_type IN ('webhook', 'email', 'slack')", name="ck_webhook_action_type"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trigger_event = Column(
        String(50), nullable=False
    )  # message.created, conversation.escalated, lead.qualified
    action_type = Column(String(30), nullable=False)  # webhook, email, slack
    config = Column(JSONB, nullable=False)  # {url, headers, payload_template}
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class WebhookOutbox(Base):
    """Webhook outbox for reliable delivery with retry logic"""

    __tablename__ = "webhook_outbox"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'dead')", name="ck_webhook_outbox_status"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    event_type = Column(String(50), nullable=False)
    payload = Column(JSONB, nullable=False)
    target_url = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending, sent, failed, dead
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    next_retry_at = Column(TIMESTAMP(timezone=True))
    error_message = Column(Text)
    sequence = Column(BigInteger, autoincrement=True, nullable=False)  # For ordering guarantee
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    sent_at = Column(TIMESTAMP(timezone=True))


class MessageDeliveryLog(Base):
    """Delivery status updates from channel providers (e.g. Twilio WhatsApp status callbacks)."""

    __tablename__ = "message_delivery_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_message_id = Column(String(64), nullable=False)  # Twilio MessageSid
    channel = Column(String(20), nullable=False)  # whatsapp, telegram, etc.
    status = Column(String(20), nullable=False)  # queued/sent/delivered/failed/undelivered/read
    error_code = Column(String(20), nullable=True)  # Provider error code on failure
    error_message = Column(Text, nullable=True)
    raw_payload = Column(JSONB, nullable=False, default=dict)  # Full webhook payload
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


# Index for looking up delivery status by provider message ID
Index(
    "idx_delivery_log_provider_msg",
    MessageDeliveryLog.provider_message_id,
    MessageDeliveryLog.status,
)


# Create indexes after table definition
# Partial index for pending/failed webhooks
Index(
    "idx_webhook_outbox_pending",
    WebhookOutbox.status,
    WebhookOutbox.next_retry_at,
    postgresql_where=(WebhookOutbox.status.in_(["pending", "failed"])),
)

# Sequence index for ordered processing per workspace
Index(
    "idx_webhook_outbox_sequence",
    WebhookOutbox.workspace_id,
    WebhookOutbox.sequence,
    postgresql_where=(WebhookOutbox.status.in_(["pending", "failed"])),
)
