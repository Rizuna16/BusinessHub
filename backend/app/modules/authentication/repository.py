from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

from app.modules.authentication.schemas import UserInDB, UserCreate
from app.modules.authentication.security import hash_password


class AbstractUserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[UserInDB]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[UserInDB]:
        pass

    @abstractmethod
    async def create(self, user_data: UserCreate) -> UserInDB:
        pass

    @abstractmethod
    async def update_status(self, user_id: str, is_active: bool) -> Optional[UserInDB]:
        pass


class InMemoryUserRepository(AbstractUserRepository):
    """Thread-safe / process-safe singleton-like in-memory user store for modular monolith without SQL dependency yet."""
    _users: Dict[str, UserInDB] = {}

    async def get_by_id(self, user_id: str) -> Optional[UserInDB]:
        return self._users.get(user_id)

    async def get_by_email(self, email: str) -> Optional[UserInDB]:
        normalized_email = email.lower().strip()
        for user in self._users.values():
            if user.email.lower().strip() == normalized_email:
                return user
        return None

    async def create(self, user_data: UserCreate) -> UserInDB:
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        hashed_pwd = hash_password(user_data.password)
        
        user_in_db = UserInDB(
            id=user_id,
            email=user_data.email.lower().strip(),
            full_name=user_data.full_name.strip(),
            password_hash=hashed_pwd,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self._users[user_id] = user_in_db
        return user_in_db

    async def update_status(self, user_id: str, is_active: bool) -> Optional[UserInDB]:
        user = self._users.get(user_id)
        if not user:
            return None
        updated_user = user.model_copy(update={"is_active": is_active, "updated_at": datetime.now(timezone.utc)})
        self._users[user_id] = updated_user
        return updated_user

    @classmethod
    def clear(cls):
        cls._users.clear()


# Global repository instance
user_repository = InMemoryUserRepository()
