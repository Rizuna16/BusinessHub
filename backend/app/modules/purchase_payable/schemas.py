from enum import Enum
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class PayableStatus(str, Enum):
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"


class PayableReturnItem(BaseModel):
    id: str
    return_number: str
    return_date: datetime
    grand_total: Decimal
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchasePayableResponse(BaseModel):
    purchase_id: str
    business_id: str
    purchase_number: str
    purchase_date: datetime
    supplier_id: str
    supplier_name: Optional[str] = None
    supplier_code: Optional[str] = None
    branch_id: str
    branch_name: Optional[str] = None
    currency: str = "IDR"
    gross_payable: Decimal
    return_adjustment: Decimal
    net_payable: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    status: PayableStatus
    return_count: int = 0
    returns: List[PayableReturnItem] = []

    model_config = ConfigDict(from_attributes=True)


class PurchasePayableListResponse(BaseModel):
    items: List[PurchasePayableResponse]
    page: int
    page_size: int
    total: int


class PurchasePayableSummaryResponse(BaseModel):
    currency: str = "IDR"
    total_gross_payable: Decimal
    total_return_adjustment: Decimal
    total_net_payable: Decimal
    total_paid_amount: Decimal
    total_outstanding_amount: Decimal
    unpaid_count: int
    partially_paid_count: int
    paid_count: int
    supplier_count: int


class SupplierPayableSummaryItem(BaseModel):
    supplier_id: str
    supplier_name: Optional[str] = None
    supplier_code: Optional[str] = None
    currency: str = "IDR"
    total_gross_payable: Decimal
    total_return_adjustment: Decimal
    total_net_payable: Decimal
    total_paid_amount: Decimal
    total_outstanding_amount: Decimal
    purchase_count: int
    status: PayableStatus


class SupplierPayableSummaryListResponse(BaseModel):
    items: List[SupplierPayableSummaryItem]


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


class SupplierStatementResponse(BaseModel):
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

