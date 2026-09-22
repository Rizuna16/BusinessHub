import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.database import Base

# Import ALL models so Alembic discovers them via Base.metadata
import app.modules.account.models
import app.modules.accounting.models
import app.modules.authentication.models
import app.modules.barcode.models
import app.modules.branch.models
import app.modules.business.models
import app.modules.business_membership.models
import app.modules.business_template.models
import app.modules.cash_account.models
import app.modules.cashier_shift.models
import app.modules.category.models
import app.modules.customer.models
import app.modules.customer_credit.models
import app.modules.delivery_note.models
import app.modules.expense.models
import app.modules.inventory.models
import app.modules.inventory_batch.models
import app.modules.notification.models
import app.modules.payment.models
import app.modules.platform_admin.models
import app.modules.pricing.models
import app.modules.product.models
import app.modules.product_variant.models
import app.modules.purchase.models
import app.modules.purchase_return.models
import app.modules.receiving.models
import app.modules.sales.models
import app.modules.sales_order.models
import app.modules.sales_payment.models
import app.modules.sales_return.models
import app.modules.stock_opname.models
import app.modules.subscription.models
import app.modules.supplier.models
import app.modules.supplier_catalog.models
import app.modules.transfer.models
import app.modules.unit.models
import app.modules.warehouse.models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})

    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        configuration["sqlalchemy.url"] = database_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
