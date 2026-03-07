"""add_onboarding_progress_table

Revision ID: e7f3a1b24c50
Revises: d4b2e6f91a30
Create Date: 2026-02-15 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e7f3a1b24c50"  # pragma: allowlist secret
down_revision: str = "d4b2e6f91a30"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "onboarding_progress",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "step_completed",
            postgresql.JSONB(),
            nullable=False,
            server_default='{"personality": false, "first_document": false, "test_chat": false, "deploy_channel": false, "complete": false}',
        ),
        sa.Column("current_step", sa.String(30), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("workspace_id", name="uq_onboarding_workspace"),
    )


def downgrade() -> None:
    op.drop_table("onboarding_progress")
