from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
import uuid
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

from app.modules.product.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductStatus,
    ProductType,
    ProductTaxTreatment,
    ProductResponse,
)


class ProductInDB(BaseModel):
    id: str
    business_id: str
    category_id: Optional[str] = None
    unit_id: str
    name: str
    code: str
    description: Optional[str] = None
    product_type: ProductType
    tax_treatment: ProductTaxTreatment = ProductTaxTreatment.STANDARD_NON_LUXURY
    status: ProductStatus = ProductStatus.ACTIVE
    created_at: datetime
    updated_at: datetime


class AbstractProductRepository(ABC):
    @abstractmethod
    async def create(
        self,
        business_id: str,
        product_data: ProductCreate,
    ) -> ProductInDB:
        pass

    @abstractmethod
    async def get_by_id(self, product_id: str, business_id: str) -> Optional[ProductInDB]:
        pass

    @abstractmethod
    async def list_by_business(
        self,
        business_id: str,
        status: Optional[ProductStatus] = None,
        product_type: Optional[ProductType] = None,
        category_id: Optional[str] = None,
        search: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[ProductInDB]:
        pass

    @abstractmethod
    async def update(
        self,
        product_id: str,
        business_id: str,
        update_data: ProductUpdate,
    ) -> Optional[ProductInDB]:
        pass

    @abstractmethod
    async def archive(self, product_id: str, business_id: str) -> Optional[ProductInDB]:
        pass

    @abstractmethod
    async def find_by_code(self, business_id: str, code: str) -> Optional[ProductInDB]:
        pass

    @abstractmethod
    async def exists(self, product_id: str, business_id: str) -> bool:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryProductRepository(AbstractProductRepository):
    """
    In-memory repository for Product entities.
    All queries are strictly scoped by business_id.
    """
    _products: Dict[str, ProductInDB] = {}  # keyed by "business_id:product_id"

    def _key(self, business_id: str, product_id: str) -> str:
        return f"{business_id}:{product_id}"

    async def create(
        self,
        business_id: str,
        product_data: ProductCreate,
    ) -> ProductInDB:
        product_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        product = ProductInDB(
            id=product_id,
            business_id=business_id,
            category_id=product_data.category_id,
            unit_id=product_data.unit_id,
            name=product_data.name.strip(),
            code=product_data.code.strip().upper(),
            description=product_data.description.strip() if product_data.description else None,
            product_type=product_data.product_type,
            tax_treatment=product_data.tax_treatment,
            status=ProductStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self._products[self._key(business_id, product_id)] = product
        return product

    async def get_by_id(self, product_id: str, business_id: str) -> Optional[ProductInDB]:
        return self._products.get(self._key(business_id, product_id))

    async def list_by_business(
        self,
        business_id: str,
        status: Optional[ProductStatus] = None,
        product_type: Optional[ProductType] = None,
        category_id: Optional[str] = None,
        search: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[ProductInDB]:
        results = []
        for prod in self._products.values():
            if prod.business_id != business_id:
                continue
            
            # Status filter
            if status is not None:
                if prod.status != status:
                    continue
            elif not include_archived and prod.status == ProductStatus.ARCHIVED:
                continue

            # Product type filter
            if product_type is not None and prod.product_type != product_type:
                continue

            # Category filter
            if category_id is not None:
                if prod.category_id != category_id:
                    continue

            # Search filter (code or name)
            if search is not None and search.strip():
                query = search.strip().lower()
                if query not in prod.code.lower() and query not in prod.name.lower():
                    continue

            results.append(prod)

        # Deterministic sorting: name ASC, then code ASC, then id ASC
        results.sort(key=lambda p: (p.name.lower(), p.code.upper(), p.id))
        return results

    async def update(
        self,
        product_id: str,
        business_id: str,
        update_data: ProductUpdate,
    ) -> Optional[ProductInDB]:
        key = self._key(business_id, product_id)
        product = self._products.get(key)
        if not product:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return product

        current = product.model_dump()
        for field, value in update_dict.items():
            if field == "code" and value is not None:
                current[field] = value.strip().upper()
            elif field == "name" and value is not None:
                current[field] = value.strip()
            elif field == "description" and value is not None:
                current[field] = value.strip() if value else None
            else:
                current[field] = value
        current["updated_at"] = datetime.now(timezone.utc)

        updated = ProductInDB(**current)
        self._products[key] = updated
        return updated

    async def archive(self, product_id: str, business_id: str) -> Optional[ProductInDB]:
        key = self._key(business_id, product_id)
        product = self._products.get(key)
        if not product:
            return None
        updated = product.model_copy(
            update={
                "status": ProductStatus.ARCHIVED,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._products[key] = updated
        return updated

    async def find_by_code(self, business_id: str, code: str) -> Optional[ProductInDB]:
        norm = code.strip().upper()
        for prod in self._products.values():
            if prod.business_id == business_id and prod.code.upper() == norm:
                return prod
        return None

    async def exists(self, product_id: str, business_id: str) -> bool:
        return self._key(business_id, product_id) in self._products

    @classmethod
    def clear(cls):
        cls._products.clear()


product_repository = InMemoryProductRepository()
