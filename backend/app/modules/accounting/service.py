from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone, date, timedelta
from fastapi import HTTPException, status

from app.modules.accounting.schemas import (
    AccountInDB,
    AccountResponse,
    AccountListResponse,
    AccountCreate,
    AccountUpdate,
    JournalEntryInDB,
    JournalEntryResponse,
    JournalEntryListResponse,
    JournalEntryCreate,
    GeneralLedgerResponse,
    LedgerLineItem,
    TrialBalanceResponse,
    TrialBalanceItem,
    AccountType,
    NormalBalance,
    JournalStatus,
    AccountingPeriodStatus,
    AccountingPeriodInDB,
    AccountingPeriodResponse,
    AccountingPeriodCreate,
    AccountingPeriodListResponse,
    ProfitAndLossResponse,
    ReportAccountItem,
    BalanceSheetResponse,
    BalanceSheetItem,
    TaxConfigurationInDB,
    TaxConfigurationCreate,
    TaxConfigurationUpdate,
    TaxConfigurationResponse,
    TaxSummaryResponse,
    TaxTreatment,
    PricingMode,
    CashFlowResponse,
    CashFlowPeriodInfo,
    CashFlowDateRange,
    CashFlowOperatingActivities,
    CashFlowInvestingActivities,
    CashFlowFinancingActivities,
)
from app.modules.accounting.repository import (
    AbstractAccountingRepository,
    accounting_repository,
)
from app.modules.payment.repository import (
    AbstractPaymentRepository,
    payment_repository,
)
from app.modules.payment.schemas import PaymentDirection, PaymentStatus
from app.modules.expense.repository import (
    AbstractExpenseRepository,
    expense_repository,
)
from app.modules.expense.schemas import ExpenseStatus
from app.modules.cash_account.repository import (
    AbstractCashAccountRepository,
    cash_account_repository,
)
from app.modules.cash_account.schemas import CashMovementStatus, MovementDirection
from app.modules.branch.repository import branch_repository
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole


DEFAULT_CHART_OF_ACCOUNTS = [
    # ASSET (Normal balance DEBIT)
    {"code": "1000", "name": "ASSETS", "account_type": AccountType.ASSET, "normal_balance": NormalBalance.DEBIT, "is_system": True},
    {"code": "1100", "name": "Cash & Bank", "account_type": AccountType.ASSET, "normal_balance": NormalBalance.DEBIT, "is_system": True},
    {"code": "1200", "name": "Accounts Receivable", "account_type": AccountType.ASSET, "normal_balance": NormalBalance.DEBIT, "is_system": True},
    {"code": "1300", "name": "Inventory Assets", "account_type": AccountType.ASSET, "normal_balance": NormalBalance.DEBIT, "is_system": True},
    {"code": "1400", "name": "PPN Masukan (Input VAT)", "account_type": AccountType.ASSET, "normal_balance": NormalBalance.DEBIT, "is_system": True},
    
    # LIABILITY (Normal balance CREDIT)
    {"code": "2000", "name": "LIABILITIES", "account_type": AccountType.LIABILITY, "normal_balance": NormalBalance.CREDIT, "is_system": True},
    {"code": "2100", "name": "Accounts Payable", "account_type": AccountType.LIABILITY, "normal_balance": NormalBalance.CREDIT, "is_system": True},
    {"code": "2200", "name": "PPN Keluaran (Output VAT)", "account_type": AccountType.LIABILITY, "normal_balance": NormalBalance.CREDIT, "is_system": True},

    # EQUITY (Normal balance CREDIT)
    {"code": "3000", "name": "EQUITY", "account_type": AccountType.EQUITY, "normal_balance": NormalBalance.CREDIT, "is_system": True},
    {"code": "3100", "name": "Owner Equity", "account_type": AccountType.EQUITY, "normal_balance": NormalBalance.CREDIT, "is_system": True},

    # REVENUE (Normal balance CREDIT)
    {"code": "4000", "name": "REVENUE", "account_type": AccountType.REVENUE, "normal_balance": NormalBalance.CREDIT, "is_system": True},
    {"code": "4100", "name": "Sales Revenue", "account_type": AccountType.REVENUE, "normal_balance": NormalBalance.CREDIT, "is_system": True},

    # EXPENSE (Normal balance DEBIT)
    {"code": "5000", "name": "EXPENSES", "account_type": AccountType.EXPENSE, "normal_balance": NormalBalance.DEBIT, "is_system": True},
    {"code": "5100", "name": "General & Operational Expense", "account_type": AccountType.EXPENSE, "normal_balance": NormalBalance.DEBIT, "is_system": True},
    {"code": "5200", "name": "Cost of Goods Sold", "account_type": AccountType.EXPENSE, "normal_balance": NormalBalance.DEBIT, "is_system": True},
]


