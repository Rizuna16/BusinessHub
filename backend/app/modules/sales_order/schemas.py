from enum import Enum
from datetime import datetime
from typing import Optional, List, Any
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class QuotationStatus(str, Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    CONVERTED = "CONVERTED"


class SalesOrderStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"


class ReservationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FULFILLED = "FULFILLED"
    RELEASED = "RELEASED"


class QuotationLineCreate(BaseModel):
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

    def model_post_init(self, __context) -> None:
        p_provided = self.product_id is not None and self.product_id != ""
        v_provided = self.variant_id is not None and self.variant_id != ""
        if (p_provided and v_provided) or (not p_provided and not v_provided):
            raise ValueError("Quotation line must target exactly one product OR variant.")

        line_subtotal = self.quantity * self.unit_price
        line_total = line_subtotal - self.discount_amount + self.tax_amount
        if line_total < Decimal("0"):
            raise ValueError("Discount causes line total to be negative.")


class QuotationLineUpdate(BaseModel):
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


class QuotationLineInDB(BaseModel):
    id: str
    quotation_id: str
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


class QuotationLineResponse(QuotationLineInDB):
    suggested_selling_price: Optional[str] = None


class QuotationCreate(BaseModel):
    customer_id: Optional[str] = None
    branch_id: str = Field(..., min_length=1)
    warehouse_id: str = Field(..., min_length=1)
    quotation_date: datetime
    validity_date: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None

    @field_validator("validity_date")
    @classmethod
    def validate_validity_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        return v


class QuotationUpdate(BaseModel):
    customer_id: Optional[str] = None
    branch_id: Optional[str] = Field(None, min_length=1)
    warehouse_id: Optional[str] = Field(None, min_length=1)
    quotation_date: Optional[datetime] = None
    validity_date: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None

    @field_validator("validity_date")
    @classmethod
    def validate_validity_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        return v


class QuotationAction(BaseModel):
    reason: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")


class QuotationConvert(BaseModel):
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")


class QuotationInDB(BaseModel):
    id: str
    business_id: str
    customer_id: Optional[str] = None
    branch_id: str
    warehouse_id: str
    quotation_number: str
    quotation_date: datetime
    validity_date: Optional[datetime] = None
    notes: Optional[str] = None
    status: QuotationStatus
    is_deleted: bool = False
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    grand_total: Decimal
    created_by_user_id: str
    sent_by_user_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    accepted_by_user_id: Optional[str] = None
    accepted_at: Optional[datetime] = None
    rejected_by_user_id: Optional[str] = None
    rejected_at: Optional[datetime] = None
    expired_by_user_id: Optional[str] = None
    expired_at: Optional[datetime] = None
    cancelled_by_user_id: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    converted_at: Optional[datetime] = None
    converted_sales_order_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuotationResponse(QuotationInDB):
    lines: List[QuotationLineResponse] = []


class QuotationListResponse(BaseModel):
    items: List[QuotationResponse]
    page: int
    page_size: int
    total: int


class SalesOrderLineCreate(BaseModel):
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

    def model_post_init(self, __context) -> None:
        p_provided = self.product_id is not None and self.product_id != ""
        v_provided = self.variant_id is not None and self.variant_id != ""
        if (p_provided and v_provided) or (not p_provided and not v_provided):
            raise ValueError("Sales order line must target exactly one product OR variant.")

        line_subtotal = self.quantity * self.unit_price
        line_total = line_subtotal - self.discount_amount + self.tax_amount
        if line_total < Decimal("0"):
            raise ValueError("Discount causes line total to be negative.")


class SalesOrderLineUpdate(BaseModel):
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


class SalesOrderLineInDB(BaseModel):
    id: str
    sales_order_id: str
    product_id: str
    variant_id: Optional[str] = None
    description: Optional[str] = None
    quantity_ordered: Decimal
    quantity_fulfilled: Decimal = Decimal("0")
    quantity_remaining: Decimal
    unit_price: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    line_subtotal: Decimal
    line_total: Decimal
    tax_snapshot: Optional[Any] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SalesOrderLineResponse(SalesOrderLineInDB):
    suggested_selling_price: Optional[str] = None


class SalesOrderCreate(BaseModel):
    customer_id: Optional[str] = None
    branch_id: str = Field(..., min_length=1)
    warehouse_id: str = Field(..., min_length=1)
    order_date: datetime
    notes: Optional[str] = Field(None, max_length=1000)
    quotation_id: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class SalesOrderUpdate(BaseModel):
    customer_id: Optional[str] = None
    branch_id: Optional[str] = Field(None, min_length=1)
    warehouse_id: Optional[str] = Field(None, min_length=1)
    order_date: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class SalesOrderAction(BaseModel):
    reason: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")


class SalesOrderFulfill(BaseModel):
    line_fulfillments: List["SalesOrderLineFulfill"]
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")


class SalesOrderLineFulfill(BaseModel):
    line_id: str = Field(..., min_length=1)
    quantity: Decimal = Field(..., gt=0)

    model_config = ConfigDict(extra="forbid")


SalesOrderFulfill.model_rebuild()


class SalesOrderInDB(BaseModel):
    id: str
    business_id: str
    customer_id: Optional[str] = None
    branch_id: str
    warehouse_id: str
    sales_order_number: str
    order_date: datetime
    notes: Optional[str] = None
    status: SalesOrderStatus
    is_deleted: bool = False
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    grand_total: Decimal
    created_by_user_id: str
    confirmed_by_user_id: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    cancelled_by_user_id: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    fulfilled_by_user_id: Optional[str] = None
    fulfilled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SalesOrderResponse(SalesOrderInDB):
    lines: List[SalesOrderLineResponse] = []


class SalesOrderListResponse(BaseModel):
    items: List[SalesOrderResponse]
    page: int
    page_size: int
    total: int


class SalesOrderReservationInDB(BaseModel):
    id: str
    business_id: str
    sales_order_id: str
    sales_order_line_id: str
    warehouse_id: str
    product_id: str
    variant_id: Optional[str] = None
    quantity: Decimal
    status: ReservationStatus = ReservationStatus.ACTIVE
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SalesOrderReservationResponse(SalesOrderReservationInDB):
    pass


class AvailableStockResponse(BaseModel):
    product_id: str
    variant_id: Optional[str] = None
    warehouse_id: str
    physical_on_hand: Decimal
    active_reserved_quantity: Decimal
    available_to_sell: Decimal


class AvailabilityCheckRequest(BaseModel):
    product_id: str = Field(..., min_length=1)
    variant_id: Optional[str] = None
    warehouse_id: str = Field(..., min_length=1)
    requested_quantity: Decimal = Field(..., gt=0)

    model_config = ConfigDict(extra="forbid")


class AvailabilityCheckResponse(BaseModel):
    available: bool
    physical_on_hand: Decimal
    active_reserved_quantity: Decimal
    available_to_sell: Decimal
    requested_quantity: Decimal


class InventoryReservationConflict(BaseModel):
    warehouse_id: str
    product_id: str
    variant_id: Optional[str] = None
    physical_on_hand: Decimal
    active_reserved_quantity: Decimal
    shortfall_quantity: Decimal
    conflicting_order_ids: List[str]


class SalesOrderFulfillResponse(BaseModel):
    sales_order: SalesOrderResponse
    fulfilled_lines: List[SalesOrderLineResponse]