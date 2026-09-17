from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.stock_opname.models import (
    StockOpnameInDB as StockOpnameModel,
    StockOpnameLineInDB as StockOpnameLineModel,
)
from app.modules.stock_opname.repository import AbstractStockOpnameRepository
from app.modules.stock_opname.schemas import (
    StockOpnameInDB,
    StockOpnameLineInDB,
    StockOpnameStatus,
)
from app.modules.sqla_base import sa_create


def _to_opname(obj: StockOpnameModel) -> StockOpnameInDB:
    return StockOpnameInDB(
        id=obj.id,
        business_id=obj.business_id,
        inventory_location_id=obj.inventory_location_id,
        status=StockOpnameStatus(obj.status),
        notes=obj.notes,
        created_by_user_id=obj.created_by_user_id,
        finalized_by_user_id=obj.finalized_by_user_id,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        finalized_at=obj.finalized_at,
    )


def _to_opname_line(obj: StockOpnameLineModel) -> StockOpnameLineInDB:
    return StockOpnameLineInDB(
        id=obj.id,
        opname_id=obj.opname_id,
        inventory_location_id=obj.inventory_location_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        system_quantity=obj.system_quantity,
        counted_quantity=obj.counted_quantity,
        variance=obj.variance,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyStockOpnameRepository(AbstractStockOpnameRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_opname(
        self,
        business_id: str,
        inventory_location_id: str,
        created_by_user_id: str,
        notes: Optional[str] = None,
    ) -> StockOpnameInDB:
        data = {
            "business_id": business_id,
            "inventory_location_id": inventory_location_id,
            "status": StockOpnameStatus.DRAFT.value,
            "notes": notes,
            "created_by_user_id": created_by_user_id,
        }
        obj = await sa_create(self.session, StockOpnameModel, data)
        return _to_opname(obj)

    async def get_opname_by_id(
        self, opname_id: str, business_id: str
    ) -> Optional[StockOpnameInDB]:
        stmt = select(StockOpnameModel).where(
            StockOpnameModel.id == opname_id,
            StockOpnameModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_opname(obj) if obj else None

    async def list_opnames(
        self,
        business_id: str,
        status: Optional[StockOpnameStatus] = None,
        inventory_location_id: Optional[str] = None,
    ) -> List[StockOpnameInDB]:
        filters = [StockOpnameModel.business_id == business_id]
        if status:
            filters.append(StockOpnameModel.status == status.value)
        if inventory_location_id:
            filters.append(StockOpnameModel.inventory_location_id == inventory_location_id)
        stmt = select(StockOpnameModel).where(and_(*filters)).order_by(desc(StockOpnameModel.created_at))
        res = await self.session.execute(stmt)
        return [_to_opname(o) for o in res.scalars().all()]

    async def update_opname_status(
        self,
        opname_id: str,
        business_id: str,
        status: StockOpnameStatus,
        finalized_by_user_id: str,
        finalized_at: datetime,
    ) -> Optional[StockOpnameInDB]:
        stmt = select(StockOpnameModel).where(
            StockOpnameModel.id == opname_id,
            StockOpnameModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        obj.status = status.value
        obj.finalized_by_user_id = finalized_by_user_id
        obj.finalized_at = finalized_at
        await self.session.flush()
        return _to_opname(obj)

    async def delete_opname(self, opname_id: str, business_id: str) -> bool:
        obj = await self.get_opname_by_id(opname_id, business_id)
        if not obj:
            return False
        # Delete lines first
        line_stmt = select(StockOpnameLineModel).where(StockOpnameLineModel.opname_id == opname_id)
        line_res = await self.session.execute(line_stmt)
        for l in line_res.scalars().all():
            await self.session.delete(l)

        stmt = select(StockOpnameModel).where(StockOpnameModel.id == opname_id)
        res = await self.session.execute(stmt)
        model_obj = res.scalar_one_or_none()
        if model_obj:
            await self.session.delete(model_obj)
            await self.session.flush()
            return True
        return False

    async def create_line(
        self,
        opname_id: str,
        inventory_location_id: str,
        product_id: str,
        variant_id: Optional[str],
        system_quantity: Decimal,
    ) -> StockOpnameLineInDB:
        data = {
            "opname_id": opname_id,
            "inventory_location_id": inventory_location_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "system_quantity": system_quantity,
        }
        obj = await sa_create(self.session, StockOpnameLineModel, data)
        return _to_opname_line(obj)

    async def get_line_by_id(
        self, line_id: str, opname_id: str
    ) -> Optional[StockOpnameLineInDB]:
        stmt = select(StockOpnameLineModel).where(
            StockOpnameLineModel.id == line_id,
            StockOpnameLineModel.opname_id == opname_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_opname_line(obj) if obj else None

    async def list_lines_for_opname(self, opname_id: str) -> List[StockOpnameLineInDB]:
        stmt = select(StockOpnameLineModel).where(
            StockOpnameLineModel.opname_id == opname_id
        ).order_by(asc(StockOpnameLineModel.created_at))
        res = await self.session.execute(stmt)
        return [_to_opname_line(l) for l in res.scalars().all()]

    async def update_line_count(
        self,
        line_id: str,
        opname_id: str,
        counted_quantity: Decimal,
        variance: Decimal,
    ) -> Optional[StockOpnameLineInDB]:
        stmt = select(StockOpnameLineModel).where(
            StockOpnameLineModel.id == line_id,
            StockOpnameLineModel.opname_id == opname_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        obj.counted_quantity = counted_quantity
        obj.variance = variance
        await self.session.flush()
        return _to_opname_line(obj)

    async def delete_line(self, line_id: str, opname_id: str) -> bool:
        stmt = select(StockOpnameLineModel).where(
            StockOpnameLineModel.id == line_id,
            StockOpnameLineModel.opname_id == opname_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True

    @classmethod
    def clear(cls):
        pass
