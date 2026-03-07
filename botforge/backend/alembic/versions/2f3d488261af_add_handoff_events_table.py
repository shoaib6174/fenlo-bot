"""add handoff_events table

Revision ID: 2f3d488261af
Revises: a3f7b2d18e40
Create Date: 2026-02-15 17:23:14.293899

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2f3d488261af'  # pragma: allowlist secret
down_revision: Union[str, Sequence[str], None] = 'a3f7b2d18e40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('handoff_events',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('conversation_id', sa.UUID(), nullable=False),
    sa.Column('workspace_id', sa.UUID(), nullable=False),
    sa.Column('event_type', sa.String(length=30), nullable=False),
    sa.Column('actor', sa.String(length=255), nullable=True),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.CheckConstraint("event_type IN ('escalated', 'message_forwarded', 'agent_replied', 'resolved', 'auto_resolved')", name='ck_handoff_event_type'),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_handoff_events_conversation', 'handoff_events', ['conversation_id', sa.literal_column('created_at DESC')], unique=False)
    op.create_index(op.f('ix_handoff_events_conversation_id'), 'handoff_events', ['conversation_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_handoff_events_conversation_id'), table_name='handoff_events')
    op.drop_index('idx_handoff_events_conversation', table_name='handoff_events')
    op.drop_table('handoff_events')
