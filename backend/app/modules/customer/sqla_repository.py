from datetime import datetime, timezone
from typing import Optional, List, Tuple
from decimal import Decimal

from sqlalchemy import select, func, and_, or_, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.customer.models import Customer
from app.modules.customer.repository import AbstractCustomerRepository, CustomerInDB
from app.modules.customer.schemas import (
    CustomerCreate,
    CustomerUpdate,
    CustomerStatus,
    CustomerType,
)
from app.modules.sqla_base import sa_create


def _to_customer_in_db(obj: Customer) -> CustomerInDB:
    return CustomerInDB(
        id=obj.id,
        business_id=obj.business_id,
        customer_type=CustomerType(obj.customer_type),
        code=obj.code,
        name=obj.name,
        legal_name=obj.legal_name,
        phone=obj.phone,
        email=obj.email,
        address=obj.address,
        city=obj.city,
        province=obj.province,
        postal_code=obj.postal_code,
        country=obj.country,
        notes=obj.notes,
        status=CustomerStatus(obj.status),
        credit_limit=obj.credit_limit,
        store_credit_balance=obj.store_credit_balance,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyCustomerRepository(AbstractCustomerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        business_id: str,
        customer_data: CustomerCreate,
        code: str,
    ) -> CustomerInDB:
        data = {
            "business_id": business_id,
            "customer_type": customer_data.customer_type.value,
            "code": code.strip().upper(),
            "name": customer_data.name,
            "legal_name": customer_data.legal_name,
            "phone": customer_data.phone,
            "email": customer_data.email,
            "address": customer_data.address,
            "city": customer_data.city,
            "province": customer_data.province,
            "postal_code": customer_data.postal_code,
            "country": customer_data.country,
            "notes": customer_data.notes,
            "status": CustomerStatus.ACTIVE.value,
            "credit_limit": customer_data.credit_limit,
            "store_credit_balance": customer_data.store_credit_balance,
        }
        obj = await sa_create(self.session, Customer, data)
        return _to_customer_in_db(obj)

    async def get_by_id(self, customer_id: str, business_id: str) -> Optional[CustomerInDB]:
        stmt = select(Customer).where(
            Customer.id == customer_id,
            Customer.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_customer_in_db(obj) if obj else None

    async def list_by_business(
        self,
        business_id: str,
        search: Optional[str] = None,
        status: Optional[CustomerStatus] = None,
        customer_type: Optional[CustomerType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[CustomerInDB], int]:
        filters = [Customer.business_id == business_id]
        if status is not None:
            filters.append(Customer.status == status.value)
        if customer_type is not None:
            filters.append(Customer.customer_type == customer_type.value)
        if search is not None and search.strip():
            q = f"%{search.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(Customer.code).like(q),
                    func.lower(Customer.name).like(q),
                    func.lower(Customer.legal_name).like(q),
                    func.lower(Customer.phone).like(q),
                    func.lower(Customer.email).like(q),
                )
            )

        count_stmt = select(func.count()).select_from(Customer).where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Customer)
            .where(and_(*filters))
            .order_by(asc(Customer.created_at), asc(Customer.id))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        result = await self.session.execute(stmt)
        items = [_to_customer_in_db(o) for o in result.scalars().all()]
        return items, total

    async def update(
        self,
        customer_id: str,
        business_id: str,
        update_data: CustomerUpdate,
    ) -> Optional[CustomerInDB]:
        stmt = select(Customer).where(
            Customer.id == customer_id,
            Customer.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return _to_customer_in_db(obj)
        for field, value in update_dict.items():
            setattr(obj, field, value)
        await self.session.flush()
        return _to_customer_in_db(obj)

    async def update_status(
        self,
        customer_id: str,
        business_id: str,
        status: CustomerStatus,
    ) -> Optional[CustomerInDB]:
        stmt = select(Customer).where(
            Customer.id == customer_id,
            Customer.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.status = status.value
        await self.session.flush()
        return _to_customer_in_db(obj)

    async def update_credit_fields(
        self,
        customer_id: str,
        business_id: str,
        credit_limit: Optional[Decimal] = None,
        store_credit_balance: Optional[Decimal] = None,
    ) -> Optional[CustomerInDB]:
        stmt = select(Customer).where(
            Customer.id == customer_id,
            Customer.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        if credit_limit is not None:
            obj.credit_limit = credit_limit
        if store_credit_balance is not None:
            obj.store_credit_balance = store_credit_balance
        await self.session.flush()
        return _to_customer_in_db(obj)

    async def find_by_code(self, business_id: str, code: str) -> Optional[CustomerInDB]:
        norm = code.strip().upper()
        stmt = select(Customer).where(
            Customer.business_id == business_id,
            Customer.code == norm,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_customer_in_db(obj) if obj else None

    async def count_by_business(self, business_id: str) -> int:
        stmt = select(func.count()).select_from(Customer).where(
            Customer.business_id == business_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    @classmethod
    def clear(cls):
        pass
