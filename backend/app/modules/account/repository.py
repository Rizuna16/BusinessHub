from abc import ABC, abstractmethod
from typing import Dict, Optional
from datetime import datetime, timezone
import uuid

from app.modules.account.schemas import AccountInDB, AccountUpdate


class AbstractAccountRepository(ABC):
    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> Optional[AccountInDB]:
        pass

    @abstractmethod
    async def create_for_user(self, user_id: str, display_name: str) -> AccountInDB:
        pass

    @abstractmethod
    async def update(self, user_id: str, update_data: AccountUpdate) -> Optional[AccountInDB]:
        pass


class InMemoryAccountRepository(AbstractAccountRepository):
    """In-memory repository for Account profiles, linked strictly 1:1 with user_id."""
    _accounts: Dict[str, AccountInDB] = {}  # keyed by user_id for unique constraint & O(1) lookup

    async def get_by_user_id(self, user_id: str) -> Optional[AccountInDB]:
        return self._accounts.get(user_id)

    async def create_for_user(self, user_id: str, display_name: str) -> AccountInDB:
        account_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        account = AccountInDB(
            id=account_id,
            user_id=user_id,
            display_name=display_name,
            phone=None,
            avatar_url=None,
            timezone="UTC",
            locale="en-US",
            created_at=now,
            updated_at=now,
        )
        self._accounts[user_id] = account
        return account

    async def update(self, user_id: str, update_data: AccountUpdate) -> Optional[AccountInDB]:
        account = self._accounts.get(user_id)
        if not account:
            return None
        
        update_dict = update_data.model_dump(exclude_unset=True)
        current_data = account.model_dump()
        
        for field, value in update_dict.items():
            current_data[field] = value
        
        current_data["updated_at"] = datetime.now(timezone.utc)
        
        updated_account = AccountInDB(**current_data)
        self._accounts[user_id] = updated_account
        return updated_account

    @classmethod
    def clear(cls):
        cls._accounts.clear()


account_repository = InMemoryAccountRepository()
