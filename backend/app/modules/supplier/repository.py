from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid
from abc import ABC, abstractmethod
from pydantic import BaseModel

from app.modules.supplier.schemas import (
    SupplierCreate,
    SupplierUpdate,
    SupplierStatus,
    SupplierType,
)


class SupplierInDB(BaseModel):
    id: str
    business_id: str
    supplier_type: SupplierType
    code: str
    name: str
    legal_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    notes: Optional[str] = None
    status: SupplierStatus = SupplierStatus.ACTIVE
    created_at: datetime
    updated_at: datetime


class AbstractSupplierRepository(ABC):
    @abstractmethod
    async def create(
        self,
        business_id: str,
        supplier_data: SupplierCreate,
        code: str,
    ) -> SupplierInDB:
        pass

    @abstractmethod
    async def get_by_id(self, supplier_id: str, business_id: str) -> Optional[SupplierInDB]:
        pass

    @abstractmethod
    async def list_by_business(
        self,
        business_id: str,
        search: Optional[str] = None,
        status: Optional[SupplierStatus] = None,
        supplier_type: Optional[SupplierType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[SupplierInDB], int]:
        pass

    @abstractmethod
    async def update(
        self,
        supplier_id: str,
        business_id: str,
        update_data: SupplierUpdate,
    ) -> Optional[SupplierInDB]:
        pass

    @abstractmethod
    async def update_status(
        self,
        supplier_id: str,
        business_id: str,
        status: SupplierStatus,
    ) -> Optional[SupplierInDB]:
        pass

    @abstractmethod
    async def find_by_code(self, business_id: str, code: str) -> Optional[SupplierInDB]:
        pass

    @abstractmethod
    async def count_by_business(self, business_id: str) -> int:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemorySupplierRepository(AbstractSupplierRepository):
    """
    In-memory repository for Supplier entities.
    Strictly scoped by business_id.
    """
    _suppliers: Dict[str, SupplierInDB] = {}  # keyed by "business_id:supplier_id"

    def _key(self, business_id: str, supplier_id: str) -> str:
        return f"{business_id}:{supplier_id}"

    async def create(
        self,
        business_id: str,
        supplier_data: SupplierCreate,
        code: str,
    ) -> SupplierInDB:
        supplier_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        supplier = SupplierInDB(
            id=supplier_id,
            business_id=business_id,
            supplier_type=supplier_data.supplier_type,
            code=code.strip().upper(),
            name=supplier_data.name,
            legal_name=supplier_data.legal_name,
            phone=supplier_data.phone,
            email=supplier_data.email,
            address=supplier_data.address,
            city=supplier_data.city,
            province=supplier_data.province,
            postal_code=supplier_data.postal_code,
            country=supplier_data.country,
            notes=supplier_data.notes,
            status=SupplierStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self._suppliers[self._key(business_id, supplier_id)] = supplier
        return supplier

    async def get_by_id(self, supplier_id: str, business_id: str) -> Optional[SupplierInDB]:
        return self._suppliers.get(self._key(business_id, supplier_id))

    async def list_by_business(
        self,
        business_id: str,
        search: Optional[str] = None,
        status: Optional[SupplierStatus] = None,
        supplier_type: Optional[SupplierType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[SupplierInDB], int]:
        results = []
        search_lower = search.strip().lower() if search else None

        for sup in self._suppliers.values():
            if sup.business_id != business_id:
                continue

            if status is not None and sup.status != status:
                continue

            if supplier_type is not None and sup.supplier_type != supplier_type:
                continue

            if search_lower:
                match_code = search_lower in sup.code.lower()
                match_name = search_lower in sup.name.lower()
                match_legal = sup.legal_name and search_lower in sup.legal_name.lower()
                match_phone = sup.phone and search_lower in sup.phone.lower()
                match_email = sup.email and search_lower in sup.email.lower()
                if not (match_code or match_name or match_legal or match_phone or match_email):
                    continue

            results.append(sup)

        # Default deterministic ordering: created_at ASC, id ASC
        results.sort(key=lambda s: (s.created_at, s.id))

        total = len(results)

        start = (page - 1) * page_size
        end = start + page_size
        paginated = results[start:end]

        return paginated, total

    async def update(
        self,
        supplier_id: str,
        business_id: str,
        update_data: SupplierUpdate,
    ) -> Optional[SupplierInDB]:
        key = self._key(business_id, supplier_id)
        supplier = self._suppliers.get(key)
        if not supplier:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return supplier

        current = supplier.model_dump()
        for field, value in update_dict.items():
            current[field] = value
        current["updated_at"] = datetime.now(timezone.utc)

        updated = SupplierInDB(**current)
        self._suppliers[key] = updated
        return updated

    async def update_status(
        self,
        supplier_id: str,
        business_id: str,
        status: SupplierStatus,
    ) -> Optional[SupplierInDB]:
        key = self._key(business_id, supplier_id)
        supplier = self._suppliers.get(key)
        if not supplier:
            return None
        updated = supplier.model_copy(
            update={
                "status": status,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._suppliers[key] = updated
        return updated

    async def find_by_code(self, business_id: str, code: str) -> Optional[SupplierInDB]:
        norm = code.strip().upper()
        for sup in self._suppliers.values():
            if sup.business_id == business_id and sup.code.upper() == norm:
                return sup
        return None

    async def count_by_business(self, business_id: str) -> int:
        count = 0
        for sup in self._suppliers.values():
            if sup.business_id == business_id:
                count += 1
        return count

    @classmethod
    def clear(cls):
        cls._suppliers.clear()


supplier_repository: AbstractSupplierRepository = InMemorySupplierRepository()
