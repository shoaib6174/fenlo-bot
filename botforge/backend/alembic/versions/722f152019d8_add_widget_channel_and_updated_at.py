"""add_widget_channel_and_updated_at

Revision ID: 722f152019d8
Revises: a3b9e7f12d45
Create Date: 2026-02-14 05:35:38.686851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '722f152019d8'  # pragma: allowlist secret
down_revision: Union[str, Sequence[str], None] = 'a3b9e7f12d45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add 'widget' to Conversation.channel constraint and add updated_at to ChannelConfig.

    Phase 4 S50: Widget backend support.
    """
    # Drop existing check constraint on conversations.channel (if exists)
    # Use raw SQL because Alembic doesn't support IF EXISTS for drop_constraint
    op.execute('ALTER TABLE conversations DROP CONSTRAINT IF EXISTS ck_conversation_channel')

    # Create new check constraint that includes 'widget'
    op.create_check_constraint(
        'ck_conversation_channel',
        'conversations',
        "channel IN ('web', 'whatsapp', 'telegram', 'voice', 'widget')"
    )

    # Add updated_at column to channel_configs
    op.add_column(
        'channel_configs',
        sa.Column(
            'updated_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,  # Nullable because existing rows won't have this
            server_default=sa.text('CURRENT_TIMESTAMP')
        )
    )

    # Backfill updated_at with created_at for existing rows
    op.execute("UPDATE channel_configs SET updated_at = created_at WHERE updated_at IS NULL")


def downgrade() -> None:
    """
    Remove 'widget' from Conversation.channel constraint and remove updated_at from ChannelConfig.
    """
    # Drop updated_at column from channel_configs
    op.drop_column('channel_configs', 'updated_at')

    # Drop current check constraint (if exists)
    op.execute('ALTER TABLE conversations DROP CONSTRAINT IF EXISTS ck_conversation_channel')

    # Restore original check constraint without 'widget'
    op.create_check_constraint(
        'ck_conversation_channel',
        'conversations',
        "channel IN ('web', 'whatsapp', 'telegram', 'voice')"
    )
