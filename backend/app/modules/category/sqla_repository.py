from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func, and_, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.category.models import Category
from app.modules.category.repository import AbstractCategoryRepository, CategoryInDB
from app.modules.category.schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryStatus,
)
from app.modules.sqla_base import sa_create


def _to_category_in_db(obj: Category) -> CategoryInDB:
    return CategoryInDB(
        id=obj.id,
        business_id=obj.business_id,
        name=obj.name,
        code=obj.code,
        description=obj.description,
        parent_id=obj.parent_id,
        status=CategoryStatus(obj.status),
        sort_order=obj.sort_order,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyCategoryRepository(AbstractCategoryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        business_id: str,
        category_data: CategoryCreate,
    ) -> CategoryInDB:
        data = {
            "business_id": business_id,
            "name": category_data.name,
            "code": category_data.code.upper(),
            "description": category_data.description,
            "parent_id": category_data.parent_id,
            "status": CategoryStatus.ACTIVE.value,
            "sort_order": category_data.sort_order,
        }
        obj = await sa_create(self.session, Category, data)
        return _to_category_in_db(obj)

    async def get_by_id(self, category_id: str, business_id: str) -> Optional[CategoryInDB]:
        stmt = select(Category).where(
            Category.id == category_id,
            Category.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_category_in_db(obj) if obj else None

    async def list_by_business(
        self,
        business_id: str,
        parent_id: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[CategoryInDB]:
        filters = [Category.business_id == business_id]
        if parent_id is not None:
            filters.append(Category.parent_id == parent_id)
        else:
            filters.append(Category.parent_id.is_(None))
        if not include_archived:
            filters.append(Category.status != CategoryStatus.ARCHIVED.value)
        stmt = (
            select(Category)
            .where(and_(*filters))
            .order_by(asc(Category.sort_order), asc(Category.name), asc(Category.id))
        )
        result = await self.session.execute(stmt)
        return [_to_category_in_db(o) for o in result.scalars().all()]

    async def update(
        self,
        category_id: str,
        business_id: str,
        update_data: CategoryUpdate,
    ) -> Optional[CategoryInDB]:
        stmt = select(Category).where(
            Category.id == category_id,
            Category.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return _to_category_in_db(obj)
        for field, value in update_dict.items():
            if field == "code" and value is not None:
                setattr(obj, field, value.upper())
            else:
                setattr(obj, field, value)
        await self.session.flush()
        return _to_category_in_db(obj)

    async def archive(self, category_id: str, business_id: str) -> Optional[CategoryInDB]:
        stmt = select(Category).where(
            Category.id == category_id,
            Category.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.status = CategoryStatus.ARCHIVED.value
        await self.session.flush()
        return _to_category_in_db(obj)

    async def find_by_code(self, business_id: str, code: str) -> Optional[CategoryInDB]:
        norm = code.strip().upper()
        stmt = select(Category).where(
            Category.business_id == business_id,
            Category.code == norm,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_category_in_db(obj) if obj else None

    async def find_by_name(self, business_id: str, name: str) -> Optional[CategoryInDB]:
        norm = name.strip().lower()
        stmt = select(Category).where(
            Category.business_id == business_id,
            func.lower(Category.name) == norm,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_category_in_db(obj) if obj else None

    async def list_children(self, business_id: str, parent_id: str) -> List[CategoryInDB]:
        stmt = (
            select(Category)
            .where(
                Category.business_id == business_id,
                Category.parent_id == parent_id,
            )
            .order_by(asc(Category.sort_order), asc(Category.name), asc(Category.id))
        )
        result = await self.session.execute(stmt)
        return [_to_category_in_db(o) for o in result.scalars().all()]

    async def count_children(self, business_id: str, parent_id: str) -> int:
        stmt = select(func.count()).select_from(Category).where(
            Category.business_id == business_id,
            Category.parent_id == parent_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists(self, category_id: str, business_id: str) -> bool:
        stmt = select(func.count()).select_from(Category).where(
            Category.id == category_id,
            Category.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    @classmethod
    def clear(cls):
        pass
