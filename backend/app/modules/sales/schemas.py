from enum import Enum
from datetime import datetime
from typing import Optional, List, Any
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class SalesStatus(str, Enum):
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"
    CANCELLED = "CANCELLED"


class SalesLineCreate(BaseModel):
    product_id: Optional[str] = None
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

    def model_post_init(self, __context) -> None:
        # 31. product + variant rejected & 32. neither rejected
        p_provided = self.product_id is not None and self.product_id != ""
        v_provided = self.variant_id is not None and self.variant_id != ""
        if (p_provided and v_provided) or (not p_provided and not v_provided):
            raise ValueError("Sales line must target exactly one product OR variant.")

        line_subtotal = self.quantity * self.unit_price
        line_total = line_subtotal - self.discount_amount + self.tax_amount
        if line_total < Decimal("0"):
            raise ValueError("Discount causes line total to be negative.")


class SalesLineUpdate(BaseModel):
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


class SalesLineInDB(BaseModel):
    id: str
    sales_id: str
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
    unit_cost_snapshot: Optional[Decimal] = None
    cost_total_snapshot: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SalesLineResponse(SalesLineInDB):
    suggested_selling_price: Optional[str] = None


class SalesCreate(BaseModel):
    customer_id: Optional[str] = None
    branch_id: str = Field(..., min_length=1)
    sales_date: datetime
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class SalesUpdate(BaseModel):
    customer_id: Optional[str] = None
    branch_id: Optional[str] = Field(None, min_length=1)
    sales_date: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class SalesFinalize(BaseModel):
    inventory_location_id: Optional[str] = Field(None, min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("inventory_location_id")
    @classmethod
    def validate_location(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class SalesInDB(BaseModel):
    id: str
    business_id: str
    customer_id: Optional[str] = None
    branch_id: str
    sales_number: str
    sales_date: datetime
    notes: Optional[str] = None
    status: SalesStatus
    is_deleted: bool = False
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    grand_total: Decimal
    created_by_user_id: str
    finalized_by_user_id: Optional[str] = None
    cancelled_by_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    finalized_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SalesResponse(SalesInDB):
    lines: List[SalesLineResponse] = []


class SalesListResponse(BaseModel):
    items: List[SalesResponse]
    page: int
    page_size: int
    total: int
