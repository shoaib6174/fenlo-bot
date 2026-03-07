"""add analytics indexes

Revision ID: c9a1d5e83f20
Revises: b702faf362c8
Create Date: 2026-02-14 18:30:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9a1d5e83f20"  # pragma: allowlist secret
down_revision: Union[str, None] = "b702faf362c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Conversations analytics index — covers workspace-scoped date range,
    # channel breakdown, status filtering, and lead score distribution queries.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_conversations_analytics
        ON conversations(workspace_id, started_at, channel, status, lead_score)
        """
    )

    # Messages analytics index — covers sentiment/quality/intent aggregation
    # after joining through conversations. The messages table is partitioned
    # by created_at, so this index is created on each partition automatically.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_messages_analytics
        ON messages(conversation_id, created_at, sentiment, quality_score)
        INCLUDE (latency_ms, intent)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_messages_analytics")
    op.execute("DROP INDEX IF EXISTS idx_conversations_analytics")
