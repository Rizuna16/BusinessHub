from enum import Enum
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator

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
