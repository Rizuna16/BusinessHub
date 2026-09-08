from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class PaymentMethod(str, Enum):
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"
    DEBIT_CARD = "DEBIT_CARD"
    CREDIT_CARD = "CREDIT_CARD"
    QRIS = "QRIS"
    E_WALLET = "E_WALLET"
    OTHER = "OTHER"


class PaymentStatus(str, Enum):
    RECORDED = "RECORDED"
    CANCELLED = "CANCELLED"


class SalesPaymentCreate(BaseModel):
    payment_date: Optional[datetime] = None
    payment_method: PaymentMethod
    amount: Decimal = Field(..., gt=0)
    reference_number: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("reference_number")
    @classmethod
    def validate_reference_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Payment amount must be greater than 0")
        return v


class SalesPaymentInDB(BaseModel):
    id: str
    business_id: str
    sales_id: str
    payment_number: str
    payment_date: datetime
    payment_method: PaymentMethod
    amount: Decimal
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    status: PaymentStatus
    created_by_user_id: str
    cancelled_by_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    cancelled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SalesPaymentResponse(SalesPaymentInDB):
    pass


class SalesPaymentSummary(BaseModel):
    total_paid: Decimal
    remaining_amount: Decimal
    grand_total: Decimal


class SalesPaymentListResponse(BaseModel):
    items: List[SalesPaymentResponse]
    summary: SalesPaymentSummary
    page: int
    page_size: int
    total: int
