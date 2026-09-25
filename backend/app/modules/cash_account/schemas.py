from enum import Enum
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re


class CashAccountType(str, Enum):
    CASH = "CASH"
    BANK = "BANK"
    E_WALLET = "E_WALLET"
    OTHER = "OTHER"


class CashAccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class CashMovementType(str, Enum):
    OPENING_BALANCE = "OPENING_BALANCE"
    CASH_IN = "CASH_IN"
    CASH_OUT = "CASH_OUT"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    SALES_PAYMENT = "SALES_PAYMENT"
    EXPENSE = "EXPENSE"


class MovementDirection(str, Enum):
    IN = "IN"
    OUT = "OUT"


class CashMovementStatus(str, Enum):
    POSTED = "POSTED"
    CANCELLED = "CANCELLED"


# --- CashAccount Schemas ---

class CashAccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    account_type: CashAccountType
    currency: str = Field("IDR", min_length=3, max_length=3)
    description: Optional[str] = Field(None, max_length=500)
    opening_balance: Decimal = Field(default=Decimal("0"), ge=0)
    is_default: bool = False

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Cash account name cannot be empty or whitespace only.")
        return v.strip()

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("Cash account code cannot be empty or whitespace only.")
        if not re.match(r"^[A-Z0-9_\-]+$", cleaned):
            raise ValueError("Cash account code must contain only alphanumeric characters, hyphens, or underscores.")
        return cleaned

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if cleaned not in ["IDR", "USD", "SGD", "MYR", "EUR", "JPY"]:
            raise ValueError(f"Unsupported currency code: {cleaned}")
        return cleaned


class CashAccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_default: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Cash account name cannot be empty or whitespace only.")
            return v.strip()
        return v


class CashAccountInDB(BaseModel):
    id: str
    business_id: str
    name: str
    code: str
    account_type: CashAccountType
    currency: str
    description: Optional[str] = None
    opening_balance: Decimal
    status: CashAccountStatus
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CashAccountResponse(CashAccountInDB):
    current_balance: Decimal = Decimal("0")


class CashAccountListResponse(BaseModel):
    items: List[CashAccountResponse]
    page: int
    page_size: int
    total: int


# --- CashMovement Schemas ---

class CashMovementCreate(BaseModel):
    movement_type: CashMovementType
    amount: Decimal = Field(..., gt=0)
    direction: MovementDirection
    reference_type: Optional[str] = Field(None, max_length=50)
    reference_id: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    shift_id: Optional[str] = Field(None, max_length=100)

    model_config = ConfigDict(extra="forbid")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Amount must be greater than 0")
        return v


class CashTransferInput(BaseModel):
    source_account_id: str = Field(..., min_length=1)
    destination_account_id: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=1000)
    idempotency_key: Optional[str] = Field(None, max_length=100)

    model_config = ConfigDict(extra="forbid")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Transfer amount must be greater than 0")
        return v


class CashMovementInDB(BaseModel):
    id: str
    business_id: str
    cash_account_id: str
    movement_type: CashMovementType
    amount: Decimal
    direction: MovementDirection
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    description: Optional[str] = None
    performed_by_user_id: str
    shift_id: Optional[str] = None
    status: CashMovementStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CashMovementResponse(CashMovementInDB):
    pass


class CashMovementListResponse(BaseModel):
    items: List[CashMovementResponse]
    page: int
    page_size: int
    total: int


class CashSummaryResponse(BaseModel):
    total_cash_balance: Decimal
    cash_account_count: int
    active_account_count: int
    currency: str = "IDR"
