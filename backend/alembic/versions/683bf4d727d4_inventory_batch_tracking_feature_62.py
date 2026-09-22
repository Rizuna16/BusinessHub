"""inventory batch tracking feature 62

Revision ID: 683bf4d727d4
Revises: c3d4e5f6a7b8
Create Date: 2026-09-20 22:38:53.427963

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '683bf4d727d4'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Feature #62 — Inventory Batch, Lot & Expiry Management

    # 1. Add batch tracking flag to products
    op.add_column('products', sa.Column('batch_tracking_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    # 2. Create inventory_batches table
    op.create_table('inventory_batches',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('business_id', sa.String(length=36), nullable=False),
        sa.Column('inventory_location_id', sa.String(length=36), nullable=False),
        sa.Column('product_id', sa.String(length=36), nullable=False),
        sa.Column('variant_id', sa.String(length=36), nullable=True),
        sa.Column('batch_number', sa.String(length=100), nullable=False),
        sa.Column('manufacture_date', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('business_id', 'inventory_location_id', 'product_id', 'variant_id', 'batch_number', name='uq_inventory_batch_identity'),
    )
    op.create_index('ix_batch_expiry', 'inventory_batches', ['business_id', 'expiry_date'], unique=False)
    op.create_index(op.f('ix_inventory_batches_business_id'), 'inventory_batches', ['business_id'], unique=False)
    op.create_index(op.f('ix_inventory_batches_inventory_location_id'), 'inventory_batches', ['inventory_location_id'], unique=False)
    op.create_index(op.f('ix_inventory_batches_product_id'), 'inventory_batches', ['product_id'], unique=False)

    # 3. Create batch_stock_balances table
    op.create_table('batch_stock_balances',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('business_id', sa.String(length=36), nullable=False),
        sa.Column('inventory_location_id', sa.String(length=36), nullable=False),
        sa.Column('batch_id', sa.String(length=36), nullable=False),
        sa.Column('product_id', sa.String(length=36), nullable=False),
        sa.Column('variant_id', sa.String(length=36), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['inventory_batches.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('business_id', 'inventory_location_id', 'batch_id', name='uq_batch_stock_balance_identity'),
    )
    op.create_index(op.f('ix_batch_stock_balances_batch_id'), 'batch_stock_balances', ['batch_id'], unique=False)
    op.create_index(op.f('ix_batch_stock_balances_business_id'), 'batch_stock_balances', ['business_id'], unique=False)
    op.create_index(op.f('ix_batch_stock_balances_inventory_location_id'), 'batch_stock_balances', ['inventory_location_id'], unique=False)
    op.create_index(op.f('ix_batch_stock_balances_product_id'), 'batch_stock_balances', ['product_id'], unique=False)

    # 4. Create batch_stock_movements table
    op.create_table('batch_stock_movements',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('business_id', sa.String(length=36), nullable=False),
        sa.Column('stock_movement_id', sa.String(length=36), nullable=False),
        sa.Column('batch_id', sa.String(length=36), nullable=False),
        sa.Column('inventory_location_id', sa.String(length=36), nullable=False),
        sa.Column('product_id', sa.String(length=36), nullable=False),
        sa.Column('variant_id', sa.String(length=36), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['inventory_batches.id']),
        sa.ForeignKeyConstraint(['stock_movement_id'], ['stock_movements.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_batch_stock_movements_batch_id'), 'batch_stock_movements', ['batch_id'], unique=False)
    op.create_index(op.f('ix_batch_stock_movements_business_id'), 'batch_stock_movements', ['business_id'], unique=False)
    op.create_index(op.f('ix_batch_stock_movements_product_id'), 'batch_stock_movements', ['product_id'], unique=False)
    op.create_index(op.f('ix_batch_stock_movements_stock_movement_id'), 'batch_stock_movements', ['stock_movement_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_batch_stock_movements_stock_movement_id'), table_name='batch_stock_movements')
    op.drop_index(op.f('ix_batch_stock_movements_product_id'), table_name='batch_stock_movements')
    op.drop_index(op.f('ix_batch_stock_movements_business_id'), table_name='batch_stock_movements')
    op.drop_index(op.f('ix_batch_stock_movements_batch_id'), table_name='batch_stock_movements')
    op.drop_table('batch_stock_movements')

    op.drop_index(op.f('ix_batch_stock_balances_product_id'), table_name='batch_stock_balances')
    op.drop_index(op.f('ix_batch_stock_balances_inventory_location_id'), table_name='batch_stock_balances')
    op.drop_index(op.f('ix_batch_stock_balances_business_id'), table_name='batch_stock_balances')
    op.drop_index(op.f('ix_batch_stock_balances_batch_id'), table_name='batch_stock_balances')
    op.drop_table('batch_stock_balances')

    op.drop_index(op.f('ix_inventory_batches_product_id'), table_name='inventory_batches')
    op.drop_index(op.f('ix_inventory_batches_inventory_location_id'), table_name='inventory_batches')
    op.drop_index(op.f('ix_inventory_batches_business_id'), table_name='inventory_batches')
    op.drop_index('ix_batch_expiry', table_name='inventory_batches')
    op.drop_table('inventory_batches')

    op.drop_column('products', 'batch_tracking_enabled')
