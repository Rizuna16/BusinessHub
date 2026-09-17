from datetime import datetime, timezone
from typing import Optional, List, Tuple
from decimal import Decimal

from sqlalchemy import select, func, and_, desc, asc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.supplier_catalog.models import SupplierCatalogItem
from app.modules.supplier_catalog.repository import (
    AbstractSupplierCatalogRepository,
    SupplierCatalogItemInDB,
)
from app.modules.supplier_catalog.schemas import (
    SupplierCatalogItemCreate,
    SupplierCatalogItemUpdate,
    SupplierCatalogStatus,
)
from app.modules.sqla_base import sa_create


def _to_item(obj: SupplierCatalogItem) -> SupplierCatalogItemInDB:
    return SupplierCatalogItemInDB(
        id=obj.id,
        business_id=obj.business_id,
        supplier_id=obj.supplier_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        supplier_code=obj.supplier_code,
        supplier_product_name=obj.supplier_product_name,
        purchase_price=obj.purchase_price,
        currency=obj.currency,
        minimum_order_quantity=obj.minimum_order_quantity,
        lead_time_days=obj.lead_time_days,
        is_preferred=obj.is_preferred,
        status=SupplierCatalogStatus(obj.status),
        notes=obj.notes,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemySupplierCatalogRepository(AbstractSupplierCatalogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        business_id: str,
        item_data: SupplierCatalogItemCreate,
    ) -> SupplierCatalogItemInDB:
        data = {
            "business_id": business_id,
            "supplier_id": item_data.supplier_id,
            "product_id": item_data.product_id,
            "variant_id": item_data.variant_id,
            "supplier_code": item_data.supplier_code,
            "supplier_product_name": item_data.supplier_product_name,
            "purchase_price": item_data.purchase_price,
            "currency": item_data.currency,
            "minimum_order_quantity": item_data.minimum_order_quantity,
            "lead_time_days": item_data.lead_time_days,
            "is_preferred": item_data.is_preferred,
            "status": SupplierCatalogStatus.ACTIVE.value,
            "notes": item_data.notes,
        }
        obj = await sa_create(self.session, SupplierCatalogItem, data)
        return _to_item(obj)

    async def get_by_id(
        self, item_id: str, business_id: str
    ) -> Optional[SupplierCatalogItemInDB]:
        stmt = select(SupplierCatalogItem).where(
            SupplierCatalogItem.id == item_id,
            SupplierCatalogItem.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_item(obj) if obj else None

    async def list_by_business(
        self,
        business_id: str,
        search: Optional[str] = None,
        supplier_id: Optional[str] = None,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
        status: Optional[SupplierCatalogStatus] = None,
        is_preferred: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[SupplierCatalogItemInDB], int]:
        filters = [SupplierCatalogItem.business_id == business_id]
        if supplier_id:
            filters.append(SupplierCatalogItem.supplier_id == supplier_id)
        if product_id:
            filters.append(SupplierCatalogItem.product_id == product_id)
        if variant_id:
            filters.append(SupplierCatalogItem.variant_id == variant_id)
        if status is not None:
            filters.append(SupplierCatalogItem.status == status.value)
        if is_preferred is not None:
            filters.append(SupplierCatalogItem.is_preferred == is_preferred)
        if search:
            s_lower = search.lower()
            filters.append(
                or_(
                    func.lower(SupplierCatalogItem.supplier_code).like(f"%{s_lower}%"),
                    func.lower(SupplierCatalogItem.supplier_product_name).like(f"%{s_lower}%"),
                )
            )

        count_stmt = select(func.count()).select_from(SupplierCatalogItem).where(and_(*filters))
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            select(SupplierCatalogItem)
            .where(and_(*filters))
            .order_by(asc(SupplierCatalogItem.created_at), asc(SupplierCatalogItem.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        res = await self.session.execute(stmt)
        items = [_to_item(o) for o in res.scalars().all()]
        return items, total

    async def update(
        self,
        item_id: str,
        business_id: str,
        update_data: SupplierCatalogItemUpdate,
    ) -> Optional[SupplierCatalogItemInDB]:
        stmt = select(SupplierCatalogItem).where(
            SupplierCatalogItem.id == item_id,
            SupplierCatalogItem.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return _to_item(obj)
        for field, value in update_dict.items():
            setattr(obj, field, value)
        await self.session.flush()
        return _to_item(obj)

    async def update_status(
        self,
        item_id: str,
        business_id: str,
        status: SupplierCatalogStatus,
    ) -> Optional[SupplierCatalogItemInDB]:
        stmt = select(SupplierCatalogItem).where(
            SupplierCatalogItem.id == item_id,
            SupplierCatalogItem.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        obj.status = status.value
        await self.session.flush()
        return _to_item(obj)

    async def unset_preferred_for_target(
        self,
        business_id: str,
        product_id: Optional[str],
        variant_id: Optional[str],
        exclude_item_id: Optional[str] = None,
    ) -> None:
        filters = [
            SupplierCatalogItem.business_id == business_id,
            SupplierCatalogItem.is_preferred == True,
        ]
        if exclude_item_id:
            filters.append(SupplierCatalogItem.id != exclude_item_id)
        if product_id:
            filters.append(SupplierCatalogItem.product_id == product_id)
        elif variant_id:
            filters.append(SupplierCatalogItem.variant_id == variant_id)
        else:
            return
        stmt = select(SupplierCatalogItem).where(and_(*filters))
        res = await self.session.execute(stmt)
        for obj in res.scalars().all():
            obj.is_preferred = False
        # flush only if there were items
        if res.scalars().all():
            await self.session.flush()

    async def find_existing_item(
        self,
        business_id: str,
        supplier_id: str,
        product_id: Optional[str],
        variant_id: Optional[str],
    ) -> Optional[SupplierCatalogItemInDB]:
        filters = [
            SupplierCatalogItem.business_id == business_id,
            SupplierCatalogItem.supplier_id == supplier_id,
        ]
        target_filters = []
        if product_id:
            target_filters.append(SupplierCatalogItem.product_id == product_id)
        if variant_id:
            target_filters.append(SupplierCatalogItem.variant_id == variant_id)
        if target_filters:
            filters.append(or_(*target_filters))

        stmt = select(SupplierCatalogItem).where(and_(*filters))
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_item(obj) if obj else None

    async def find_active_catalog_item(
        self,
        business_id: str,
        supplier_id: str,
        product_id: Optional[str],
        variant_id: Optional[str],
    ) -> Optional[SupplierCatalogItemInDB]:
        filters = [
            SupplierCatalogItem.business_id == business_id,
            SupplierCatalogItem.supplier_id == supplier_id,
            SupplierCatalogItem.status == SupplierCatalogStatus.ACTIVE.value,
        ]
        target_filters = []
        if product_id:
            target_filters.append(SupplierCatalogItem.product_id == product_id)
        if variant_id:
            target_filters.append(SupplierCatalogItem.variant_id == variant_id)
        if target_filters:
            filters.append(or_(*target_filters))

        stmt = select(SupplierCatalogItem).where(and_(*filters))
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_item(obj) if obj else None

    @classmethod
    def clear(cls):
        pass
