from enum import Enum
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class PaymentDirection(str, Enum):
    CUSTOMER_IN = "CUSTOMER_IN"
    SUPPLIER_OUT = "SUPPLIER_OUT"


class PaymentTargetType(str, Enum):
    SALES = "SALES"
    PURCHASE = "PURCHASE"


class PaymentMethod(str, Enum):
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"
    DEBIT_CARD = "DEBIT_CARD"
    CREDIT_CARD = "CREDIT_CARD"
    QRIS = "QRIS"
    E_WALLET = "E_WALLET"
    STORE_CREDIT = "STORE_CREDIT"
    OTHER = "OTHER"


class PaymentStatus(str, Enum):
    RECORDED = "RECORDED"
    VOIDED = "VOIDED"


class PaymentCreate(BaseModel):
    direction: PaymentDirection
    target_type: PaymentTargetType
    target_id: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("IDR", min_length=3, max_length=3)
    payment_method: PaymentMethod
    cash_account_id: Optional[str] = Field(None, min_length=1)
    customer_id: Optional[str] = Field(None, min_length=1)
    payment_date: Optional[datetime] = None
    reference_number: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=1000)
    idempotency_key: Optional[str] = Field(None, max_length=100)
    shift_id: Optional[str] = Field(None, max_length=100)

    model_config = ConfigDict(extra="forbid")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if cleaned not in ["IDR", "USD", "SGD", "MYR", "EUR", "JPY"]:
            raise ValueError(f"Unsupported currency code: {cleaned}")
        return cleaned

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Payment amount must be greater than 0")
        return v


class PaymentInDB(BaseModel):
    id: str
    business_id: str
    branch_id: str
    direction: PaymentDirection
    target_type: PaymentTargetType
    target_id: str
    payment_number: str
    payment_date: datetime
    payment_method: PaymentMethod
    amount: Decimal
    currency: str
    cash_account_id: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    status: PaymentStatus
    created_by_user_id: str
    voided_by_user_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    voided_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentResponse(PaymentInDB):
    pass


class PaymentListResponse(BaseModel):
    items: List[PaymentResponse]
    page: int
    page_size: int
    total: int


# --- Payment Analytics Schemas ---

class PaymentAnalyticsSummaryResponse(BaseModel):
    date_from: datetime
    date_to: datetime
    gross_recorded: Decimal
    customer_in_total: Decimal
    supplier_out_total: Decimal
    net_payment_flow: Decimal
    voided_count: int
    voided_amount: Decimal
    payment_count: int
    average_payment_value: Decimal


class PaymentDirectionBreakdownItem(BaseModel):
    direction: str
    amount: Decimal
    payment_count: int


class PaymentAnalyticsByDirectionResponse(BaseModel):
    date_from: datetime
    date_to: datetime
    gross_recorded: Decimal
    payment_count: int
    directions: List[PaymentDirectionBreakdownItem]


class PaymentMethodBreakdownItem(BaseModel):
    payment_method: str
    amount: Decimal
    payment_count: int


class PaymentAnalyticsByMethodResponse(BaseModel):
    date_from: datetime
    date_to: datetime
    gross_recorded: Decimal
    payment_count: int
    methods: List[PaymentMethodBreakdownItem]
