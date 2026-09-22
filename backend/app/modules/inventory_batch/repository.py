from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from abc import ABC, abstractmethod

from app.modules.inventory_batch.schemas import (
    InventoryBatchInDB,
    BatchStockBalanceInDB,
    BatchStockMovementInDB,
)


class AbstractInventoryBatchRepository(ABC):
    @abstractmethod
    async def create_batch(
        self, business_id: str, inventory_location_id: str,
        product_id: str, variant_id: Optional[str],
        batch_number: str, manufacture_date: Optional[date],
        expiry_date: Optional[date],
    ) -> InventoryBatchInDB: ...

    @abstractmethod
    async def get_batch(self, batch_id: str, business_id: str) -> Optional[InventoryBatchInDB]: ...

    @abstractmethod
    async def get_batch_by_identity(
        self, business_id: str, inventory_location_id: str,
        product_id: str, variant_id: Optional[str], batch_number: str,
    ) -> Optional[InventoryBatchInDB]: ...

    @abstractmethod
    async def list_batches(
        self, business_id: str, inventory_location_id: Optional[str] = None,
        product_id: Optional[str] = None, variant_id: Optional[str] = None,
        expired_only: bool = False,
        page: int = 1, page_size: int = 50,
    ) -> tuple[List[InventoryBatchInDB], int]: ...

    @abstractmethod
    async def update_batch_dates(
        self, batch_id: str, business_id: str,
        manufacture_date: Optional[date] = None,
        expiry_date: Optional[date] = None,
    ) -> Optional[InventoryBatchInDB]: ...

    @classmethod
    @abstractmethod
    def clear(cls): ...


class AbstractBatchStockBalanceRepository(ABC):
    @abstractmethod
    async def get_balance(
        self, business_id: str, inventory_location_id: str, batch_id: str,
    ) -> Optional[BatchStockBalanceInDB]: ...

    @abstractmethod
    async def get_balance_for_update(
        self, business_id: str, inventory_location_id: str, batch_id: str,
    ) -> Optional[BatchStockBalanceInDB]: ...

    @abstractmethod
    async def upsert_balance(
        self, business_id: str, inventory_location_id: str,
        batch_id: str, product_id: str, variant_id: Optional[str],
        delta: Decimal,
    ) -> BatchStockBalanceInDB: ...

    @abstractmethod
    async def list_balances_for_product(
        self, business_id: str, inventory_location_id: str,
        product_id: str, variant_id: Optional[str] = None,
    ) -> List[BatchStockBalanceInDB]: ...

    @abstractmethod
    async def list_all_balances_for_product(
        self, business_id: str, product_id: str, variant_id: Optional[str] = None,
    ) -> List[BatchStockBalanceInDB]: ...

    @classmethod
    @abstractmethod
    def clear(cls): ...


class AbstractBatchStockMovementRepository(ABC):
    @abstractmethod
    async def create_movement(
        self, business_id: str, stock_movement_id: str,
        batch_id: str, inventory_location_id: str,
        product_id: str, variant_id: Optional[str],
        quantity: Decimal, direction: str,
    ) -> BatchStockMovementInDB: ...

    @abstractmethod
    async def list_movements_for_batch(
        self, batch_id: str, business_id: str,
    ) -> List[BatchStockMovementInDB]: ...

    @abstractmethod
    async def list_movements_for_product(
        self, business_id: str, product_id: str,
        variant_id: Optional[str] = None,
        inventory_location_id: Optional[str] = None,
    ) -> List[BatchStockMovementInDB]: ...

    @classmethod
    @abstractmethod
    def clear(cls): ...


# ── InMemory implementations ─────────────────────────────────────────────────

