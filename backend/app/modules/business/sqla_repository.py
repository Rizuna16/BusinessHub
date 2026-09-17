from datetime import datetime, timezone
from typing import Optional, List, Set

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.business.models import Business
from app.modules.business.repository import AbstractBusinessRepository
from app.modules.business.schemas import BusinessInDB, BusinessCreate, BusinessUpdate, BusinessStatus
from app.modules.sqla_base import sa_create


def _to_business_in_db(obj: Business) -> BusinessInDB:
    return BusinessInDB(
        id=obj.id,
        owner_user_id=obj.owner_user_id,
        name=obj.name,
        slug=obj.slug,
        description=obj.description,
        business_type=obj.business_type,
        status=obj.status,
        timezone=obj.timezone,
        locale=obj.locale,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyBusinessRepository(AbstractBusinessRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, business_data: BusinessCreate, owner_user_id: str, slug: str) -> BusinessInDB:
        data = {
            "owner_user_id": owner_user_id,
            "name": business_data.name,
            "slug": slug,
            "description": business_data.description,
            "business_type": business_data.business_type.value,
            "status": BusinessStatus.ACTIVE.value,
            "timezone": business_data.timezone,
            "locale": business_data.locale,
        }
        obj = await sa_create(self.session, Business, data)
        return _to_business_in_db(obj)

    async def get_by_id(self, business_id: str) -> Optional[BusinessInDB]:
        stmt = select(Business).where(Business.id == business_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_business_in_db(obj) if obj else None

    async def get_by_slug(self, slug: str) -> Optional[BusinessInDB]:
        stmt = select(Business).where(Business.slug == slug)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_business_in_db(obj) if obj else None

    async def exists_by_slug(self, slug: str) -> bool:
        stmt = select(func.count()).select_from(Business).where(Business.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    def get_used_slugs(self) -> Set[str]:
        raise NotImplementedError("Synchronous slug scan not supported in async SQLAlchemy repository. Use exists_by_slug instead.")

    async def list_by_ids(self, business_ids: List[str]) -> List[BusinessInDB]:
        if not business_ids:
            return []
        stmt = select(Business).where(
            Business.id.in_(business_ids),
            Business.status != BusinessStatus.ARCHIVED.value,
        )
        result = await self.session.execute(stmt)
        return [_to_business_in_db(o) for o in result.scalars().all()]

    async def update(self, business_id: str, update_data: BusinessUpdate) -> Optional[BusinessInDB]:
        stmt = select(Business).where(Business.id == business_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return _to_business_in_db(obj)
        for field, value in update_dict.items():
            setattr(obj, field, value)
        await self.session.flush()
        await self.session.refresh(obj)
        return _to_business_in_db(obj)

    async def archive(self, business_id: str) -> Optional[BusinessInDB]:
        stmt = select(Business).where(Business.id == business_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.status = BusinessStatus.ARCHIVED.value
        await self.session.flush()
        await self.session.refresh(obj)
        return _to_business_in_db(obj)

    async def count(self) -> int:
        stmt = select(func.count()).select_from(Business)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    @classmethod
    def clear(cls):
        pass
