from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func, and_, asc, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.unit.models import Unit
from app.modules.unit.repository import AbstractUnitRepository, UnitInDB
from app.modules.unit.schemas import (
    UnitCreate,
    UnitUpdate,
    UnitStatus,
    UnitType,
)
from app.modules.sqla_base import sa_create


def _to_unit_in_db(obj: Unit) -> UnitInDB:
    return UnitInDB(
        id=obj.id,
        business_id=obj.business_id,
        name=obj.name,
        code=obj.code,
        symbol=obj.symbol,
        description=obj.description,
        unit_type=UnitType(obj.unit_type),
        precision=obj.precision,
        status=UnitStatus(obj.status),
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyUnitRepository(AbstractUnitRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        business_id: str,
        unit_data: UnitCreate,
    ) -> UnitInDB:
        data = {
            "business_id": business_id,
            "name": unit_data.name,
            "code": unit_data.code.upper(),
            "symbol": unit_data.symbol,
            "description": unit_data.description,
            "unit_type": unit_data.unit_type.value,
            "precision": unit_data.precision,
            "status": UnitStatus.ACTIVE.value,
        }
        obj = await sa_create(self.session, Unit, data)
        return _to_unit_in_db(obj)

    async def get_by_id(self, unit_id: str, business_id: str) -> Optional[UnitInDB]:
        stmt = select(Unit).where(
            Unit.id == unit_id,
            Unit.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_unit_in_db(obj) if obj else None

    async def list_by_business(
        self,
        business_id: str,
        unit_type: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[UnitInDB]:
        filters = [Unit.business_id == business_id]
        if unit_type is not None:
            filters.append(Unit.unit_type == unit_type)
        if not include_archived:
            filters.append(Unit.status != UnitStatus.ARCHIVED.value)
        stmt = (
            select(Unit)
            .where(and_(*filters))
            .order_by(asc(Unit.name), asc(Unit.code), asc(Unit.id))
        )
        result = await self.session.execute(stmt)
        return [_to_unit_in_db(o) for o in result.scalars().all()]

    async def update(
        self,
        unit_id: str,
        business_id: str,
        update_data: UnitUpdate,
    ) -> Optional[UnitInDB]:
        stmt = select(Unit).where(
            Unit.id == unit_id,
            Unit.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return _to_unit_in_db(obj)
        for field, value in update_dict.items():
            if field == "code" and value is not None:
                setattr(obj, field, value.upper())
            else:
                setattr(obj, field, value)
        await self.session.flush()
        return _to_unit_in_db(obj)

    async def archive(self, unit_id: str, business_id: str) -> Optional[UnitInDB]:
        stmt = select(Unit).where(
            Unit.id == unit_id,
            Unit.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.status = UnitStatus.ARCHIVED.value
        await self.session.flush()
        return _to_unit_in_db(obj)

    async def find_by_code(self, business_id: str, code: str) -> Optional[UnitInDB]:
        norm = code.strip().upper()
        stmt = select(Unit).where(
            Unit.business_id == business_id,
            Unit.code == norm,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_unit_in_db(obj) if obj else None

    async def find_by_name(self, business_id: str, name: str) -> Optional[UnitInDB]:
        norm = name.strip().lower()
        stmt = select(Unit).where(
            Unit.business_id == business_id,
            func.lower(Unit.name) == norm,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_unit_in_db(obj) if obj else None

    async def exists(self, unit_id: str, business_id: str) -> bool:
        stmt = select(func.count()).select_from(Unit).where(
            Unit.id == unit_id,
            Unit.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    @classmethod
    def clear(cls):
        pass
