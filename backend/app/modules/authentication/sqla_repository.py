from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authentication.models import User
from app.modules.authentication.repository import AbstractUserRepository
from app.modules.authentication.schemas import UserInDB, UserCreate, PlatformRole
from app.modules.authentication.security import hash_password
from app.modules.sqla_base import sa_create


def _to_user_in_db(obj: User) -> UserInDB:
    return UserInDB(
        id=obj.id,
        email=obj.email,
        full_name=obj.full_name,
        password_hash=obj.password_hash,
        is_active=obj.is_active,
        platform_role=PlatformRole(obj.platform_role) if obj.platform_role else None,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyUserRepository(AbstractUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: str) -> Optional[UserInDB]:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_user_in_db(obj) if obj else None

    async def get_by_email(self, email: str) -> Optional[UserInDB]:
        normalized = email.lower().strip()
        stmt = select(User).where(func.lower(User.email) == normalized)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_user_in_db(obj) if obj else None

    async def list_all(self) -> List[UserInDB]:
        stmt = select(User)
        result = await self.session.execute(stmt)
        return [_to_user_in_db(o) for o in result.scalars().all()]

    async def create(self, user_data: UserCreate) -> UserInDB:
        now = datetime.now(timezone.utc)
        data = {
            "email": user_data.email.lower().strip(),
            "full_name": user_data.full_name.strip(),
            "password_hash": hash_password(user_data.password),
            "is_active": True,
            "platform_role": None,
        }
        obj = await sa_create(self.session, User, data)
        await self.session.flush()
        return _to_user_in_db(obj)

    async def update_status(self, user_id: str, is_active: bool) -> Optional[UserInDB]:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.is_active = is_active
        await self.session.flush()
        return _to_user_in_db(obj)

    async def update_platform_role(self, user_id: str, platform_role: Optional[PlatformRole]) -> Optional[UserInDB]:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.platform_role = platform_role.value if platform_role else None
        await self.session.flush()
        return _to_user_in_db(obj)

    async def update_password(self, user_id: str, password_hash: str) -> Optional[UserInDB]:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.password_hash = password_hash
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_user_in_db(obj)
