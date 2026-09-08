from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
import uuid
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

from app.modules.category.schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryStatus,
    CategoryResponse,
)


class CategoryInDB(BaseModel):
    id: str
    business_id: str
    name: str
    code: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    status: CategoryStatus = CategoryStatus.ACTIVE
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime


class AbstractCategoryRepository(ABC):
    @abstractmethod
    async def create(
        self,
        business_id: str,
        category_data: CategoryCreate,
    ) -> CategoryInDB:
        pass

    @abstractmethod
    async def get_by_id(self, category_id: str, business_id: str) -> Optional[CategoryInDB]:
        pass

    @abstractmethod
    async def list_by_business(
        self,
        business_id: str,
        parent_id: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[CategoryInDB]:
        pass

    @abstractmethod
    async def update(
        self,
        category_id: str,
        business_id: str,
        update_data: CategoryUpdate,
    ) -> Optional[CategoryInDB]:
        pass

    @abstractmethod
    async def archive(self, category_id: str, business_id: str) -> Optional[CategoryInDB]:
        pass

    @abstractmethod
    async def find_by_code(self, business_id: str, code: str) -> Optional[CategoryInDB]:
        pass

    @abstractmethod
    async def find_by_name(self, business_id: str, name: str) -> Optional[CategoryInDB]:
        pass

    @abstractmethod
    async def list_children(self, business_id: str, parent_id: str) -> List[CategoryInDB]:
        pass

    @abstractmethod
    async def count_children(self, business_id: str, parent_id: str) -> int:
        pass

    @abstractmethod
    async def exists(self, category_id: str, business_id: str) -> bool:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryCategoryRepository(AbstractCategoryRepository):
    """
    In-memory repository for Category entities.
    All queries are strictly scoped by business_id.
    Access control (membership) is enforced at the service layer.
    """
    _categories: Dict[str, CategoryInDB] = {}  # keyed by "business_id:category_id"

    def _key(self, business_id: str, category_id: str) -> str:
        return f"{business_id}:{category_id}"

    async def create(
        self,
        business_id: str,
        category_data: CategoryCreate,
    ) -> CategoryInDB:
        category_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        category = CategoryInDB(
            id=category_id,
            business_id=business_id,
            name=category_data.name,
            code=category_data.code.upper(),
            description=category_data.description,
            parent_id=category_data.parent_id,
            status=CategoryStatus.ACTIVE,
            sort_order=category_data.sort_order,
            created_at=now,
            updated_at=now,
        )
        self._categories[self._key(business_id, category_id)] = category
        return category

    async def get_by_id(self, category_id: str, business_id: str) -> Optional[CategoryInDB]:
        return self._categories.get(self._key(business_id, category_id))

    async def list_by_business(
        self,
        business_id: str,
        parent_id: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[CategoryInDB]:
        results = []
        for cat in self._categories.values():
            if cat.business_id != business_id:
                continue
            if parent_id is not None:
                if cat.parent_id != parent_id:
                    continue
            else:
                if cat.parent_id is not None:
                    continue
            if not include_archived and cat.status == CategoryStatus.ARCHIVED:
                continue
            results.append(cat)
        # Sort: sort_order ASC, name ASC, id ASC
        results.sort(key=lambda c: (c.sort_order, c.name.lower(), c.id))
        return results

    async def update(
        self,
        category_id: str,
        business_id: str,
        update_data: CategoryUpdate,
    ) -> Optional[CategoryInDB]:
        key = self._key(business_id, category_id)
        category = self._categories.get(key)
        if not category:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return category

        current = category.model_dump()
        for field, value in update_dict.items():
            if field == "code" and value is not None:
                current[field] = value.upper()
            else:
                current[field] = value
        current["updated_at"] = datetime.now(timezone.utc)

        updated = CategoryInDB(**current)
        self._categories[key] = updated
        return updated

    async def archive(self, category_id: str, business_id: str) -> Optional[CategoryInDB]:
        key = self._key(business_id, category_id)
        category = self._categories.get(key)
        if not category:
            return None
        updated = category.model_copy(
            update={
                "status": CategoryStatus.ARCHIVED,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._categories[key] = updated
        return updated

    async def find_by_code(self, business_id: str, code: str) -> Optional[CategoryInDB]:
        norm = code.strip().upper()
        for cat in self._categories.values():
            if cat.business_id == business_id and cat.code.upper() == norm:
                return cat
        return None

    async def find_by_name(self, business_id: str, name: str) -> Optional[CategoryInDB]:
        norm = name.strip().lower()
        for cat in self._categories.values():
            if cat.business_id == business_id and cat.name.lower() == norm:
                return cat
        return None

    async def list_children(self, business_id: str, parent_id: str) -> List[CategoryInDB]:
        results = [c for c in self._categories.values()
                   if c.business_id == business_id and c.parent_id == parent_id]
        results.sort(key=lambda c: (c.sort_order, c.name.lower(), c.id))
        return results

    async def count_children(self, business_id: str, parent_id: str) -> int:
        count = 0
        for cat in self._categories.values():
            if cat.business_id == business_id and cat.parent_id == parent_id:
                count += 1
        return count

    async def exists(self, category_id: str, business_id: str) -> bool:
        return self._key(business_id, category_id) in self._categories

    @classmethod
    def clear(cls):
        cls._categories.clear()


category_repository = InMemoryCategoryRepository()
