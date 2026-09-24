from datetime import datetime, timezone
from typing import Optional, List
import hashlib
import secrets

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.authentication.models import User, PasswordResetToken
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

    async def create_reset_token(self, user_id: str) -> str:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        now = datetime.now(timezone.utc)
        from app.core.config import settings
        expires_at = now + __import__('datetime').timedelta(minutes=settings.reset_token_expire_minutes)

        import uuid
        token = PasswordResetToken(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(token)
        await self.session.flush()
        return raw_token

    async def get_reset_token(self, token_hash: str) -> Optional[dict]:
        now = datetime.now(timezone.utc)
        stmt = select(PasswordResetToken).where(
            and_(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.expires_at > now,
                PasswordResetToken.used_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        return {"id": obj.id, "user_id": obj.user_id, "expires_at": obj.expires_at, "used_at": obj.used_at}

    async def consume_reset_token(self, token_hash: str) -> Optional[dict]:
        now = datetime.now(timezone.utc)
        stmt = select(PasswordResetToken).where(
            and_(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.expires_at > now,
                PasswordResetToken.used_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.used_at = now
        await self.session.flush()
        return {"id": obj.id, "user_id": obj.user_id, "expires_at": obj.expires_at, "used_at": obj.used_at}

    async def invalidate_user_tokens(self, user_id: str) -> None:
        now = datetime.now(timezone.utc)
        stmt = select(PasswordResetToken).where(
            and_(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
            )
        )
        result = await self.session.execute(stmt)
        tokens = result.scalars().all()
        for token in tokens:
            token.used_at = now
        if tokens:
            await self.session.flush()
