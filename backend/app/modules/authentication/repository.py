from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

from app.modules.authentication.schemas import UserInDB, UserCreate, PlatformRole
from app.modules.authentication.security import hash_password


class AbstractUserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[UserInDB]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[UserInDB]:
        pass

    @abstractmethod
    async def list_all(self) -> List[UserInDB]:
        pass

    @abstractmethod
    async def create(self, user_data: UserCreate) -> UserInDB:
        pass

    @abstractmethod
    async def update_status(self, user_id: str, is_active: bool) -> Optional[UserInDB]:
        pass

    @abstractmethod
    async def update_platform_role(self, user_id: str, platform_role: Optional[PlatformRole]) -> Optional[UserInDB]:
        pass

    @abstractmethod
    async def update_password(self, user_id: str, password_hash: str) -> Optional[UserInDB]:
        pass

    @abstractmethod
    async def create_reset_token(self, user_id: str) -> str:
        pass

    @abstractmethod
    async def get_reset_token(self, token_hash: str) -> Optional[dict]:
        pass

    @abstractmethod
    async def consume_reset_token(self, token_hash: str) -> Optional[dict]:
        pass

    @abstractmethod
    async def invalidate_user_tokens(self, user_id: str) -> None:
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

    async def list_all(self) -> List[UserInDB]:
        return list(self._users.values())

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
            platform_role=None,  # Public registration NEVER grants platform_role
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

    async def update_platform_role(self, user_id: str, platform_role: Optional[PlatformRole]) -> Optional[UserInDB]:
        user = self._users.get(user_id)
        if not user:
            return None
        updated_user = user.model_copy(update={"platform_role": platform_role, "updated_at": datetime.now(timezone.utc)})
        self._users[user_id] = updated_user
        return updated_user

    async def update_password(self, user_id: str, password_hash: str) -> Optional[UserInDB]:
        user = self._users.get(user_id)
        if not user:
            return None
        updated_user = user.model_copy(update={"password_hash": password_hash, "updated_at": datetime.now(timezone.utc)})
        self._users[user_id] = updated_user
        return updated_user

    async def create_reset_token(self, user_id: str) -> str:
        return str(uuid.uuid4())

    async def get_reset_token(self, token_hash: str) -> Optional[dict]:
        return None

    async def consume_reset_token(self, token_hash: str) -> Optional[dict]:
        return None

    async def invalidate_user_tokens(self, user_id: str) -> None:
        pass

    @classmethod
    def clear(cls):
        cls._users.clear()

    @classmethod
    async def seed_development_user(cls, email: str, plain_password: str, full_name: str = "Development Owner"):
        normalized_email = email.lower().strip()
        for user in cls._users.values():
            if user.email.lower().strip() == normalized_email:
                return user
        
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        hashed_pwd = hash_password(plain_password)
        
        user_in_db = UserInDB(
            id=user_id,
            email=normalized_email,
            full_name=full_name.strip(),
            password_hash=hashed_pwd,
            is_active=True,
            platform_role=None,
            created_at=now,
            updated_at=now,
        )
        cls._users[user_id] = user_in_db
        return user_in_db

    @classmethod
    async def seed_development_superadmin(cls, email: str, plain_password: str, full_name: str = "Platform Super Admin"):
        normalized_email = email.lower().strip()
        for user in cls._users.values():
            if user.email.lower().strip() == normalized_email:
                if user.platform_role != PlatformRole.SUPER_ADMIN:
                    updated = user.model_copy(update={"platform_role": PlatformRole.SUPER_ADMIN, "updated_at": datetime.now(timezone.utc)})
                    cls._users[user.id] = updated
                    return updated
                return user
        
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        hashed_pwd = hash_password(plain_password)
        
        user_in_db = UserInDB(
            id=user_id,
            email=normalized_email,
            full_name=full_name.strip(),
            password_hash=hashed_pwd,
            is_active=True,
            platform_role=PlatformRole.SUPER_ADMIN,
            created_at=now,
            updated_at=now,
        )
        cls._users[user_id] = user_in_db
        return user_in_db


# Global repository instance
user_repository = InMemoryUserRepository()
