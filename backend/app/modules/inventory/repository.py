from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import uuid
from abc import ABC, abstractmethod

from app.modules.inventory.schemas import (
    StockBalanceInDB,
    StockMovementInDB,
    StockMovementLineInDB,
    MovementType,
    MovementStatus,
    MovementDirection,
    ReferenceType,
    InventoryCostStateInDB,
    InventoryCostMovementInDB,
    InventoryCostMovementType,
)


class AbstractStockBalanceRepository(ABC):
    @abstractmethod
    async def get_balance(
        self,
        business_id: str,
        inventory_location_id: str,
        product_id: str,
        variant_id: Optional[str] = None,
    ) -> Optional[StockBalanceInDB]:
        pass

    @abstractmethod
    async def get_by_id(self, stock_id: str, business_id: str) -> Optional[StockBalanceInDB]:
        pass

    @abstractmethod
    async def upsert_balance(
        self,
        business_id: str,
        inventory_location_id: str,
        product_id: str,
        variant_id: Optional[str],
        delta: Decimal,
    ) -> StockBalanceInDB:
        pass

    @abstractmethod
    async def list_balances(
        self,
        business_id: str,
        inventory_location_id: Optional[str] = None,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
    ) -> List[StockBalanceInDB]:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class AbstractStockMovementRepository(ABC):
    @abstractmethod
    async def create_movement(
        self,
        business_id: str,
        movement_type: MovementType,
        performed_by_user_id: str,
        reference_type: Optional[ReferenceType] = None,
        reference_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> StockMovementInDB:
        pass

    @abstractmethod
    async def create_line(
        self,
        movement_id: str,
        inventory_location_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
        direction: MovementDirection,
    ) -> StockMovementLineInDB:
        pass

    @abstractmethod
    async def get_movement_by_id(
        self, movement_id: str, business_id: str
    ) -> Optional[StockMovementInDB]:
        pass

    @abstractmethod
    async def list_lines_for_movement(self, movement_id: str) -> List[StockMovementLineInDB]:
        pass

    @abstractmethod
    async def list_movements(
        self,
        business_id: str,
        movement_type: Optional[MovementType] = None,
        inventory_location_id: Optional[str] = None,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
    ) -> List[StockMovementInDB]:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class AbstractInventoryCostRepository(ABC):
    @abstractmethod
    async def get_cost_state(
        self,
        business_id: str,
        product_id: str,
        variant_id: Optional[str] = None,
    ) -> Optional[InventoryCostStateInDB]:
        pass

    @abstractmethod
    async def update_cost_state(
        self,
        business_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
        total_cost: Decimal,
        unit_cost: Decimal,
    ) -> InventoryCostStateInDB:
        pass

    @abstractmethod
    async def create_cost_movement(
        self,
        business_id: str,
        product_id: str,
        variant_id: Optional[str],
        movement_type: InventoryCostMovementType,
        reference_type: Optional[str],
        reference_id: Optional[str],
        quantity_delta: Decimal,
        cost_delta: Decimal,
        unit_cost_at_time: Decimal,
    ) -> InventoryCostMovementInDB:
        pass

    @abstractmethod
    async def list_cost_states(
        self,
        business_id: str,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
    ) -> List[InventoryCostStateInDB]:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryStockBalanceRepository(AbstractStockBalanceRepository):
    """
    In-memory repository for StockBalance.
    Keyed by unique composite key: business_id:location_id:product_id:(variant_id or NONE)
    """

    _balances: Dict[str, StockBalanceInDB] = {}

    def _composite_key(
        self,
        business_id: str,
        inventory_location_id: str,
        product_id: str,
        variant_id: Optional[str] = None,
    ) -> str:
        var_key = variant_id if variant_id is not None else "NONE"
        return f"{business_id}:{inventory_location_id}:{product_id}:{var_key}"

    async def get_balance(
        self,
        business_id: str,
        inventory_location_id: str,
        product_id: str,
        variant_id: Optional[str] = None,
    ) -> Optional[StockBalanceInDB]:
        key = self._composite_key(business_id, inventory_location_id, product_id, variant_id)
        return self._balances.get(key)

    async def get_by_id(self, stock_id: str, business_id: str) -> Optional[StockBalanceInDB]:
        for sb in self._balances.values():
            if sb.id == stock_id and sb.business_id == business_id:
                return sb
        return None

    async def upsert_balance(
        self,
        business_id: str,
        inventory_location_id: str,
        product_id: str,
        variant_id: Optional[str],
        delta: Decimal,
    ) -> StockBalanceInDB:
        key = self._composite_key(business_id, inventory_location_id, product_id, variant_id)
        now = datetime.now(timezone.utc)
        existing = self._balances.get(key)

        if existing:
            new_qty = existing.quantity + delta
            if new_qty < Decimal("0"):
                raise ValueError("Stock balance cannot be negative")
            updated = StockBalanceInDB(
                id=existing.id,
                business_id=business_id,
                inventory_location_id=inventory_location_id,
                product_id=product_id,
                variant_id=variant_id,
                quantity=new_qty,
                created_at=existing.created_at,
                updated_at=now,
            )
            self._balances[key] = updated
            return updated
        else:
            if delta < Decimal("0"):
                raise ValueError("Stock balance cannot be negative")
            stock_id = str(uuid.uuid4())
            new_balance = StockBalanceInDB(
                id=stock_id,
                business_id=business_id,
                inventory_location_id=inventory_location_id,
                product_id=product_id,
                variant_id=variant_id,
                quantity=delta,
                created_at=now,
                updated_at=now,
            )
            self._balances[key] = new_balance
            return new_balance

    async def list_balances(
        self,
        business_id: str,
        inventory_location_id: Optional[str] = None,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
    ) -> List[StockBalanceInDB]:
        results = []
        for sb in self._balances.values():
            if sb.business_id != business_id:
                continue
            if inventory_location_id and sb.inventory_location_id != inventory_location_id:
                continue
            if product_id and sb.product_id != product_id:
                continue
            if variant_id is not None and sb.variant_id != variant_id:
                continue
            results.append(sb)

        results.sort(key=lambda b: (b.product_id, b.variant_id or "", b.inventory_location_id))
        return results

    @classmethod
    def clear(cls):
        cls._balances.clear()


class InMemoryStockMovementRepository(AbstractStockMovementRepository):
    """
    In-memory repository for StockMovement and StockMovementLine.
    """

    _movements: Dict[str, StockMovementInDB] = {}
    _lines: List[StockMovementLineInDB] = []

    async def create_movement(
        self,
        business_id: str,
        movement_type: MovementType,
        performed_by_user_id: str,
        reference_type: Optional[ReferenceType] = None,
        reference_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> StockMovementInDB:
        movement_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        movement = StockMovementInDB(
            id=movement_id,
            business_id=business_id,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            performed_by_user_id=performed_by_user_id,
            status=MovementStatus.POSTED,
            created_at=now,
        )
        self._movements[movement_id] = movement
        return movement

    async def create_line(
        self,
        movement_id: str,
        inventory_location_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
        direction: MovementDirection,
    ) -> StockMovementLineInDB:
        line_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        line = StockMovementLineInDB(
            id=line_id,
            movement_id=movement_id,
            inventory_location_id=inventory_location_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
            direction=direction,
            created_at=now,
        )
        self._lines.append(line)
        return line

    async def get_movement_by_id(
        self, movement_id: str, business_id: str
    ) -> Optional[StockMovementInDB]:
        m = self._movements.get(movement_id)
        if m and m.business_id == business_id:
            return m
        return None

    async def list_lines_for_movement(self, movement_id: str) -> List[StockMovementLineInDB]:
        return [l for l in self._lines if l.movement_id == movement_id]

    async def list_movements(
        self,
        business_id: str,
        movement_type: Optional[MovementType] = None,
        inventory_location_id: Optional[str] = None,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
    ) -> List[StockMovementInDB]:
        matching_movement_ids = set()

        if inventory_location_id or product_id or variant_id is not None:
            for l in self._lines:
                if inventory_location_id and l.inventory_location_id != inventory_location_id:
                    continue
                if product_id and l.product_id != product_id:
                    continue
                if variant_id is not None and l.variant_id != variant_id:
                    continue
                matching_movement_ids.add(l.movement_id)

        results = []
        for m in self._movements.values():
            if m.business_id != business_id:
                continue
            if movement_type and m.movement_type != movement_type:
                continue
            if (
                inventory_location_id or product_id or variant_id is not None
            ) and m.id not in matching_movement_ids:
                continue
            results.append(m)

        # Sort by created_at DESC
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results

    @classmethod
    def clear(cls):
        cls._movements.clear()
        cls._lines.clear()


stock_balance_repository = InMemoryStockBalanceRepository()
stock_movement_repository = InMemoryStockMovementRepository()


class InMemoryInventoryCostRepository(AbstractInventoryCostRepository):
    """
    In-memory repository for InventoryCostState and InventoryCostMovement.
    Keyed by unique composite key: business_id:product_id:(variant_id or NONE)
    """

    _cost_states: Dict[str, InventoryCostStateInDB] = {}
    _cost_movements: List[InventoryCostMovementInDB] = []

    def _composite_key(
        self,
        business_id: str,
        product_id: str,
        variant_id: Optional[str] = None,
    ) -> str:
        var_key = variant_id if variant_id is not None else "NONE"
        return f"{business_id}:{product_id}:{var_key}"

    async def get_cost_state(
        self,
        business_id: str,
        product_id: str,
        variant_id: Optional[str] = None,
    ) -> Optional[InventoryCostStateInDB]:
        key = self._composite_key(business_id, product_id, variant_id)
        return self._cost_states.get(key)

    async def update_cost_state(
        self,
        business_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
        total_cost: Decimal,
        unit_cost: Decimal,
    ) -> InventoryCostStateInDB:
        key = self._composite_key(business_id, product_id, variant_id)
        now = datetime.now(timezone.utc)
        existing = self._cost_states.get(key)
        cost_id = existing.id if existing else str(uuid.uuid4())
        created_at = existing.created_at if existing else now

        cost_state = InventoryCostStateInDB(
            id=cost_id,
            business_id=business_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
            total_cost=total_cost,
            unit_cost=unit_cost,
            created_at=created_at,
            updated_at=now,
        )
        self._cost_states[key] = cost_state
        return cost_state

    async def create_cost_movement(
        self,
        business_id: str,
        product_id: str,
        variant_id: Optional[str],
        movement_type: InventoryCostMovementType,
        reference_type: Optional[str],
        reference_id: Optional[str],
        quantity_delta: Decimal,
        cost_delta: Decimal,
        unit_cost_at_time: Decimal,
    ) -> InventoryCostMovementInDB:
        mov_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        movement = InventoryCostMovementInDB(
            id=mov_id,
            business_id=business_id,
            product_id=product_id,
            variant_id=variant_id,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            quantity_delta=quantity_delta,
            cost_delta=cost_delta,
            unit_cost_at_time=unit_cost_at_time,
            created_at=now,
        )
        self._cost_movements.append(movement)
        return movement

    async def list_cost_states(
        self,
        business_id: str,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
    ) -> List[InventoryCostStateInDB]:
        results = []
        for cs in self._cost_states.values():
            if cs.business_id != business_id:
                continue
            if product_id and cs.product_id != product_id:
                continue
            if variant_id is not None and cs.variant_id != variant_id:
                continue
            results.append(cs)
        results.sort(key=lambda x: (x.product_id, x.variant_id or ""))
        return results

    @classmethod
    def clear(cls):
        cls._cost_states.clear()
        cls._cost_movements.clear()


inventory_cost_repository = InMemoryInventoryCostRepository()
