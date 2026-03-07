"""add weekly_insights table

Revision ID: d4b2e6f91a30
Revises: c9a1d5e83f20
Create Date: 2026-02-15 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "d4b2e6f91a30"  # pragma: allowlist secret
down_revision: Union[str, None] = "c9a1d5e83f20"  # pragma: allowlist secret
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "weekly_insights",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("week_start", sa.Date, nullable=False),
        sa.Column("week_end", sa.Date, nullable=False),
        sa.Column("period", sa.String(60), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("metrics", JSONB, nullable=False, server_default="{}"),
        sa.Column("recommendations", JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(20), nullable=False, server_default="completed"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "idx_weekly_insights_workspace_week",
        "weekly_insights",
        ["workspace_id", "week_start"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_weekly_insights_workspace_week")
    op.drop_table("weekly_insights")
