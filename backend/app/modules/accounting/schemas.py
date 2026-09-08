from enum import Enum
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re


class AccountType(str, Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"


class NormalBalance(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class JournalStatus(str, Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    VOIDED = "VOIDED"


class AccountingPeriodStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


# --- Tax Schemas (Feature #37) ---

class TaxTreatment(str, Enum):
    STANDARD_NON_LUXURY = "STANDARD_NON_LUXURY"
    NON_TAXABLE = "NON_TAXABLE"


class PricingMode(str, Enum):
    TAX_EXCLUSIVE = "TAX_EXCLUSIVE"
    TAX_INCLUSIVE = "TAX_INCLUSIVE"


class TaxConfigurationInDB(BaseModel):
    id: str
    business_id: str
    tax_enabled: bool = False
    pricing_mode: PricingMode = PricingMode.TAX_EXCLUSIVE
    default_tax_treatment: TaxTreatment = TaxTreatment.STANDARD_NON_LUXURY
    created_at: datetime
    created_by_user_id: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaxConfigurationCreate(BaseModel):
    tax_enabled: bool = False
    pricing_mode: PricingMode = PricingMode.TAX_EXCLUSIVE
    default_tax_treatment: TaxTreatment = TaxTreatment.STANDARD_NON_LUXURY

    model_config = ConfigDict(extra="forbid")


class TaxConfigurationUpdate(BaseModel):
    tax_enabled: Optional[bool] = None
    pricing_mode: Optional[PricingMode] = None
    default_tax_treatment: Optional[TaxTreatment] = None

    model_config = ConfigDict(extra="forbid")


class TaxConfigurationResponse(TaxConfigurationInDB):
    pass


class TaxCalculationResult(BaseModel):
    tax_treatment: TaxTreatment
    pricing_mode: PricingMode
    statutory_rate: Decimal
    dpp_factor: Decimal
    commercial_amount: Decimal
    dpp: Decimal
    tax_amount: Decimal
    gross_total: Decimal


class TaxSummaryResponse(BaseModel):
    year: int
    month: int
    output_vat: Decimal = Decimal("0")
    input_vat: Decimal = Decimal("0")
    net_vat: Decimal = Decimal("0")
    taxable_sales_count: int = 0
    taxable_purchase_count: int = 0


class TaxSnapshot(BaseModel):
    tax_treatment: TaxTreatment
    pricing_mode: PricingMode
    statutory_rate: Decimal
    dpp_factor: Decimal
    commercial_amount: Decimal
    dpp: Decimal
    tax_amount: Decimal


# --- Chart of Accounts Schemas ---

class AccountCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=150)
    account_type: AccountType
    normal_balance: Optional[NormalBalance] = None
    parent_id: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)

    model_config = ConfigDict(extra="forbid")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("Account code cannot be empty or whitespace only.")
        if not re.match(r"^[A-Z0-9_\-\.]+$", cleaned):
            raise ValueError("Account code contains invalid characters.")
        return cleaned

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Account name cannot be empty or whitespace only.")
        return v.strip()


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Account name cannot be empty or whitespace only.")
            return v.strip()
        return v


class AccountInDB(BaseModel):
    id: str
    business_id: str
    code: str
    name: str
    account_type: AccountType
    normal_balance: NormalBalance
    parent_id: Optional[str] = None
    is_active: bool = True
    is_system: bool = False
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountResponse(AccountInDB):
    current_balance: Decimal = Decimal("0")


class AccountListResponse(BaseModel):
    items: List[AccountResponse]
    total: int


# --- Journal Entry Schemas ---

class JournalLineInput(BaseModel):
    account_id: str = Field(..., min_length=1)
    description: Optional[str] = Field(None, max_length=500)
    debit: Decimal = Field(default=Decimal("0"), ge=0)
    credit: Decimal = Field(default=Decimal("0"), ge=0)

    model_config = ConfigDict(extra="forbid")

    @field_validator("debit", "credit")
    @classmethod
    def validate_amounts(cls, v: Decimal) -> Decimal:
        if v < Decimal("0"):
            raise ValueError("Amount cannot be negative.")
        return v


class JournalEntryCreate(BaseModel):
    branch_id: Optional[str] = None
    journal_date: datetime
    description: str = Field(..., min_length=1, max_length=1000)
    reference_type: Optional[str] = Field(None, max_length=50)
    reference_id: Optional[str] = Field(None, max_length=100)
    lines: List[JournalLineInput] = Field(..., min_items=2)
    idempotency_key: Optional[str] = Field(None, max_length=100)

    model_config = ConfigDict(extra="forbid")


class JournalLineInDB(BaseModel):
    id: str
    journal_entry_id: str
    account_id: str
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    description: Optional[str] = None
    debit: Decimal
    credit: Decimal
    currency: str = "IDR"

    model_config = ConfigDict(from_attributes=True)


class JournalEntryInDB(BaseModel):
    id: str
    business_id: str
    branch_id: Optional[str] = None
    journal_number: str
    journal_date: datetime
    description: str
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    status: JournalStatus
    source: str = "MANUAL"
    total_debit: Decimal
    total_credit: Decimal
    currency: str = "IDR"
    posted_at: Optional[datetime] = None
    posted_by_user_id: Optional[str] = None
    voided_at: Optional[datetime] = None
    voided_by_user_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JournalEntryResponse(JournalEntryInDB):
    lines: List[JournalLineInDB] = []


class JournalEntryListResponse(BaseModel):
    items: List[JournalEntryResponse]
    page: int
    page_size: int
    total: int


# --- Accounting Period & Reports Schemas ---

class AccountingPeriodInDB(BaseModel):
    id: str
    business_id: str
    period_name: str
    start_date: date
    end_date: date
    status: AccountingPeriodStatus
    created_at: datetime
    created_by_user_id: str
    updated_at: datetime
    closed_at: Optional[datetime] = None
    closed_by_user_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AccountingPeriodResponse(AccountingPeriodInDB):
    pass


class AccountingPeriodCreate(BaseModel):
    period_name: str = Field(..., min_length=1, max_length=50)
    start_date: date
    end_date: date

    model_config = ConfigDict(extra="forbid")

    @field_validator("period_name")
    @classmethod
    def validate_period_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Period name cannot be empty or whitespace only.")
        return cleaned

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: date, info) -> date:
        start = info.data.get("start_date")
        if start is not None and v < start:
            raise ValueError("End date must not be earlier than start date.")
        return v


