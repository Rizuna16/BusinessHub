from datetime import datetime, timezone, date
from typing import Dict, List, Optional
from decimal import Decimal
import uuid
from abc import ABC, abstractmethod

from app.modules.accounting.schemas import (
    AccountInDB,
    JournalEntryInDB,
    JournalLineInDB,
    AccountingPeriodInDB,
    TaxConfigurationInDB,
    AccountType,
    NormalBalance,
    JournalStatus,
    AccountingPeriodStatus,
)


class AbstractAccountingRepository(ABC):
    @abstractmethod
    async def create_account(self, account_data: dict) -> AccountInDB:
        pass

    @abstractmethod
    async def get_account_by_id(self, account_id: str, business_id: str) -> Optional[AccountInDB]:
        pass

    @abstractmethod
    async def get_account_by_code(self, business_id: str, code: str) -> Optional[AccountInDB]:
        pass

    @abstractmethod
    async def list_accounts(self, business_id: str, account_type: Optional[AccountType] = None) -> List[AccountInDB]:
        pass

    @abstractmethod
    async def update_account(self, account_id: str, business_id: str, update_data: dict) -> Optional[AccountInDB]:
        pass

    @abstractmethod
    async def archive_account(self, account_id: str, business_id: str) -> Optional[AccountInDB]:
        pass

    @abstractmethod
    async def get_next_journal_sequence(self, business_id: str) -> int:
        pass

    @abstractmethod
    async def create_journal_entry(self, entry_data: dict, lines_data: List[dict]) -> tuple[JournalEntryInDB, List[JournalLineInDB]]:
        pass

    @abstractmethod
    async def get_journal_by_id(self, journal_id: str, business_id: str) -> Optional[JournalEntryInDB]:
        pass

    @abstractmethod
    async def get_journal_by_idempotency_key(self, idempotency_key: str, business_id: str) -> Optional[JournalEntryInDB]:
        pass

    @abstractmethod
    async def list_lines_for_journal(self, journal_id: str) -> List[JournalLineInDB]:
        pass

    @abstractmethod
    async def list_journals(
        self,
        business_id: str,
        branch_id: Optional[str] = None,
        status: Optional[JournalStatus] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[JournalEntryInDB], int]:
        pass

    @abstractmethod
    async def void_journal(self, journal_id: str, business_id: str, voided_by_user_id: str) -> Optional[JournalEntryInDB]:
        pass

    @abstractmethod
    async def list_posted_lines_for_account(
        self,
        business_id: str,
        account_id: str,
        branch_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[tuple[JournalEntryInDB, JournalLineInDB]]:
        pass

    @abstractmethod
    async def get_period_for_date(self, business_id: str, check_date: date) -> Optional[AccountingPeriodInDB]:
        pass

    @abstractmethod
    async def close_period(self, business_id: str, period_name: str, closed_by_user_id: str) -> Optional[AccountingPeriodInDB]:
        pass

    @abstractmethod
    async def create_period(self, period_data: dict) -> AccountingPeriodInDB:
        pass

    @abstractmethod
    async def list_periods(self, business_id: str) -> List[AccountingPeriodInDB]:
        pass

    @abstractmethod
    async def get_period_by_id(self, period_id: str, business_id: str) -> Optional[AccountingPeriodInDB]:
        pass

    @abstractmethod
    async def get_period_by_name(self, business_id: str, period_name: str) -> Optional[AccountingPeriodInDB]:
        pass

    @abstractmethod
    async def get_tax_config_by_business(self, business_id: str) -> Optional[TaxConfigurationInDB]:
        pass

    @abstractmethod
    async def create_tax_config(self, config_data: dict) -> TaxConfigurationInDB:
        pass

    @abstractmethod
    async def update_tax_config(self, business_id: str, update_data: dict) -> Optional[TaxConfigurationInDB]:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryAccountingRepository(AbstractAccountingRepository):
    _accounts: Dict[str, AccountInDB] = {}
    _journals: Dict[str, JournalEntryInDB] = {}
    _journal_lines: Dict[str, JournalLineInDB] = {}
    _periods: Dict[str, AccountingPeriodInDB] = {}
    _tax_configs: Dict[str, TaxConfigurationInDB] = {}
    _sequences: Dict[str, int] = {}

    async def get_next_journal_sequence(self, business_id: str) -> int:
        current = self._sequences.get(business_id, 0)
        current += 1
        self._sequences[business_id] = current
        return current

    async def create_account(self, account_data: dict) -> AccountInDB:
        acc_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        data = dict(account_data)
        data["id"] = acc_id
        data["created_at"] = now
        data["updated_at"] = now
        acc = AccountInDB(**data)
        self._accounts[acc_id] = acc
        return acc

    async def get_account_by_id(self, account_id: str, business_id: str) -> Optional[AccountInDB]:
        acc = self._accounts.get(account_id)
        if not acc or acc.business_id != business_id:
            return None
        return acc

    async def get_account_by_code(self, business_id: str, code: str) -> Optional[AccountInDB]:
        code_norm = code.strip().upper()
        for acc in self._accounts.values():
            if acc.business_id == business_id and acc.code.upper() == code_norm and acc.is_active:
                return acc
        return None

    async def list_accounts(self, business_id: str, account_type: Optional[AccountType] = None) -> List[AccountInDB]:
        results = [
            acc for acc in self._accounts.values()
            if acc.business_id == business_id and acc.is_active
            and (account_type is None or acc.account_type == account_type)
        ]
        results.sort(key=lambda x: x.code)
        return results

    async def update_account(self, account_id: str, business_id: str, update_data: dict) -> Optional[AccountInDB]:
        acc = await self.get_account_by_id(account_id, business_id)
        if not acc:
            return None
        data = acc.model_dump()
        for k, v in update_data.items():
            if v is not None:
                data[k] = v
        data["updated_at"] = datetime.now(timezone.utc)
        updated = AccountInDB(**data)
        self._accounts[account_id] = updated
        return updated

    async def archive_account(self, account_id: str, business_id: str) -> Optional[AccountInDB]:
        return await self.update_account(account_id, business_id, {"is_active": False})

    async def create_journal_entry(self, entry_data: dict, lines_data: List[dict]) -> tuple[JournalEntryInDB, List[JournalLineInDB]]:
        entry_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        e_data = dict(entry_data)
        e_data["id"] = entry_id
        e_data["created_at"] = now
        e_data["updated_at"] = now
        
        entry = JournalEntryInDB(**e_data)
        self._journals[entry_id] = entry
        
        created_lines = []
        for l_dict in lines_data:
            line_id = str(uuid.uuid4())
            ld = dict(l_dict)
            ld["id"] = line_id
            ld["journal_entry_id"] = entry_id
            line = JournalLineInDB(**ld)
            self._journal_lines[line_id] = line
            created_lines.append(line)

        return entry, created_lines

    async def get_journal_by_id(self, journal_id: str, business_id: str) -> Optional[JournalEntryInDB]:
        j = self._journals.get(journal_id)
        if not j or j.business_id != business_id:
            return None
        return j

    async def get_journal_by_idempotency_key(self, idempotency_key: str, business_id: str) -> Optional[JournalEntryInDB]:
        for j in self._journals.values():
            if j.business_id == business_id and j.idempotency_key == idempotency_key and j.status == JournalStatus.POSTED:
                return j
        return None

    async def list_lines_for_journal(self, journal_id: str) -> List[JournalLineInDB]:
        return [l for l in self._journal_lines.values() if l.journal_entry_id == journal_id]

    async def list_journals(
        self,
        business_id: str,
        branch_id: Optional[str] = None,
        status: Optional[JournalStatus] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[JournalEntryInDB], int]:
        filtered = []
        for j in self._journals.values():
            if j.business_id != business_id:
                continue
            if branch_id and j.branch_id != branch_id:
                continue
            if status and j.status != status:
                continue
            if date_from and j.journal_date < date_from:
                continue
            if date_to and j.journal_date > date_to:
                continue
            filtered.append(j)

        filtered.sort(key=lambda x: (x.journal_date, x.created_at, x.id), reverse=True)
        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        return filtered[start:end], total

    async def void_journal(self, journal_id: str, business_id: str, voided_by_user_id: str) -> Optional[JournalEntryInDB]:
        j = await self.get_journal_by_id(journal_id, business_id)
        if not j:
            return None
        now = datetime.now(timezone.utc)
        data = j.model_dump()
        data["status"] = JournalStatus.VOIDED
        data["voided_by_user_id"] = voided_by_user_id
        data["voided_at"] = now
        data["updated_at"] = now
        updated = JournalEntryInDB(**data)
        self._journals[journal_id] = updated
        return updated

    async def list_posted_lines_for_account(
        self,
        business_id: str,
        account_id: str,
        branch_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[tuple[JournalEntryInDB, JournalLineInDB]]:
        results = []
        for line in self._journal_lines.values():
            if line.account_id != account_id:
                continue
            j = self._journals.get(line.journal_entry_id)
            if not j or j.business_id != business_id or j.status != JournalStatus.POSTED:
                continue
            if branch_id and j.branch_id != branch_id:
                continue
            if date_from and j.journal_date < date_from:
                continue
            if date_to and j.journal_date > date_to:
                continue
            results.append((j, line))
        
        results.sort(key=lambda item: (item[0].journal_date, item[0].created_at, item[0].id))
        return results

    async def get_period_for_date(self, business_id: str, check_date: date) -> Optional[AccountingPeriodInDB]:
        for p in self._periods.values():
            if p.business_id == business_id and p.start_date <= check_date <= p.end_date:
                return p
        return None

    async def close_period(self, business_id: str, period_name: str, closed_by_user_id: str) -> Optional[AccountingPeriodInDB]:
        for p in self._periods.values():
            if p.business_id == business_id and p.period_name == period_name:
                now = datetime.now(timezone.utc)
                data = p.model_dump()
                data["status"] = AccountingPeriodStatus.CLOSED
                data["closed_by_user_id"] = closed_by_user_id
                data["closed_at"] = now
                data["updated_at"] = now
                updated = AccountingPeriodInDB(**data)
                self._periods[p.id] = updated
                return updated
        return None

    async def create_period(self, period_data: dict) -> AccountingPeriodInDB:
        period_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        data = dict(period_data)
        data["id"] = period_id
        data["status"] = AccountingPeriodStatus.OPEN
        data["created_at"] = now
        data["updated_at"] = now
        period = AccountingPeriodInDB(**data)
        self._periods[period_id] = period
        return period

    async def list_periods(self, business_id: str) -> List[AccountingPeriodInDB]:
        results = [p for p in self._periods.values() if p.business_id == business_id]
        results.sort(key=lambda x: x.start_date, reverse=True)
        return results

    async def get_period_by_id(self, period_id: str, business_id: str) -> Optional[AccountingPeriodInDB]:
        p = self._periods.get(period_id)
        if not p or p.business_id != business_id:
            return None
        return p

    async def get_period_by_name(self, business_id: str, period_name: str) -> Optional[AccountingPeriodInDB]:
        for p in self._periods.values():
            if p.business_id == business_id and p.period_name == period_name:
                return p
        return None

    # --- Tax Configuration ---

    async def get_tax_config_by_business(self, business_id: str) -> Optional[TaxConfigurationInDB]:
        for tc in self._tax_configs.values():
            if tc.business_id == business_id:
                return tc
        return None

    async def create_tax_config(self, config_data: dict) -> TaxConfigurationInDB:
        tc_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        data = dict(config_data)
        data["id"] = tc_id
        data["created_at"] = now
        data["updated_at"] = now
        tc = TaxConfigurationInDB(**data)
        self._tax_configs[tc_id] = tc
        return tc

    async def update_tax_config(self, business_id: str, update_data: dict) -> Optional[TaxConfigurationInDB]:
        tc = await self.get_tax_config_by_business(business_id)
        if not tc:
            return None
        data = tc.model_dump()
        for k, v in update_data.items():
            if v is not None:
                data[k] = v
        data["updated_at"] = datetime.now(timezone.utc)
        updated = TaxConfigurationInDB(**data)
        self._tax_configs[tc.id] = updated
        return updated

    @classmethod
    def clear(cls):
        cls._accounts.clear()
        cls._journals.clear()
        cls._journal_lines.clear()
        cls._periods.clear()
        cls._tax_configs.clear()
        cls._sequences.clear()


accounting_repository = InMemoryAccountingRepository()
