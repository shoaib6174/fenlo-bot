"""add title to conversations

Revision ID: f4a0138fa8d7
Revises: 2f3d488261af
Create Date: 2026-02-16 12:23:15.399773

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a0138fa8d7'  # pragma: allowlist secret
down_revision: Union[str, Sequence[str], None] = '2f3d488261af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add title column to conversations table."""
    op.add_column('conversations', sa.Column('title', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Remove title column from conversations table."""
    op.drop_column('conversations', 'title')
