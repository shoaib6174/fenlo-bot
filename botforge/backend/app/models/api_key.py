"""API Key model for programmatic access (S86)"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import TIMESTAMP, Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base


class APIKey(Base):
    """API key for workspace programmatic access"""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    prefix = Column(String(20), nullable=False)  # e.g. "bf_live_abc1"
    scopes = Column(JSONB, nullable=False, default=lambda: ["read", "chat"])  # read, chat, admin
    rate_limit = Column(Integer, nullable=False, default=100)  # requests per minute
    is_revoked = Column(Boolean, nullable=False, default=False)
    last_used_at = Column(TIMESTAMP(timezone=True), nullable=True)
    request_count = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    revoked_at = Column(TIMESTAMP(timezone=True), nullable=True)
