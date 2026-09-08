from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import uuid
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

from app.modules.product_variant.schemas import (
    ProductVariantCreate,
    ProductVariantUpdate,
    ProductVariantStatus,
)


class ProductVariantInDB(BaseModel):
    id: str
    business_id: str
    product_id: str
    name: str
    code: str
    attributes: Optional[Dict[str, Any]] = None
    status: ProductVariantStatus = ProductVariantStatus.ACTIVE
    created_at: datetime
    updated_at: datetime


class AbstractProductVariantRepository(ABC):
    @abstractmethod
    async def create(
        self,
        business_id: str,
        product_id: str,
        variant_data: ProductVariantCreate,
    ) -> ProductVariantInDB:
        pass

    @abstractmethod
    async def get_by_id(
        self, variant_id: str, business_id: str
    ) -> Optional[ProductVariantInDB]:
        pass

    @abstractmethod
    async def list_by_product(
        self,
        business_id: str,
        product_id: str,
        include_archived: bool = False,
    ) -> List[ProductVariantInDB]:
        pass

    @abstractmethod
    async def list_by_business(
        self,
        business_id: str,
        include_archived: bool = False,
    ) -> List[ProductVariantInDB]:
        pass

    @abstractmethod
    async def update(
        self,
        variant_id: str,
        business_id: str,
        update_data: ProductVariantUpdate,
    ) -> Optional[ProductVariantInDB]:
        pass

    @abstractmethod
    async def archive(
        self, variant_id: str, business_id: str
    ) -> Optional[ProductVariantInDB]:
        pass

    @abstractmethod
    async def find_by_code(
        self, business_id: str, code: str
    ) -> Optional[ProductVariantInDB]:
        pass

    @abstractmethod
    async def exists(self, variant_id: str, business_id: str) -> bool:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryProductVariantRepository(AbstractProductVariantRepository):
    """
    In-memory repository for ProductVariant entities.
    All queries are strictly scoped by business_id.
    """

    _variants: Dict[str, ProductVariantInDB] = {}  # keyed by "business_id:variant_id"

    def _key(self, business_id: str, variant_id: str) -> str:
        return f"{business_id}:{variant_id}"

    async def create(
        self,
        business_id: str,
        product_id: str,
        variant_data: ProductVariantCreate,
    ) -> ProductVariantInDB:
        variant_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        variant = ProductVariantInDB(
            id=variant_id,
            business_id=business_id,
            product_id=product_id,
            name=variant_data.name.strip(),
            code=variant_data.code.strip().upper(),
            attributes=variant_data.attributes,
            status=ProductVariantStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self._variants[self._key(business_id, variant_id)] = variant
        return variant

    async def get_by_id(
        self, variant_id: str, business_id: str
    ) -> Optional[ProductVariantInDB]:
        return self._variants.get(self._key(business_id, variant_id))

    async def list_by_product(
        self,
        business_id: str,
        product_id: str,
        include_archived: bool = False,
    ) -> List[ProductVariantInDB]:
        results = []
        for var in self._variants.values():
            if var.business_id == business_id and var.product_id == product_id:
                if not include_archived and var.status == ProductVariantStatus.ARCHIVED:
                    continue
                results.append(var)
        results.sort(key=lambda v: (v.name.lower(), v.code.upper(), v.id))
        return results

    async def list_by_business(
        self,
        business_id: str,
        include_archived: bool = False,
    ) -> List[ProductVariantInDB]:
        results = []
        for var in self._variants.values():
            if var.business_id == business_id:
                if not include_archived and var.status == ProductVariantStatus.ARCHIVED:
                    continue
                results.append(var)
        results.sort(key=lambda v: (v.name.lower(), v.code.upper(), v.id))
        return results

    async def update(
        self,
        variant_id: str,
        business_id: str,
        update_data: ProductVariantUpdate,
    ) -> Optional[ProductVariantInDB]:
        key = self._key(business_id, variant_id)
        variant = self._variants.get(key)
        if not variant:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return variant

        current = variant.model_dump()
        for field, value in update_dict.items():
            if field == "code" and value is not None:
                current[field] = value.strip().upper()
            elif field == "name" and value is not None:
                current[field] = value.strip()
            else:
                current[field] = value
        current["updated_at"] = datetime.now(timezone.utc)

        updated = ProductVariantInDB(**current)
        self._variants[key] = updated
        return updated

    async def archive(
        self, variant_id: str, business_id: str
    ) -> Optional[ProductVariantInDB]:
        key = self._key(business_id, variant_id)
        variant = self._variants.get(key)
        if not variant:
            return None
        updated = variant.model_copy(
            update={
                "status": ProductVariantStatus.ARCHIVED,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._variants[key] = updated
        return updated

    async def find_by_code(
        self, business_id: str, code: str
    ) -> Optional[ProductVariantInDB]:
        norm = code.strip().upper()
        for var in self._variants.values():
            if var.business_id == business_id and var.code.upper() == norm:
                return var
        return None

    async def exists(self, variant_id: str, business_id: str) -> bool:
        return self._key(business_id, variant_id) in self._variants

    @classmethod
    def clear(cls):
        cls._variants.clear()


product_variant_repository = InMemoryProductVariantRepository()
