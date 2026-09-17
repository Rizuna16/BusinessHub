from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class CreditLimitUpdate(BaseModel):
    credit_limit: Decimal = Field(..., ge=0)

    model_config = ConfigDict(extra="forbid")


class StoreCreditAdjust(BaseModel):
    amount: Decimal = Field(..., gt=0)
    reason: Optional[str] = Field(None, max_length=500)

    model_config = ConfigDict(extra="forbid")


class StoreCreditRedeem(BaseModel):
    amount: Decimal = Field(..., gt=0)

    model_config = ConfigDict(extra="forbid")


class CreditExposureResponse(BaseModel):
    customer_id: str
    business_id: str
    credit_limit: Decimal
    total_receivable: Decimal
    exposure: Decimal
    available_credit: Decimal

    model_config = ConfigDict(from_attributes=True)


class CustomerCreditSummaryResponse(BaseModel):
    customer_id: str
    business_id: str
    credit_limit: Decimal
    total_receivable: Decimal
    exposure: Decimal
    available_credit: Decimal
    store_credit_balance: Decimal

    model_config = ConfigDict(from_attributes=True)


class StoreCreditLedgerEntry(BaseModel):
    id: str
    customer_id: str
    business_id: str
    amount: Decimal
    balance_after: Decimal
    direction: str
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    reason: Optional[str] = None
    created_by_user_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StoreCreditLedgerResponse(BaseModel):
    items: list[StoreCreditLedgerEntry]
    total: int
