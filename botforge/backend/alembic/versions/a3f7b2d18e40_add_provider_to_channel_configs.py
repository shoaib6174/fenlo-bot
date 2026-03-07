"""add provider to channel_configs

Revision ID: a3f7b2d18e40
Revises: c9a1d5e83f20
Create Date: 2026-02-15 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f7b2d18e40"  # pragma: allowlist secret
down_revision: Union[str, None] = "f8d2c3a17b90"  # pragma: allowlist secret
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("channel_configs", sa.Column("provider", sa.String(20), nullable=True))
    # Backfill existing whatsapp configs with 'twilio'
    op.execute("UPDATE channel_configs SET provider = 'twilio' WHERE channel = 'whatsapp'")


def downgrade() -> None:
    op.drop_column("channel_configs", "provider")
