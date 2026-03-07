"""Purge operation saga state machine — tracks GDPR purge progress for crash recovery."""

import uuid

from sqlalchemy import Column, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models.base import Base

# Valid purge phases (ordered lifecycle)
PURGE_PHASES = [
    "initiated",
    "health_check",
    "external_delete",
    "db_delete",
    "complete",
    "failed",
    "rolled_back",
]


class PurgeOperation(Base):
    """Tracks purge operation lifecycle for crash recovery and audit."""

    __tablename__ = "purge_operations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id"),
        nullable=False,
    )
    requester_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    phase = Column(String(20), nullable=False, default="initiated")
    details = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    started_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "idx_purge_operations_incomplete",
            "phase",
            postgresql_where=text("phase NOT IN ('complete', 'failed', 'rolled_back')"),
        ),
    )
