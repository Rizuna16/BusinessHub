from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.warehouse.models import Warehouse, InventoryLocation
from app.modules.warehouse.repository import AbstractWarehouseRepository, AbstractInventoryLocationRepository
from app.modules.warehouse.schemas import (
    WarehouseInDB,
    WarehouseCreate,
    WarehouseUpdate,
    WarehouseStatus,
    InventoryLocationInDB,
    InventoryLocationCreate,
    InventoryLocationUpdate,
    InventoryLocationStatus,
)
from app.modules.sqla_base import sa_create


def _to_warehouse(obj: Warehouse) -> WarehouseInDB:
    return WarehouseInDB(
        id=obj.id,
        business_id=obj.business_id,
        branch_id=obj.branch_id,
        name=obj.name,
        code=obj.code,
        description=obj.description,
        address=obj.address,
        phone=obj.phone,
        email=obj.email,
        status=WarehouseStatus(obj.status),
        is_default=obj.is_default,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_location(obj: InventoryLocation) -> InventoryLocationInDB:
    return InventoryLocationInDB(
        id=obj.id,
        business_id=obj.business_id,
        warehouse_id=obj.warehouse_id,
        name=obj.name,
        code=obj.code,
        description=obj.description,
        location_type=obj.location_type,
        status=InventoryLocationStatus(obj.status),
        is_default=obj.is_default,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyWarehouseRepository(AbstractWarehouseRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, business_id: str, warehouse_data: WarehouseCreate, is_default: bool = False
    ) -> WarehouseInDB:
        data = {
            "business_id": business_id,
            "branch_id": warehouse_data.branch_id,
            "name": warehouse_data.name.strip(),
            "code": warehouse_data.code.strip().upper(),
            "description": warehouse_data.description,
            "address": warehouse_data.address,
            "phone": warehouse_data.phone,
            "email": warehouse_data.email,
            "status": WarehouseStatus.ACTIVE.value,
            "is_default": is_default,
        }
        obj = await sa_create(self.session, Warehouse, data)
        return _to_warehouse(obj)

    async def get_by_id(self, warehouse_id: str) -> Optional[WarehouseInDB]:
        stmt = select(Warehouse).where(Warehouse.id == warehouse_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_warehouse(obj) if obj else None

    async def list_by_business(self, business_id: str) -> List[WarehouseInDB]:
        stmt = (
            select(Warehouse)
            .where(Warehouse.business_id == business_id)
            .order_by(
                desc(Warehouse.is_default),
                asc(Warehouse.status),
                asc(Warehouse.created_at),
                asc(Warehouse.id),
            )
        )
        res = await self.session.execute(stmt)
        return [_to_warehouse(o) for o in res.scalars().all()]

    async def list_by_branch(self, business_id: str, branch_id: str) -> List[WarehouseInDB]:
        stmt = (
            select(Warehouse)
            .where(Warehouse.business_id == business_id, Warehouse.branch_id == branch_id)
            .order_by(
                desc(Warehouse.is_default),
                asc(Warehouse.status),
                asc(Warehouse.created_at),
                asc(Warehouse.id),
            )
        )
        res = await self.session.execute(stmt)
        return [_to_warehouse(o) for o in res.scalars().all()]

    async def update(
        self, warehouse_id: str, update_data: WarehouseUpdate
    ) -> Optional[WarehouseInDB]:
        stmt = select(Warehouse).where(Warehouse.id == warehouse_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return _to_warehouse(obj)
        for field, value in update_dict.items():
            setattr(obj, field, value)
        await self.session.flush()
        return _to_warehouse(obj)

    async def suspend(self, warehouse_id: str) -> Optional[WarehouseInDB]:
        stmt = select(Warehouse).where(Warehouse.id == warehouse_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        obj.status = WarehouseStatus.SUSPENDED.value
        obj.is_default = False
        await self.session.flush()
        return _to_warehouse(obj)

    async def activate(self, warehouse_id: str) -> Optional[WarehouseInDB]:
        stmt = select(Warehouse).where(Warehouse.id == warehouse_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        obj.status = WarehouseStatus.ACTIVE.value
        await self.session.flush()
        return _to_warehouse(obj)

    async def archive(self, warehouse_id: str) -> Optional[WarehouseInDB]:
        stmt = select(Warehouse).where(Warehouse.id == warehouse_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        obj.status = WarehouseStatus.ARCHIVED.value
        obj.is_default = False
        await self.session.flush()
        return _to_warehouse(obj)

    async def find_by_code(self, business_id: str, code: str) -> Optional[WarehouseInDB]:
        norm = code.strip().upper()
        stmt = select(Warehouse).where(
            Warehouse.business_id == business_id,
            func.upper(Warehouse.code) == norm,
            Warehouse.status != WarehouseStatus.ARCHIVED.value,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_warehouse(obj) if obj else None

    async def exists_by_code(self, business_id: str, code: str) -> bool:
        return (await self.find_by_code(business_id, code)) is not None

    async def get_default(self, business_id: str) -> Optional[WarehouseInDB]:
        stmt = select(Warehouse).where(
            Warehouse.business_id == business_id,
            Warehouse.is_default == True,
            Warehouse.status == WarehouseStatus.ACTIVE.value,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_warehouse(obj) if obj else None

    async def set_default(self, business_id: str, warehouse_id: str) -> Optional[WarehouseInDB]:
        # Unset existing default
        stmt = select(Warehouse).where(
            Warehouse.business_id == business_id,
            Warehouse.is_default == True,
        )
        res = await self.session.execute(stmt)
        for wh in res.scalars().all():
            wh.is_default = False

        # Set new default
        stmt2 = select(Warehouse).where(
            Warehouse.id == warehouse_id,
            Warehouse.business_id == business_id,
        )
        res2 = await self.session.execute(stmt2)
        obj = res2.scalar_one_or_none()
        if not obj:
            return None
        obj.is_default = True
        await self.session.flush()
        return _to_warehouse(obj)

    async def count_active(self, business_id: str) -> int:
        stmt = select(func.count()).select_from(Warehouse).where(
            Warehouse.business_id == business_id,
            Warehouse.status == WarehouseStatus.ACTIVE.value,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one() or 0

    @classmethod
    def clear(cls):
        pass


class SQLAlchemyInventoryLocationRepository(AbstractInventoryLocationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, business_id: str, warehouse_id: str, location_data: InventoryLocationCreate, is_default: bool = False
    ) -> InventoryLocationInDB:
        data = {
            "business_id": business_id,
            "warehouse_id": warehouse_id,
            "name": location_data.name.strip(),
            "code": location_data.code.strip().upper(),
            "description": location_data.description,
            "location_type": location_data.location_type.value,
            "status": InventoryLocationStatus.ACTIVE.value,
            "is_default": is_default,
        }
        obj = await sa_create(self.session, InventoryLocation, data)
        return _to_location(obj)

    async def get_by_id(self, location_id: str) -> Optional[InventoryLocationInDB]:
        stmt = select(InventoryLocation).where(InventoryLocation.id == location_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_location(obj) if obj else None

    async def list_by_business(self, business_id: str) -> List[InventoryLocationInDB]:
        stmt = (
            select(InventoryLocation)
            .where(InventoryLocation.business_id == business_id)
            .order_by(
                desc(InventoryLocation.is_default),
                asc(InventoryLocation.status),
                asc(InventoryLocation.created_at),
                asc(InventoryLocation.id),
            )
        )
        res = await self.session.execute(stmt)
        return [_to_location(o) for o in res.scalars().all()]

    async def list_by_warehouse(self, warehouse_id: str, include_archived: bool = False) -> List[InventoryLocationInDB]:
        filters = [InventoryLocation.warehouse_id == warehouse_id]
        if not include_archived:
            filters.append(InventoryLocation.status != InventoryLocationStatus.ARCHIVED.value)
        stmt = (
            select(InventoryLocation)
            .where(and_(*filters))
            .order_by(
                desc(InventoryLocation.is_default),
                asc(InventoryLocation.status),
                asc(InventoryLocation.created_at),
                asc(InventoryLocation.id),
            )
        )
        res = await self.session.execute(stmt)
        return [_to_location(o) for o in res.scalars().all()]

    async def update(
        self, location_id: str, update_data: InventoryLocationUpdate
    ) -> Optional[InventoryLocationInDB]:
        stmt = select(InventoryLocation).where(InventoryLocation.id == location_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return _to_location(obj)
        for field, value in update_dict.items():
            if field == "location_type" and value is not None:
                setattr(obj, field, value.value if hasattr(value, "value") else value)
            else:
                setattr(obj, field, value)
        await self.session.flush()
        return _to_location(obj)

    async def archive(self, location_id: str) -> Optional[InventoryLocationInDB]:
        stmt = select(InventoryLocation).where(InventoryLocation.id == location_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        obj.status = InventoryLocationStatus.ARCHIVED.value
        obj.is_default = False
        await self.session.flush()
        return _to_location(obj)

    async def find_by_code(self, warehouse_id: str, code: str) -> Optional[InventoryLocationInDB]:
        norm = code.strip().upper()
        stmt = select(InventoryLocation).where(
            InventoryLocation.warehouse_id == warehouse_id,
            func.upper(InventoryLocation.code) == norm,
            InventoryLocation.status != InventoryLocationStatus.ARCHIVED.value,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_location(obj) if obj else None

    async def exists_by_code(self, warehouse_id: str, code: str) -> bool:
        return (await self.find_by_code(warehouse_id, code)) is not None

    async def get_default(self, warehouse_id: str) -> Optional[InventoryLocationInDB]:
        stmt = select(InventoryLocation).where(
            InventoryLocation.warehouse_id == warehouse_id,
            InventoryLocation.is_default == True,
            InventoryLocation.status == InventoryLocationStatus.ACTIVE.value,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_location(obj) if obj else None

    async def set_default(self, warehouse_id: str, location_id: str) -> Optional[InventoryLocationInDB]:
        # Unset existing default
        stmt = select(InventoryLocation).where(
            InventoryLocation.warehouse_id == warehouse_id,
            InventoryLocation.is_default == True,
        )
        res = await self.session.execute(stmt)
        for loc in res.scalars().all():
            loc.is_default = False

        # Set new default
        stmt2 = select(InventoryLocation).where(InventoryLocation.id == location_id)
        res2 = await self.session.execute(stmt2)
        obj = res2.scalar_one_or_none()
        if not obj:
            return None
        obj.is_default = True
        await self.session.flush()
        return _to_location(obj)

    async def count_active(self, warehouse_id: str) -> int:
        stmt = select(func.count()).select_from(InventoryLocation).where(
            InventoryLocation.warehouse_id == warehouse_id,
            InventoryLocation.status == InventoryLocationStatus.ACTIVE.value,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one() or 0

    @classmethod
    def clear(cls):
        pass
