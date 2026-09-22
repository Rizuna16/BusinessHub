from enum import Enum
from datetime import datetime, date
from typing import Optional, List, Any
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class DeliveryNoteStatus(str, Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class DeliveryNoteLineCreate(BaseModel):
    sales_order_line_id: str = Field(..., min_length=1)
    delivery_quantity: Decimal = Field(..., gt=0)
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class DeliveryNoteLineUpdate(BaseModel):
    delivery_quantity: Optional[Decimal] = Field(None, gt=0)
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class DeliveryNoteLineInDB(BaseModel):
    id: str
    delivery_note_id: str
    sales_order_line_id: str
    product_id: str
    variant_id: Optional[str] = None
    product_name_snapshot: str
    variant_snapshot: Optional[str] = None
    ordered_quantity_snapshot: Decimal
    fulfilled_quantity_snapshot: Decimal
    delivery_quantity: Decimal
    unit: Optional[str] = None
    notes: Optional[str] = None
    batch_allocations: Optional[List[dict]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeliveryNoteLineResponse(DeliveryNoteLineInDB):
    pass


class DeliveryNoteCreate(BaseModel):
    sales_order_id: str = Field(..., min_length=1)
    branch_id: str = Field(..., min_length=1)
    customer_id: Optional[str] = None
    delivery_date: datetime
    shipping_address: Optional[str] = Field(None, max_length=1000)
    recipient_name: Optional[str] = Field(None, max_length=255)
    recipient_phone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=1000)
    lines: List[DeliveryNoteLineCreate] = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("shipping_address", "recipient_name", "recipient_phone", "notes")
    @classmethod
    def validate_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class DeliveryNoteUpdate(BaseModel):
    delivery_date: Optional[datetime] = None
    shipping_address: Optional[str] = Field(None, max_length=1000)
    recipient_name: Optional[str] = Field(None, max_length=255)
    recipient_phone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("shipping_address", "recipient_name", "recipient_phone", "notes")
    @classmethod
    def validate_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class DeliveryNoteInDB(BaseModel):
    id: str
    business_id: str
    branch_id: str
    delivery_number: str
    sales_order_id: str
    customer_id: Optional[str] = None
    delivery_date: datetime
    status: DeliveryNoteStatus
    shipping_address: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None
    notes: Optional[str] = None
    created_by_user_id: str
    ready_by_user_id: Optional[str] = None
    ready_at: Optional[datetime] = None
    delivered_by_user_id: Optional[str] = None
    delivered_at: Optional[datetime] = None
    cancelled_by_user_id: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeliveryNoteResponse(DeliveryNoteInDB):
    lines: List[DeliveryNoteLineResponse] = []


class DeliveryNoteListResponse(BaseModel):
    items: List[DeliveryNoteResponse]
    page: int
    page_size: int
    total: int
