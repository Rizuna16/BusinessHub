"""concurrency, idempotency and document uniqueness wave2 - inventory uniqueness indexes

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6
Create Date: 2026-09-18 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # Stock balance partial unique indexes - nullable variant_id handling #
    # ------------------------------------------------------------------ #

    # For rows where variant_id IS NOT NULL: UNIQUE(business_id, inventory_location_id, product_id, variant_id)
    op.create_index(
        'uq_stock_balances_identity_with_variant',
        'stock_balances',
        ['business_id', 'inventory_location_id', 'product_id', 'variant_id'],
        unique=True,
        postgresql_where=sa.text('variant_id IS NOT NULL'),
    )

    # For rows where variant_id IS NULL: UNIQUE(business_id, inventory_location_id, product_id)
    op.create_index(
        'uq_stock_balances_identity_null_variant',
        'stock_balances',
        ['business_id', 'inventory_location_id', 'product_id'],
        unique=True,
        postgresql_where=sa.text('variant_id IS NULL'),
    )

    # ------------------------------------------------------------------ #
    # Inventory cost state partial unique indexes - nullable variant_id handling #
    # ------------------------------------------------------------------ #

    # For rows where variant_id IS NOT NULL: UNIQUE(business_id, product_id, variant_id)
    op.create_index(
        'uq_inventory_cost_states_identity_with_variant',
        'inventory_cost_states',
        ['business_id', 'product_id', 'variant_id'],
        unique=True,
        postgresql_where=sa.text('variant_id IS NOT NULL'),
    )

    # For rows where variant_id IS NULL: UNIQUE(business_id, product_id)
    op.create_index(
        'uq_inventory_cost_states_identity_null_variant',
        'inventory_cost_states',
        ['business_id', 'product_id'],
        unique=True,
        postgresql_where=sa.text('variant_id IS NULL'),
    )


def downgrade() -> None:
    # ------------------------------------------------------------------ #
    # Drop inventory cost state partial unique indexes                 #
    # ------------------------------------------------------------------ #
    op.drop_index(
        'uq_inventory_cost_states_identity_null_variant',
        table_name='inventory_cost_states',
    )
    op.drop_index(
        'uq_inventory_cost_states_identity_with_variant',
        table_name='inventory_cost_states',
    )

    # ------------------------------------------------------------------ #
    # Drop stock balance partial unique indexes                       #
    # ------------------------------------------------------------------ #
    op.drop_index(
        'uq_stock_balances_identity_null_variant',
        table_name='stock_balances',
    )
    op.drop_index(
        'uq_stock_balances_identity_with_variant',
        table_name='stock_balances',
    )