class AccountingService:
    def __init__(
        self,
        repository: AbstractAccountingRepository = accounting_repository,
        membership_service: BusinessMembershipService = business_membership_service,
        payment_repo: AbstractPaymentRepository = payment_repository,
        expense_repo: AbstractExpenseRepository = expense_repository,
        cash_account_repo: AbstractCashAccountRepository = cash_account_repository,
    ):
        self.repository = repository
        self.membership_service = membership_service
        self.payment_repo = payment_repo
        self.expense_repo = expense_repo
        self.cash_account_repo = cash_account_repo

    async def _validate_access(
        self,
        business_id: str,
        user_id: str,
        required_roles: Optional[tuple[BusinessMembershipRole, ...]] = None,
    ):
        membership = await self.membership_service.require_active_membership(business_id, user_id)
        if required_roles and membership.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of roles: {[r.value for r in required_roles]}",
            )
        return membership

    async def ensure_default_chart_of_accounts(self, business_id: str):
        existing = await self.repository.list_accounts(business_id)
        if not existing:
            for item in DEFAULT_CHART_OF_ACCOUNTS:
                acc_data = dict(item)
                acc_data["business_id"] = business_id
                await self.repository.create_account(acc_data)

    async def create_account(
        self, business_id: str, user_id: str, payload: AccountCreate
    ) -> AccountResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        await self.ensure_default_chart_of_accounts(business_id)

        # Code uniqueness check
        existing_code = await self.repository.get_account_by_code(business_id, payload.code)
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Account code '{payload.code.upper()}' already exists in this business.",
            )

        # Validate parent account if specified
        parent_id = None
        if payload.parent_id:
            parent = await self.repository.get_account_by_id(payload.parent_id, business_id)
            if not parent or not parent.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent account not found or is inactive.",
                )
            parent_id = parent.id

        # Determine normal balance if not supplied
        normal_bal = payload.normal_balance
        if not normal_bal:
            if payload.account_type in (AccountType.ASSET, AccountType.EXPENSE):
                normal_bal = NormalBalance.DEBIT
            else:
                normal_bal = NormalBalance.CREDIT

        account_data = {
            "business_id": business_id,
            "code": payload.code,
            "name": payload.name,
            "account_type": payload.account_type,
            "normal_balance": normal_bal,
            "parent_id": parent_id,
            "is_active": True,
            "is_system": False,
            "description": payload.description,
        }

        acc = await self.repository.create_account(account_data)
        return AccountResponse(**acc.model_dump(), current_balance=Decimal("0"))

    async def list_accounts(
        self, business_id: str, user_id: str, account_type: Optional[AccountType] = None
    ) -> AccountListResponse:
        await self._validate_access(business_id, user_id)
        await self.ensure_default_chart_of_accounts(business_id)

        accounts = await self.repository.list_accounts(business_id, account_type)
        
        items = []
        for acc in accounts:
            bal = await self._calculate_account_balance(business_id, acc)
            items.append(AccountResponse(**acc.model_dump(), current_balance=bal))

        return AccountListResponse(items=items, total=len(items))

    async def get_account(
        self, business_id: str, account_id: str, user_id: str
    ) -> AccountResponse:
        await self._validate_access(business_id, user_id)
        acc = await self.repository.get_account_by_id(account_id, business_id)
        if not acc or not acc.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found.",
            )

        bal = await self._calculate_account_balance(business_id, acc)
        return AccountResponse(**acc.model_dump(), current_balance=bal)

    async def update_account(
        self, business_id: str, account_id: str, user_id: str, payload: AccountUpdate
    ) -> AccountResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        acc = await self.repository.get_account_by_id(account_id, business_id)
        if not acc or not acc.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found.",
            )

        if acc.is_system:
            if payload.is_active is False:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="System accounts cannot be deactivated.",
                )

        if payload.parent_id:
            if payload.parent_id == account_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Account cannot be its own parent.",
                )
            parent = await self.repository.get_account_by_id(payload.parent_id, business_id)
            if not parent or not parent.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent account not found or is inactive.",
                )

        updated = await self.repository.update_account(
            account_id, business_id, payload.model_dump(exclude_unset=True)
        )
        bal = await self._calculate_account_balance(business_id, updated)
        return AccountResponse(**updated.model_dump(), current_balance=bal)

    async def archive_account(
        self, business_id: str, account_id: str, user_id: str
    ) -> AccountResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        acc = await self.repository.get_account_by_id(account_id, business_id)
        if not acc or not acc.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found.",
            )

        if acc.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="System accounts cannot be archived.",
            )

        posted_lines = await self.repository.list_posted_lines_for_account(business_id, account_id)
        if posted_lines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot archive account that is referenced in posted journal entries.",
            )

        archived = await self.repository.archive_account(account_id, business_id)
        return AccountResponse(**archived.model_dump(), current_balance=Decimal("0"))

    # --- Journal Entry & Posting Engine ---

    async def create_and_post_journal(
        self, business_id: str, user_id: str, payload: JournalEntryCreate
    ) -> JournalEntryResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        await self.ensure_default_chart_of_accounts(business_id)

        # Idempotency check
        if payload.idempotency_key:
            existing = await self.repository.get_journal_by_idempotency_key(payload.idempotency_key, business_id)
            if existing:
                lines = await self.repository.list_lines_for_journal(existing.id)
                return JournalEntryResponse(**existing.model_dump(), lines=lines)

        # Period check
        period = await self.repository.get_period_for_date(business_id, payload.journal_date.date())
        if period and period.status == AccountingPeriodStatus.CLOSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Accounting period for date {payload.journal_date.date()} is CLOSED.",
            )

        # Branch validation if provided
        if payload.branch_id:
            br = await branch_repository.get_by_id(payload.branch_id)
            if not br or br.business_id != business_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Branch not found in this business.",
                )

        # Double-entry invariant validation
        tot_debit = Decimal("0")
        tot_credit = Decimal("0")
        validated_lines = []

        if len(payload.lines) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Journal entry must contain at least 2 lines.",
            )

        for line_in in payload.lines:
            acc = await self.repository.get_account_by_id(line_in.account_id, business_id)
            if not acc or not acc.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Account {line_in.account_id} not found or inactive.",
                )

            if line_in.debit < Decimal("0") or line_in.credit < Decimal("0"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Debit and Credit cannot be negative.",
                )

            if line_in.debit > Decimal("0") and line_in.credit > Decimal("0"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A single line cannot have both Debit and Credit greater than zero.",
                )

            if line_in.debit == Decimal("0") and line_in.credit == Decimal("0"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A line must have either Debit or Credit greater than zero.",
                )

            tot_debit += line_in.debit
            tot_credit += line_in.credit

            validated_lines.append({
                "account_id": acc.id,
                "account_code": acc.code,
                "account_name": acc.name,
                "description": line_in.description,
                "debit": line_in.debit,
                "credit": line_in.credit,
                "currency": "IDR",
            })

        if tot_debit != tot_credit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unbalanced journal entry: Total Debit ({tot_debit}) != Total Credit ({tot_credit}).",
            )

        seq = await self.repository.get_next_journal_sequence(business_id)
        journal_number = f"JV-{seq:06d}"
        now = datetime.now(timezone.utc)

        entry_data = {
            "business_id": business_id,
            "branch_id": payload.branch_id,
            "journal_number": journal_number,
            "journal_date": payload.journal_date,
            "description": payload.description,
            "reference_type": payload.reference_type,
            "reference_id": payload.reference_id,
            "status": JournalStatus.POSTED,
            "source": "MANUAL",
            "total_debit": tot_debit,
            "total_credit": tot_credit,
            "currency": "IDR",
            "posted_at": now,
            "posted_by_user_id": user_id,
            "idempotency_key": payload.idempotency_key,
            "created_by_user_id": user_id,
        }

        entry, created_lines = await self.repository.create_journal_entry(entry_data, validated_lines)
        return JournalEntryResponse(**entry.model_dump(), lines=created_lines)

    async def list_journals(
        self,
        business_id: str,
        user_id: str,
        branch_id: Optional[str] = None,
        status_filter: Optional[JournalStatus] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> JournalEntryListResponse:
        await self._validate_access(business_id, user_id)
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        journals, total = await self.repository.list_journals(
            business_id, branch_id, status_filter, date_from, date_to, page, page_size
        )

        items = []
        for j in journals:
            lines = await self.repository.list_lines_for_journal(j.id)
            items.append(JournalEntryResponse(**j.model_dump(), lines=lines))

        return JournalEntryListResponse(items=items, page=page, page_size=page_size, total=total)

    async def get_journal(
        self, business_id: str, journal_id: str, user_id: str
    ) -> JournalEntryResponse:
        await self._validate_access(business_id, user_id)
        j = await self.repository.get_journal_by_id(journal_id, business_id)
        if not j:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found.",
            )
        lines = await self.repository.list_lines_for_journal(j.id)
        return JournalEntryResponse(**j.model_dump(), lines=lines)

    async def void_journal(
        self, business_id: str, journal_id: str, user_id: str
    ) -> JournalEntryResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        j = await self.repository.get_journal_by_id(journal_id, business_id)
        if not j:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found.",
            )

        if j.status == JournalStatus.VOIDED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Journal entry is already VOIDED.",
            )

        voided = await self.repository.void_journal(journal_id, business_id, user_id)
        lines = await self.repository.list_lines_for_journal(journal_id)
        return JournalEntryResponse(**voided.model_dump(), lines=lines)

    # --- Ledger & Trial Balance ---

    async def _calculate_account_balance(self, business_id: str, account: AccountInDB) -> Decimal:
        lines = await self.repository.list_posted_lines_for_account(business_id, account.id)
        tot_debit = sum((l[1].debit for l in lines), Decimal("0"))
        tot_credit = sum((l[1].credit for l in lines), Decimal("0"))

        if account.normal_balance == NormalBalance.DEBIT:
            return tot_debit - tot_credit
        else:
            return tot_credit - tot_debit

    async def get_general_ledger(
        self,
        business_id: str,
        account_id: str,
        user_id: str,
        branch_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> GeneralLedgerResponse:
        await self._validate_access(business_id, user_id)
        acc = await self.repository.get_account_by_id(account_id, business_id)
        if not acc or not acc.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found.",
            )

        posted_pairs = await self.repository.list_posted_lines_for_account(
            business_id, account_id, branch_id, date_from, date_to
        )

        opening_balance = Decimal("0")
        tot_debit = Decimal("0")
        tot_credit = Decimal("0")
        ledger_lines = []

        curr_balance = opening_balance

        for j_entry, j_line in posted_pairs:
            tot_debit += j_line.debit
            tot_credit += j_line.credit

            if acc.normal_balance == NormalBalance.DEBIT:
                curr_balance += (j_line.debit - j_line.credit)
            else:
                curr_balance += (j_line.credit - j_line.debit)

            ledger_lines.append(
                LedgerLineItem(
                    journal_id=j_entry.id,
                    journal_number=j_entry.journal_number,
                    journal_date=j_entry.journal_date,
                    description=j_line.description or j_entry.description,
                    reference_type=j_entry.reference_type,
                    reference_id=j_entry.reference_id,
                    debit=j_line.debit,
                    credit=j_line.credit,
                    running_balance=curr_balance,
                )
            )

        return GeneralLedgerResponse(
            account_id=acc.id,
            account_code=acc.code,
            account_name=acc.name,
            account_type=acc.account_type,
            normal_balance=acc.normal_balance,
            opening_balance=opening_balance,
            total_debit=tot_debit,
            total_credit=tot_credit,
            ending_balance=curr_balance,
            lines=ledger_lines,
        )

    async def get_trial_balance(
        self, business_id: str, user_id: str
    ) -> TrialBalanceResponse:
        await self._validate_access(business_id, user_id)
        await self.ensure_default_chart_of_accounts(business_id)

        accounts = await self.repository.list_accounts(business_id)
        
        total_debit = Decimal("0")
        total_credit = Decimal("0")
        items = []

        for acc in accounts:
            posted_pairs = await self.repository.list_posted_lines_for_account(business_id, acc.id)
            d_sum = sum((l[1].debit for l in posted_pairs), Decimal("0"))
            c_sum = sum((l[1].credit for l in posted_pairs), Decimal("0"))

            if d_sum == Decimal("0") and c_sum == Decimal("0"):
                continue

            total_debit += d_sum
            total_credit += c_sum

            items.append(
                TrialBalanceItem(
                    account_id=acc.id,
                    account_code=acc.code,
                    account_name=acc.name,
                    account_type=acc.account_type,
                    normal_balance=acc.normal_balance,
                    debit_balance=d_sum,
                    credit_balance=c_sum,
                )
            )

        items.sort(key=lambda x: x.account_code)
        is_balanced = (total_debit == total_credit)

        return TrialBalanceResponse(
            currency="IDR",
            total_debit=total_debit,
            total_credit=total_credit,
            is_balanced=is_balanced,
            items=items,
        )

    # --- Accounting Period Operations ---

    async def create_period(
        self, business_id: str, user_id: str, payload: AccountingPeriodCreate
    ) -> AccountingPeriodResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        # Period name uniqueness check per business
        existing_name = await self.repository.get_period_by_name(business_id, payload.period_name)
        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Accounting period with name '{payload.period_name}' already exists in this business.",
            )

        # Period overlap check per business
        existing_periods = await self.repository.list_periods(business_id)
        for ep in existing_periods:
            if ep.start_date <= payload.end_date and ep.end_date >= payload.start_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Date range ({payload.start_date} to {payload.end_date}) overlaps with existing period '{ep.period_name}' ({ep.start_date} to {ep.end_date}).",
                )

        period_data = {
            "business_id": business_id,
            "period_name": payload.period_name,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
            "created_by_user_id": user_id,
        }

        period = await self.repository.create_period(period_data)
        return AccountingPeriodResponse(**period.model_dump())

    async def list_periods(
        self, business_id: str, user_id: str
    ) -> AccountingPeriodListResponse:
        await self._validate_access(business_id, user_id)
        periods = await self.repository.list_periods(business_id)
        return AccountingPeriodListResponse(items=periods, total=len(periods))

    async def get_period(
        self, business_id: str, period_id: str, user_id: str
    ) -> AccountingPeriodResponse:
        await self._validate_access(business_id, user_id)
        period = await self.repository.get_period_by_id(period_id, business_id)
        if not period:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Accounting period not found.",
            )
        return AccountingPeriodResponse(**period.model_dump())

    async def close_period_by_id(
        self, business_id: str, period_id: str, user_id: str
    ) -> AccountingPeriodResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        period = await self.repository.get_period_by_id(period_id, business_id)
        if not period:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Accounting period not found.",
            )

        if period.status == AccountingPeriodStatus.CLOSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Accounting period '{period.period_name}' is already CLOSED.",
            )

        closed = await self.repository.close_period(business_id, period.period_name, user_id)
        if not closed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Failed to close accounting period.",
            )
        return AccountingPeriodResponse(**closed.model_dump())

    # --- Financial Reports (Feature #36) ---

    async def _get_period_or_404(
        self, business_id: str, period_id: str, user_id: str
    ) -> AccountingPeriodInDB:
        await self._validate_access(business_id, user_id)
        period = await self.repository.get_period_by_id(period_id, business_id)
        if not period:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Accounting period not found.")
        return period

    async def _account_balance_for_range(
        self,
        business_id: str,
        account: AccountInDB,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Decimal:
        posted = await self.repository.list_posted_lines_for_account(
            business_id, account.id, date_from=date_from, date_to=date_to,
        )
        tot_debit = sum((l[1].debit for l in posted), Decimal("0"))
        tot_credit = sum((l[1].credit for l in posted), Decimal("0"))
        if account.normal_balance == NormalBalance.DEBIT:
            return tot_debit - tot_credit
        return tot_credit - tot_debit

    async def get_profit_and_loss(
        self, business_id: str, period_id: str, user_id: str
    ) -> "ProfitAndLossResponse":  # noqa: F821
        from app.modules.accounting.schemas import ProfitAndLossResponse, ReportAccountItem

        period = await self._get_period_or_404(business_id, period_id, user_id)

        start_dt = datetime.combine(period.start_date, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(period.end_date, datetime.max.time(), tzinfo=timezone.utc)

        accounts = await self.repository.list_accounts(business_id)

        revenue_items: List[ReportAccountItem] = []
        expense_items: List[ReportAccountItem] = []
        total_revenue = Decimal("0")
        total_expense = Decimal("0")

        for acc in accounts:
            if not acc.is_active:
                continue
            if acc.account_type == AccountType.REVENUE:
                bal = await self._account_balance_for_range(business_id, acc, date_from=start_dt, date_to=end_dt)
                if bal != Decimal("0"):
                    revenue_items.append(ReportAccountItem(
                        account_id=acc.id, account_code=acc.code, account_name=acc.name, amount=bal,
                    ))
                    total_revenue += bal
            elif acc.account_type == AccountType.EXPENSE:
                bal = await self._account_balance_for_range(business_id, acc, date_from=start_dt, date_to=end_dt)
                if bal != Decimal("0"):
                    expense_items.append(ReportAccountItem(
                        account_id=acc.id, account_code=acc.code, account_name=acc.name, amount=bal,
                    ))
                    total_expense += bal

        net_profit = total_revenue - total_expense

        return ProfitAndLossResponse(
            period=period,
            revenue_items=revenue_items,
            total_revenue=total_revenue,
            expense_items=expense_items,
            total_expense=total_expense,
            net_profit=net_profit,
        )

    async def get_balance_sheet(
        self, business_id: str, period_id: str, user_id: str
    ) -> "BalanceSheetResponse":  # noqa: F821
        from app.modules.accounting.schemas import BalanceSheetResponse, BalanceSheetItem, AccountType as AT

        period = await self._get_period_or_404(business_id, period_id, user_id)

        end_dt = datetime.combine(period.end_date, datetime.max.time(), tzinfo=timezone.utc)

        accounts = await self.repository.list_accounts(business_id)

        asset_items: List[BalanceSheetItem] = []
        liability_items: List[BalanceSheetItem] = []
        equity_items: List[BalanceSheetItem] = []
        total_assets = Decimal("0")
        total_liabilities = Decimal("0")
        total_equity = Decimal("0")

        for acc in accounts:
            if not acc.is_active:
                continue
            bal = await self._account_balance_for_range(business_id, acc, date_to=end_dt)
            if bal == Decimal("0"):
                continue
            item = BalanceSheetItem(
                account_id=acc.id, account_code=acc.code, account_name=acc.name, balance=bal,
            )
            if acc.account_type == AT.ASSET:
                asset_items.append(item)
                total_assets += bal
            elif acc.account_type == AT.LIABILITY:
                liability_items.append(item)
                total_liabilities += bal
            elif acc.account_type == AT.EQUITY:
                equity_items.append(item)
                total_equity += bal

        # Current period profit: revenue - expense through period end
        start_dt = datetime.combine(period.start_date, datetime.min.time(), tzinfo=timezone.utc)
        current_rev = Decimal("0")
        current_exp = Decimal("0")
        for acc in accounts:
            if not acc.is_active:
                continue
            if acc.account_type == AT.REVENUE:
                bal = await self._account_balance_for_range(business_id, acc, date_from=start_dt, date_to=end_dt)
                current_rev += bal
            elif acc.account_type == AT.EXPENSE:
                bal = await self._account_balance_for_range(business_id, acc, date_from=start_dt, date_to=end_dt)
                current_exp += bal
        net_profit_current_period = current_rev - current_exp

        total_le = total_liabilities + total_equity + net_profit_current_period
        is_balanced = total_assets == total_le

        return BalanceSheetResponse(
            period=period,
            as_of_date=period.end_date,
            asset_items=asset_items,
            total_assets=total_assets,
            liability_items=liability_items,
            total_liabilities=total_liabilities,
            equity_items=equity_items,
            total_equity=total_equity,
            net_profit_current_period=net_profit_current_period,
            total_liabilities_and_equity=total_le,
            is_balanced=is_balanced,
        )

    # --- Tax Configuration (Feature #37) ---

    async def get_tax_config(
        self, business_id: str, user_id: str
    ) -> TaxConfigurationResponse:
        await self._validate_access(business_id, user_id)
        tc = await self.repository.get_tax_config_by_business(business_id)
        if not tc:
            # Lazy default creation
            tc = await self.repository.create_tax_config({
                "business_id": business_id,
                "tax_enabled": False,
                "pricing_mode": PricingMode.TAX_EXCLUSIVE,
                "default_tax_treatment": TaxTreatment.STANDARD_NON_LUXURY,
                "created_by_user_id": user_id,
            })
        return TaxConfigurationResponse(**tc.model_dump())

    async def update_tax_config(
        self, business_id: str, user_id: str, payload: TaxConfigurationUpdate
    ) -> TaxConfigurationResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        tc = await self.repository.get_tax_config_by_business(business_id)
        if not tc:
            # Lazy auto-create if not fetched via GET first
            tc = await self.repository.create_tax_config({
                "business_id": business_id,
                "tax_enabled": False,
                "pricing_mode": PricingMode.TAX_EXCLUSIVE,
                "default_tax_treatment": TaxTreatment.STANDARD_NON_LUXURY,
                "created_by_user_id": user_id,
            })
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update.",
            )
        updated = await self.repository.update_tax_config(business_id, update_data)
        return TaxConfigurationResponse(**updated.model_dump())

    # --- Tax Summary Report (Feature #37) ---

    async def get_tax_summary(
        self, business_id: str, user_id: str, year: int, month: int
    ) -> TaxSummaryResponse:
        await self._validate_access(business_id, user_id)

        # Calculate date range for the month
        from datetime import timedelta
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

        # Get Output VAT account (2200)
        output_vat_acc = await self.repository.get_account_by_code(business_id, "2200")
        # Get Input VAT account (1400)
        input_vat_acc = await self.repository.get_account_by_code(business_id, "1400")

        output_vat = Decimal("0")
        input_vat = Decimal("0")
        taxable_sales_count = 0
        taxable_purchase_count = 0

        if output_vat_acc:
            output_vat = await self._account_balance_for_range(
                business_id, output_vat_acc, date_from=start_dt, date_to=end_dt
            )

        if input_vat_acc:
            input_vat = await self._account_balance_for_range(
                business_id, input_vat_acc, date_from=start_dt, date_to=end_dt
            )

        # Count taxable sales and purchases from journals
        sales_acc = await self.repository.get_account_by_code(business_id, "4100")
        purchase_acc = await self.repository.get_account_by_code(business_id, "1300")

        if sales_acc:
            posted = await self.repository.list_posted_lines_for_account(
                business_id, sales_acc.id, date_from=start_dt, date_to=end_dt
            )
            sales_journal_ids = set()
            for j_entry, _ in posted:
                if j_entry.reference_type == "SALES":
                    sales_journal_ids.add(j_entry.id)
            taxable_sales_count = len(sales_journal_ids)

        if purchase_acc:
            posted = await self.repository.list_posted_lines_for_account(
                business_id, purchase_acc.id, date_from=start_dt, date_to=end_dt
            )
            purchase_journal_ids = set()
            for j_entry, _ in posted:
                if j_entry.reference_type == "PURCHASE":
                    purchase_journal_ids.add(j_entry.id)
            taxable_purchase_count = len(purchase_journal_ids)

        net_vat = output_vat - input_vat

        return TaxSummaryResponse(
            year=year,
            month=month,
            output_vat=output_vat,
            input_vat=input_vat,
            net_vat=net_vat,
            taxable_sales_count=taxable_sales_count,
            taxable_purchase_count=taxable_purchase_count,
        )

    # --- Cash Flow Statement Report (Feature #40) ---

    async def get_cash_flow_statement(
        self,
        business_id: str,
        user_id: str,
        period_id: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> CashFlowResponse:
        await self._validate_access(
            business_id,
            user_id,
            required_roles=(
                BusinessMembershipRole.OWNER,
                BusinessMembershipRole.ADMIN,
                BusinessMembershipRole.MEMBER,
            ),
        )

        period_info: Optional[CashFlowPeriodInfo] = None
        if period_id is not None:
            period = await self._get_period_or_404(business_id, period_id, user_id)
            start_date = period.start_date
            end_date = period.end_date
            period_info = CashFlowPeriodInfo(id=period.id, period_name=period.period_name)
        elif date_from is not None and date_to is not None:
            if date_from > date_to:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="date_from must be less than or equal to date_to",
                )
            start_date = date_from
            end_date = date_to
            period_info = None
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Either period_id or both date_from and date_to must be provided.",
            )

        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        end_dt_exclusive = datetime.combine(
            end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
        )

        def _normalize_dt(dt: datetime) -> datetime:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        # 1. Historical Cash Balance Reconstruction for Opening
        all_accounts, _ = await self.cash_account_repo.list_accounts(
            business_id, page=1, page_size=10000
        )

        opening_cash_balance = Decimal("0.00")
        for acc in all_accounts:
            opening_cash_balance += acc.opening_balance

        all_movements = []
        for acc in all_accounts:
            acc_movements = await self.cash_account_repo.list_all_movements_for_account(
                business_id, acc.id
            )
            all_movements.extend(acc_movements)

        for m in all_movements:
            if m.status != CashMovementStatus.POSTED:
                continue
            m_dt = _normalize_dt(m.created_at)
            if m_dt < start_dt:
                if m.direction == MovementDirection.IN:
                    opening_cash_balance += m.amount
                elif m.direction == MovementDirection.OUT:
                    opening_cash_balance -= m.amount

        # 2. Operating Activities from Canonical Sources
        # Customer Receipts & Supplier Payments
        all_payments, _ = await self.payment_repo.list_payments(
            business_id=business_id, page=1, page_size=10000
        )

        cash_received_from_customers = Decimal("0.00")
        cash_paid_to_suppliers = Decimal("0.00")

        for p in all_payments:
            if p.business_id != business_id or p.status != PaymentStatus.RECORDED:
                continue
            p_dt = _normalize_dt(p.payment_date) if p.payment_date else _normalize_dt(p.created_at)
            if start_dt <= p_dt < end_dt_exclusive:
                if p.direction == PaymentDirection.CUSTOMER_IN:
                    cash_received_from_customers += p.amount
                elif p.direction == PaymentDirection.SUPPLIER_OUT:
                    cash_paid_to_suppliers += p.amount

        # Operating Expenses
        all_expenses, _ = await self.expense_repo.list_expenses(
            business_id=business_id, page=1, page_size=10000
        )

        cash_paid_for_expenses = Decimal("0.00")
        for e in all_expenses:
            if (
                e.business_id != business_id
                or e.status != ExpenseStatus.FINALIZED
                or e.cash_account_id is None
            ):
                continue
            e_dt = _normalize_dt(e.expense_date)
            if start_dt <= e_dt < end_dt_exclusive:
                cash_paid_for_expenses += e.amount

        net_cash_from_operating = (
            cash_received_from_customers - cash_paid_to_suppliers - cash_paid_for_expenses
        )
        net_cash_from_investing = Decimal("0.00")
        net_cash_from_financing = Decimal("0.00")

        net_increase_in_cash = (
            net_cash_from_operating + net_cash_from_investing + net_cash_from_financing
        )
        closing_cash_balance = opening_cash_balance + net_increase_in_cash

        return CashFlowResponse(
            period=period_info,
            date_range=CashFlowDateRange(start_date=start_date, end_date=end_date),
            opening_cash_balance=opening_cash_balance,
            operating_activities=CashFlowOperatingActivities(
                cash_received_from_customers=cash_received_from_customers,
                cash_paid_to_suppliers=cash_paid_to_suppliers,
                cash_paid_for_expenses=cash_paid_for_expenses,
                net_cash_from_operating=net_cash_from_operating,
            ),
            investing_activities=CashFlowInvestingActivities(
                net_cash_from_investing=net_cash_from_investing
            ),
            financing_activities=CashFlowFinancingActivities(
                net_cash_from_financing=net_cash_from_financing
            ),
            net_increase_in_cash=net_increase_in_cash,
            closing_cash_balance=closing_cash_balance,
            reconciliation_status="SUBLEDGER_RECONCILED",
        )


accounting_service = AccountingService()
