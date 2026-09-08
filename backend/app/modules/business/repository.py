from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid
import re

from app.modules.business.schemas import BusinessInDB, BusinessStatus, BusinessCreate, BusinessUpdate


def _generate_slug(name: str, existing_slugs: set[str]) -> str:
    """Generate a URL-friendly slug from business name, handling collisions."""
    slug_base = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    if not slug_base:
        slug_base = "business"
    
    candidate = slug_base
    counter = 2
    while candidate in existing_slugs:
        candidate = f"{slug_base}-{counter}"
        counter += 1
    
    existing_slugs.add(candidate)
    return candidate


class AbstractBusinessRepository(ABC):
    @abstractmethod
    async def create(self, business_data: BusinessCreate, owner_user_id: str, slug: str) -> BusinessInDB:
        pass

    @abstractmethod
    async def get_by_id(self, business_id: str) -> Optional[BusinessInDB]:
        """Fetch business by id."""
        pass

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Optional[BusinessInDB]:
        """Fetch business by slug."""
        pass

    @abstractmethod
    async def exists_by_slug(self, slug: str) -> bool:
        """Check if a slug exists globally (for collision detection)."""
        pass

    @abstractmethod
    def get_used_slugs(self) -> set[str]:
        """Return set of all used slugs for collision detection."""
        pass

    @abstractmethod
    async def list_by_ids(self, business_ids: List[str]) -> List[BusinessInDB]:
        """List businesses matching given IDs, excluding archived ones."""
        pass

    @abstractmethod
    async def update(
        self, business_id: str, update_data: BusinessUpdate
    ) -> Optional[BusinessInDB]:
        """Update a business."""
        pass

    @abstractmethod
    async def archive(self, business_id: str) -> Optional[BusinessInDB]:
        """Soft-archive a business."""
        pass

    @abstractmethod
    async def count(self) -> int:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryBusinessRepository(AbstractBusinessRepository):
    """
    In-memory repository for Business entities.
    Designed to swap seamlessly to PostgreSQL without architectural changes.
    Access control & membership validated at the service layer.
    """
    _businesses: Dict[str, BusinessInDB] = {}  # keyed by business_id
    _all_slugs: set[str] = set()

    async def create(
        self, business_data: BusinessCreate, owner_user_id: str, slug: str
    ) -> BusinessInDB:
        business_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        business = BusinessInDB(
            id=business_id,
            owner_user_id=owner_user_id,
            name=business_data.name,
            slug=slug,
            description=business_data.description,
            business_type=business_data.business_type,
            status=BusinessStatus.ACTIVE,
            timezone=business_data.timezone,
            locale=business_data.locale,
            created_at=now,
            updated_at=now,
        )
        self._businesses[business_id] = business
        self._all_slugs.add(slug)
        return business

    async def get_by_id(self, business_id: str) -> Optional[BusinessInDB]:
        return self._businesses.get(business_id)

    async def get_by_slug(self, slug: str) -> Optional[BusinessInDB]:
        for business in self._businesses.values():
            if business.slug == slug:
                return business
        return None

    async def exists_by_slug(self, slug: str) -> bool:
        return slug in self._all_slugs

    def get_used_slugs(self) -> set[str]:
        return set(self._all_slugs)

    async def list_by_ids(self, business_ids: List[str]) -> List[BusinessInDB]:
        return [
            self._businesses[b_id] for b_id in business_ids
            if b_id in self._businesses and self._businesses[b_id].status != BusinessStatus.ARCHIVED
        ]

    async def update(
        self, business_id: str, update_data: BusinessUpdate
    ) -> Optional[BusinessInDB]:
        business = self._businesses.get(business_id)
        if not business:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return business

        current = business.model_dump()
        for field, value in update_dict.items():
            current[field] = value
        current["updated_at"] = datetime.now(timezone.utc)

        updated = BusinessInDB(**current)
        self._businesses[business_id] = updated
        return updated

    async def archive(self, business_id: str) -> Optional[BusinessInDB]:
        business = self._businesses.get(business_id)
        if not business:
            return None
        updated = business.model_copy(
            update={"status": BusinessStatus.ARCHIVED, "updated_at": datetime.now(timezone.utc)}
        )
        self._businesses[business_id] = updated
        return updated

    async def count(self) -> int:
        return len(self._businesses)

    @classmethod
    def clear(cls):
        cls._businesses.clear()
        cls._all_slugs.clear()


business_repository = InMemoryBusinessRepository()
