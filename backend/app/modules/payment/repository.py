from typing import Dict, List, Optional
from decimal import Decimal
import uuid
from datetime import datetime, timezone
from abc import ABC, abstractmethod

from app.modules.payment.schemas import (
    PaymentInDB,
    PaymentDirection,
    PaymentTargetType,
    PaymentStatus,
)


class AbstractPaymentRepository(ABC):
    @abstractmethod
    async def create_payment(self, payment_data: dict) -> PaymentInDB:
        pass

    @abstractmethod
    async def get_payment_by_id(self, payment_id: str, business_id: str) -> Optional[PaymentInDB]:
        pass

    @abstractmethod
    async def get_payment_by_idempotency_key(self, idempotency_key: str, business_id: str) -> Optional[PaymentInDB]:
        pass

    @abstractmethod
    async def list_payments(
        self,
        business_id: str,
        direction: Optional[PaymentDirection] = None,
        target_type: Optional[PaymentTargetType] = None,
        target_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[PaymentInDB], int]:
        pass

    @abstractmethod
    async def get_active_payments_total_for_target(self, business_id: str, target_type: PaymentTargetType, target_id: str) -> Decimal:
        pass

    @abstractmethod
    async def void_payment(self, payment_id: str, business_id: str, voided_by_user_id: str) -> Optional[PaymentInDB]:
        pass

    @abstractmethod
    async def delete_payment(self, payment_id: str, business_id: str) -> bool:
        pass

    @abstractmethod
    async def reset_to_recorded(self, payment_id: str, business_id: str) -> Optional[PaymentInDB]:
        pass

    @abstractmethod
    async def get_next_payment_sequence(self, business_id: str) -> int:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryPaymentRepository(AbstractPaymentRepository):
    _payments: Dict[str, PaymentInDB] = {}
    _sequences: Dict[str, int] = {}

    async def get_next_payment_sequence(self, business_id: str) -> int:
        current = self._sequences.get(business_id, 0)
        current += 1
        self._sequences[business_id] = current
        return current

    async def create_payment(self, payment_data: dict) -> PaymentInDB:
        payment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        data = dict(payment_data)
        data["id"] = payment_id
        data["created_at"] = now
        data["updated_at"] = now
        
        payment = PaymentInDB(**data)
        self._payments[payment_id] = payment
        return payment

    async def get_payment_by_id(self, payment_id: str, business_id: str) -> Optional[PaymentInDB]:
        p = self._payments.get(payment_id)
        if not p or p.business_id != business_id:
            return None
        return p

    async def get_payment_by_idempotency_key(self, idempotency_key: str, business_id: str) -> Optional[PaymentInDB]:
        for p in self._payments.values():
            if p.business_id == business_id and p.idempotency_key == idempotency_key and p.status == PaymentStatus.RECORDED:
                return p
        return None

    async def list_payments(
        self,
        business_id: str,
        direction: Optional[PaymentDirection] = None,
        target_type: Optional[PaymentTargetType] = None,
        target_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[PaymentInDB], int]:
        filtered = []
        for p in self._payments.values():
            if p.business_id != business_id:
                continue
            if direction and p.direction != direction:
                continue
            if target_type and p.target_type != target_type:
                continue
            if target_id and p.target_id != target_id:
                continue
            filtered.append(p)

        filtered.sort(key=lambda x: (x.payment_date, x.created_at, x.id), reverse=True)
        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        return filtered[start:end], total

    async def get_active_payments_total_for_target(self, business_id: str, target_type: PaymentTargetType, target_id: str) -> Decimal:
        total = Decimal("0")
        for p in self._payments.values():
            if (p.business_id == business_id and 
                p.target_type == target_type and 
                p.target_id == target_id and 
                p.status == PaymentStatus.RECORDED):
                total += p.amount
        return total

    async def void_payment(self, payment_id: str, business_id: str, voided_by_user_id: str) -> Optional[PaymentInDB]:
        p = await self.get_payment_by_id(payment_id, business_id)
        if not p:
            return None
        
        now = datetime.now(timezone.utc)
        
        data = p.model_dump()
        data["status"] = PaymentStatus.VOIDED
        data["voided_by_user_id"] = voided_by_user_id
        data["voided_at"] = now
        data["updated_at"] = now
        
        updated = PaymentInDB(**data)
        self._payments[payment_id] = updated
        return updated

    async def delete_payment(self, payment_id: str, business_id: str) -> bool:
        p = self._payments.get(payment_id)
        if p and p.business_id == business_id:
            del self._payments[payment_id]
            return True
        return False

    async def reset_to_recorded(self, payment_id: str, business_id: str) -> Optional[PaymentInDB]:
        p = await self.get_payment_by_id(payment_id, business_id)
        if not p:
            return None
        now = datetime.now(timezone.utc)
        data = p.model_dump()
        data["status"] = PaymentStatus.RECORDED
        data["voided_by_user_id"] = None
        data["voided_at"] = None
        data["updated_at"] = now
        updated = PaymentInDB(**data)
        self._payments[payment_id] = updated
        return updated

    @classmethod
    def clear(cls):
        cls._payments.clear()
        cls._sequences.clear()


payment_repository = InMemoryPaymentRepository()
