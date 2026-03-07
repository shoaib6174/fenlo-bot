"""WeeklyInsight model — stores AI-generated weekly analytics summaries."""

import uuid

from sqlalchemy import Column, Date, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models.base import Base


class WeeklyInsight(Base):
    """AI-generated weekly analytics insight for a workspace."""

    __tablename__ = "weekly_insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    period = Column(String(60), nullable=False)  # "Week of Feb 10-16, 2026"
    summary = Column(Text, nullable=False)
    metrics = Column(JSONB, nullable=False, default=dict)
    recommendations = Column(JSONB, nullable=False, default=list)  # list[str]
    status = Column(
        String(20), nullable=False, default="completed"
    )  # generating, completed, failed
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_weekly_insights_workspace_week", "workspace_id", "week_start", unique=True),
    )
