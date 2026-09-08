from datetime import datetime, timezone
from typing import Dict, List, Optional
from decimal import Decimal
import uuid
from abc import ABC, abstractmethod

from app.modules.sales_payment.schemas import (
    SalesPaymentInDB,
    PaymentMethod,
    PaymentStatus,
)


class AbstractSalesPaymentRepository(ABC):
    @abstractmethod
    async def create_payment(
        self,
        business_id: str,
        sales_id: str,
        payment_number: str,
        payment_date: datetime,
        payment_method: PaymentMethod,
        amount: Decimal,
        created_by_user_id: str,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> SalesPaymentInDB:
        pass

    @abstractmethod
    async def get_payment_by_id(self, payment_id: str, business_id: str) -> Optional[SalesPaymentInDB]:
        pass

    @abstractmethod
    async def list_payments_for_sales(
        self,
        business_id: str,
        sales_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[SalesPaymentInDB], int]:
        pass

    @abstractmethod
    async def get_active_payments_total(self, business_id: str, sales_id: str) -> Decimal:
        pass

    @abstractmethod
    async def cancel_payment(
        self,
        payment_id: str,
        business_id: str,
        cancelled_by_user_id: str,
        cancelled_at: datetime,
    ) -> Optional[SalesPaymentInDB]:
        pass

    @abstractmethod
    async def get_next_payment_sequence(self, business_id: str) -> int:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemorySalesPaymentRepository(AbstractSalesPaymentRepository):
    _payments: Dict[str, SalesPaymentInDB] = {}
    _sequences: Dict[str, int] = {}

    async def get_next_payment_sequence(self, business_id: str) -> int:
        current = self._sequences.get(business_id, 0)
        current += 1
        self._sequences[business_id] = current
        return current

    async def create_payment(
        self,
        business_id: str,
        sales_id: str,
        payment_number: str,
        payment_date: datetime,
        payment_method: PaymentMethod,
        amount: Decimal,
        created_by_user_id: str,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> SalesPaymentInDB:
        payment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        payment = SalesPaymentInDB(
            id=payment_id,
            business_id=business_id,
            sales_id=sales_id,
            payment_number=payment_number,
            payment_date=payment_date,
            payment_method=payment_method,
            amount=amount,
            reference_number=reference_number,
            notes=notes,
            status=PaymentStatus.RECORDED,
            created_by_user_id=created_by_user_id,
            cancelled_by_user_id=None,
            created_at=now,
            updated_at=now,
            cancelled_at=None,
        )
        self._payments[payment_id] = payment
        return payment

    async def get_payment_by_id(self, payment_id: str, business_id: str) -> Optional[SalesPaymentInDB]:
        p = self._payments.get(payment_id)
        if not p or p.business_id != business_id:
            return None
        return p

    async def list_payments_for_sales(
        self,
        business_id: str,
        sales_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[SalesPaymentInDB], int]:
        filtered = [
            p for p in self._payments.values()
            if p.business_id == business_id and p.sales_id == sales_id
        ]
        filtered.sort(key=lambda x: (x.payment_date, x.created_at, x.id), reverse=True)

        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = filtered[start:end]
        return paginated, total

    async def get_active_payments_total(self, business_id: str, sales_id: str) -> Decimal:
        total = Decimal("0")
        for p in self._payments.values():
            if p.business_id == business_id and p.sales_id == sales_id and p.status == PaymentStatus.RECORDED:
                total += p.amount
        return total

    async def cancel_payment(
        self,
        payment_id: str,
        business_id: str,
        cancelled_by_user_id: str,
        cancelled_at: datetime,
    ) -> Optional[SalesPaymentInDB]:
        p = await self.get_payment_by_id(payment_id, business_id)
        if not p:
            return None

        update_data = p.model_dump()
        update_data["status"] = PaymentStatus.CANCELLED
        update_data["cancelled_by_user_id"] = cancelled_by_user_id
        update_data["cancelled_at"] = cancelled_at
        update_data["updated_at"] = datetime.now(timezone.utc)

        updated = SalesPaymentInDB(**update_data)
        self._payments[payment_id] = updated
        return updated

    @classmethod
    def clear(cls):
        cls._payments.clear()
        cls._sequences.clear()


sales_payment_repository = InMemorySalesPaymentRepository()
