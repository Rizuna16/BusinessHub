from enum import Enum
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ShiftStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class CashierShiftCreate(BaseModel):
    branch_id: str = Field(..., min_length=1)
    cash_account_id: str = Field(..., min_length=1)
    opening_balance: Decimal = Field(default=Decimal("0"), ge=0)
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class CashierShiftClose(BaseModel):
    actual_cash_count: Decimal = Field(..., ge=0)
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class CashierShiftForceClose(BaseModel):
    notes: str = Field(..., min_length=1, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: str) -> str:
        return v.strip()


class CashierShiftInDB(BaseModel):
    id: str
    business_id: str
    branch_id: str
    cashier_user_id: str
    cash_account_id: str
    opening_balance: Decimal
    actual_cash_count: Optional[Decimal] = None
    discrepancy: Optional[Decimal] = None
    status: ShiftStatus
    opened_at: datetime
    closed_at: Optional[datetime] = None
    closed_by_user_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CashierShiftResponse(CashierShiftInDB):
    expected_cash: Optional[Decimal] = None
    cash_account_name: Optional[str] = None
    branch_name: Optional[str] = None
    cashier_name: Optional[str] = None


class CashierShiftListResponse(BaseModel):
    items: List[CashierShiftResponse]
    page: int
    page_size: int
    total: int
