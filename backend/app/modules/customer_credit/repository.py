from datetime import datetime, timezone
from typing import Dict, List, Optional
from decimal import Decimal
import uuid
from abc import ABC, abstractmethod

from app.modules.customer_credit.schemas import StoreCreditLedgerEntry


class AbstractStoreCreditLedgerRepository(ABC):
    @abstractmethod
    async def append(
        self,
        customer_id: str,
        business_id: str,
        amount: Decimal,
        balance_after: Decimal,
        direction: str,
        reference_type: Optional[str],
        reference_id: Optional[str],
        reason: Optional[str],
        created_by_user_id: str,
    ) -> StoreCreditLedgerEntry:
        pass

    @abstractmethod
    async def list_by_customer(
        self,
        customer_id: str,
        business_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[StoreCreditLedgerEntry], int]:
        pass

    @abstractmethod
    async def sum_issued_not_voided(
        self, customer_id: str, business_id: str
    ) -> Decimal:
        pass

    @abstractmethod
    async def sum_redeemed_not_voided(
        self, customer_id: str, business_id: str
    ) -> Decimal:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryStoreCreditLedgerRepository(AbstractStoreCreditLedgerRepository):
    _entries: List[StoreCreditLedgerEntry] = []

    async def append(
        self,
        customer_id: str,
        business_id: str,
        amount: Decimal,
        balance_after: Decimal,
        direction: str,
        reference_type: Optional[str],
        reference_id: Optional[str],
        reason: Optional[str],
        created_by_user_id: str,
    ) -> StoreCreditLedgerEntry:
        entry_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        entry = StoreCreditLedgerEntry(
            id=entry_id,
            customer_id=customer_id,
            business_id=business_id,
            amount=amount,
            balance_after=balance_after,
            direction=direction,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason,
            created_by_user_id=created_by_user_id,
            created_at=now,
        )
        self._entries.append(entry)
        return entry

    async def list_by_customer(
        self,
        customer_id: str,
        business_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[StoreCreditLedgerEntry], int]:
        filtered = [
            e for e in self._entries
            if e.customer_id == customer_id and e.business_id == business_id
        ]
        filtered.sort(key=lambda x: (x.created_at, x.id))
        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        return filtered[start:end], total

    async def sum_issued_not_voided(
        self, customer_id: str, business_id: str
    ) -> Decimal:
        total = Decimal("0")
        for e in self._entries:
            if e.customer_id == customer_id and e.business_id == business_id and e.direction == "ISSUED":
                total += e.amount
        return total

    async def sum_redeemed_not_voided(
        self, customer_id: str, business_id: str
    ) -> Decimal:
        total = Decimal("0")
        for e in self._entries:
            if e.customer_id == customer_id and e.business_id == business_id and e.direction == "REDEEMED":
                total += e.amount
        return total

    @classmethod
    def clear(cls):
        cls._entries.clear()


store_credit_ledger_repository: AbstractStoreCreditLedgerRepository = (
    InMemoryStoreCreditLedgerRepository()
)
