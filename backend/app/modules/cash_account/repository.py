from datetime import datetime, timezone
from typing import Dict, List, Optional
from decimal import Decimal
import uuid
from abc import ABC, abstractmethod

from app.modules.cash_account.schemas import (
    CashAccountInDB,
    CashMovementInDB,
    CashAccountType,
    CashAccountStatus,
    CashMovementType,
    MovementDirection,
    CashMovementStatus,
)


class AbstractCashAccountRepository(ABC):
    @abstractmethod
    async def create_account(
        self,
        business_id: str,
        name: str,
        code: str,
        account_type: CashAccountType,
        currency: str,
        opening_balance: Decimal,
        is_default: bool,
        description: Optional[str] = None,
    ) -> CashAccountInDB:
        pass

    @abstractmethod
    async def get_account_by_id(self, account_id: str, business_id: str) -> Optional[CashAccountInDB]:
        pass

    @abstractmethod
    async def get_account_by_code(self, business_id: str, code: str) -> Optional[CashAccountInDB]:
        pass

    @abstractmethod
    async def get_default_account(self, business_id: str) -> Optional[CashAccountInDB]:
        pass

    @abstractmethod
    async def list_accounts(
        self,
        business_id: str,
        account_type: Optional[CashAccountType] = None,
        status: Optional[CashAccountStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[CashAccountInDB], int]:
        pass

    @abstractmethod
    async def update_account(
        self,
        account_id: str,
        business_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[CashAccountStatus] = None,
        is_default: Optional[bool] = None,
    ) -> Optional[CashAccountInDB]:
        pass

    @abstractmethod
    async def create_movement(
        self,
        business_id: str,
        cash_account_id: str,
        movement_type: CashMovementType,
        amount: Decimal,
        direction: MovementDirection,
        performed_by_user_id: str,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> CashMovementInDB:
        pass

    @abstractmethod
    async def list_movements_for_account(
        self,
        business_id: str,
        cash_account_id: str,
        movement_type: Optional[CashMovementType] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[CashMovementInDB], int]:
        pass

    @abstractmethod
    async def list_all_movements_for_account(
        self, business_id: str, cash_account_id: str
    ) -> List[CashMovementInDB]:
        pass

    @abstractmethod
    async def find_movement_by_reference(
        self, business_id: str, reference_type: str, reference_id: str
    ) -> Optional[CashMovementInDB]:
        pass

    @abstractmethod
    async def delete_movement_by_reference(
        self, business_id: str, reference_type: str, reference_id: str
    ) -> bool:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryCashAccountRepository(AbstractCashAccountRepository):
    _accounts: Dict[str, CashAccountInDB] = {}
    _movements: Dict[str, CashMovementInDB] = {}

    async def create_account(
        self,
        business_id: str,
        name: str,
        code: str,
        account_type: CashAccountType,
        currency: str,
        opening_balance: Decimal,
        is_default: bool,
        description: Optional[str] = None,
    ) -> CashAccountInDB:
        # If new account is default, unset any existing default
        if is_default:
            for a in self._accounts.values():
                if a.business_id == business_id and a.is_default:
                    d = a.model_dump()
                    d["is_default"] = False
                    d["updated_at"] = datetime.now(timezone.utc)
                    self._accounts[a.id] = CashAccountInDB(**d)

        account_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        account = CashAccountInDB(
            id=account_id,
            business_id=business_id,
            name=name,
            code=code.upper(),
            account_type=account_type,
            currency=currency,
            description=description,
            opening_balance=opening_balance,
            status=CashAccountStatus.ACTIVE,
            is_default=is_default,
            created_at=now,
            updated_at=now,
        )
        self._accounts[account_id] = account
        return account

    async def get_account_by_id(self, account_id: str, business_id: str) -> Optional[CashAccountInDB]:
        a = self._accounts.get(account_id)
        if not a or a.business_id != business_id:
            return None
        return a

    async def get_account_by_code(self, business_id: str, code: str) -> Optional[CashAccountInDB]:
        code_upper = code.upper()
        for a in self._accounts.values():
            if a.business_id == business_id and a.code == code_upper and a.status != CashAccountStatus.ARCHIVED:
                return a
        return None

    async def get_default_account(self, business_id: str) -> Optional[CashAccountInDB]:
        for a in self._accounts.values():
            if a.business_id == business_id and a.status == CashAccountStatus.ACTIVE and a.is_default:
                return a
        return None

    async def list_accounts(
        self,
        business_id: str,
        account_type: Optional[CashAccountType] = None,
        status: Optional[CashAccountStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[CashAccountInDB], int]:
        filtered = []
        for a in self._accounts.values():
            if a.business_id != business_id or a.status == CashAccountStatus.ARCHIVED:
                continue
            if account_type and a.account_type != account_type:
                continue
            if status and a.status != status:
                continue
            if search:
                s_lower = search.lower()
                if s_lower not in a.name.lower() and s_lower not in a.code.lower():
                    continue
            filtered.append(a)

        filtered.sort(key=lambda x: (x.is_default, x.created_at, x.id), reverse=True)
        total = len(filtered)

        start = (page - 1) * page_size
        end = start + page_size
        return filtered[start:end], total

    async def update_account(
        self,
        account_id: str,
        business_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[CashAccountStatus] = None,
        is_default: Optional[bool] = None,
    ) -> Optional[CashAccountInDB]:
        a = await self.get_account_by_id(account_id, business_id)
        if not a:
            return None

        if is_default:
            for acc in self._accounts.values():
                if acc.business_id == business_id and acc.is_default and acc.id != account_id:
                    d = acc.model_dump()
                    d["is_default"] = False
                    d["updated_at"] = datetime.now(timezone.utc)
                    self._accounts[acc.id] = CashAccountInDB(**d)

        data = a.model_dump()
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if status is not None:
            data["status"] = status
        if is_default is not None:
            data["is_default"] = is_default

        data["updated_at"] = datetime.now(timezone.utc)
        updated = CashAccountInDB(**data)
        self._accounts[account_id] = updated
        return updated

    async def create_movement(
        self,
        business_id: str,
        cash_account_id: str,
        movement_type: CashMovementType,
        amount: Decimal,
        direction: MovementDirection,
        performed_by_user_id: str,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> CashMovementInDB:
        mov_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        mov = CashMovementInDB(
            id=mov_id,
            business_id=business_id,
            cash_account_id=cash_account_id,
            movement_type=movement_type,
            amount=amount,
            direction=direction,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
            performed_by_user_id=performed_by_user_id,
            status=CashMovementStatus.POSTED,
            created_at=now,
            updated_at=now,
        )
        self._movements[mov_id] = mov
        return mov

    async def list_movements_for_account(
        self,
        business_id: str,
        cash_account_id: str,
        movement_type: Optional[CashMovementType] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[CashMovementInDB], int]:
        filtered = []
        for m in self._movements.values():
            if m.business_id != business_id or m.cash_account_id != cash_account_id:
                continue
            if movement_type and m.movement_type != movement_type:
                continue
            if date_from and m.created_at < date_from:
                continue
            if date_to and m.created_at > date_to:
                continue
            filtered.append(m)

        filtered.sort(key=lambda x: (x.created_at, x.id), reverse=True)
        total = len(filtered)

        start = (page - 1) * page_size
        end = start + page_size
        return filtered[start:end], total

    async def list_all_movements_for_account(
        self, business_id: str, cash_account_id: str
    ) -> List[CashMovementInDB]:
        return [
            m for m in self._movements.values()
            if m.business_id == business_id and m.cash_account_id == cash_account_id and m.status == CashMovementStatus.POSTED
        ]

    async def find_movement_by_reference(
        self, business_id: str, reference_type: str, reference_id: str
    ) -> Optional[CashMovementInDB]:
        for m in self._movements.values():
            if m.business_id == business_id and m.reference_type == reference_type and m.reference_id == reference_id:
                return m
        return None

    async def delete_movement_by_reference(
        self, business_id: str, reference_type: str, reference_id: str
    ) -> bool:
        to_delete = [
            m_id for m_id, m in self._movements.items()
            if m.business_id == business_id and m.reference_type == reference_type and m.reference_id == reference_id
        ]
        for m_id in to_delete:
            del self._movements[m_id]
        return len(to_delete) > 0

    @classmethod
    def clear(cls):
        cls._accounts.clear()
        cls._movements.clear()


cash_account_repository = InMemoryCashAccountRepository()
