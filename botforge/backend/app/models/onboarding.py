"""Onboarding progress model — tracks wizard completion per workspace."""

import uuid

from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models.base import Base

# Ordered onboarding steps
ONBOARDING_STEPS = ["personality", "first_document", "test_chat", "deploy_channel", "complete"]


class OnboardingProgress(Base):
    """Tracks onboarding wizard progress for a workspace."""

    __tablename__ = "onboarding_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_completed = Column(
        JSONB,
        nullable=False,
        server_default='{"personality": false, "first_document": false, "test_chat": false, "deploy_channel": false, "complete": false}',
    )
    current_step = Column(String(30), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("workspace_id", name="uq_onboarding_workspace"),)
