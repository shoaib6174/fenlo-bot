"""voice constraints add business_hours and web direction

Revision ID: 1f7c10bee771
Revises: 7e455c8b2c74
Create Date: 2026-02-13 19:51:46.000330

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f7c10bee771'
down_revision: Union[str, Sequence[str], None] = '7e455c8b2c74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 'business_hours' to escalation rule_type and 'web' to call_log direction."""
    # Drop existing constraints if they exist (may not exist on fresh DB)
    op.execute(sa.text(
        "ALTER TABLE escalation_rules DROP CONSTRAINT IF EXISTS ck_escalation_rule_type"
    ))
    op.create_check_constraint(
        'ck_escalation_rule_type',
        'escalation_rules',
        "rule_type IN ('sentiment', 'keyword', 'confidence', 'intent', 'business_hours')",
    )

    op.execute(sa.text(
        "ALTER TABLE call_logs DROP CONSTRAINT IF EXISTS ck_call_log_direction"
    ))
    op.create_check_constraint(
        'ck_call_log_direction',
        'call_logs',
        "direction IN ('inbound', 'outbound', 'web')",
    )


def downgrade() -> None:
    """Revert to original constraints without 'business_hours' and 'web'."""
    op.execute(sa.text(
        "ALTER TABLE call_logs DROP CONSTRAINT IF EXISTS ck_call_log_direction"
    ))
    op.create_check_constraint(
        'ck_call_log_direction',
        'call_logs',
        "direction IN ('inbound', 'outbound')",
    )

    op.execute(sa.text(
        "ALTER TABLE escalation_rules DROP CONSTRAINT IF EXISTS ck_escalation_rule_type"
    ))
    op.create_check_constraint(
        'ck_escalation_rule_type',
        'escalation_rules',
        "rule_type IN ('sentiment', 'keyword', 'confidence', 'intent')",
    )
