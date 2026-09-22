import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.inventory_batch.models import (
    InventoryBatch, BatchStockBalance, BatchStockMovement,
)
from app.modules.inventory_batch.repository import (
    AbstractInventoryBatchRepository,
    AbstractBatchStockBalanceRepository,
    AbstractBatchStockMovementRepository,
)
from app.modules.inventory_batch.schemas import (
    InventoryBatchInDB, BatchStockBalanceInDB, BatchStockMovementInDB,
)
from app.modules.sqla_base import sa_create


def _to_batch(obj: InventoryBatch) -> InventoryBatchInDB:
    return InventoryBatchInDB(
        id=obj.id,
        business_id=obj.business_id,
        inventory_location_id=obj.inventory_location_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        batch_number=obj.batch_number,
        manufacture_date=obj.manufacture_date,
        expiry_date=obj.expiry_date,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_balance(obj: BatchStockBalance) -> BatchStockBalanceInDB:
    return BatchStockBalanceInDB(
        id=obj.id,
        business_id=obj.business_id,
        inventory_location_id=obj.inventory_location_id,
        batch_id=obj.batch_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        quantity=obj.quantity,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_movement(obj: BatchStockMovement) -> BatchStockMovementInDB:
    return BatchStockMovementInDB(
        id=obj.id,
        business_id=obj.business_id,
        stock_movement_id=obj.stock_movement_id,
        batch_id=obj.batch_id,
        inventory_location_id=obj.inventory_location_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        quantity=obj.quantity,
        direction=obj.direction,
        created_at=obj.created_at,
    )


class SQLAlchemyInventoryBatchRepository(AbstractInventoryBatchRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_batch(
        self, business_id: str, inventory_location_id: str,
        product_id: str, variant_id: Optional[str],
        batch_number: str, manufacture_date: Optional[date],
        expiry_date: Optional[date],
    ) -> InventoryBatchInDB:
        data = {
            "business_id": business_id,
            "inventory_location_id": inventory_location_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "batch_number": batch_number.strip(),
            "manufacture_date": manufacture_date,
            "expiry_date": expiry_date,
        }
        obj = await sa_create(self.session, InventoryBatch, data)
        return _to_batch(obj)

    async def get_batch(self, batch_id: str, business_id: str) -> Optional[InventoryBatchInDB]:
        stmt = select(InventoryBatch).where(
            InventoryBatch.id == batch_id,
            InventoryBatch.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_batch(obj) if obj else None

    async def get_batch_by_identity(
        self, business_id: str, inventory_location_id: str,
        product_id: str, variant_id: Optional[str], batch_number: str,
    ) -> Optional[InventoryBatchInDB]:
        filters = [
            InventoryBatch.business_id == business_id,
            InventoryBatch.inventory_location_id == inventory_location_id,
            InventoryBatch.product_id == product_id,
            InventoryBatch.batch_number == batch_number.strip(),
        ]
        if variant_id is not None:
            filters.append(InventoryBatch.variant_id == variant_id)
        else:
            filters.append(InventoryBatch.variant_id == None)
        stmt = select(InventoryBatch).where(and_(*filters))
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_batch(obj) if obj else None

    async def list_batches(
        self, business_id: str, inventory_location_id: Optional[str] = None,
        product_id: Optional[str] = None, variant_id: Optional[str] = None,
        expired_only: bool = False,
        page: int = 1, page_size: int = 50,
    ) -> tuple[List[InventoryBatchInDB], int]:
        filters = [InventoryBatch.business_id == business_id]
        if inventory_location_id:
            filters.append(InventoryBatch.inventory_location_id == inventory_location_id)
        if product_id:
            filters.append(InventoryBatch.product_id == product_id)
        if variant_id is not None:
            filters.append(InventoryBatch.variant_id == variant_id)
        if expired_only:
            filters.append(InventoryBatch.expiry_date < func.current_date())
        count_stmt = select(func.count()).select_from(InventoryBatch).where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()
        stmt = (
            select(InventoryBatch)
            .where(and_(*filters))
            .order_by(asc(InventoryBatch.expiry_date), asc(InventoryBatch.created_at))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        res = await self.session.execute(stmt)
        return [_to_batch(o) for o in res.scalars().all()], total

    async def update_batch_dates(
        self, batch_id: str, business_id: str,
        manufacture_date: Optional[date] = None,
        expiry_date: Optional[date] = None,
    ) -> Optional[InventoryBatchInDB]:
        stmt = select(InventoryBatch).where(
            InventoryBatch.id == batch_id,
            InventoryBatch.business_id == business_id,
        ).with_for_update()
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        if manufacture_date is not None:
            obj.manufacture_date = manufacture_date
        if expiry_date is not None:
            obj.expiry_date = expiry_date
        await self.session.flush()
        return _to_batch(obj)

    @classmethod
    def clear(cls):
        pass


class SQLAlchemyBatchStockBalanceRepository(AbstractBatchStockBalanceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_balance(
        self, business_id: str, inventory_location_id: str, batch_id: str,
    ) -> Optional[BatchStockBalanceInDB]:
        stmt = select(BatchStockBalance).where(
            BatchStockBalance.business_id == business_id,
            BatchStockBalance.inventory_location_id == inventory_location_id,
            BatchStockBalance.batch_id == batch_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_balance(obj) if obj else None

    async def get_balance_for_update(
        self, business_id: str, inventory_location_id: str, batch_id: str,
    ) -> Optional[BatchStockBalanceInDB]:
        stmt = select(BatchStockBalance).where(
            BatchStockBalance.business_id == business_id,
            BatchStockBalance.inventory_location_id == inventory_location_id,
            BatchStockBalance.batch_id == batch_id,
        ).with_for_update()
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_balance(obj) if obj else None

    async def upsert_balance(
        self, business_id: str, inventory_location_id: str,
        batch_id: str, product_id: str, variant_id: Optional[str],
        delta: Decimal,
    ) -> BatchStockBalanceInDB:
        stmt = select(BatchStockBalance).where(
            BatchStockBalance.business_id == business_id,
            BatchStockBalance.inventory_location_id == inventory_location_id,
            BatchStockBalance.batch_id == batch_id,
        ).with_for_update()
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if obj:
            new_qty = obj.quantity + delta
            if new_qty < Decimal("0"):
                raise ValueError("Batch stock balance cannot be negative")
            obj.quantity = new_qty
            await self.session.flush()
            return _to_balance(obj)
        if delta < Decimal("0"):
            raise ValueError("Batch stock balance cannot be negative")
        try:
            data = {
                "id": str(uuid.uuid4()),
                "business_id": business_id,
                "inventory_location_id": inventory_location_id,
                "batch_id": batch_id,
                "product_id": product_id,
                "variant_id": variant_id,
                "quantity": delta,
            }
            obj = await sa_create(self.session, BatchStockBalance, data)
            return _to_balance(obj)
        except Exception:
            stmt = select(BatchStockBalance).where(
                BatchStockBalance.business_id == business_id,
                BatchStockBalance.inventory_location_id == inventory_location_id,
                BatchStockBalance.batch_id == batch_id,
            ).with_for_update()
            res = await self.session.execute(stmt)
            obj = res.scalar_one_or_none()
            if obj:
                new_qty = obj.quantity + delta
                if new_qty < Decimal("0"):
                    raise ValueError("Batch stock balance cannot be negative")
                obj.quantity = new_qty
                await self.session.flush()
                return _to_balance(obj)
            raise

    async def list_balances_for_product(
        self, business_id: str, inventory_location_id: str,
        product_id: str, variant_id: Optional[str] = None,
    ) -> List[BatchStockBalanceInDB]:
        filters = [
            BatchStockBalance.business_id == business_id,
            BatchStockBalance.inventory_location_id == inventory_location_id,
            BatchStockBalance.product_id == product_id,
        ]
        if variant_id is not None:
            filters.append(BatchStockBalance.variant_id == variant_id)
        stmt = select(BatchStockBalance).where(and_(*filters)).order_by(asc(BatchStockBalance.quantity))
        res = await self.session.execute(stmt)
        return [_to_balance(o) for o in res.scalars().all()]

    async def list_all_balances_for_product(
        self, business_id: str, product_id: str, variant_id: Optional[str] = None,
    ) -> List[BatchStockBalanceInDB]:
        filters = [
            BatchStockBalance.business_id == business_id,
            BatchStockBalance.product_id == product_id,
        ]
        if variant_id is not None:
            filters.append(BatchStockBalance.variant_id == variant_id)
        stmt = select(BatchStockBalance).where(and_(*filters))
        res = await self.session.execute(stmt)
        return [_to_balance(o) for o in res.scalars().all()]

    @classmethod
    def clear(cls):
        pass


class SQLAlchemyBatchStockMovementRepository(AbstractBatchStockMovementRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_movement(
        self, business_id: str, stock_movement_id: str,
        batch_id: str, inventory_location_id: str,
        product_id: str, variant_id: Optional[str],
        quantity: Decimal, direction: str,
    ) -> BatchStockMovementInDB:
        data = {
            "business_id": business_id,
            "stock_movement_id": stock_movement_id,
            "batch_id": batch_id,
            "inventory_location_id": inventory_location_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "quantity": quantity,
            "direction": direction,
        }
        obj = await sa_create(self.session, BatchStockMovement, data)
        return _to_movement(obj)

    async def list_movements_for_batch(
        self, batch_id: str, business_id: str,
    ) -> List[BatchStockMovementInDB]:
        stmt = (
            select(BatchStockMovement)
            .where(
                BatchStockMovement.batch_id == batch_id,
                BatchStockMovement.business_id == business_id,
            )
            .order_by(desc(BatchStockMovement.created_at))
        )
        res = await self.session.execute(stmt)
        return [_to_movement(o) for o in res.scalars().all()]

    async def list_movements_for_product(
        self, business_id: str, product_id: str,
        variant_id: Optional[str] = None,
        inventory_location_id: Optional[str] = None,
    ) -> List[BatchStockMovementInDB]:
        filters = [
            BatchStockMovement.business_id == business_id,
            BatchStockMovement.product_id == product_id,
        ]
        if variant_id is not None:
            filters.append(BatchStockMovement.variant_id == variant_id)
        if inventory_location_id:
            filters.append(BatchStockMovement.inventory_location_id == inventory_location_id)
        stmt = (
            select(BatchStockMovement)
            .where(and_(*filters))
            .order_by(desc(BatchStockMovement.created_at))
        )
        res = await self.session.execute(stmt)
        return [_to_movement(o) for o in res.scalars().all()]

    @classmethod
    def clear(cls):
        pass
