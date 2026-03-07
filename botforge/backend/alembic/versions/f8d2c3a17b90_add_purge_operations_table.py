"""add_purge_operations_table

Revision ID: f8d2c3a17b90
Revises: e7f3a1b24c50
Create Date: 2026-02-15 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f8d2c3a17b90"  # pragma: allowlist secret
down_revision: str = "e7f3a1b24c50"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "purge_operations",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "requester_user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("phase", sa.String(20), nullable=False, server_default="initiated"),
        sa.Column(
            "details",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "started_at",
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
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_purge_operations_incomplete",
        "purge_operations",
        ["phase"],
        postgresql_where=sa.text("phase NOT IN ('complete', 'failed', 'rolled_back')"),
    )


def downgrade() -> None:
    op.drop_index("idx_purge_operations_incomplete", table_name="purge_operations")
    op.drop_table("purge_operations")
