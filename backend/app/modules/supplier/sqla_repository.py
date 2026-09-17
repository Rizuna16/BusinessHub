from datetime import datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy import select, func, and_, or_, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.supplier.models import Supplier
from app.modules.supplier.repository import AbstractSupplierRepository, SupplierInDB
from app.modules.supplier.schemas import (
    SupplierCreate,
    SupplierUpdate,
    SupplierStatus,
    SupplierType,
)
from app.modules.sqla_base import sa_create


def _to_supplier_in_db(obj: Supplier) -> SupplierInDB:
    return SupplierInDB(
        id=obj.id,
        business_id=obj.business_id,
        supplier_type=SupplierType(obj.supplier_type),
        code=obj.code,
        name=obj.name,
        legal_name=obj.legal_name,
        phone=obj.phone,
        email=obj.email,
        address=obj.address,
        city=obj.city,
        province=obj.province,
        postal_code=obj.postal_code,
        country=obj.country,
        notes=obj.notes,
        status=SupplierStatus(obj.status),
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemySupplierRepository(AbstractSupplierRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        business_id: str,
        supplier_data: SupplierCreate,
        code: str,
    ) -> SupplierInDB:
        data = {
            "business_id": business_id,
            "supplier_type": supplier_data.supplier_type.value,
            "code": code.strip().upper(),
            "name": supplier_data.name,
            "legal_name": supplier_data.legal_name,
            "phone": supplier_data.phone,
            "email": supplier_data.email,
            "address": supplier_data.address,
            "city": supplier_data.city,
            "province": supplier_data.province,
            "postal_code": supplier_data.postal_code,
            "country": supplier_data.country,
            "notes": supplier_data.notes,
            "status": SupplierStatus.ACTIVE.value,
        }
        obj = await sa_create(self.session, Supplier, data)
        return _to_supplier_in_db(obj)

    async def get_by_id(self, supplier_id: str, business_id: str) -> Optional[SupplierInDB]:
        stmt = select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_supplier_in_db(obj) if obj else None

    async def list_by_business(
        self,
        business_id: str,
        search: Optional[str] = None,
        status: Optional[SupplierStatus] = None,
        supplier_type: Optional[SupplierType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[SupplierInDB], int]:
        filters = [Supplier.business_id == business_id]
        if status is not None:
            filters.append(Supplier.status == status.value)
        if supplier_type is not None:
            filters.append(Supplier.supplier_type == supplier_type.value)
        if search is not None and search.strip():
            q = f"%{search.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(Supplier.code).like(q),
                    func.lower(Supplier.name).like(q),
                    func.lower(Supplier.legal_name).like(q),
                    func.lower(Supplier.phone).like(q),
                    func.lower(Supplier.email).like(q),
                )
            )

        count_stmt = select(func.count()).select_from(Supplier).where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Supplier)
            .where(and_(*filters))
            .order_by(asc(Supplier.created_at), asc(Supplier.id))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        result = await self.session.execute(stmt)
        items = [_to_supplier_in_db(o) for o in result.scalars().all()]
        return items, total

    async def update(
        self,
        supplier_id: str,
        business_id: str,
        update_data: SupplierUpdate,
    ) -> Optional[SupplierInDB]:
        stmt = select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return _to_supplier_in_db(obj)
        for field, value in update_dict.items():
            setattr(obj, field, value)
        await self.session.flush()
        return _to_supplier_in_db(obj)

    async def update_status(
        self,
        supplier_id: str,
        business_id: str,
        status: SupplierStatus,
    ) -> Optional[SupplierInDB]:
        stmt = select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.status = status.value
        await self.session.flush()
        return _to_supplier_in_db(obj)

    async def find_by_code(self, business_id: str, code: str) -> Optional[SupplierInDB]:
        norm = code.strip().upper()
        stmt = select(Supplier).where(
            Supplier.business_id == business_id,
            Supplier.code == norm,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_supplier_in_db(obj) if obj else None

    async def count_by_business(self, business_id: str) -> int:
        stmt = select(func.count()).select_from(Supplier).where(
            Supplier.business_id == business_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    @classmethod
    def clear(cls):
        pass
