from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.product_image.models import ProductImage as ProductImageModel
from app.modules.product_image.repository import AbstractProductImageRepository
from app.modules.product_image.schemas import ProductImageInDB
from app.modules.sqla_base import sa_create


def _to_image(obj: ProductImageModel) -> ProductImageInDB:
    return ProductImageInDB(
        id=obj.id,
        business_id=obj.business_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        storage_key=obj.storage_key,
        original_filename=obj.original_filename,
        mime_type=obj.mime_type,
        file_size=obj.file_size,
        width=obj.width,
        height=obj.height,
        sort_order=obj.sort_order,
        is_primary=obj.is_primary,
        status=obj.status,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyProductImageRepository(AbstractProductImageRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, business_id: str, data: dict) -> "ProductImageInDB":
        obj = await sa_create(self.session, ProductImageModel, {
            "business_id": business_id,
            **data,
        })
        return _to_image(obj)

    async def get_by_id(self, image_id: str, business_id: str) -> Optional["ProductImageInDB"]:
        stmt = select(ProductImageModel).where(
            ProductImageModel.id == image_id,
            ProductImageModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_image(obj) if obj else None

    async def list_by_owner(self, business_id: str, product_id: str, variant_id: Optional[str] = None) -> List["ProductImageInDB"]:
        filters = [
            ProductImageModel.business_id == business_id,
            ProductImageModel.product_id == product_id,
            ProductImageModel.status == "ACTIVE",
        ]
        if variant_id is None:
            filters.append(ProductImageModel.variant_id.is_(None))
        else:
            filters.append(ProductImageModel.variant_id == variant_id)
        stmt = select(ProductImageModel).where(and_(*filters)).order_by(
            ProductImageModel.sort_order, ProductImageModel.id
        )
        res = await self.session.execute(stmt)
        return [_to_image(o) for o in res.scalars().all()]

    async def update(self, image_id: str, business_id: str, updates: dict) -> Optional["ProductImageInDB"]:
        stmt = select(ProductImageModel).where(
            ProductImageModel.id == image_id,
            ProductImageModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        for k, v in updates.items():
            if v is not None and hasattr(obj, k):
                setattr(obj, k, v)
        await self.session.flush()
        return _to_image(obj)

    async def delete(self, image_id: str, business_id: str) -> bool:
        stmt = select(ProductImageModel).where(
            ProductImageModel.id == image_id,
            ProductImageModel.business_id == business_id,
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
