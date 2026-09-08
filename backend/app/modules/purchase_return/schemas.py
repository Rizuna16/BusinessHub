from enum import Enum
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class PurchaseReturnStatus(str, Enum):
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"
    CANCELLED = "CANCELLED"


# --- Purchase Return Line Schemas ---

class PurchaseReturnLineCreate(BaseModel):
    purchase_line_id: str = Field(..., min_length=1)
    quantity: Decimal = Field(..., gt=0)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    discount_amount: Optional[Decimal] = Field(None, ge=0)
    tax_amount: Optional[Decimal] = Field(None, ge=0)

    model_config = ConfigDict(extra="forbid")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
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


class PurchaseReturnLineUpdate(BaseModel):
    quantity: Optional[Decimal] = Field(None, gt=0)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    discount_amount: Optional[Decimal] = Field(None, ge=0)
    tax_amount: Optional[Decimal] = Field(None, ge=0)

    model_config = ConfigDict(extra="forbid")

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


class PurchaseReturnLineInDB(BaseModel):
    id: str
    return_id: str
    purchase_line_id: str
    product_id: str
    variant_id: Optional[str] = None
    quantity: Decimal
    unit_price: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    line_subtotal: Decimal
    line_total: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseReturnLineResponse(PurchaseReturnLineInDB):
    pass


# --- Purchase Return Schemas ---

class PurchaseReturnCreate(BaseModel):
    purchase_id: str = Field(..., min_length=1)
    inventory_location_id: str = Field(..., min_length=1)
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class PurchaseReturnUpdate(BaseModel):
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class PurchaseReturnInDB(BaseModel):
    id: str
    business_id: str
    purchase_id: str
    inventory_location_id: str
    return_number: str
    status: PurchaseReturnStatus
    notes: Optional[str] = None
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    grand_total: Decimal
    created_by_user_id: str
    finalized_by_user_id: Optional[str] = None
    cancelled_by_user_id: Optional[str] = None
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime
    finalized_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseReturnResponse(PurchaseReturnInDB):
    lines: List[PurchaseReturnLineResponse] = []


class PurchaseReturnListResponse(BaseModel):
    items: List[PurchaseReturnResponse]
    page: int
    page_size: int
    total: int
