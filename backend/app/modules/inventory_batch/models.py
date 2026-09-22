import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, DateTime, Numeric, ForeignKey, Date, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InventoryBatch(Base):
    __tablename__ = "inventory_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    inventory_location_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    variant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    batch_number: Mapped[str] = mapped_column(String(100), nullable=False)
    manufacture_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("business_id", "inventory_location_id", "product_id", "variant_id", "batch_number",
                         name="uq_inventory_batch_identity"),
        Index("ix_batch_expiry", "business_id", "expiry_date"),
    )


class BatchStockBalance(Base):
    __tablename__ = "batch_stock_balances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    inventory_location_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("inventory_batches.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    variant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("business_id", "inventory_location_id", "batch_id",
                         name="uq_batch_stock_balance_identity"),
    )


class BatchStockMovement(Base):
    __tablename__ = "batch_stock_movements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    stock_movement_id: Mapped[str] = mapped_column(String(36), ForeignKey("stock_movements.id"), nullable=False, index=True)
    batch_id: Mapped[str] = mapped_column(String(36), ForeignKey("inventory_batches.id"), nullable=False, index=True)
    inventory_location_id: Mapped[str] = mapped_column(String(36), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    variant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
