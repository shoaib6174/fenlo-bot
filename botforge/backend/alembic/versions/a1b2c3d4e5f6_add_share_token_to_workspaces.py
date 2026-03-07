"""add share_token to workspaces

Revision ID: a1b2c3d4e5f6
Revises: d34ee49d0027
Create Date: 2026-03-02 12:00:00.000000

"""
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"  # pragma: allowlist secret
down_revision: str = "d34ee49d0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add share_token column (nullable first for existing rows)
    op.add_column(
        "workspaces",
        sa.Column("share_token", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column("share_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )

    # Backfill existing rows with unique UUIDs
    conn = op.get_bind()
    workspaces = conn.execute(sa.text("SELECT id FROM workspaces WHERE share_token IS NULL"))
    for row in workspaces:
        conn.execute(
            sa.text("UPDATE workspaces SET share_token = :token WHERE id = :id"),
            {"token": str(uuid4()), "id": row[0]},
        )

    # Now make it non-nullable and add unique constraint
    op.alter_column("workspaces", "share_token", nullable=False)
    op.create_unique_constraint("uq_workspaces_share_token", "workspaces", ["share_token"])


def downgrade() -> None:
    op.drop_constraint("uq_workspaces_share_token", "workspaces", type_="unique")
    op.drop_column("workspaces", "share_enabled")
    op.drop_column("workspaces", "share_token")
