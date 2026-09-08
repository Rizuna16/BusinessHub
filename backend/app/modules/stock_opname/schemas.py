from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator
from decimal import Decimal


class StockOpnameStatus(str, Enum):
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"


class StockOpnameLineBase(BaseModel):
    product_id: str = Field(..., min_length=1)
    variant_id: Optional[str] = None


class StockOpnameLineCreate(StockOpnameLineBase):
    model_config = ConfigDict(extra="forbid")


class StockOpnameLineUpdateCount(BaseModel):
    counted_quantity: Decimal = Field(..., ge=0, decimal_places=4)

    @field_validator("counted_quantity")
    @classmethod
    def validate_counted_quantity(cls, v: Decimal) -> Decimal:
        if v < Decimal("0"):
            raise ValueError("Counted quantity cannot be negative")
        return v

    model_config = ConfigDict(extra="forbid")


class StockOpnameLineInDB(BaseModel):
    id: str
    opname_id: str
    inventory_location_id: str
    product_id: str
    variant_id: Optional[str] = None
    system_quantity: Decimal
    counted_quantity: Optional[Decimal] = None
    variance: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockOpnameLineResponse(StockOpnameLineInDB):
    pass


class StockOpnameCreate(BaseModel):
    inventory_location_id: str = Field(..., min_length=1)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None

    model_config = ConfigDict(extra="forbid")


class StockOpnameInDB(BaseModel):
    id: str
    business_id: str
    inventory_location_id: str
    status: StockOpnameStatus
    notes: Optional[str] = None
    created_by_user_id: str
    finalized_by_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    finalized_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StockOpnameResponse(StockOpnameInDB):
    lines: List[StockOpnameLineResponse] = []


class StockOpnameListResponse(BaseModel):
    items: List[StockOpnameResponse]
    page: int
    page_size: int
    total: int
