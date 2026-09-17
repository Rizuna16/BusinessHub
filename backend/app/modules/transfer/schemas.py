from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransferStatus(str, Enum):
    DRAFT = "DRAFT"
    DISPATCHED = "DISPATCHED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class TransferLineCreate(BaseModel):
    product_id: str = Field(..., min_length=1)
    variant_id: Optional[str] = Field(None, min_length=1)
    quantity: Decimal = Field(..., gt=0, decimal_places=4)

    model_config = ConfigDict(extra="forbid")

    @field_validator("product_id")
    @classmethod
    def validate_product_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("product_id must not be blank")
        return v

    @field_validator("variant_id")
    @classmethod
    def validate_variant_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class TransferLineInDB(BaseModel):
    id: str
    transfer_id: str
    product_id: str
    variant_id: Optional[str] = None
    quantity: Decimal
    unit_cost_snapshot: Decimal = Decimal("0")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransferLineResponse(TransferLineInDB):
    pass


class TransferCreate(BaseModel):
    source_location_id: str = Field(..., min_length=1)
    destination_location_id: str = Field(..., min_length=1)
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("source_location_id")
    @classmethod
    def validate_source_location_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("source_location_id must not be blank")
        return v

    @field_validator("destination_location_id")
    @classmethod
    def validate_destination_location_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("destination_location_id must not be blank")
        return v

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class TransferInDB(BaseModel):
    id: str
    business_id: str
    transfer_number: str
    source_location_id: str
    destination_location_id: str
    status: TransferStatus
    notes: Optional[str] = None
    created_by_user_id: str
    dispatched_by_user_id: Optional[str] = None
    received_by_user_id: Optional[str] = None
    cancelled_by_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    dispatched_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TransferResponse(TransferInDB):
    lines: List[TransferLineResponse] = []


class TransferListResponse(BaseModel):
    items: List[TransferResponse]
    page: int
    page_size: int
    total: int
