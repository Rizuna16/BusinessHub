from enum import Enum
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re


class ExpenseStatus(str, Enum):
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"
    CANCELLED = "CANCELLED"


class ExpenseCategoryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


# --- ExpenseCategory Schemas ---

class ExpenseCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=500)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Category name cannot be empty or whitespace only.")
        return v.strip()

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("Category code cannot be empty or whitespace only.")
        if not re.match(r"^[A-Z0-9_\-]+$", cleaned):
            raise ValueError("Category code must contain only alphanumeric characters, hyphens, or underscores.")
        return cleaned


class ExpenseCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Category name cannot be empty or whitespace only.")
            return v.strip()
        return v


class ExpenseCategoryInDB(BaseModel):
    id: str
    business_id: str
    name: str
    code: str
    description: Optional[str] = None
    status: ExpenseCategoryStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpenseCategoryResponse(ExpenseCategoryInDB):
    pass


class ExpenseCategoryListResponse(BaseModel):
    items: List[ExpenseCategoryResponse]
    page: int
    page_size: int
    total: int


# --- Expense Schemas ---

class ExpenseCreate(BaseModel):
    category_id: str = Field(..., min_length=1)
    cash_account_id: Optional[str] = Field(None, min_length=1)
    supplier_id: Optional[str] = Field(None, min_length=1)
    expense_date: datetime
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("IDR", min_length=3, max_length=3)
    description: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Amount must be greater than 0")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if cleaned not in ["IDR", "USD", "SGD", "MYR", "EUR", "JPY"]:
            raise ValueError(f"Unsupported currency code: {cleaned}")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class ExpenseUpdate(BaseModel):
    category_id: Optional[str] = Field(None, min_length=1)
    cash_account_id: Optional[str] = Field(None, min_length=1)
    supplier_id: Optional[str] = Field(None, min_length=1)
    expense_date: Optional[datetime] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    description: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= Decimal("0"):
            raise ValueError("Amount must be greater than 0")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip().upper()
            if cleaned not in ["IDR", "USD", "SGD", "MYR", "EUR", "JPY"]:
                raise ValueError(f"Unsupported currency code: {cleaned}")
            return cleaned
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class ExpenseInDB(BaseModel):
    id: str
    business_id: str
    expense_number: str
    expense_date: datetime
    category_id: str
    cash_account_id: Optional[str] = None
    supplier_id: Optional[str] = None
    amount: Decimal
    currency: str
    description: Optional[str] = None
    status: ExpenseStatus
    created_by_user_id: str
    finalized_by_user_id: Optional[str] = None
    cancelled_by_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    finalized_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ExpenseResponse(ExpenseInDB):
    category_name: Optional[str] = None
    cash_account_name: Optional[str] = None
    supplier_name: Optional[str] = None


class ExpenseListResponse(BaseModel):
    items: List[ExpenseResponse]
    page: int
    page_size: int
    total: int


class ExpenseSummaryResponse(BaseModel):
    total_expense_amount: Decimal
    expense_count: int
    finalized_count: int
    draft_count: int
    currency: str = "IDR"


class CategoryBreakdownItem(BaseModel):
    category_id: Optional[str] = None
    category_code: str
    category_name: str
    total: Decimal
    expense_count: int


class ExpenseAnalyticsByCategoryResponse(BaseModel):
    date_from: datetime
    date_to: datetime
    total: Decimal
    expense_count: int
    categories: List[CategoryBreakdownItem]