class AccountingPeriodListResponse(BaseModel):
    items: List[AccountingPeriodInDB]
    total: int


class LedgerLineItem(BaseModel):
    journal_id: str
    journal_number: str
    journal_date: datetime
    description: str
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    debit: Decimal
    credit: Decimal
    running_balance: Decimal

    model_config = ConfigDict(from_attributes=True)


class GeneralLedgerResponse(BaseModel):
    account_id: str
    account_code: str
    account_name: str
    account_type: AccountType
    normal_balance: NormalBalance
    opening_balance: Decimal
    total_debit: Decimal
    total_credit: Decimal
    ending_balance: Decimal
    lines: List[LedgerLineItem] = []


class TrialBalanceItem(BaseModel):
    account_id: str
    account_code: str
    account_name: str
    account_type: AccountType
    normal_balance: NormalBalance
    debit_balance: Decimal
    credit_balance: Decimal


class TrialBalanceResponse(BaseModel):
    currency: str = "IDR"
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool
    items: List[TrialBalanceItem] = []


# --- Financial Report Schemas (Feature #36) ---

class ReportAccountItem(BaseModel):
    account_id: str
    account_code: str
    account_name: str
    amount: Decimal


class ProfitAndLossResponse(BaseModel):
    period: AccountingPeriodInDB
    revenue_items: List[ReportAccountItem] = []
    total_revenue: Decimal = Decimal("0")
    expense_items: List[ReportAccountItem] = []
    total_expense: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")


class BalanceSheetItem(BaseModel):
    account_id: str
    account_code: str
    account_name: str
    balance: Decimal


class BalanceSheetResponse(BaseModel):
    period: AccountingPeriodInDB
    as_of_date: date
    asset_items: List[BalanceSheetItem] = []
    total_assets: Decimal = Decimal("0")
    liability_items: List[BalanceSheetItem] = []
    total_liabilities: Decimal = Decimal("0")
    equity_items: List[BalanceSheetItem] = []
    total_equity: Decimal = Decimal("0")
    net_profit_current_period: Decimal = Decimal("0")
    total_liabilities_and_equity: Decimal = Decimal("0")
    is_balanced: bool = True


# --- Cash Flow Report Schemas (Feature #40) ---

class CashFlowPeriodInfo(BaseModel):
    id: Optional[str] = None
    period_name: Optional[str] = None


class CashFlowDateRange(BaseModel):
    start_date: date
    end_date: date


class CashFlowOperatingActivities(BaseModel):
    cash_received_from_customers: Decimal = Decimal("0.00")
    cash_paid_to_suppliers: Decimal = Decimal("0.00")
    cash_paid_for_expenses: Decimal = Decimal("0.00")
    net_cash_from_operating: Decimal = Decimal("0.00")


class CashFlowInvestingActivities(BaseModel):
    net_cash_from_investing: Decimal = Decimal("0.00")


class CashFlowFinancingActivities(BaseModel):
    net_cash_from_financing: Decimal = Decimal("0.00")


class CashFlowResponse(BaseModel):
    period: Optional[CashFlowPeriodInfo] = None
    date_range: CashFlowDateRange
    opening_cash_balance: Decimal = Decimal("0.00")
    operating_activities: CashFlowOperatingActivities
    investing_activities: CashFlowInvestingActivities
    financing_activities: CashFlowFinancingActivities
    net_increase_in_cash: Decimal = Decimal("0.00")
    closing_cash_balance: Decimal = Decimal("0.00")
    reconciliation_status: str = "SUBLEDGER_RECONCILED"

