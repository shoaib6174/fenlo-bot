"""add api_keys table

Revision ID: d34ee49d0027
Revises: f4a0138fa8d7
Create Date: 2026-02-16 16:34:52.793033

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd34ee49d0027'
down_revision: Union[str, Sequence[str], None] = 'f4a0138fa8d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add api_keys table for programmatic API access (S86)."""
    op.create_table('api_keys',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('key_hash', sa.String(length=255), nullable=False),
    sa.Column('prefix', sa.String(length=20), nullable=False),
    sa.Column('scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('rate_limit', sa.Integer(), nullable=False),
    sa.Column('is_revoked', sa.Boolean(), nullable=False),
    sa.Column('last_used_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('request_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=True)
    op.create_index(op.f('ix_api_keys_workspace_id'), 'api_keys', ['workspace_id'], unique=False)


def downgrade() -> None:
    """Remove api_keys table."""
    op.drop_index(op.f('ix_api_keys_workspace_id'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_table('api_keys')
