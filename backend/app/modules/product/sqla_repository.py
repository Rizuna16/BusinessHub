from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func, and_, or_, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.product.models import Product
from app.modules.product.repository import AbstractProductRepository, ProductInDB
from app.modules.product.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductStatus,
    ProductType,
    ProductTaxTreatment,
)
from app.modules.sqla_base import sa_create


def _to_product_in_db(obj: Product) -> ProductInDB:
    return ProductInDB(
        id=obj.id,
        business_id=obj.business_id,
        category_id=obj.category_id,
        unit_id=obj.unit_id,
        name=obj.name,
        code=obj.code,
        description=obj.description,
        product_type=ProductType(obj.product_type),
        tax_treatment=ProductTaxTreatment(obj.tax_treatment),
        status=ProductStatus(obj.status),
        batch_tracking_enabled=getattr(obj, 'batch_tracking_enabled', False),
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyProductRepository(AbstractProductRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        business_id: str,
        product_data: ProductCreate,
    ) -> ProductInDB:
        data = {
            "business_id": business_id,
            "category_id": product_data.category_id,
            "unit_id": product_data.unit_id,
            "name": product_data.name.strip(),
            "code": product_data.code.strip().upper(),
            "description": product_data.description.strip() if product_data.description else None,
            "product_type": product_data.product_type.value,
            "tax_treatment": product_data.tax_treatment.value,
            "status": ProductStatus.ACTIVE.value,
        }
        obj = await sa_create(self.session, Product, data)
        return _to_product_in_db(obj)

    async def get_by_id(self, product_id: str, business_id: str) -> Optional[ProductInDB]:
        stmt = select(Product).where(
            Product.id == product_id,
            Product.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_product_in_db(obj) if obj else None

    async def list_by_business(
        self,
        business_id: str,
        status: Optional[ProductStatus] = None,
        product_type: Optional[ProductType] = None,
        category_id: Optional[str] = None,
        search: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[ProductInDB]:
        filters = [Product.business_id == business_id]
        if status is not None:
            filters.append(Product.status == status.value)
        elif not include_archived:
            filters.append(Product.status != ProductStatus.ARCHIVED.value)
        if product_type is not None:
            filters.append(Product.product_type == product_type.value)
        if category_id is not None:
            filters.append(Product.category_id == category_id)
        if search is not None and search.strip():
            q = f"%{search.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(Product.code).like(q),
                    func.lower(Product.name).like(q),
                )
            )
        stmt = (
            select(Product)
            .where(and_(*filters))
            .order_by(asc(Product.name), asc(Product.code), asc(Product.id))
        )
        result = await self.session.execute(stmt)
        return [_to_product_in_db(o) for o in result.scalars().all()]

    async def update(
        self,
        product_id: str,
        business_id: str,
        update_data: ProductUpdate,
    ) -> Optional[ProductInDB]:
        stmt = select(Product).where(
            Product.id == product_id,
            Product.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return _to_product_in_db(obj)
        for field, value in update_dict.items():
            if field == "code" and value is not None:
                setattr(obj, field, value.strip().upper())
            elif field == "name" and value is not None:
                setattr(obj, field, value.strip())
            elif field == "description":
                setattr(obj, field, value.strip() if value else None)
            else:
                setattr(obj, field, value)
        await self.session.flush()
        return _to_product_in_db(obj)

    async def archive(self, product_id: str, business_id: str) -> Optional[ProductInDB]:
        stmt = select(Product).where(
            Product.id == product_id,
            Product.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.status = ProductStatus.ARCHIVED.value
        await self.session.flush()
        return _to_product_in_db(obj)

    async def find_by_code(self, business_id: str, code: str) -> Optional[ProductInDB]:
        norm = code.strip().upper()
        stmt = select(Product).where(
            Product.business_id == business_id,
            Product.code == norm,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_product_in_db(obj) if obj else None

    async def exists(self, product_id: str, business_id: str) -> bool:
        stmt = select(func.count()).select_from(Product).where(
            Product.id == product_id,
            Product.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    @classmethod
    def clear(cls):
        pass
