from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import uuid
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

from app.modules.supplier_catalog.schemas import (
    SupplierCatalogItemCreate,
    SupplierCatalogItemUpdate,
    SupplierCatalogStatus,
)


class SupplierCatalogItemInDB(BaseModel):
    id: str
    business_id: str
    supplier_id: str
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    supplier_code: Optional[str] = None
    supplier_product_name: Optional[str] = None
    purchase_price: Decimal
    currency: str
    minimum_order_quantity: Optional[Decimal] = None
    lead_time_days: Optional[int] = None
    is_preferred: bool = False
    status: SupplierCatalogStatus = SupplierCatalogStatus.ACTIVE
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AbstractSupplierCatalogRepository(ABC):
    @abstractmethod
    async def create(
        self,
        business_id: str,
        item_data: SupplierCatalogItemCreate,
    ) -> SupplierCatalogItemInDB:
        pass

    @abstractmethod
    async def get_by_id(
        self, item_id: str, business_id: str
    ) -> Optional[SupplierCatalogItemInDB]:
        pass

    @abstractmethod
    async def list_by_business(
        self,
        business_id: str,
        search: Optional[str] = None,
        supplier_id: Optional[str] = None,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
        status: Optional[SupplierCatalogStatus] = None,
        is_preferred: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[SupplierCatalogItemInDB], int]:
        pass

    @abstractmethod
    async def update(
        self,
        item_id: str,
        business_id: str,
        update_data: SupplierCatalogItemUpdate,
    ) -> Optional[SupplierCatalogItemInDB]:
        pass

    @abstractmethod
    async def update_status(
        self,
        item_id: str,
        business_id: str,
        status: SupplierCatalogStatus,
    ) -> Optional[SupplierCatalogItemInDB]:
        pass

    @abstractmethod
    async def unset_preferred_for_target(
        self,
        business_id: str,
        product_id: Optional[str],
        variant_id: Optional[str],
        exclude_item_id: Optional[str] = None,
    ) -> None:
        pass

    @abstractmethod
    async def find_existing_item(
        self,
        business_id: str,
        supplier_id: str,
        product_id: Optional[str],
        variant_id: Optional[str],
    ) -> Optional[SupplierCatalogItemInDB]:
        pass

    @abstractmethod
    async def find_active_catalog_item(
        self,
        business_id: str,
        supplier_id: str,
        product_id: Optional[str],
        variant_id: Optional[str],
    ) -> Optional[SupplierCatalogItemInDB]:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemorySupplierCatalogRepository(AbstractSupplierCatalogRepository):
    """
    In-memory repository for SupplierCatalogItem entities.
    Strictly scoped by business_id.
    """

    _items: Dict[str, SupplierCatalogItemInDB] = {}  # keyed by "business_id:item_id"

    def _key(self, business_id: str, item_id: str) -> str:
        return f"{business_id}:{item_id}"

    async def create(
        self,
        business_id: str,
        item_data: SupplierCatalogItemCreate,
    ) -> SupplierCatalogItemInDB:
        item_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        item = SupplierCatalogItemInDB(
            id=item_id,
            business_id=business_id,
            supplier_id=item_data.supplier_id,
            product_id=item_data.product_id,
            variant_id=item_data.variant_id,
            supplier_code=item_data.supplier_code,
            supplier_product_name=item_data.supplier_product_name,
            purchase_price=item_data.purchase_price,
            currency=item_data.currency,
            minimum_order_quantity=item_data.minimum_order_quantity,
            lead_time_days=item_data.lead_time_days,
            is_preferred=item_data.is_preferred,
            status=SupplierCatalogStatus.ACTIVE,
            notes=item_data.notes,
            created_at=now,
            updated_at=now,
        )
        self._items[self._key(business_id, item_id)] = item
        return item

    async def get_by_id(
        self, item_id: str, business_id: str
    ) -> Optional[SupplierCatalogItemInDB]:
        return self._items.get(self._key(business_id, item_id))

    async def list_by_business(
        self,
        business_id: str,
        search: Optional[str] = None,
        supplier_id: Optional[str] = None,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
        status: Optional[SupplierCatalogStatus] = None,
        is_preferred: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[SupplierCatalogItemInDB], int]:
        results = []
        search_lower = search.strip().lower() if search else None

        for item in self._items.values():
            if item.business_id != business_id:
                continue

            if supplier_id and item.supplier_id != supplier_id:
                continue

            if product_id and item.product_id != product_id:
                continue

            if variant_id and item.variant_id != variant_id:
                continue

            if status is not None and item.status != status:
                continue

            if is_preferred is not None and item.is_preferred != is_preferred:
                continue

            if search_lower:
                match_code = (
                    item.supplier_code and search_lower in item.supplier_code.lower()
                )
                match_name = (
                    item.supplier_product_name
                    and search_lower in item.supplier_product_name.lower()
                )
                if not (match_code or match_name):
                    continue

            results.append(item)

        # Sort deterministically by created_at ASC, id ASC
        results.sort(key=lambda x: (x.created_at, x.id))
        total = len(results)

        start = (page - 1) * page_size
        end = start + page_size
        paginated = results[start:end]

        return paginated, total

    async def update(
        self,
        item_id: str,
        business_id: str,
        update_data: SupplierCatalogItemUpdate,
    ) -> Optional[SupplierCatalogItemInDB]:
        key = self._key(business_id, item_id)
        item = self._items.get(key)
        if not item:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return item

        current = item.model_dump()
        for field, value in update_dict.items():
            current[field] = value
        current["updated_at"] = datetime.now(timezone.utc)

        updated = SupplierCatalogItemInDB(**current)
        self._items[key] = updated
        return updated

    async def update_status(
        self,
        item_id: str,
        business_id: str,
        status: SupplierCatalogStatus,
    ) -> Optional[SupplierCatalogItemInDB]:
        key = self._key(business_id, item_id)
        item = self._items.get(key)
        if not item:
            return None

        updated = item.model_copy(
            update={
                "status": status,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._items[key] = updated
        return updated

    async def unset_preferred_for_target(
        self,
        business_id: str,
        product_id: Optional[str],
        variant_id: Optional[str],
        exclude_item_id: Optional[str] = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        for key, item in list(self._items.items()):
            if item.business_id != business_id:
                continue
            if exclude_item_id and item.id == exclude_item_id:
                continue

            target_match = False
            if product_id and item.product_id == product_id:
                target_match = True
            elif variant_id and item.variant_id == variant_id:
                target_match = True

            if target_match and item.is_preferred:
                self._items[key] = item.model_copy(
                    update={
                        "is_preferred": False,
                        "updated_at": now,
                    }
                )

    async def find_existing_item(
        self,
        business_id: str,
        supplier_id: str,
        product_id: Optional[str],
        variant_id: Optional[str],
    ) -> Optional[SupplierCatalogItemInDB]:
        for item in self._items.values():
            if item.business_id != business_id:
                continue
            if item.supplier_id != supplier_id:
                continue

            # Check target uniqueness
            if product_id and item.product_id == product_id:
                return item
            if variant_id and item.variant_id == variant_id:
                return item

        return None

    async def find_active_catalog_item(
        self,
        business_id: str,
        supplier_id: str,
        product_id: Optional[str],
        variant_id: Optional[str],
    ) -> Optional[SupplierCatalogItemInDB]:
        for item in self._items.values():
            if item.business_id != business_id:
                continue
            if item.supplier_id != supplier_id:
                continue
            if item.status != SupplierCatalogStatus.ACTIVE:
                continue

            if product_id and item.product_id == product_id:
                return item
            if variant_id and item.variant_id == variant_id:
                return item

        return None

    @classmethod
    def clear(cls):
        cls._items.clear()


supplier_catalog_repository: AbstractSupplierCatalogRepository = (
    InMemorySupplierCatalogRepository()
)
