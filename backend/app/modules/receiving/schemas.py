from enum import Enum
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ReceivingStatus(str, Enum):
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"
    CANCELLED = "CANCELLED"


class ReceivingLineCreate(BaseModel):
    purchase_line_id: str = Field(..., min_length=1)
    quantity: Decimal = Field(..., gt=0)

    model_config = ConfigDict(extra="forbid")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Quantity must be greater than 0")
        return v


class ReceivingLineUpdate(BaseModel):
    quantity: Decimal = Field(..., gt=0)

    model_config = ConfigDict(extra="forbid")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Quantity must be greater than 0")
        return v


class ReceivingLineInDB(BaseModel):
    id: str
    receiving_id: str
    purchase_line_id: str
    product_id: str
    variant_id: Optional[str] = None
    quantity: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReceivingLineResponse(ReceivingLineInDB):
    pass


class ReceivingCreate(BaseModel):
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


class ReceivingUpdate(BaseModel):
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class ReceivingInDB(BaseModel):
    id: str
    business_id: str
    purchase_id: str
    inventory_location_id: str
    receiving_number: str
    status: ReceivingStatus
    notes: Optional[str] = None
    created_by_user_id: str
    finalized_by_user_id: Optional[str] = None
    cancelled_by_user_id: Optional[str] = None
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime
    finalized_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ReceivingResponse(ReceivingInDB):
    lines: List[ReceivingLineResponse] = []


class ReceivingListResponse(BaseModel):
    items: List[ReceivingResponse]
    page: int
    page_size: int
    total: int
