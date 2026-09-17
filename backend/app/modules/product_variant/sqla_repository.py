from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.product_variant.models import ProductVariant
from app.modules.product_variant.repository import AbstractProductVariantRepository, ProductVariantInDB
from app.modules.product_variant.schemas import (
    ProductVariantCreate,
    ProductVariantUpdate,
    ProductVariantStatus,
)
from app.modules.sqla_base import sa_create


def _to_variant_in_db(obj: ProductVariant) -> ProductVariantInDB:
    return ProductVariantInDB(
        id=obj.id,
        business_id=obj.business_id,
        product_id=obj.product_id,
        name=obj.name,
        code=obj.code,
        attributes=obj.attributes,
        status=ProductVariantStatus(obj.status),
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyProductVariantRepository(AbstractProductVariantRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        business_id: str,
        product_id: str,
        variant_data: ProductVariantCreate,
    ) -> ProductVariantInDB:
        data = {
            "business_id": business_id,
            "product_id": product_id,
            "name": variant_data.name.strip(),
            "code": variant_data.code.strip().upper(),
            "attributes": variant_data.attributes,
            "status": ProductVariantStatus.ACTIVE.value,
        }
        obj = await sa_create(self.session, ProductVariant, data)
        return _to_variant_in_db(obj)

    async def get_by_id(
        self, variant_id: str, business_id: str
    ) -> Optional[ProductVariantInDB]:
        stmt = select(ProductVariant).where(
            ProductVariant.id == variant_id,
            ProductVariant.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_variant_in_db(obj) if obj else None

    async def list_by_product(
        self,
        business_id: str,
        product_id: str,
        include_archived: bool = False,
    ) -> List[ProductVariantInDB]:
        filters = [
            ProductVariant.business_id == business_id,
            ProductVariant.product_id == product_id,
        ]
        if not include_archived:
            filters.append(ProductVariant.status != ProductVariantStatus.ARCHIVED.value)
        stmt = (
            select(ProductVariant)
            .where(and_(*filters))
            .order_by(asc(ProductVariant.name), asc(ProductVariant.code), asc(ProductVariant.id))
        )
        result = await self.session.execute(stmt)
        return [_to_variant_in_db(o) for o in result.scalars().all()]

    async def list_by_business(
        self,
        business_id: str,
        include_archived: bool = False,
    ) -> List[ProductVariantInDB]:
        filters = [ProductVariant.business_id == business_id]
        if not include_archived:
            filters.append(ProductVariant.status != ProductVariantStatus.ARCHIVED.value)
        stmt = (
            select(ProductVariant)
            .where(and_(*filters))
            .order_by(asc(ProductVariant.name), asc(ProductVariant.code), asc(ProductVariant.id))
        )
        result = await self.session.execute(stmt)
        return [_to_variant_in_db(o) for o in result.scalars().all()]

    async def update(
        self,
        variant_id: str,
        business_id: str,
        update_data: ProductVariantUpdate,
    ) -> Optional[ProductVariantInDB]:
        stmt = select(ProductVariant).where(
            ProductVariant.id == variant_id,
            ProductVariant.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return _to_variant_in_db(obj)
        for field, value in update_dict.items():
            if field == "code" and value is not None:
                setattr(obj, field, value.strip().upper())
            elif field == "name" and value is not None:
                setattr(obj, field, value.strip())
            else:
                setattr(obj, field, value)
        await self.session.flush()
        return _to_variant_in_db(obj)

    async def archive(
        self, variant_id: str, business_id: str
    ) -> Optional[ProductVariantInDB]:
        stmt = select(ProductVariant).where(
            ProductVariant.id == variant_id,
            ProductVariant.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.status = ProductVariantStatus.ARCHIVED.value
        await self.session.flush()
        return _to_variant_in_db(obj)

    async def find_by_code(
        self, business_id: str, code: str
    ) -> Optional[ProductVariantInDB]:
        norm = code.strip().upper()
        stmt = select(ProductVariant).where(
            ProductVariant.business_id == business_id,
            ProductVariant.code == norm,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_variant_in_db(obj) if obj else None

    async def exists(self, variant_id: str, business_id: str) -> bool:
        stmt = select(func.count()).select_from(ProductVariant).where(
            ProductVariant.id == variant_id,
            ProductVariant.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    @classmethod
    def clear(cls):
        pass
