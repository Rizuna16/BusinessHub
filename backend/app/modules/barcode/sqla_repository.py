from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func, and_, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.barcode.models import Barcode
from app.modules.barcode.repository import AbstractBarcodeRepository, BarcodeInDB
from app.modules.barcode.schemas import (
    BarcodeCreate,
    BarcodeUpdate,
    BarcodeStatus,
    BarcodeType,
)
from app.modules.sqla_base import sa_create


def _to_barcode_in_db(obj: Barcode) -> BarcodeInDB:
    return BarcodeInDB(
        id=obj.id,
        business_id=obj.business_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        code=obj.code,
        barcode_type=BarcodeType(obj.barcode_type),
        status=BarcodeStatus(obj.status),
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyBarcodeRepository(AbstractBarcodeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, business_id: str, data: BarcodeCreate) -> BarcodeInDB:
        create_data = {
            "business_id": business_id,
            "product_id": data.product_id,
            "variant_id": data.variant_id,
            "code": data.code,
            "barcode_type": data.barcode_type.value,
            "status": BarcodeStatus.ACTIVE.value,
        }
        obj = await sa_create(self.session, Barcode, create_data)
        return _to_barcode_in_db(obj)

    async def get_by_id(self, barcode_id: str, business_id: str) -> Optional[BarcodeInDB]:
        stmt = select(Barcode).where(
            Barcode.id == barcode_id,
            Barcode.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_barcode_in_db(obj) if obj else None

    async def list_by_business(
        self,
        business_id: str,
        include_archived: bool = False,
    ) -> List[BarcodeInDB]:
        filters = [Barcode.business_id == business_id]
        if not include_archived:
            filters.append(Barcode.status != BarcodeStatus.ARCHIVED.value)
        stmt = (
            select(Barcode)
            .where(and_(*filters))
            .order_by(asc(Barcode.created_at), asc(Barcode.id))
        )
        result = await self.session.execute(stmt)
        return [_to_barcode_in_db(o) for o in result.scalars().all()]

    async def list_by_product(self, business_id: str, product_id: str) -> List[BarcodeInDB]:
        stmt = select(Barcode).where(
            Barcode.business_id == business_id,
            Barcode.product_id == product_id,
            Barcode.status == BarcodeStatus.ACTIVE.value,
        )
        result = await self.session.execute(stmt)
        return [_to_barcode_in_db(o) for o in result.scalars().all()]

    async def list_by_variant(self, business_id: str, variant_id: str) -> List[BarcodeInDB]:
        stmt = select(Barcode).where(
            Barcode.business_id == business_id,
            Barcode.variant_id == variant_id,
            Barcode.status == BarcodeStatus.ACTIVE.value,
        )
        result = await self.session.execute(stmt)
        return [_to_barcode_in_db(o) for o in result.scalars().all()]

    async def update(
        self,
        barcode_id: str,
        business_id: str,
        data: BarcodeUpdate,
    ) -> Optional[BarcodeInDB]:
        stmt = select(Barcode).where(
            Barcode.id == barcode_id,
            Barcode.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        update_dict = data.model_dump(exclude_unset=True)
        if not update_dict:
            return _to_barcode_in_db(obj)
        for field, value in update_dict.items():
            if value is not None:
                setattr(obj, field, value)
        await self.session.flush()
        return _to_barcode_in_db(obj)

    async def archive(self, barcode_id: str, business_id: str) -> Optional[BarcodeInDB]:
        stmt = select(Barcode).where(
            Barcode.id == barcode_id,
            Barcode.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.status = BarcodeStatus.ARCHIVED.value
        await self.session.flush()
        return _to_barcode_in_db(obj)

    async def find_by_code(self, business_id: str, code: str) -> Optional[BarcodeInDB]:
        stmt = select(Barcode).where(
            Barcode.business_id == business_id,
            func.lower(Barcode.code) == code.lower(),
            Barcode.status == BarcodeStatus.ACTIVE.value,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_barcode_in_db(obj) if obj else None

    async def exists(self, barcode_id: str, business_id: str) -> bool:
        stmt = select(func.count()).select_from(Barcode).where(
            Barcode.id == barcode_id,
            Barcode.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    @classmethod
    def clear(cls):
        pass
