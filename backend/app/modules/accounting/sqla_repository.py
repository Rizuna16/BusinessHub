from datetime import datetime, timezone, date
from typing import Dict, List, Optional
from decimal import Decimal
import uuid

from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounting.models import (
    AccountingAccount,
    JournalEntryInDB as JournalEntryModel,
    JournalLineInDB as JournalLineModel,
    AccountingPeriodInDB as AccountingPeriodModel,
    TaxConfigurationInDB as TaxConfigurationModel,
)
from app.modules.accounting.repository import AbstractAccountingRepository
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
    TaxTreatment,
    PricingMode,
)
from app.modules.sqla_base import sa_create


def _to_account(obj: AccountingAccount) -> AccountInDB:
    return AccountInDB(
        id=obj.id,
        business_id=obj.business_id,
        code=obj.code,
        name=obj.name,
        account_type=AccountType(obj.account_type),
        normal_balance=NormalBalance(obj.normal_balance),
        parent_id=obj.parent_id,
        is_active=obj.is_active,
        is_system=obj.is_system,
        description=obj.description,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_journal_entry(obj: JournalEntryModel) -> JournalEntryInDB:
    return JournalEntryInDB(
        id=obj.id,
        business_id=obj.business_id,
        branch_id=obj.branch_id,
        journal_number=obj.journal_number,
        journal_date=obj.journal_date,
        description=obj.description,
        reference_type=obj.reference_type,
        reference_id=obj.reference_id,
        status=JournalStatus(obj.status),
        source=obj.source,
        total_debit=obj.total_debit,
        total_credit=obj.total_credit,
        currency=obj.currency,
        posted_at=obj.posted_at,
        posted_by_user_id=obj.posted_by_user_id,
        voided_at=obj.voided_at,
        voided_by_user_id=obj.voided_by_user_id,
        idempotency_key=obj.idempotency_key,
        created_by_user_id=obj.created_by_user_id,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_journal_line(obj: JournalLineModel) -> JournalLineInDB:
    return JournalLineInDB(
        id=obj.id,
        journal_entry_id=obj.journal_entry_id,
        account_id=obj.account_id,
        account_code=obj.account_code,
        account_name=obj.account_name,
        description=obj.description,
        debit=obj.debit,
        credit=obj.credit,
        currency=obj.currency,
    )


def _to_accounting_period(obj: AccountingPeriodModel) -> AccountingPeriodInDB:
    return AccountingPeriodInDB(
        id=obj.id,
        business_id=obj.business_id,
        period_name=obj.period_name,
        start_date=obj.start_date,
        end_date=obj.end_date,
        status=AccountingPeriodStatus(obj.status),
        created_at=obj.created_at,
        created_by_user_id=obj.created_by_user_id,
        updated_at=obj.updated_at,
        closed_at=obj.closed_at,
        closed_by_user_id=obj.closed_by_user_id,
    )


def _to_tax_config(obj: TaxConfigurationModel) -> TaxConfigurationInDB:
    return TaxConfigurationInDB(
        id=obj.id,
        business_id=obj.business_id,
        tax_enabled=obj.tax_enabled,
        pricing_mode=PricingMode(obj.pricing_mode),
        default_tax_treatment=TaxTreatment(obj.default_tax_treatment),
        created_at=obj.created_at,
        created_by_user_id=obj.created_by_user_id,
        updated_at=obj.updated_at,
    )


class SQLAlchemyAccountingRepository(AbstractAccountingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_account(self, account_data: dict) -> AccountInDB:
        obj = await sa_create(self.session, AccountingAccount, account_data)
        return _to_account(obj)

    async def get_account_by_id(self, account_id: str, business_id: str) -> Optional[AccountInDB]:
        stmt = select(AccountingAccount).where(
            AccountingAccount.id == account_id,
            AccountingAccount.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_account(obj) if obj else None

    async def get_account_by_code(self, business_id: str, code: str) -> Optional[AccountInDB]:
        code_norm = code.strip().upper()
        stmt = select(AccountingAccount).where(
            AccountingAccount.business_id == business_id,
            func.upper(AccountingAccount.code) == code_norm,
            AccountingAccount.is_active == True,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_account(obj) if obj else None

    async def list_accounts(self, business_id: str, account_type: Optional[AccountType] = None) -> List[AccountInDB]:
        stmt = select(AccountingAccount).where(
            AccountingAccount.business_id == business_id,
            AccountingAccount.is_active == True,
        )
        if account_type:
            stmt = stmt.where(AccountingAccount.account_type == account_type.value)
        stmt = stmt.order_by(asc(AccountingAccount.code))
        res = await self.session.execute(stmt)
        return [_to_account(o) for o in res.scalars().all()]

    async def update_account(self, account_id: str, business_id: str, update_data: dict) -> Optional[AccountInDB]:
        acc = await self.get_account_by_id(account_id, business_id)
        if not acc:
            return None
        stmt = select(AccountingAccount).where(AccountingAccount.id == account_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        for k, v in update_data.items():
            if v is not None:
                setattr(obj, k, v)
        await self.session.flush()
        return _to_account(obj)

    async def archive_account(self, account_id: str, business_id: str) -> Optional[AccountInDB]:
        return await self.update_account(account_id, business_id, {"is_active": False})

    async def get_next_journal_sequence(self, business_id: str) -> int:
        stmt = select(func.count()).select_from(JournalEntryModel).where(JournalEntryModel.business_id == business_id)
        res = await self.session.execute(stmt)
        count = res.scalar_one() or 0
        return count + 1

    async def create_journal_entry(self, entry_data: dict, lines_data: List[dict]) -> tuple[JournalEntryInDB, List[JournalLineInDB]]:
        entry = await sa_create(self.session, JournalEntryModel, entry_data)
        created_lines = []
        for l_data in lines_data:
            ld = dict(l_data)
            ld["journal_entry_id"] = entry.id
            line_obj = await sa_create(self.session, JournalLineModel, ld)
            created_lines.append(_to_journal_line(line_obj))
        return _to_journal_entry(entry), created_lines

    async def get_journal_by_id(self, journal_id: str, business_id: str) -> Optional[JournalEntryInDB]:
        stmt = select(JournalEntryModel).where(
            JournalEntryModel.id == journal_id,
            JournalEntryModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_journal_entry(obj) if obj else None

    async def get_journal_by_idempotency_key(self, idempotency_key: str, business_id: str) -> Optional[JournalEntryInDB]:
        stmt = select(JournalEntryModel).where(
            JournalEntryModel.business_id == business_id,
            JournalEntryModel.idempotency_key == idempotency_key,
            JournalEntryModel.status == JournalStatus.POSTED.value,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_journal_entry(obj) if obj else None

    async def list_lines_for_journal(self, journal_id: str) -> List[JournalLineInDB]:
        stmt = select(JournalLineModel).where(JournalLineModel.journal_entry_id == journal_id)
        res = await self.session.execute(stmt)
        return [_to_journal_line(l) for l in res.scalars().all()]

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
        filters = [JournalEntryModel.business_id == business_id]
        if branch_id:
            filters.append(JournalEntryModel.branch_id == branch_id)
        if status:
            filters.append(JournalEntryModel.status == status.value)
        if date_from:
            filters.append(JournalEntryModel.journal_date >= date_from)
        if date_to:
            filters.append(JournalEntryModel.journal_date <= date_to)

        count_stmt = select(func.count()).select_from(JournalEntryModel).where(and_(*filters))
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = select(JournalEntryModel).where(and_(*filters)).order_by(
            desc(JournalEntryModel.journal_date),
            desc(JournalEntryModel.created_at),
            desc(JournalEntryModel.id),
        ).offset((page - 1) * page_size).limit(page_size)

        res = await self.session.execute(stmt)
        items = [_to_journal_entry(o) for o in res.scalars().all()]
        return items, total

    async def void_journal(self, journal_id: str, business_id: str, voided_by_user_id: str) -> Optional[JournalEntryInDB]:
        stmt = select(JournalEntryModel).where(
            JournalEntryModel.id == journal_id,
            JournalEntryModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        now = datetime.now(timezone.utc)
        obj.status = JournalStatus.VOIDED.value
        obj.voided_by_user_id = voided_by_user_id
        obj.voided_at = now
        await self.session.flush()
        return _to_journal_entry(obj)

    async def list_posted_lines_for_account(
        self,
        business_id: str,
        account_id: str,
        branch_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[tuple[JournalEntryInDB, JournalLineInDB]]:
        stmt = select(JournalEntryModel, JournalLineModel).join(
            JournalLineModel, JournalLineModel.journal_entry_id == JournalEntryModel.id
        ).where(
            JournalEntryModel.business_id == business_id,
            JournalLineModel.account_id == account_id,
            JournalEntryModel.status == JournalStatus.POSTED.value,
        )
        if branch_id:
            stmt = stmt.where(JournalEntryModel.branch_id == branch_id)
        if date_from:
            stmt = stmt.where(JournalEntryModel.journal_date >= date_from)
        if date_to:
            stmt = stmt.where(JournalEntryModel.journal_date <= date_to)

        stmt = stmt.order_by(
            asc(JournalEntryModel.journal_date),
            asc(JournalEntryModel.created_at),
            asc(JournalEntryModel.id),
        )
        res = await self.session.execute(stmt)
        results = []
        for entry_obj, line_obj in res.all():
            results.append((_to_journal_entry(entry_obj), _to_journal_line(line_obj)))
        return results

    async def get_period_for_date(self, business_id: str, check_date: date) -> Optional[AccountingPeriodInDB]:
        stmt = select(AccountingPeriodModel).where(
            AccountingPeriodModel.business_id == business_id,
            AccountingPeriodModel.start_date <= check_date,
            AccountingPeriodModel.end_date >= check_date,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_accounting_period(obj) if obj else None

    async def close_period(self, business_id: str, period_name: str, closed_by_user_id: str) -> Optional[AccountingPeriodInDB]:
        stmt = select(AccountingPeriodModel).where(
            AccountingPeriodModel.business_id == business_id,
            AccountingPeriodModel.period_name == period_name,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        now = datetime.now(timezone.utc)
        obj.status = AccountingPeriodStatus.CLOSED.value
        obj.closed_by_user_id = closed_by_user_id
        obj.closed_at = now
        await self.session.flush()
        return _to_accounting_period(obj)

    async def create_period(self, period_data: dict) -> AccountingPeriodInDB:
        data = dict(period_data)
        if "status" not in data:
            data["status"] = AccountingPeriodStatus.OPEN.value
        obj = await sa_create(self.session, AccountingPeriodModel, data)
        return _to_accounting_period(obj)

    async def list_periods(self, business_id: str) -> List[AccountingPeriodInDB]:
        stmt = select(AccountingPeriodModel).where(
            AccountingPeriodModel.business_id == business_id
        ).order_by(desc(AccountingPeriodModel.start_date))
        res = await self.session.execute(stmt)
        return [_to_accounting_period(o) for o in res.scalars().all()]

    async def get_period_by_id(self, period_id: str, business_id: str) -> Optional[AccountingPeriodInDB]:
        stmt = select(AccountingPeriodModel).where(
            AccountingPeriodModel.id == period_id,
            AccountingPeriodModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_accounting_period(obj) if obj else None

    async def get_period_by_name(self, business_id: str, period_name: str) -> Optional[AccountingPeriodInDB]:
        stmt = select(AccountingPeriodModel).where(
            AccountingPeriodModel.business_id == business_id,
            AccountingPeriodModel.period_name == period_name,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_accounting_period(obj) if obj else None

    async def get_tax_config_by_business(self, business_id: str) -> Optional[TaxConfigurationInDB]:
        stmt = select(TaxConfigurationModel).where(
            TaxConfigurationModel.business_id == business_id
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_tax_config(obj) if obj else None

    async def create_tax_config(self, config_data: dict) -> TaxConfigurationInDB:
        obj = await sa_create(self.session, TaxConfigurationModel, config_data)
        return _to_tax_config(obj)

    async def update_tax_config(self, business_id: str, update_data: dict) -> Optional[TaxConfigurationInDB]:
        tc = await self.get_tax_config_by_business(business_id)
        if not tc:
            return None
        stmt = select(TaxConfigurationModel).where(TaxConfigurationModel.business_id == business_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        for k, v in update_data.items():
            if v is not None:
                setattr(obj, k, v)
        await self.session.flush()
        return _to_tax_config(obj)

    @classmethod
    def clear(cls):
        pass