class InMemoryInventoryBatchRepository(AbstractInventoryBatchRepository):
    _batches: dict[str, InventoryBatchInDB] = {}

    @classmethod
    def clear(cls):
        cls._batches.clear()

    async def create_batch(self, business_id, inventory_location_id, product_id, variant_id, batch_number, manufacture_date, expiry_date):
        import uuid
        now = datetime.utcnow()
        batch = InventoryBatchInDB(
            id=str(uuid.uuid4()), business_id=business_id,
            inventory_location_id=inventory_location_id,
            product_id=product_id, variant_id=variant_id,
            batch_number=batch_number, manufacture_date=manufacture_date,
            expiry_date=expiry_date, created_at=now, updated_at=now,
        )
        self._batches[batch.id] = batch
        return batch

    async def get_batch(self, batch_id, business_id):
        b = self._batches.get(batch_id)
        if b and b.business_id == business_id:
            return b
        return None

    async def get_batch_by_identity(self, business_id, inventory_location_id, product_id, variant_id, batch_number):
        for b in self._batches.values():
            if (b.business_id == business_id and b.inventory_location_id == inventory_location_id
                and b.product_id == product_id and b.variant_id == variant_id
                and b.batch_number == batch_number):
                return b
        return None

    async def list_batches(self, business_id, inventory_location_id=None, product_id=None, variant_id=None, expired_only=False, page=1, page_size=50):
        items = [b for b in self._batches.values() if b.business_id == business_id]
        if inventory_location_id:
            items = [b for b in items if b.inventory_location_id == inventory_location_id]
        if product_id:
            items = [b for b in items if b.product_id == product_id]
        if variant_id is not None:
            items = [b for b in items if b.variant_id == variant_id]
        if expired_only:
            today = date.today()
            items = [b for b in items if b.expiry_date and b.expiry_date < today]
        total = len(items)
        start = (page - 1) * page_size
        return items[start:start + page_size], total

    async def update_batch_dates(self, batch_id, business_id, manufacture_date=None, expiry_date=None):
        b = self._batches.get(batch_id)
        if b and b.business_id == business_id:
            if manufacture_date is not None:
                b.manufacture_date = manufacture_date
            if expiry_date is not None:
                b.expiry_date = expiry_date
            b.updated_at = datetime.utcnow()
            return b
        return None


class InMemoryBatchStockBalanceRepository(AbstractBatchStockBalanceRepository):
    _balances: dict[str, BatchStockBalanceInDB] = {}

    @classmethod
    def clear(cls):
        cls._balances.clear()

    async def get_balance(self, business_id, inventory_location_id, batch_id):
        for b in self._balances.values():
            if (b.business_id == business_id and b.inventory_location_id == inventory_location_id and b.batch_id == batch_id):
                return b
        return None

    async def get_balance_for_update(self, business_id, inventory_location_id, batch_id):
        return await self.get_balance(business_id, inventory_location_id, batch_id)

    async def upsert_balance(self, business_id, inventory_location_id, batch_id, product_id, variant_id, delta):
        import uuid
        existing = await self.get_balance(business_id, inventory_location_id, batch_id)
        if existing:
            existing.quantity += delta
            existing.updated_at = datetime.utcnow()
            return existing
        now = datetime.utcnow()
        bal = BatchStockBalanceInDB(
            id=str(uuid.uuid4()), business_id=business_id,
            inventory_location_id=inventory_location_id,
            batch_id=batch_id, product_id=product_id, variant_id=variant_id,
            quantity=delta, created_at=now, updated_at=now,
        )
        self._balances[bal.id] = bal
        return bal

    async def list_balances_for_product(self, business_id, inventory_location_id, product_id, variant_id=None):
        items = [b for b in self._balances.values()
                 if b.business_id == business_id and b.inventory_location_id == inventory_location_id and b.product_id == product_id]
        if variant_id is not None:
            items = [b for b in items if b.variant_id == variant_id]
        return items

    async def list_all_balances_for_product(self, business_id, product_id, variant_id=None):
        items = [b for b in self._balances.values()
                 if b.business_id == business_id and b.product_id == product_id]
        if variant_id is not None:
            items = [b for b in items if b.variant_id == variant_id]
        return items


class InMemoryBatchStockMovementRepository(AbstractBatchStockMovementRepository):
    _movements: dict[str, BatchStockMovementInDB] = {}

    @classmethod
    def clear(cls):
        cls._movements.clear()

    async def create_movement(self, business_id, stock_movement_id, batch_id, inventory_location_id, product_id, variant_id, quantity, direction):
        import uuid
        mov = BatchStockMovementInDB(
            id=str(uuid.uuid4()), business_id=business_id,
            stock_movement_id=stock_movement_id, batch_id=batch_id,
            inventory_location_id=inventory_location_id,
            product_id=product_id, variant_id=variant_id,
            quantity=quantity, direction=direction,
            created_at=datetime.utcnow(),
        )
        self._movements[mov.id] = mov
        return mov

    async def list_movements_for_batch(self, batch_id, business_id):
        return [m for m in self._movements.values() if m.batch_id == batch_id and m.business_id == business_id]

    async def list_movements_for_product(self, business_id, product_id, variant_id=None, inventory_location_id=None):
        items = [m for m in self._movements.values() if m.business_id == business_id and m.product_id == product_id]
        if variant_id is not None:
            items = [m for m in items if m.variant_id == variant_id]
        if inventory_location_id:
            items = [m for m in items if m.inventory_location_id == inventory_location_id]
        return items
