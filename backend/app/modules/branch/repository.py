from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

from app.modules.branch.schemas import BranchInDB, BranchCreate, BranchUpdate, BranchStatus


class AbstractBranchRepository(ABC):
    @abstractmethod
    async def create(
        self, business_id: str, branch_data: BranchCreate, is_default: bool = False
    ) -> BranchInDB:
        pass

    @abstractmethod
    async def get_by_id(self, branch_id: str) -> Optional[BranchInDB]:
        pass

    @abstractmethod
    async def list_by_business(self, business_id: str) -> List[BranchInDB]:
        pass

    @abstractmethod
    async def update(
        self, branch_id: str, update_data: BranchUpdate
    ) -> Optional[BranchInDB]:
        pass

    @abstractmethod
    async def suspend(self, branch_id: str) -> Optional[BranchInDB]:
        pass

    @abstractmethod
    async def archive(self, branch_id: str) -> Optional[BranchInDB]:
        pass

    @abstractmethod
    async def set_default(self, business_id: str, branch_id: str) -> Optional[BranchInDB]:
        pass

    @abstractmethod
    async def find_by_code(self, business_id: str, code: str) -> Optional[BranchInDB]:
        pass

    @abstractmethod
    async def find_by_name(self, business_id: str, name: str) -> Optional[BranchInDB]:
        pass

    @abstractmethod
    async def find_default(self, business_id: str) -> Optional[BranchInDB]:
        pass

    @abstractmethod
    async def count_active(self, business_id: str) -> int:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryBranchRepository(AbstractBranchRepository):
    """In-memory repository for Branch entities, scoped strictly by business_id."""

    _branches: Dict[str, BranchInDB] = {}  # keyed by branch_id

    async def create(
        self, business_id: str, branch_data: BranchCreate, is_default: bool = False
    ) -> BranchInDB:
        branch_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        branch = BranchInDB(
            id=branch_id,
            business_id=business_id,
            name=branch_data.name,
            code=branch_data.code.upper(),
            description=branch_data.description,
            address=branch_data.address,
            phone=branch_data.phone,
            email=branch_data.email,
            timezone=branch_data.timezone,
            locale=branch_data.locale,
            status=BranchStatus.ACTIVE,
            is_default=is_default,
            created_at=now,
            updated_at=now,
        )
        self._branches[branch_id] = branch
        return branch

    async def get_by_id(self, branch_id: str) -> Optional[BranchInDB]:
        return self._branches.get(branch_id)

    async def list_by_business(self, business_id: str) -> List[BranchInDB]:
        all_b = [b for b in self._branches.values() if b.business_id == business_id]
        # Ordering: ACTIVE first, default branch first, created_at ASC
        def sort_key(b: BranchInDB):
            status_order = 0 if b.status == BranchStatus.ACTIVE else (1 if b.status == BranchStatus.SUSPENDED else 2)
            default_order = 0 if b.is_default else 1
            return (status_order, default_order, b.created_at, b.id)

        return sorted(all_b, key=sort_key)

    async def update(
        self, branch_id: str, update_data: BranchUpdate
    ) -> Optional[BranchInDB]:
        branch = self._branches.get(branch_id)
        if not branch:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return branch

        current = branch.model_dump()
        for field, value in update_dict.items():
            if field == "code" and value is not None:
                current[field] = str(value).upper()
            else:
                current[field] = value
        current["updated_at"] = datetime.now(timezone.utc)

        updated = BranchInDB(**current)
        self._branches[branch_id] = updated
        return updated

    async def suspend(self, branch_id: str) -> Optional[BranchInDB]:
        branch = self._branches.get(branch_id)
        if not branch:
            return None
        updated = branch.model_copy(
            update={
                "status": BranchStatus.SUSPENDED,
                "is_default": False,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._branches[branch_id] = updated
        return updated

    async def archive(self, branch_id: str) -> Optional[BranchInDB]:
        branch = self._branches.get(branch_id)
        if not branch:
            return None
        updated = branch.model_copy(
            update={
                "status": BranchStatus.ARCHIVED,
                "is_default": False,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._branches[branch_id] = updated
        return updated

    async def set_default(self, business_id: str, branch_id: str) -> Optional[BranchInDB]:
        # Reset all branches of this business to is_default = False
        now = datetime.now(timezone.utc)
        for b_id, b in self._branches.items():
            if b.business_id == business_id and b.is_default:
                self._branches[b_id] = b.model_copy(
                    update={"is_default": False, "updated_at": now}
                )

        target = self._branches.get(branch_id)
        if not target or target.business_id != business_id:
            return None

        updated_target = target.model_copy(
            update={"is_default": True, "updated_at": now}
        )
        self._branches[branch_id] = updated_target
        return updated_target

    async def find_by_code(self, business_id: str, code: str) -> Optional[BranchInDB]:
        norm_code = code.strip().upper()
        for b in self._branches.values():
            if (
                b.business_id == business_id
                and b.code.upper() == norm_code
                and b.status != BranchStatus.ARCHIVED
            ):
                return b
        return None

    async def find_by_name(self, business_id: str, name: str) -> Optional[BranchInDB]:
        norm_name = name.strip().lower()
        for b in self._branches.values():
            if (
                b.business_id == business_id
                and b.name.strip().lower() == norm_name
                and b.status != BranchStatus.ARCHIVED
            ):
                return b
        return None

    async def find_default(self, business_id: str) -> Optional[BranchInDB]:
        for b in self._branches.values():
            if b.business_id == business_id and b.is_default and b.status == BranchStatus.ACTIVE:
                return b
        return None

    async def count_active(self, business_id: str) -> int:
        return sum(
            1
            for b in self._branches.values()
            if b.business_id == business_id and b.status == BranchStatus.ACTIVE
        )

    @classmethod
    def clear(cls):
        cls._branches.clear()


branch_repository = InMemoryBranchRepository()
