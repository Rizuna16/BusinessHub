from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

from app.modules.business_membership.schemas import (
    BusinessMembershipInDB,
    BusinessMembershipRole,
    BusinessMembershipStatus,
)


class AbstractBusinessMembershipRepository(ABC):
    @abstractmethod
    async def create(
        self,
        business_id: str,
        user_id: str,
        role: BusinessMembershipRole,
        status: BusinessMembershipStatus = BusinessMembershipStatus.ACTIVE,
    ) -> BusinessMembershipInDB:
        pass

    @abstractmethod
    async def get_by_id(self, membership_id: str) -> Optional[BusinessMembershipInDB]:
        pass

    @abstractmethod
    async def get_by_business_and_user(
        self, business_id: str, user_id: str
    ) -> Optional[BusinessMembershipInDB]:
        pass

    @abstractmethod
    async def list_by_business(self, business_id: str) -> List[BusinessMembershipInDB]:
        pass

    @abstractmethod
    async def list_by_user(self, user_id: str) -> List[BusinessMembershipInDB]:
        pass

    @abstractmethod
    async def update(
        self,
        membership_id: str,
        role: Optional[BusinessMembershipRole] = None,
        status: Optional[BusinessMembershipStatus] = None,
    ) -> Optional[BusinessMembershipInDB]:
        pass

    @abstractmethod
    async def remove(self, membership_id: str) -> Optional[BusinessMembershipInDB]:
        pass

    @abstractmethod
    async def exists(self, business_id: str, user_id: str) -> bool:
        pass

    @abstractmethod
    async def delete_by_business(self, business_id: str) -> None:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryBusinessMembershipRepository(AbstractBusinessMembershipRepository):
    """
    In-memory repository for BusinessMembership entities.
    Enforces UNIQUE(business_id, user_id).
    """
    _memberships: Dict[str, BusinessMembershipInDB] = {}  # keyed by membership_id
    _business_user_index: Dict[tuple[str, str], str] = {}  # (business_id, user_id) -> membership_id

    async def create(
        self,
        business_id: str,
        user_id: str,
        role: BusinessMembershipRole,
        status: BusinessMembershipStatus = BusinessMembershipStatus.ACTIVE,
    ) -> BusinessMembershipInDB:
        key = (business_id, user_id)
        if key in self._business_user_index:
            raise ValueError(f"Membership for business_id {business_id} and user_id {user_id} already exists.")

        membership_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        membership = BusinessMembershipInDB(
            id=membership_id,
            business_id=business_id,
            user_id=user_id,
            role=role,
            status=status,
            created_at=now,
            updated_at=now,
        )
        self._memberships[membership_id] = membership
        self._business_user_index[key] = membership_id
        return membership

    async def get_by_id(self, membership_id: str) -> Optional[BusinessMembershipInDB]:
        return self._memberships.get(membership_id)

    async def get_by_business_and_user(
        self, business_id: str, user_id: str
    ) -> Optional[BusinessMembershipInDB]:
        membership_id = self._business_user_index.get((business_id, user_id))
        if not membership_id:
            return None
        return self._memberships.get(membership_id)

    async def list_by_business(self, business_id: str) -> List[BusinessMembershipInDB]:
        return [
            m for m in self._memberships.values()
            if m.business_id == business_id
        ]

    async def list_by_user(self, user_id: str) -> List[BusinessMembershipInDB]:
        return [
            m for m in self._memberships.values()
            if m.user_id == user_id
        ]

    async def update(
        self,
        membership_id: str,
        role: Optional[BusinessMembershipRole] = None,
        status: Optional[BusinessMembershipStatus] = None,
    ) -> Optional[BusinessMembershipInDB]:
        membership = self._memberships.get(membership_id)
        if not membership:
            return None

        updated_role = role if role is not None else membership.role
        updated_status = status if status is not None else membership.status

        updated = membership.model_copy(
            update={
                "role": updated_role,
                "status": updated_status,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._memberships[membership_id] = updated
        return updated

    async def remove(self, membership_id: str) -> Optional[BusinessMembershipInDB]:
        return await self.update(membership_id, status=BusinessMembershipStatus.REMOVED)

    async def exists(self, business_id: str, user_id: str) -> bool:
        return (business_id, user_id) in self._business_user_index

    async def delete_by_business(self, business_id: str) -> None:
        memberships_to_remove = [
            m_id for m in self._memberships.values()
            if m.business_id == business_id
            for m_id in [m.id]
        ]
        for m_id in memberships_to_remove:
            del self._memberships[m_id]
        
        keys_to_remove = [
            k for k in self._business_user_index.keys()
            if k[0] == business_id
        ]
        for k in keys_to_remove:
            del self._business_user_index[k]

    @classmethod
    def clear(cls):
        cls._memberships.clear()
        cls._business_user_index.clear()


business_membership_repository = InMemoryBusinessMembershipRepository()
