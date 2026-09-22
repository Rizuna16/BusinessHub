"""batch snapshot allocation workflow lines

Revision ID: d4e5f6a7b8c9
Revises: 683bf4d727d4
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = '683bf4d727d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add batch_allocations JSON column to receiving_lines
    op.add_column('receiving_lines', sa.Column('batch_allocations', sa.JSON(), nullable=True))

    # Add batch_allocations JSON column to delivery_note_lines
    op.add_column('delivery_note_lines', sa.Column('batch_allocations', sa.JSON(), nullable=True))

    # Add batch_allocations JSON column to sales_return_lines
    op.add_column('sales_return_lines', sa.Column('batch_allocations', sa.JSON(), nullable=True))

    # Add batch_allocations JSON column to purchase_return_lines
    op.add_column('purchase_return_lines', sa.Column('batch_allocations', sa.JSON(), nullable=True))

    # Add batch_adjustments JSON column to stock_opname_lines
    op.add_column('stock_opname_lines', sa.Column('batch_adjustments', sa.JSON(), nullable=True))

    # Add batch_snapshots JSON column to transfer_lines
    op.add_column('transfer_lines', sa.Column('batch_snapshots', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('transfer_lines', 'batch_snapshots')
    op.drop_column('stock_opname_lines', 'batch_adjustments')
    op.drop_column('purchase_return_lines', 'batch_allocations')
    op.drop_column('sales_return_lines', 'batch_allocations')
    op.drop_column('delivery_note_lines', 'batch_allocations')
    op.drop_column('receiving_lines', 'batch_allocations')
