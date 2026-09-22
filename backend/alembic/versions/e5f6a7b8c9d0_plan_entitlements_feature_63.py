"""plan entitlements feature 63

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-22 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'plan_entitlements',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('plan_id', sa.String(50), nullable=False, index=True),
        sa.Column('feature_key', sa.String(50), nullable=False),
        sa.Column('limit_value', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('plan_id', 'feature_key', name='uq_plan_entitlement_key'),
    )


def downgrade() -> None:
    op.drop_table('plan_entitlements')
