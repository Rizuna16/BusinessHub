from enum import Enum
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, ConfigDict

class PriceListStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"

class PriceEntryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"

SUPPORTED_CURRENCIES = {"IDR", "USD", "SGD", "MYR", "EUR", "JPY"}

class PriceListCreate(BaseModel):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    currency: str = Field(default="IDR", max_length=10)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Price list name cannot be empty or whitespace-only")
        return v.strip()

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Price list code cannot be empty or whitespace-only")
        return v.strip().upper()

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        code = v.strip().upper()
        if code not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency '{code}'. Supported currencies: {sorted(list(SUPPORTED_CURRENCIES))}")
        return code

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None

class PriceListUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    currency: Optional[str] = Field(None, max_length=10)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Price list name cannot be empty or whitespace-only")
            return v.strip()
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            code = v.strip().upper()
            if code not in SUPPORTED_CURRENCIES:
                raise ValueError(f"Unsupported currency '{code}'.")
            return code
        return v

class PriceListResponse(BaseModel):
    id: str
    business_id: str
    name: str
    code: str
    description: Optional[str] = None
    currency: str
    status: PriceListStatus
    is_default: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_db(cls, db_obj) -> "PriceListResponse":
        return cls(
            id=db_obj.id,
            business_id=db_obj.business_id,
            name=db_obj.name,
            code=db_obj.code,
            description=db_obj.description,
            currency=db_obj.currency,
            status=db_obj.status,
            is_default=db_obj.is_default,
            created_at=db_obj.created_at.isoformat(),
            updated_at=db_obj.updated_at.isoformat(),
        )

class PriceListListResponse(BaseModel):
    items: List[PriceListResponse]
    total: int

class PriceEntryCreate(BaseModel):
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    amount: Decimal = Field(..., ge=0)
    effective_from: datetime
    effective_to: Optional[datetime] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v < Decimal("0"):
            raise ValueError("Amount must be greater than or equal to 0")
        return v

    def model_post_init(self, __context) -> None:
        p_provided = self.product_id is not None and self.product_id != ""
        v_provided = self.variant_id is not None and self.variant_id != ""
        if (p_provided and v_provided) or (not p_provided and not v_provided):
            raise ValueError("Price entry must point to exactly one target: product_id OR variant_id")

        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be greater than or equal to effective_from")

class PriceEntryUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, ge=0)
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None

class PriceEntryResponse(BaseModel):
    id: str
    business_id: str
    price_list_id: str
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    amount: str  # String representation of Decimal
    currency: str
    effective_from: str
    effective_to: Optional[str] = None
    status: PriceEntryStatus
    created_at: str
    updated_at: str

    @classmethod
    def from_db(cls, db_obj) -> "PriceEntryResponse":
        return cls(
            id=db_obj.id,
            business_id=db_obj.business_id,
            price_list_id=db_obj.price_list_id,
            product_id=db_obj.product_id,
            variant_id=db_obj.variant_id,
            amount=str(db_obj.amount),
            currency=db_obj.currency,
            effective_from=db_obj.effective_from.isoformat(),
            effective_to=db_obj.effective_to.isoformat() if db_obj.effective_to else None,
            status=db_obj.status,
            created_at=db_obj.created_at.isoformat(),
            updated_at=db_obj.updated_at.isoformat(),
        )

class PriceEntryListResponse(BaseModel):
    items: List[PriceEntryResponse]
    total: int


class DiscountRuleType(str, Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"


class DiscountRuleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class DiscountRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    type: DiscountRuleType
    value: Decimal
    currency: str = Field(default="IDR", max_length=10)
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    starts_at: datetime
    ends_at: Optional[datetime] = None
    priority: int = Field(default=100, ge=0, le=9999)

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: Decimal, info) -> Decimal:
        rule_type = info.data.get("type")
        if rule_type == DiscountRuleType.PERCENTAGE:
            if v < Decimal("0") or v > Decimal("100"):
                raise ValueError("Percentage must be between 0.00 and 100.00")
        elif rule_type == DiscountRuleType.FIXED:
            if v < Decimal("0"):
                raise ValueError("Fixed discount must be >= 0")
        return v

    def model_post_init(self, __context) -> None:
        if self.product_id is None and self.variant_id is None:
            raise ValueError("Either product_id or variant_id must be provided.")
        if self.product_id is not None and self.variant_id is not None:
            raise ValueError("Only one of product_id or variant_id may be provided, not both.")
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at.")

    model_config = ConfigDict(extra="forbid")


class DiscountRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    value: Optional[Decimal] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    priority: Optional[int] = Field(None, ge=0, le=9999)

    model_config = ConfigDict(extra="forbid")


class DiscountRuleInDB(BaseModel):
    id: str
    business_id: str
    name: str
    description: Optional[str] = None
    type: str
    value: Decimal
    currency: str = "IDR"
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    starts_at: datetime
    ends_at: Optional[datetime] = None
    priority: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscountRuleResponse(BaseModel):
    id: str
    business_id: str
    name: str
    description: Optional[str] = None
    type: str
    value: Decimal
    currency: str = "IDR"
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    starts_at: datetime
    ends_at: Optional[datetime] = None
    priority: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscountRuleListResponse(BaseModel):
    items: List[DiscountRuleResponse]
    total: int
