"""Workspace models"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    TIMESTAMP,
    BigInteger,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base


class Workspace(Base):
    """Workspace for a team or organization"""

    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    features = Column(JSONB, nullable=False, default=dict)  # {"rag": true, "voice": false}
    settings = Column(JSONB, nullable=False, default=dict)  # WorkspaceSettings schema
    token_budget_monthly = Column(Integer, nullable=False, default=1_000_000)
    share_token = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    share_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class WorkspaceMember(Base):
    """Workspace membership and roles (RBAC)"""

    __tablename__ = "workspace_members"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role = Column(String(20), nullable=False, default="viewer")  # owner, admin, agent, viewer
    invited_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class WorkspaceUsage(Base):
    """Usage metering for workspaces"""

    __tablename__ = "workspace_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    period = Column(Date, nullable=False, default=date.today)
    llm_tokens_in = Column(BigInteger, nullable=False, default=0)
    llm_tokens_out = Column(BigInteger, nullable=False, default=0)
    vector_queries = Column(Integer, nullable=False, default=0)
    documents_stored = Column(Integer, nullable=False, default=0)
    storage_bytes = Column(BigInteger, nullable=False, default=0)
    api_calls = Column(Integer, nullable=False, default=0)
    estimated_cost = Column(DECIMAL(10, 4), nullable=False, default=Decimal("0.0000"))

    __table_args__ = (UniqueConstraint("workspace_id", "period", name="uq_workspace_period"),)
