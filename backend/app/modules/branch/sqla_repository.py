from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.branch.models import Branch
from app.modules.branch.repository import AbstractBranchRepository
from app.modules.branch.schemas import BranchInDB, BranchCreate, BranchUpdate, BranchStatus
from app.modules.sqla_base import sa_create


def _to_branch_in_db(obj: Branch) -> BranchInDB:
    return BranchInDB(
        id=obj.id,
        business_id=obj.business_id,
        name=obj.name,
        code=obj.code,
        description=obj.description,
        address=obj.address,
        phone=obj.phone,
        email=obj.email,
        timezone=obj.timezone,
        locale=obj.locale,
        status=obj.status,
        is_default=obj.is_default,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyBranchRepository(AbstractBranchRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, business_id: str, branch_data: BranchCreate, is_default: bool = False
    ) -> BranchInDB:
        data = {
            "business_id": business_id,
            "name": branch_data.name,
            "code": branch_data.code.upper(),
            "description": branch_data.description,
            "address": branch_data.address,
            "phone": branch_data.phone,
            "email": branch_data.email,
            "timezone": branch_data.timezone,
            "locale": branch_data.locale,
            "status": BranchStatus.ACTIVE.value,
            "is_default": is_default,
        }
        obj = await sa_create(self.session, Branch, data)
        return _to_branch_in_db(obj)

    async def get_by_id(self, branch_id: str) -> Optional[BranchInDB]:
        stmt = select(Branch).where(Branch.id == branch_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_branch_in_db(obj) if obj else None

    async def list_by_business(self, business_id: str) -> List[BranchInDB]:
        stmt = (
            select(Branch)
            .where(Branch.business_id == business_id)
            .order_by(Branch.is_default.desc(), Branch.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return [_to_branch_in_db(o) for o in result.scalars().all()]

    async def update(self, branch_id: str, update_data: BranchUpdate) -> Optional[BranchInDB]:
        stmt = select(Branch).where(Branch.id == branch_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return _to_branch_in_db(obj)
        for field, value in update_dict.items():
            if field == "code" and value is not None:
                setattr(obj, field, value.upper())
            else:
                setattr(obj, field, value)
        await self.session.flush()
        return _to_branch_in_db(obj)

    async def suspend(self, branch_id: str) -> Optional[BranchInDB]:
        stmt = select(Branch).where(Branch.id == branch_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.status = BranchStatus.SUSPENDED.value
        obj.is_default = False
        await self.session.flush()
        return _to_branch_in_db(obj)

    async def archive(self, branch_id: str) -> Optional[BranchInDB]:
        stmt = select(Branch).where(Branch.id == branch_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.status = BranchStatus.ARCHIVED.value
        obj.is_default = False
        await self.session.flush()
        return _to_branch_in_db(obj)

    async def set_default(self, business_id: str, branch_id: str) -> Optional[BranchInDB]:
        from sqlalchemy import update as sa_update
        stmt_reset = (
            sa_update(Branch)
            .where(Branch.business_id == business_id, Branch.is_default == True)
            .values(is_default=False)
        )
        await self.session.execute(stmt_reset)

        stmt = select(Branch).where(Branch.id == branch_id, Branch.business_id == business_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.is_default = True
        await self.session.flush()
        return _to_branch_in_db(obj)

    async def find_by_code(self, business_id: str, code: str) -> Optional[BranchInDB]:
        norm_code = code.strip().upper()
        stmt = select(Branch).where(
            Branch.business_id == business_id,
            Branch.code == norm_code,
            Branch.status != BranchStatus.ARCHIVED.value,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_branch_in_db(obj) if obj else None

    async def find_by_name(self, business_id: str, name: str) -> Optional[BranchInDB]:
        norm_name = name.strip().lower()
        stmt = (
            select(Branch)
            .where(
                Branch.business_id == business_id,
                func.lower(Branch.name) == norm_name,
                Branch.status != BranchStatus.ARCHIVED.value,
            )
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_branch_in_db(obj) if obj else None

    async def find_default(self, business_id: str) -> Optional[BranchInDB]:
        stmt = select(Branch).where(
            Branch.business_id == business_id,
            Branch.is_default == True,
            Branch.status == BranchStatus.ACTIVE.value,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_branch_in_db(obj) if obj else None

    async def count_active(self, business_id: str) -> int:
        stmt = select(func.count()).select_from(Branch).where(
            Branch.business_id == business_id,
            Branch.status == BranchStatus.ACTIVE.value,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    @classmethod
    def clear(cls):
        pass
