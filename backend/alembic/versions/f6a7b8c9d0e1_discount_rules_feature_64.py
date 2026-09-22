"""discount rules feature 64

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-23 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'discount_rules',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('business_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('value', sa.Numeric(18, 4), nullable=False),
        sa.Column('product_id', sa.String(36), nullable=True),
        sa.Column('variant_id', sa.String(36), nullable=True),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('status', sa.String(20), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_discount_rules_business_status', 'discount_rules', ['business_id', 'status'])
    op.create_index('ix_discount_rules_business_product', 'discount_rules', ['business_id', 'product_id'])
    op.create_index('ix_discount_rules_business_variant', 'discount_rules', ['business_id', 'variant_id'])
    op.create_index('ix_discount_rules_business_dates', 'discount_rules', ['business_id', 'starts_at', 'ends_at'])

    op.add_column('sales_lines', sa.Column('discount_rule_id', sa.String(36), nullable=True))
    op.add_column('sales_lines', sa.Column('discount_rule_name_snapshot', sa.String(255), nullable=True))
    op.add_column('quotation_lines', sa.Column('discount_rule_id', sa.String(36), nullable=True))
    op.add_column('quotation_lines', sa.Column('discount_rule_name_snapshot', sa.String(255), nullable=True))
    op.add_column('sales_order_lines', sa.Column('discount_rule_id', sa.String(36), nullable=True))
    op.add_column('sales_order_lines', sa.Column('discount_rule_name_snapshot', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('sales_order_lines', 'discount_rule_name_snapshot')
    op.drop_column('sales_order_lines', 'discount_rule_id')
    op.drop_column('quotation_lines', 'discount_rule_name_snapshot')
    op.drop_column('quotation_lines', 'discount_rule_id')
    op.drop_column('sales_lines', 'discount_rule_name_snapshot')
    op.drop_column('sales_lines', 'discount_rule_id')
    op.drop_index('ix_discount_rules_business_dates', 'discount_rules')
    op.drop_index('ix_discount_rules_business_variant', 'discount_rules')
    op.drop_index('ix_discount_rules_business_product', 'discount_rules')
    op.drop_index('ix_discount_rules_business_status', 'discount_rules')
    op.drop_table('discount_rules')
