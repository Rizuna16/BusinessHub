from datetime import datetime, timezone
from typing import Dict, List, Optional
from decimal import Decimal
import uuid
from abc import ABC, abstractmethod

from app.modules.cashier_shift.schemas import (
    CashierShiftInDB,
    ShiftStatus,
)


class AbstractCashierShiftRepository(ABC):
    @abstractmethod
    async def create_shift(
        self,
        business_id: str,
        branch_id: str,
        cashier_user_id: str,
        cash_account_id: str,
        opening_balance: Decimal,
        notes: Optional[str] = None,
    ) -> CashierShiftInDB:
        pass

    @abstractmethod
    async def get_shift_by_id(self, shift_id: str, business_id: str) -> Optional[CashierShiftInDB]:
        pass

    @abstractmethod
    async def get_open_shift(
        self, business_id: str, cash_account_id: str
    ) -> Optional[CashierShiftInDB]:
        pass

    @abstractmethod
    async def list_shifts(
        self,
        business_id: str,
        status_filter: Optional[ShiftStatus] = None,
        branch_id: Optional[str] = None,
        cashier_user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[CashierShiftInDB], int]:
        pass

    @abstractmethod
    async def update_shift(
        self,
        shift_id: str,
        business_id: str,
        **kwargs,
    ) -> Optional[CashierShiftInDB]:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryCashierShiftRepository(AbstractCashierShiftRepository):
    _shifts: Dict[str, CashierShiftInDB] = {}

    async def create_shift(
        self,
        business_id: str,
        branch_id: str,
        cashier_user_id: str,
        cash_account_id: str,
        opening_balance: Decimal,
        notes: Optional[str] = None,
    ) -> CashierShiftInDB:
        shift_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        shift = CashierShiftInDB(
            id=shift_id,
            business_id=business_id,
            branch_id=branch_id,
            cashier_user_id=cashier_user_id,
            cash_account_id=cash_account_id,
            opening_balance=opening_balance,
            actual_cash_count=None,
            discrepancy=None,
            status=ShiftStatus.OPEN,
            opened_at=now,
            closed_at=None,
            closed_by_user_id=None,
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        self._shifts[shift_id] = shift
        return shift

    async def get_shift_by_id(self, shift_id: str, business_id: str) -> Optional[CashierShiftInDB]:
        s = self._shifts.get(shift_id)
        if not s or s.business_id != business_id:
            return None
        return s

    async def get_open_shift(
        self, business_id: str, cash_account_id: str
    ) -> Optional[CashierShiftInDB]:
        for s in self._shifts.values():
            if (
                s.business_id == business_id
                and s.cash_account_id == cash_account_id
                and s.status == ShiftStatus.OPEN
            ):
                return s
        return None

    async def list_shifts(
        self,
        business_id: str,
        status_filter: Optional[ShiftStatus] = None,
        branch_id: Optional[str] = None,
        cashier_user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[CashierShiftInDB], int]:
        filtered = []
        for s in self._shifts.values():
            if s.business_id != business_id:
                continue
            if status_filter and s.status != status_filter:
                continue
            if branch_id and s.branch_id != branch_id:
                continue
            if cashier_user_id and s.cashier_user_id != cashier_user_id:
                continue
            filtered.append(s)

        filtered.sort(key=lambda x: (x.opened_at, x.id), reverse=True)
        total = len(filtered)

        start = (page - 1) * page_size
        end = start + page_size
        return filtered[start:end], total

    async def update_shift(
        self,
        shift_id: str,
        business_id: str,
        **kwargs,
    ) -> Optional[CashierShiftInDB]:
        s = await self.get_shift_by_id(shift_id, business_id)
        if not s:
            return None

        data = s.model_dump()
        for key, value in kwargs.items():
            if key in data:
                data[key] = value
        data["updated_at"] = datetime.now(timezone.utc)
        updated = CashierShiftInDB(**data)
        self._shifts[shift_id] = updated
        return updated

    @classmethod
    def clear(cls):
        cls._shifts.clear()


cashier_shift_repository = InMemoryCashierShiftRepository()
