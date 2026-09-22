from enum import Enum
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator


class BatchMovementDirection(str, Enum):
    IN = "IN"
    OUT = "OUT"


class InventoryBatchCreate(BaseModel):
    inventory_location_id: str = Field(..., min_length=1)
    product_id: str = Field(..., min_length=1)
    variant_id: Optional[str] = None
    batch_number: str = Field(..., min_length=1, max_length=100)
    manufacture_date: Optional[date] = None
    expiry_date: Optional[date] = None
    initial_quantity: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=4)

    @field_validator("batch_number")
    @classmethod
    def validate_batch_number(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Batch number cannot be empty or whitespace-only")
        return v.strip()

    @field_validator("expiry_date", "manufacture_date", mode="before")
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v

    model_config = ConfigDict(extra="forbid")


class InventoryBatchUpdate(BaseModel):
    manufacture_date: Optional[date] = None
    expiry_date: Optional[date] = None

    @field_validator("expiry_date", "manufacture_date", mode="before")
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v

    model_config = ConfigDict(extra="forbid")


class InventoryBatchInDB(BaseModel):
    id: str
    business_id: str
    inventory_location_id: str
    product_id: str
    variant_id: Optional[str] = None
    batch_number: str
    manufacture_date: Optional[date] = None
    expiry_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryBatchResponse(InventoryBatchInDB):
    remaining_quantity: Decimal = Decimal("0")

    @classmethod
    def from_db(cls, db_obj, remaining: Decimal = Decimal("0")) -> "InventoryBatchResponse":
        return cls(
            id=db_obj.id,
            business_id=db_obj.business_id,
            inventory_location_id=db_obj.inventory_location_id,
            product_id=db_obj.product_id,
            variant_id=db_obj.variant_id,
            batch_number=db_obj.batch_number,
            manufacture_date=db_obj.manufacture_date,
            expiry_date=db_obj.expiry_date,
            created_at=db_obj.created_at,
            updated_at=db_obj.updated_at,
            remaining_quantity=remaining,
        )


class InventoryBatchListResponse(BaseModel):
    items: List[InventoryBatchResponse]
    page: int
    page_size: int
    total: int


class BatchStockBalanceInDB(BaseModel):
    id: str
    business_id: str
    inventory_location_id: str
    batch_id: str
    product_id: str
    variant_id: Optional[str] = None
    quantity: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchStockMovementInDB(BaseModel):
    id: str
    business_id: str
    stock_movement_id: str
    batch_id: str
    inventory_location_id: str
    product_id: str
    variant_id: Optional[str] = None
    quantity: Decimal
    direction: BatchMovementDirection
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchStockMovementResponse(BatchStockMovementInDB):
    pass


class BatchLedgerResponse(BaseModel):
    batch: InventoryBatchInDB
    balance: Optional[BatchStockBalanceInDB] = None
    movements: List[BatchStockMovementResponse] = []


class BatchAllocationInput(BaseModel):
    batch_id: str = Field(..., min_length=1)
    quantity: Decimal = Field(..., gt=0, decimal_places=4)

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    model_config = ConfigDict(extra="forbid")


class BatchReceivingInput(BaseModel):
    batch_number: str = Field(..., min_length=1, max_length=100)
    quantity: Decimal = Field(..., gt=0, decimal_places=4)
    manufacture_date: Optional[date] = None
    expiry_date: Optional[date] = None

    @field_validator("batch_number")
    @classmethod
    def validate_batch_number(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Batch number cannot be empty")
        return v.strip()

    @field_validator("expiry_date", "manufacture_date", mode="before")
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v

    model_config = ConfigDict(extra="forbid")


class BatchFulfillmentAllocation(BaseModel):
    batch_id: str
    quantity: Decimal


class FEFOCandidate(BaseModel):
    batch_id: str
    batch_number: str
    expiry_date: Optional[date] = None
    available_quantity: Decimal
    is_expired: bool = False


class FEFOCandidateListResponse(BaseModel):
    candidates: List[FEFOCandidate]


class ExpiredBatchOverrideInput(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Override reason is required")
        return v.strip()

    model_config = ConfigDict(extra="forbid")


class ProductBatchConfigUpdate(BaseModel):
    batch_tracking_enabled: bool

    model_config = ConfigDict(extra="forbid")


class BatchOpnameLineInput(BaseModel):
    product_id: str = Field(..., min_length=1)
    variant_id: Optional[str] = None
    batch_id: str = Field(..., min_length=1)
    counted_quantity: Decimal = Field(..., ge=0, decimal_places=4)

    model_config = ConfigDict(extra="forbid")


class BatchTransferInput(BaseModel):
    batch_id: str = Field(..., min_length=1)
    quantity: Decimal = Field(..., gt=0, decimal_places=4)

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    model_config = ConfigDict(extra="forbid")
