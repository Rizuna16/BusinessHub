from enum import Enum
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator
from decimal import Decimal


class MovementType(str, Enum):
    OPENING_BALANCE = "OPENING_BALANCE"
    ADJUSTMENT_IN = "ADJUSTMENT_IN"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    SALE_OUT = "SALE_OUT"
    SALE_RETURN_IN = "SALE_RETURN_IN"


class MovementStatus(str, Enum):
    POSTED = "POSTED"


class MovementDirection(str, Enum):
    IN = "IN"
    OUT = "OUT"


class ReferenceType(str, Enum):
    OPENING_BALANCE = "OPENING_BALANCE"
    ADJUSTMENT = "ADJUSTMENT"
    TRANSFER = "TRANSFER"
    STOCK_OPNAME = "STOCK_OPNAME"
    SALES = "SALES"
    SALES_RETURN = "SALES_RETURN"


class StockBalanceBase(BaseModel):
    inventory_location_id: str = Field(..., min_length=1)
    product_id: str = Field(..., min_length=1)
    variant_id: Optional[str] = None
    quantity: Decimal = Field(..., ge=0, decimal_places=4)

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Quantity cannot be negative")
        return v


class StockBalanceCreate(StockBalanceBase):
    model_config = ConfigDict(extra="forbid")


class StockBalanceInDB(BaseModel):
    id: str
    business_id: str
    inventory_location_id: str
    product_id: str
    variant_id: Optional[str] = None
    quantity: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockBalanceResponse(StockBalanceInDB):
    pass


class StockBalanceListResponse(BaseModel):
    items: List[StockBalanceResponse]
    page: int
    page_size: int
    total: int


class StockMovementLineBase(BaseModel):
    inventory_location_id: str = Field(..., min_length=1)
    product_id: str = Field(..., min_length=1)
    variant_id: Optional[str] = None
    quantity: Decimal = Field(..., gt=0, decimal_places=4)
    direction: MovementDirection

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v


class StockMovementLineCreate(StockMovementLineBase):
    model_config = ConfigDict(extra="forbid")


class StockMovementLineInDB(BaseModel):
    id: str
    movement_id: str
    inventory_location_id: str
    product_id: str
    variant_id: Optional[str] = None
    quantity: Decimal
    direction: MovementDirection
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockMovementLineResponse(StockMovementLineInDB):
    pass


class StockMovementBase(BaseModel):
    movement_type: MovementType
    reference_type: Optional[ReferenceType] = None
    reference_id: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=1000)
    lines: List[StockMovementLineCreate] = Field(..., min_length=1)

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class StockMovementCreate(StockMovementBase):
    model_config = ConfigDict(extra="forbid")


class StockMovementInDB(BaseModel):
    id: str
    business_id: str
    movement_type: MovementType
    reference_type: Optional[ReferenceType] = None
    reference_id: Optional[str] = None
    notes: Optional[str] = None
    performed_by_user_id: str
    status: MovementStatus = MovementStatus.POSTED
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockMovementResponse(StockMovementInDB):
    lines: List[StockMovementLineResponse] = []


class StockMovementListResponse(BaseModel):
    items: List[StockMovementResponse]
    page: int
    page_size: int
    total: int


class OpeningBalanceInput(BaseModel):
    inventory_location_id: str = Field(..., min_length=1)
    product_id: str = Field(..., min_length=1)
    variant_id: Optional[str] = None
    quantity: Decimal = Field(..., gt=0, decimal_places=4)
    unit_cost: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=4)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("unit_cost")
    @classmethod
    def validate_unit_cost(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Unit cost cannot be negative")
        return v

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None

    model_config = ConfigDict(extra="forbid")


class AdjustmentInput(BaseModel):
    inventory_location_id: str = Field(..., min_length=1)
    product_id: str = Field(..., min_length=1)
    variant_id: Optional[str] = None
    quantity: Decimal = Field(..., gt=0, decimal_places=4)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None

    model_config = ConfigDict(extra="forbid")


class TransferInput(BaseModel):
    source_inventory_location_id: str = Field(..., min_length=1)
    destination_inventory_location_id: str = Field(..., min_length=1)
    product_id: str = Field(..., min_length=1)
    variant_id: Optional[str] = None
    quantity: Decimal = Field(..., gt=0, decimal_places=4)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None

    model_config = ConfigDict(extra="forbid")


class TotalStockResponse(BaseModel):
    product_id: str
    product_name: str
    variant_id: Optional[str] = None
    variant_name: Optional[str] = None
    total_quantity: Decimal


# ============================================================
# Inventory Cost State (Feature #38 — MAC Valuation)
# ============================================================

class InventoryCostStateInDB(BaseModel):
    id: str
    business_id: str
    product_id: str
    variant_id: Optional[str] = None
    quantity: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    unit_cost: Decimal = Decimal("0")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryCostMovementType(str, Enum):
    PURCHASE_IN = "PURCHASE_IN"
    PURCHASE_RETURN_OUT = "PURCHASE_RETURN_OUT"
    SALE_OUT = "SALE_OUT"
    SALE_RETURN_IN = "SALE_RETURN_IN"
    OPENING_BALANCE = "OPENING_BALANCE"
    OPNAME_SYNC = "OPNAME_SYNC"
    TRANSFER_OUT = "TRANSFER_OUT"
    TRANSFER_IN = "TRANSFER_IN"


class InventoryCostMovementInDB(BaseModel):
    id: str
    business_id: str
    product_id: str
    variant_id: Optional[str] = None
    movement_type: InventoryCostMovementType
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    quantity_delta: Decimal
    cost_delta: Decimal
    unit_cost_at_time: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ValuationSummaryItem(BaseModel):
    product_id: str
    product_name: Optional[str] = None
    variant_id: Optional[str] = None
    variant_name: Optional[str] = None
    total_quantity: Decimal = Decimal("0")
    unit_cost: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")


class ValuationSummaryResponse(BaseModel):
    items: List[ValuationSummaryItem] = []
    total_inventory_value: Decimal = Decimal("0")


# --- Stock Card Schemas (Feature #42) ---

class StatementDateRange(BaseModel):
    start_date: date
    end_date: date


class StockCardLineResponse(BaseModel):
    transaction_date: datetime
    movement_type: str
    reference_id: str
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    qty_in: Decimal = Decimal("0.00")
    qty_out: Decimal = Decimal("0.00")
    unit_cost: Decimal = Decimal("0.00")
    movement_value: Decimal = Decimal("0.00")
    running_quantity: Decimal = Decimal("0.00")
    running_valuation: Decimal = Decimal("0.00")

    model_config = ConfigDict(from_attributes=True)


class StockCardResponse(BaseModel):
    business_id: str
    location_id: str
    location_name: Optional[str] = None
    product_id: str
    product_name: Optional[str] = None
    variant_id: Optional[str] = None
    variant_name: Optional[str] = None
    unit_code: Optional[str] = None
    date_range: StatementDateRange
    opening_quantity: Decimal = Decimal("0.00")
    opening_unit_cost: Decimal = Decimal("0.00")
    opening_valuation: Decimal = Decimal("0.00")
    lines: List[StockCardLineResponse] = []
    total_qty_in: Decimal = Decimal("0.00")
    total_qty_out: Decimal = Decimal("0.00")
    total_in_value: Decimal = Decimal("0.00")
    total_out_value: Decimal = Decimal("0.00")
    closing_quantity: Decimal = Decimal("0.00")
    closing_valuation: Decimal = Decimal("0.00")
    page: int = 1
    page_size: int = 100
    total_items: int = 0
