"""concurrency, idempotency and document uniqueness wave1

Revision ID: b1c2d3e4f5a6
Revises: a94021a6ec58
Create Date: 2026-09-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a94021a6ec58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # Idempotency-key unique indexes (business-scoped)                   #
    # ------------------------------------------------------------------ #

    # journal_entries.idempotency_key is nullable - partial index required
    op.create_index(
        'uq_journal_entries_business_idempotency_key',
        'journal_entries',
        ['business_id', 'idempotency_key'],
        unique=True,
        postgresql_where=sa.text('idempotency_key IS NOT NULL'),
    )

    # payments.idempotency_key is nullable - partial index required
    op.create_index(
        'uq_payments_business_idempotency_key',
        'payments',
        ['business_id', 'idempotency_key'],
        unique=True,
        postgresql_where=sa.text('idempotency_key IS NOT NULL'),
    )

    # payment_attempts.idempotency_key is NOT NULL - full unique index
    op.create_index(
        'uq_payment_attempts_business_idempotency_key',
        'payment_attempts',
        ['business_id', 'idempotency_key'],
        unique=True,
    )

    # ------------------------------------------------------------------ #
    # Document-number unique indexes (business-scoped)                   #
    # ------------------------------------------------------------------ #

    # sales.sales_number
    op.create_index(
        'uq_sales_business_sales_number',
        'sales',
        ['business_id', 'sales_number'],
        unique=True,
    )

    # purchases.purchase_number
    op.create_index(
        'uq_purchases_business_purchase_number',
        'purchases',
        ['business_id', 'purchase_number'],
        unique=True,
    )

    # sales_orders.sales_order_number
    op.create_index(
        'uq_sales_orders_business_sales_order_number',
        'sales_orders',
        ['business_id', 'sales_order_number'],
        unique=True,
    )

    # quotations.quotation_number
    op.create_index(
        'uq_quotations_business_quotation_number',
        'quotations',
        ['business_id', 'quotation_number'],
        unique=True,
    )

    # delivery_notes.delivery_number
    op.create_index(
        'uq_delivery_notes_business_delivery_number',
        'delivery_notes',
        ['business_id', 'delivery_number'],
        unique=True,
    )

    # transfers.transfer_number
    op.create_index(
        'uq_transfers_business_transfer_number',
        'transfers',
        ['business_id', 'transfer_number'],
        unique=True,
    )

    # expenses.expense_number
    op.create_index(
        'uq_expenses_business_expense_number',
        'expenses',
        ['business_id', 'expense_number'],
        unique=True,
    )

    # payments.payment_number
    op.create_index(
        'uq_payments_business_payment_number',
        'payments',
        ['business_id', 'payment_number'],
        unique=True,
    )

    # sales_payments.payment_number
    op.create_index(
        'uq_sales_payments_business_payment_number',
        'sales_payments',
        ['business_id', 'payment_number'],
        unique=True,
    )

    # journal_entries.journal_number
    op.create_index(
        'uq_journal_entries_business_journal_number',
        'journal_entries',
        ['business_id', 'journal_number'],
        unique=True,
    )

    # sales_returns.return_number
    op.create_index(
        'uq_sales_returns_business_return_number',
        'sales_returns',
        ['business_id', 'return_number'],
        unique=True,
    )

    # purchase_returns.return_number
    op.create_index(
        'uq_purchase_returns_business_return_number',
        'purchase_returns',
        ['business_id', 'return_number'],
        unique=True,
    )

    # receivings.receiving_number
    op.create_index(
        'uq_receivings_business_receiving_number',
        'receivings',
        ['business_id', 'receiving_number'],
        unique=True,
    )


def downgrade() -> None:
    # ------------------------------------------------------------------ #
    # Drop document-number unique indexes                                 #
    # ------------------------------------------------------------------ #
    op.drop_index(
        'uq_receivings_business_receiving_number',
        table_name='receivings',
    )
    op.drop_index(
        'uq_purchase_returns_business_return_number',
        table_name='purchase_returns',
    )
    op.drop_index(
        'uq_sales_returns_business_return_number',
        table_name='sales_returns',
    )
    op.drop_index(
        'uq_journal_entries_business_journal_number',
        table_name='journal_entries',
    )
    op.drop_index(
        'uq_sales_payments_business_payment_number',
        table_name='sales_payments',
    )
    op.drop_index(
        'uq_payments_business_payment_number',
        table_name='payments',
    )
    op.drop_index(
        'uq_expenses_business_expense_number',
        table_name='expenses',
    )
    op.drop_index(
        'uq_transfers_business_transfer_number',
        table_name='transfers',
    )
    op.drop_index(
        'uq_delivery_notes_business_delivery_number',
        table_name='delivery_notes',
    )
    op.drop_index(
        'uq_quotations_business_quotation_number',
        table_name='quotations',
    )
    op.drop_index(
        'uq_sales_orders_business_sales_order_number',
        table_name='sales_orders',
    )
    op.drop_index(
        'uq_purchases_business_purchase_number',
        table_name='purchases',
    )
    op.drop_index(
        'uq_sales_business_sales_number',
        table_name='sales',
    )

    # ------------------------------------------------------------------ #
    # Drop idempotency-key unique indexes                                #
    # ------------------------------------------------------------------ #
    op.drop_index(
        'uq_payment_attempts_business_idempotency_key',
        table_name='payment_attempts',
    )
    op.drop_index(
        'uq_payments_business_idempotency_key',
        table_name='payments',
    )
    op.drop_index(
        'uq_journal_entries_business_idempotency_key',
        table_name='journal_entries',
    )
