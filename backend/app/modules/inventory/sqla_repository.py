import uuid
from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.inventory.models import (
    StockBalance,
    StockMovement,
    StockMovementLine,
    InventoryCostState,
    InventoryCostMovement,
)
from app.modules.inventory.repository import (
    AbstractStockBalanceRepository,
    AbstractStockMovementRepository,
    AbstractInventoryCostRepository,
)
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
from app.modules.sqla_base import sa_create


def _to_stock_balance(obj: StockBalance) -> StockBalanceInDB:
    return StockBalanceInDB(
        id=obj.id,
        business_id=obj.business_id,
        inventory_location_id=obj.inventory_location_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        quantity=obj.quantity,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_movement(obj: StockMovement) -> StockMovementInDB:
    return StockMovementInDB(
        id=obj.id,
        business_id=obj.business_id,
        movement_type=MovementType(obj.movement_type),
        reference_type=ReferenceType(obj.reference_type) if obj.reference_type else None,
        reference_id=obj.reference_id,
        notes=obj.notes,
        performed_by_user_id=obj.performed_by_user_id,
        status=MovementStatus(obj.status),
        created_at=obj.created_at,
    )


def _to_movement_line(obj: StockMovementLine) -> StockMovementLineInDB:
    return StockMovementLineInDB(
        id=obj.id,
        movement_id=obj.movement_id,
        inventory_location_id=obj.inventory_location_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        quantity=obj.quantity,
        direction=MovementDirection(obj.direction),
        created_at=obj.created_at,
    )


def _to_cost_state(obj: InventoryCostState) -> InventoryCostStateInDB:
    return InventoryCostStateInDB(
        id=obj.id,
        business_id=obj.business_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        quantity=obj.quantity,
        total_cost=obj.total_cost,
        unit_cost=obj.unit_cost,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_cost_movement(obj: InventoryCostMovement) -> InventoryCostMovementInDB:
    return InventoryCostMovementInDB(
        id=obj.id,
        business_id=obj.business_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        movement_type=InventoryCostMovementType(obj.movement_type),
        reference_type=obj.reference_type,
        reference_id=obj.reference_id,
        quantity_delta=obj.quantity_delta,
        cost_delta=obj.cost_delta,
        unit_cost_at_time=obj.unit_cost_at_time,
        created_at=obj.created_at,
    )


class SQLAlchemyStockBalanceRepository(AbstractStockBalanceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_balance(
        self,
        business_id: str,
        inventory_location_id: str,
        product_id: str,
        variant_id: Optional[str] = None,
    ) -> Optional[StockBalanceInDB]:
        filters = [
            StockBalance.business_id == business_id,
            StockBalance.inventory_location_id == inventory_location_id,
            StockBalance.product_id == product_id,
        ]
        if variant_id is not None:
            filters.append(StockBalance.variant_id == variant_id)
        else:
            filters.append(StockBalance.variant_id == None)
        stmt = select(StockBalance).where(and_(*filters))
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_stock_balance(obj) if obj else None

    async def get_balance_for_update(
        self,
        business_id: str,
        inventory_location_id: str,
        product_id: str,
        variant_id: Optional[str] = None,
    ) -> Optional[StockBalanceInDB]:
        filters = [
            StockBalance.business_id == business_id,
            StockBalance.inventory_location_id == inventory_location_id,
            StockBalance.product_id == product_id,
        ]
        if variant_id is not None:
            filters.append(StockBalance.variant_id == variant_id)
        else:
            filters.append(StockBalance.variant_id == None)
        stmt = select(StockBalance).where(and_(*filters)).with_for_update()
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_stock_balance(obj) if obj else None

    async def get_by_id(self, stock_id: str, business_id: str) -> Optional[StockBalanceInDB]:
        stmt = select(StockBalance).where(
            StockBalance.id == stock_id,
            StockBalance.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_stock_balance(obj) if obj else None

    async def upsert_balance(
        self,
        business_id: str,
        inventory_location_id: str,
        product_id: str,
        variant_id: Optional[str],
        delta: Decimal,
    ) -> StockBalanceInDB:
        filters = [
            StockBalance.business_id == business_id,
            StockBalance.inventory_location_id == inventory_location_id,
            StockBalance.product_id == product_id,
        ]
        if variant_id is not None:
            filters.append(StockBalance.variant_id == variant_id)
        else:
            filters.append(StockBalance.variant_id == None)

        stmt = select(StockBalance).where(and_(*filters)).with_for_update()
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()

        if obj:
            new_qty = obj.quantity + delta
            if new_qty < Decimal("0"):
                raise ValueError("Stock balance cannot be negative")
            obj.quantity = new_qty
            await self.session.flush()
            return _to_stock_balance(obj)
        else:
            if delta < Decimal("0"):
                raise ValueError("Stock balance cannot be negative")
            try:
                data = {
                    "id": str(uuid.uuid4()),
                    "business_id": business_id,
                    "inventory_location_id": inventory_location_id,
                    "product_id": product_id,
                    "variant_id": variant_id,
                    "quantity": delta,
                }
                obj = await sa_create(self.session, StockBalance, data)
                return _to_stock_balance(obj)
            except Exception:
                # Concurrent insert race condition fallback
                stmt = select(StockBalance).where(and_(*filters)).with_for_update()
                res = await self.session.execute(stmt)
                obj = res.scalar_one_or_none()
                if obj:
                    new_qty = obj.quantity + delta
                    if new_qty < Decimal("0"):
                        raise ValueError("Stock balance cannot be negative")
                    obj.quantity = new_qty
                    await self.session.flush()
                    return _to_stock_balance(obj)
                raise

    async def list_balances(
        self,
        business_id: str,
        inventory_location_id: Optional[str] = None,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
    ) -> List[StockBalanceInDB]:
        filters = [StockBalance.business_id == business_id]
        if inventory_location_id:
            filters.append(StockBalance.inventory_location_id == inventory_location_id)
        if product_id:
            filters.append(StockBalance.product_id == product_id)
        if variant_id is not None:
            filters.append(StockBalance.variant_id == variant_id)
        stmt = (
            select(StockBalance)
            .where(and_(*filters))
            .order_by(asc(StockBalance.product_id), asc(StockBalance.variant_id), asc(StockBalance.inventory_location_id))
        )
        res = await self.session.execute(stmt)
        return [_to_stock_balance(o) for o in res.scalars().all()]

    @classmethod
    def clear(cls):
        pass


class SQLAlchemyStockMovementRepository(AbstractStockMovementRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_movement(
        self,
        business_id: str,
        movement_type: MovementType,
        performed_by_user_id: str,
        reference_type: Optional[ReferenceType] = None,
        reference_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> StockMovementInDB:
        data = {
            "business_id": business_id,
            "movement_type": movement_type.value,
            "reference_type": reference_type.value if reference_type else None,
            "reference_id": reference_id,
            "notes": notes,
            "performed_by_user_id": performed_by_user_id,
            "status": MovementStatus.POSTED.value,
        }
        obj = await sa_create(self.session, StockMovement, data)
        return _to_movement(obj)

    async def create_line(
        self,
        movement_id: str,
        inventory_location_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
        direction: MovementDirection,
    ) -> StockMovementLineInDB:
        data = {
            "movement_id": movement_id,
            "inventory_location_id": inventory_location_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "quantity": quantity,
            "direction": direction.value,
        }
        obj = await sa_create(self.session, StockMovementLine, data)
        return _to_movement_line(obj)

    async def get_movement_by_id(
        self, movement_id: str, business_id: str
    ) -> Optional[StockMovementInDB]:
        stmt = select(StockMovement).where(
            StockMovement.id == movement_id,
            StockMovement.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_movement(obj) if obj else None

    async def list_lines_for_movement(self, movement_id: str) -> List[StockMovementLineInDB]:
        stmt = select(StockMovementLine).where(StockMovementLine.movement_id == movement_id)
        res = await self.session.execute(stmt)
        return [_to_movement_line(l) for l in res.scalars().all()]

    async def list_movements(
        self,
        business_id: str,
        movement_type: Optional[MovementType] = None,
        inventory_location_id: Optional[str] = None,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
    ) -> List[StockMovementInDB]:
        filters = [StockMovement.business_id == business_id]
        if movement_type:
            filters.append(StockMovement.movement_type == movement_type.value)

        if inventory_location_id or product_id or variant_id is not None:
            line_filters = []
            if inventory_location_id:
                line_filters.append(StockMovementLine.inventory_location_id == inventory_location_id)
            if product_id:
                line_filters.append(StockMovementLine.product_id == product_id)
            if variant_id is not None:
                line_filters.append(StockMovementLine.variant_id == variant_id)

            subq = select(StockMovementLine.movement_id).where(and_(*line_filters)).distinct()
            filters.append(StockMovement.id.in_(subq))

        stmt = select(StockMovement).where(and_(*filters)).order_by(desc(StockMovement.created_at))
        res = await self.session.execute(stmt)
        return [_to_movement(o) for o in res.scalars().all()]

    @classmethod
    def clear(cls):
        pass


class SQLAlchemyInventoryCostRepository(AbstractInventoryCostRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_cost_state(
        self,
        business_id: str,
        product_id: str,
        variant_id: Optional[str] = None,
    ) -> Optional[InventoryCostStateInDB]:
        filters = [
            InventoryCostState.business_id == business_id,
            InventoryCostState.product_id == product_id,
        ]
        if variant_id is not None:
            filters.append(InventoryCostState.variant_id == variant_id)
        else:
            filters.append(InventoryCostState.variant_id == None)
        stmt = select(InventoryCostState).where(and_(*filters))
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_cost_state(obj) if obj else None

    async def update_cost_state(
        self,
        business_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
        total_cost: Decimal,
        unit_cost: Decimal,
    ) -> InventoryCostStateInDB:
        filters = [
            InventoryCostState.business_id == business_id,
            InventoryCostState.product_id == product_id,
        ]
        if variant_id is not None:
            filters.append(InventoryCostState.variant_id == variant_id)
        else:
            filters.append(InventoryCostState.variant_id == None)

        stmt = select(InventoryCostState).where(and_(*filters)).with_for_update()
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()

        if obj:
            obj.quantity = quantity
            obj.total_cost = total_cost
            obj.unit_cost = unit_cost
            await self.session.flush()
            return _to_cost_state(obj)

        try:
            data = {
                "id": str(uuid.uuid4()),
                "business_id": business_id,
                "product_id": product_id,
                "variant_id": variant_id,
                "quantity": quantity,
                "total_cost": total_cost,
                "unit_cost": unit_cost,
            }
            obj = await sa_create(self.session, InventoryCostState, data)
            return _to_cost_state(obj)
        except Exception:
            stmt = select(InventoryCostState).where(and_(*filters)).with_for_update()
            res = await self.session.execute(stmt)
            obj = res.scalar_one_or_none()
            if obj:
                obj.quantity = quantity
                obj.total_cost = total_cost
                obj.unit_cost = unit_cost
                await self.session.flush()
                return _to_cost_state(obj)
            raise

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
        data = {
            "business_id": business_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "movement_type": movement_type.value,
            "reference_type": reference_type,
            "reference_id": reference_id,
            "quantity_delta": quantity_delta,
            "cost_delta": cost_delta,
            "unit_cost_at_time": unit_cost_at_time,
        }
        obj = await sa_create(self.session, InventoryCostMovement, data)
        return _to_cost_movement(obj)

    async def list_cost_states(
        self,
        business_id: str,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
    ) -> List[InventoryCostStateInDB]:
        filters = [InventoryCostState.business_id == business_id]
        if product_id:
            filters.append(InventoryCostState.product_id == product_id)
        if variant_id is not None:
            filters.append(InventoryCostState.variant_id == variant_id)
        stmt = (
            select(InventoryCostState)
            .where(and_(*filters))
            .order_by(asc(InventoryCostState.product_id), asc(InventoryCostState.variant_id))
        )
        res = await self.session.execute(stmt)
        return [_to_cost_state(o) for o in res.scalars().all()]

    @classmethod
    def clear(cls):
        pass
