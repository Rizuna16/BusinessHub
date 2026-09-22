from datetime import datetime, timezone
from typing import Dict, List, Optional
from decimal import Decimal
import uuid
from abc import ABC, abstractmethod
from pydantic import BaseModel

from app.modules.customer.schemas import (
    CustomerCreate,
    CustomerUpdate,
    CustomerStatus,
    CustomerType,
    CustomerResponse,
)


class CustomerInDB(BaseModel):
    id: str
    business_id: str
    customer_type: CustomerType
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
    status: CustomerStatus = CustomerStatus.ACTIVE
    credit_limit: Decimal = Decimal("0.00")
    store_credit_balance: Decimal = Decimal("0.00")
    created_at: datetime
    updated_at: datetime


class AbstractCustomerRepository(ABC):
    @abstractmethod
    async def create(
        self,
        business_id: str,
        customer_data: CustomerCreate,
        code: str,
    ) -> CustomerInDB:
        pass

    @abstractmethod
    async def get_by_id(self, customer_id: str, business_id: str) -> Optional[CustomerInDB]:
        pass

    async def get_by_id_for_update(self, customer_id: str, business_id: str) -> Optional[CustomerInDB]:
        return await self.get_by_id(customer_id, business_id)

    @abstractmethod
    async def list_by_business(
        self,
        business_id: str,
        search: Optional[str] = None,
        status: Optional[CustomerStatus] = None,
        customer_type: Optional[CustomerType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[CustomerInDB], int]:
        pass

    @abstractmethod
    async def update(
        self,
        customer_id: str,
        business_id: str,
        update_data: CustomerUpdate,
    ) -> Optional[CustomerInDB]:
        pass

    @abstractmethod
    async def update_status(
        self,
        customer_id: str,
        business_id: str,
        status: CustomerStatus,
    ) -> Optional[CustomerInDB]:
        pass

    @abstractmethod
    async def update_credit_fields(
        self,
        customer_id: str,
        business_id: str,
        credit_limit: Optional[Decimal] = None,
        store_credit_balance: Optional[Decimal] = None,
    ) -> Optional[CustomerInDB]:
        pass

    @abstractmethod
    async def find_by_code(self, business_id: str, code: str) -> Optional[CustomerInDB]:
        pass

    @abstractmethod
    async def count_by_business(self, business_id: str) -> int:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryCustomerRepository(AbstractCustomerRepository):
    """
    In-memory repository for Customer entities.
    Strictly scoped by business_id.
    """
    _customers: Dict[str, CustomerInDB] = {}  # keyed by "business_id:customer_id"

    def _key(self, business_id: str, customer_id: str) -> str:
        return f"{business_id}:{customer_id}"

    async def create(
        self,
        business_id: str,
        customer_data: CustomerCreate,
        code: str,
    ) -> CustomerInDB:
        customer_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        customer = CustomerInDB(
            id=customer_id,
            business_id=business_id,
            customer_type=customer_data.customer_type,
            code=code.strip().upper(),
            name=customer_data.name,
            legal_name=customer_data.legal_name,
            phone=customer_data.phone,
            email=customer_data.email,
            address=customer_data.address,
            city=customer_data.city,
            province=customer_data.province,
            postal_code=customer_data.postal_code,
            country=customer_data.country,
            notes=customer_data.notes,
            status=CustomerStatus.ACTIVE,
            credit_limit=customer_data.credit_limit,
            store_credit_balance=customer_data.store_credit_balance,
            created_at=now,
            updated_at=now,
        )
        self._customers[self._key(business_id, customer_id)] = customer
        return customer

    async def get_by_id(self, customer_id: str, business_id: str) -> Optional[CustomerInDB]:
        return self._customers.get(self._key(business_id, customer_id))

    async def get_by_id_for_update(self, customer_id: str, business_id: str) -> Optional[CustomerInDB]:
        return self._customers.get(self._key(business_id, customer_id))

    async def list_by_business(
        self,
        business_id: str,
        search: Optional[str] = None,
        status: Optional[CustomerStatus] = None,
        customer_type: Optional[CustomerType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[CustomerInDB], int]:
        results = []
        search_lower = search.strip().lower() if search else None

        for cust in self._customers.values():
            if cust.business_id != business_id:
                continue
            
            # Filter by status
            if status is not None and cust.status != status:
                continue

            # Filter by customer_type
            if customer_type is not None and cust.customer_type != customer_type:
                continue

            # Filter by search
            if search_lower:
                match_code = search_lower in cust.code.lower()
                match_name = search_lower in cust.name.lower()
                match_legal = cust.legal_name and search_lower in cust.legal_name.lower()
                match_phone = cust.phone and search_lower in cust.phone.lower()
                match_email = cust.email and search_lower in cust.email.lower()
                if not (match_code or match_name or match_legal or match_phone or match_email):
                    continue

            results.append(cust)

        # Default deterministic ordering: created_at ASC, id ASC
        results.sort(key=lambda c: (c.created_at, c.id))

        total = len(results)

        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated = results[start:end]

        return paginated, total

    async def update(
        self,
        customer_id: str,
        business_id: str,
        update_data: CustomerUpdate,
    ) -> Optional[CustomerInDB]:
        key = self._key(business_id, customer_id)
        customer = self._customers.get(key)
        if not customer:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return customer

        current = customer.model_dump()
        for field, value in update_dict.items():
            current[field] = value
        current["updated_at"] = datetime.now(timezone.utc)

        updated = CustomerInDB(**current)
        self._customers[key] = updated
        return updated

    async def update_status(
        self,
        customer_id: str,
        business_id: str,
        status: CustomerStatus,
    ) -> Optional[CustomerInDB]:
        key = self._key(business_id, customer_id)
        customer = self._customers.get(key)
        if not customer:
            return None
        updated = customer.model_copy(
            update={
                "status": status,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._customers[key] = updated
        return updated

    async def update_credit_fields(
        self,
        customer_id: str,
        business_id: str,
        credit_limit: Optional[Decimal] = None,
        store_credit_balance: Optional[Decimal] = None,
    ) -> Optional[CustomerInDB]:
        key = self._key(business_id, customer_id)
        customer = self._customers.get(key)
        if not customer:
            return None
        updates: dict = {"updated_at": datetime.now(timezone.utc)}
        if credit_limit is not None:
            updates["credit_limit"] = credit_limit
        if store_credit_balance is not None:
            updates["store_credit_balance"] = store_credit_balance
        updated = customer.model_copy(update=updates)
        self._customers[key] = updated
        return updated

    async def find_by_code(self, business_id: str, code: str) -> Optional[CustomerInDB]:
        norm = code.strip().upper()
        for cust in self._customers.values():
            if cust.business_id == business_id and cust.code.upper() == norm:
                return cust
        return None

    async def count_by_business(self, business_id: str) -> int:
        count = 0
        for cust in self._customers.values():
            if cust.business_id == business_id:
                count += 1
        return count

    @classmethod
    def clear(cls):
        cls._customers.clear()


customer_repository: AbstractCustomerRepository = InMemoryCustomerRepository()
