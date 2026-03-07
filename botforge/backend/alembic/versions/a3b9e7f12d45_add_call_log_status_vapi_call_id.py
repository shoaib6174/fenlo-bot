"""add call_log status, vapi_call_id, make phone fields nullable

Revision ID: a3b9e7f12d45
Revises: 1f7c10bee771
Create Date: 2026-02-13 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b9e7f12d45'  # pragma: allowlist secret
down_revision: Union[str, Sequence[str], None] = '1f7c10bee771'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add status, vapi_call_id to call_logs; make phone fields nullable."""
    # Add status column with default
    op.add_column(
        'call_logs',
        sa.Column('status', sa.String(20), nullable=False, server_default='initiated'),
    )
    # Add vapi_call_id column (unique, indexed)
    op.add_column(
        'call_logs',
        sa.Column('vapi_call_id', sa.String(255), nullable=True),
    )
    op.create_index('ix_call_logs_vapi_call_id', 'call_logs', ['vapi_call_id'], unique=True)

    # Make phone_from and phone_to nullable (web calls have no phone numbers)
    op.alter_column('call_logs', 'phone_from', existing_type=sa.String(20), nullable=True)
    op.alter_column('call_logs', 'phone_to', existing_type=sa.String(20), nullable=True)

    # Add status CHECK constraint
    op.create_check_constraint(
        'ck_call_log_status',
        'call_logs',
        "status IN ('initiated', 'ringing', 'connected', 'ended', "
        "'failed', 'canceled', 'no_answer')",
    )


def downgrade() -> None:
    """Remove status, vapi_call_id; restore phone field NOT NULL."""
    op.drop_constraint('ck_call_log_status', 'call_logs', type_='check')
    op.drop_index('ix_call_logs_vapi_call_id', table_name='call_logs')
    op.drop_column('call_logs', 'vapi_call_id')
    op.drop_column('call_logs', 'status')
    op.alter_column('call_logs', 'phone_from', existing_type=sa.String(20), nullable=False)
    op.alter_column('call_logs', 'phone_to', existing_type=sa.String(20), nullable=False)
