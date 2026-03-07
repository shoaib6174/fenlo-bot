"""Voice call and escalation models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base


class CallLog(Base):
    """Voice call log"""

    __tablename__ = "call_logs"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('inbound', 'outbound', 'web')", name="ck_call_log_direction"
        ),
        CheckConstraint(
            "sentiment IS NULL OR sentiment IN ('positive', 'neutral', 'negative')",
            name="ck_call_log_sentiment",
        ),
        CheckConstraint(
            "status IN ('initiated', 'ringing', 'connected', 'ended', "
            "'failed', 'canceled', 'no_answer')",
            name="ck_call_log_status",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vapi_call_id = Column(String(255), unique=True, index=True)
    status = Column(String(20), nullable=False, default="initiated")
    direction = Column(String(10), nullable=False)  # inbound, outbound, web
    phone_from = Column(String(20), nullable=True, default="")
    phone_to = Column(String(20), nullable=True, default="")
    duration_sec = Column(Integer)
    recording_url = Column(Text)
    transcript = Column(Text)
    summary = Column(Text)
    sentiment = Column(String(20))  # positive, neutral, negative
    actions_taken = Column(JSONB)  # [{action_type, timestamp, details}]
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class EscalationRule(Base):
    """Escalation rule for conversation routing"""

    __tablename__ = "escalation_rules"
    __table_args__ = (
        CheckConstraint(
            "rule_type IN ('sentiment', 'keyword', 'confidence', 'intent', 'business_hours')",
            name="ck_escalation_rule_type",
        ),
        CheckConstraint(
            "action IN ('escalate', 'notify', 'log')", name="ck_escalation_rule_action"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_type = Column(String(30), nullable=False)  # sentiment, keyword, confidence, intent
    condition = Column(
        JSONB, nullable=False
    )  # {"threshold": -0.5, "consecutive": 3} or {"keywords": ["speak to human"]}
    action = Column(String(20), nullable=False, default="escalate")  # escalate, notify, log
    is_active = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=0)  # Higher priority wins on conflict
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
