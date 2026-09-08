from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from app.modules.aging.utils import AgingBucket


class ARInvoiceAgingItem(BaseModel):
    sales_id: str
    sales_number: str
    sales_date: datetime
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    branch_id: str
    branch_name: Optional[str] = None
    original_amount: Decimal
    return_adjustment: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    aging_days: int
    aging_bucket: AgingBucket

    model_config = ConfigDict(from_attributes=True)


class ARCustomerAgingSummaryItem(BaseModel):
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    total_original: Decimal
    total_return_adjustment: Decimal
    total_paid: Decimal
    total_outstanding: Decimal
    invoice_count: int
    current: Decimal
    bucket_1_30: Decimal
    bucket_31_60: Decimal
    bucket_61_90: Decimal
    bucket_91_120: Decimal
    bucket_over_120: Decimal

    model_config = ConfigDict(from_attributes=True)


class ARAgingSummary(BaseModel):
    total_original: Decimal
    total_return_adjustment: Decimal
    total_paid: Decimal
    total_outstanding: Decimal
    current: Decimal
    bucket_1_30: Decimal
    bucket_31_60: Decimal
    bucket_61_90: Decimal
    bucket_91_120: Decimal
    bucket_over_120: Decimal


class ARAgingResponse(BaseModel):
    as_of_date: datetime
    summary: ARAgingSummary
    customers: List[ARCustomerAgingSummaryItem]
    invoices: List[ARInvoiceAgingItem]


class APInvoiceAgingItem(BaseModel):
    purchase_id: str
    purchase_number: str
    purchase_date: datetime
    supplier_id: str
    supplier_name: Optional[str] = None
    supplier_code: Optional[str] = None
    branch_id: str
    branch_name: Optional[str] = None
    gross_payable: Decimal
    return_adjustment: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    aging_days: int
    aging_bucket: AgingBucket

    model_config = ConfigDict(from_attributes=True)


class APSupplierAgingSummaryItem(BaseModel):
    supplier_id: str
    supplier_name: Optional[str] = None
    supplier_code: Optional[str] = None
    total_gross: Decimal
    total_return_adjustment: Decimal
    total_paid: Decimal
    total_outstanding: Decimal
    purchase_count: int
    current: Decimal
    bucket_1_30: Decimal
    bucket_31_60: Decimal
    bucket_61_90: Decimal
    bucket_91_120: Decimal
    bucket_over_120: Decimal

    model_config = ConfigDict(from_attributes=True)


class APAgingSummary(BaseModel):
    total_gross: Decimal
    total_return_adjustment: Decimal
    total_paid: Decimal
    total_outstanding: Decimal
    current: Decimal
    bucket_1_30: Decimal
    bucket_31_60: Decimal
    bucket_61_90: Decimal
    bucket_91_120: Decimal
    bucket_over_120: Decimal


class APAgingResponse(BaseModel):
    as_of_date: datetime
    summary: APAgingSummary
    suppliers: List[APSupplierAgingSummaryItem]
    purchases: List[APInvoiceAgingItem]


class AgingFilterParams(BaseModel):
    as_of_date: Optional[datetime] = None
    customer_id: Optional[str] = None
    supplier_id: Optional[str] = None
    branch_id: Optional[str] = None
    bucket: Optional[AgingBucket] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)