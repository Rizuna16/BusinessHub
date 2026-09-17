from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.account.models import Account
from app.modules.account.repository import AbstractAccountRepository
from app.modules.account.schemas import AccountInDB, AccountUpdate
from app.modules.sqla_base import sa_create


def _to_account_in_db(obj: Account) -> AccountInDB:
    return AccountInDB(
        id=obj.id,
        user_id=obj.user_id,
        display_name=obj.display_name,
        phone=obj.phone,
        avatar_url=obj.avatar_url,
        timezone=obj.timezone,
        locale=obj.locale,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyAccountRepository(AbstractAccountRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: str) -> Optional[AccountInDB]:
        stmt = select(Account).where(Account.user_id == user_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_account_in_db(obj) if obj else None

    async def create_for_user(self, user_id: str, display_name: str) -> AccountInDB:
        data = {
            "user_id": user_id,
            "display_name": display_name,
            "timezone": "UTC",
            "locale": "en-US",
        }
        obj = await sa_create(self.session, Account, data)
        return _to_account_in_db(obj)

    async def update(self, user_id: str, update_data: AccountUpdate) -> Optional[AccountInDB]:
        stmt = select(Account).where(Account.user_id == user_id)
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return _to_account_in_db(obj)
        for field, value in update_dict.items():
            setattr(obj, field, value)
        await self.session.flush()
        return _to_account_in_db(obj)
