from enum import Enum
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class ReceivableStatus(str, Enum):
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"


class ReceivablePaymentItem(BaseModel):
    id: str
    payment_number: str
    payment_date: datetime
    payment_method: str
    amount: Decimal
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    status: str
    created_by_user_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SalesReceivableResponse(BaseModel):
    sales_id: str
    business_id: str
    sales_number: str
    sales_date: datetime
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    branch_id: str
    branch_name: Optional[str] = None
    sales_total: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    status: ReceivableStatus
    payment_count: int
    last_payment_date: Optional[datetime] = None
    payments: List[ReceivablePaymentItem] = []

    model_config = ConfigDict(from_attributes=True)


class SalesReceivableListResponse(BaseModel):
    items: List[SalesReceivableResponse]
    page: int
    page_size: int
    total: int


class SalesReceivableSummaryResponse(BaseModel):
    total_sales_amount: Decimal
    total_paid_amount: Decimal
    total_outstanding_amount: Decimal
    unpaid_count: int
    partially_paid_count: int
    paid_count: int


class CustomerReceivableSummaryItem(BaseModel):
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    total_sales: Decimal
    total_paid: Decimal
    total_outstanding: Decimal
    sales_count: int


class CustomerReceivableSummaryListResponse(BaseModel):
    items: List[CustomerReceivableSummaryItem]


# --- Statement of Account Schemas (Feature #41) ---

class StatementDateRange(BaseModel):
    start_date: date
    end_date: date


class StatementLineResponse(BaseModel):
    transaction_date: datetime
    transaction_type: str
    reference_id: str
    reference_number: Optional[str] = None
    description: Optional[str] = None
    debit: Decimal = Decimal("0.00")
    credit: Decimal = Decimal("0.00")
    running_balance: Decimal = Decimal("0.00")

    model_config = ConfigDict(from_attributes=True)


class CustomerStatementResponse(BaseModel):
    entity_id: str
    entity_name: Optional[str] = None
    date_range: StatementDateRange
    opening_balance: Decimal = Decimal("0.00")
    lines: List[StatementLineResponse] = []
    closing_balance: Decimal = Decimal("0.00")
    total_debit: Decimal = Decimal("0.00")
    total_credit: Decimal = Decimal("0.00")
    page: int = 1
    page_size: int = 100
    total_items: int = 0

