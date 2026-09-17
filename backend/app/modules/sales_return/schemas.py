from enum import Enum
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class SalesReturnStatus(str, Enum):
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"
    CANCELLED = "CANCELLED"


class SalesReturnRefundDestination(str, Enum):
    CASH = "CASH"
    STORE_CREDIT = "STORE_CREDIT"


class SalesReturnLineCreate(BaseModel):
    sales_line_id: str = Field(..., min_length=1)
    quantity: Decimal = Field(..., gt=0)
    delivery_note_id: Optional[str] = Field(None, min_length=1)
    delivery_note_line_id: Optional[str] = Field(None, min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Quantity must be greater than 0")
        return v

    @field_validator("delivery_note_id", "delivery_note_line_id")
    @classmethod
    def validate_dn_refs(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v if v else None
        return None


class SalesReturnLineUpdate(BaseModel):
    quantity: Decimal = Field(..., gt=0)
    delivery_note_id: Optional[str] = Field(None, min_length=1)
    delivery_note_line_id: Optional[str] = Field(None, min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Quantity must be greater than 0")
        return v

    @field_validator("delivery_note_id", "delivery_note_line_id")
    @classmethod
    def validate_dn_refs(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v if v else None
        return None


class SalesReturnLineInDB(BaseModel):
    id: str
    sales_return_id: str
    sales_line_id: str
    product_id: str
    variant_id: Optional[str] = None
    quantity: Decimal
    unit_price: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    line_subtotal: Decimal
    line_total: Decimal
    delivery_note_id: Optional[str] = None
    delivery_note_line_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SalesReturnLineResponse(SalesReturnLineInDB):
    pass


class SalesReturnCreate(BaseModel):
    sales_id: str = Field(..., min_length=1)
    inventory_location_id: Optional[str] = Field(None, min_length=1)
    refund_destination: Optional[str] = Field("CASH", pattern="^(CASH|STORE_CREDIT)$")
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("refund_destination")
    @classmethod
    def validate_destination(cls, v: Optional[str]) -> str:
        if v is None:
            return "CASH"
        v = v.strip().upper()
        if v not in ("CASH", "STORE_CREDIT"):
            raise ValueError("refund_destination must be CASH or STORE_CREDIT.")
        return v

    @field_validator("inventory_location_id")
    @classmethod
    def validate_location(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class SalesReturnUpdate(BaseModel):
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class SalesReturnInDB(BaseModel):
    id: str
    business_id: str
    sales_id: str
    inventory_location_id: str
    return_number: str
    return_date: datetime
    status: SalesReturnStatus
    refund_destination: str = "CASH"
    notes: Optional[str] = None
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


class SalesReturnResponse(SalesReturnInDB):
    lines: List[SalesReturnLineResponse] = []


class SalesReturnListResponse(BaseModel):
    items: List[SalesReturnResponse]
    page: int
    page_size: int
    total: int
