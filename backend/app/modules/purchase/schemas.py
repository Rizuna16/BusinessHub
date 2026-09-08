from enum import Enum
from datetime import datetime, date
from typing import Optional, List, Any
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class PurchaseStatus(str, Enum):
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"
    CANCELLED = "CANCELLED"


# --- Purchase Line Schemas ---

class PurchaseLineCreate(BaseModel):
    product_id: str = Field(..., min_length=1)
    variant_id: Optional[str] = None
    description: Optional[str] = Field(None, max_length=1000)
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0)

    model_config = ConfigDict(extra="forbid")

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Quantity must be greater than 0")
        return v

    @field_validator("unit_price")
    @classmethod
    def validate_unit_price(cls, v: Decimal) -> Decimal:
        if v < Decimal("0"):
            raise ValueError("Unit price cannot be negative")
        return v

    @field_validator("discount_amount")
    @classmethod
    def validate_discount_amount(cls, v: Decimal) -> Decimal:
        if v < Decimal("0"):
            raise ValueError("Discount amount cannot be negative")
        return v

    @field_validator("tax_amount")
    @classmethod
    def validate_tax_amount(cls, v: Decimal) -> Decimal:
        if v < Decimal("0"):
            raise ValueError("Tax amount cannot be negative")
        return v


class PurchaseLineUpdate(BaseModel):
    product_id: Optional[str] = Field(None, min_length=1)
    variant_id: Optional[str] = None
    description: Optional[str] = Field(None, max_length=1000)
    quantity: Optional[Decimal] = Field(None, gt=0)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    discount_amount: Optional[Decimal] = Field(None, ge=0)
    tax_amount: Optional[Decimal] = Field(None, ge=0)

    model_config = ConfigDict(extra="forbid")

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= Decimal("0"):
            raise ValueError("Quantity must be greater than 0")
        return v

    @field_validator("unit_price")
    @classmethod
    def validate_unit_price(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0"):
            raise ValueError("Unit price cannot be negative")
        return v

    @field_validator("discount_amount")
    @classmethod
    def validate_discount_amount(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0"):
            raise ValueError("Discount amount cannot be negative")
        return v

    @field_validator("tax_amount")
    @classmethod
    def validate_tax_amount(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < Decimal("0"):
            raise ValueError("Tax amount cannot be negative")
        return v


class PurchaseLineInDB(BaseModel):
    id: str
    purchase_id: str
    product_id: str
    variant_id: Optional[str] = None
    description: Optional[str] = None
    quantity: Decimal
    unit_price: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    line_subtotal: Decimal
    line_total: Decimal
    tax_snapshot: Optional[Any] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DerivedReceivingStatus(str, Enum):
    NOT_RECEIVED = "NOT_RECEIVED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    FULLY_RECEIVED = "FULLY_RECEIVED"


class PurchaseReceivingSummary(BaseModel):
    total_ordered: str
    total_received: str
    total_remaining: str
    status: DerivedReceivingStatus

    model_config = ConfigDict(from_attributes=True)


class PurchaseLineResponse(PurchaseLineInDB):
    ordered_quantity: str = "0"
    received_quantity: str = "0"
    remaining_quantity: str = "0"
    suggested_supplier_price: Optional[str] = None


# --- Purchase Schemas ---

class PurchaseCreate(BaseModel):
    supplier_id: str = Field(..., min_length=1)
    branch_id: str = Field(..., min_length=1)
    purchase_date: datetime
    input_vat_creditable: bool = False
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class PurchaseUpdate(BaseModel):
    supplier_id: Optional[str] = Field(None, min_length=1)
    branch_id: Optional[str] = Field(None, min_length=1)
    purchase_date: Optional[datetime] = None
    input_vat_creditable: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class PurchaseInDB(BaseModel):
    id: str
    business_id: str
    supplier_id: str
    branch_id: str
    purchase_number: str
    purchase_date: datetime
    notes: Optional[str] = None
    status: PurchaseStatus
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    grand_total: Decimal
    input_vat_creditable: bool = False
    created_by_user_id: str
    finalized_by_user_id: Optional[str] = None
    cancelled_by_user_id: Optional[str] = None
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime
    finalized_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseResponse(PurchaseInDB):
    lines: List[PurchaseLineResponse] = []
    receiving_summary: Optional[PurchaseReceivingSummary] = None


class PurchaseListResponse(BaseModel):
    items: List[PurchaseResponse]
    page: int
    page_size: int
    total: int
