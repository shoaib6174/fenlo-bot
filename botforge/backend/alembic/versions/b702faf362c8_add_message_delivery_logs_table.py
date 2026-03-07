"""add message_delivery_logs table

Revision ID: b702faf362c8
Revises: 722f152019d8
Create Date: 2026-02-14 15:19:32.016775

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b702faf362c8'  # pragma: allowlist secret
down_revision: Union[str, Sequence[str], None] = '722f152019d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('message_delivery_logs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.Column('provider_message_id', sa.String(length=64), nullable=False),
    sa.Column('channel', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('error_code', sa.String(length=20), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('raw_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_delivery_log_provider_msg', 'message_delivery_logs', ['provider_message_id', 'status'], unique=False)
    op.create_index(op.f('ix_message_delivery_logs_workspace_id'), 'message_delivery_logs', ['workspace_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_message_delivery_logs_workspace_id'), table_name='message_delivery_logs')
    op.drop_index('idx_delivery_log_provider_msg', table_name='message_delivery_logs')
    op.drop_table('message_delivery_logs')
