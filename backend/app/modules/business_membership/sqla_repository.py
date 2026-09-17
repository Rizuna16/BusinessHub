from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.business_membership.models import BusinessMembership
from app.modules.business_membership.repository import AbstractBusinessMembershipRepository
from app.modules.business_membership.schemas import (
    BusinessMembershipInDB,
    BusinessMembershipRole,
    BusinessMembershipStatus,
)
from app.modules.sqla_base import sa_create


def _to_membership_in_db(obj: BusinessMembership) -> BusinessMembershipInDB:
    return BusinessMembershipInDB(
        id=obj.id,
        business_id=obj.business_id,
        user_id=obj.user_id,
        role=BusinessMembershipRole(obj.role),
        status=BusinessMembershipStatus(obj.status),
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyBusinessMembershipRepository(AbstractBusinessMembershipRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        business_id: str,
        user_id: str,
        role: BusinessMembershipRole,
        status: BusinessMembershipStatus = BusinessMembershipStatus.ACTIVE,
    ) -> BusinessMembershipInDB:
        data = {
            "business_id": business_id,
            "user_id": user_id,
            "role": role.value,
            "status": status.value,
        }
        obj = await sa_create(self.session, BusinessMembership, data)
        return _to_membership_in_db(obj)

    async def get_by_id(self, membership_id: str) -> Optional[BusinessMembershipInDB]:
        stmt = select(BusinessMembership).where(BusinessMembership.id == membership_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_membership_in_db(obj) if obj else None

    async def get_by_business_and_user(
        self, business_id: str, user_id: str
    ) -> Optional[BusinessMembershipInDB]:
        stmt = select(BusinessMembership).where(
            BusinessMembership.business_id == business_id,
            BusinessMembership.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_membership_in_db(obj) if obj else None

    async def list_by_business(self, business_id: str) -> List[BusinessMembershipInDB]:
        stmt = select(BusinessMembership).where(BusinessMembership.business_id == business_id)
        result = await self.session.execute(stmt)
        return [_to_membership_in_db(o) for o in result.scalars().all()]

    async def list_by_user(self, user_id: str) -> List[BusinessMembershipInDB]:
        stmt = select(BusinessMembership).where(BusinessMembership.user_id == user_id)
        result = await self.session.execute(stmt)
        return [_to_membership_in_db(o) for o in result.scalars().all()]

    async def update(
        self,
        membership_id: str,
        role: Optional[BusinessMembershipRole] = None,
        status: Optional[BusinessMembershipStatus] = None,
    ) -> Optional[BusinessMembershipInDB]:
        stmt = select(BusinessMembership).where(BusinessMembership.id == membership_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        if role is not None:
            obj.role = role.value
        if status is not None:
            obj.status = status.value
        await self.session.flush()
        await self.session.refresh(obj)
        return _to_membership_in_db(obj)

    async def remove(self, membership_id: str) -> Optional[BusinessMembershipInDB]:
        return await self.update(membership_id, status=BusinessMembershipStatus.REMOVED)

    async def exists(self, business_id: str, user_id: str) -> bool:
        stmt = select(func.count()).select_from(BusinessMembership).where(
            BusinessMembership.business_id == business_id,
            BusinessMembership.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def delete_by_business(self, business_id: str) -> None:
        from sqlalchemy import delete
        stmt = delete(BusinessMembership).where(BusinessMembership.business_id == business_id)
        await self.session.execute(stmt)
        await self.session.flush()

    @classmethod
    def clear(cls):
        pass
