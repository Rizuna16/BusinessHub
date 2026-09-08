from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class SupplierCatalogStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


SUPPORTED_CURRENCIES = {"IDR", "USD", "SGD", "MYR", "EUR", "JPY"}


class SupplierCatalogItemBase(BaseModel):
    supplier_id: str = Field(..., min_length=1)
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    supplier_code: Optional[str] = Field(None, max_length=100)
    supplier_product_name: Optional[str] = Field(None, max_length=255)
    purchase_price: Decimal = Field(..., ge=0)
    currency: str = Field(default="IDR", max_length=10)
    minimum_order_quantity: Optional[Decimal] = None
    lead_time_days: Optional[int] = None
    is_preferred: bool = False
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("supplier_id")
    @classmethod
    def validate_supplier_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("supplier_id cannot be empty")
        return v.strip()

    @field_validator("product_id")
    @classmethod
    def validate_product_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v if v else None
        return None

    @field_validator("variant_id")
    @classmethod
    def validate_variant_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v if v else None
        return None

    @field_validator("supplier_code")
    @classmethod
    def validate_supplier_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v if v else None
        return None

    @field_validator("supplier_product_name")
    @classmethod
    def validate_supplier_product_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v if v else None
        return None

    @field_validator("purchase_price")
    @classmethod
    def validate_purchase_price(cls, v: Decimal) -> Decimal:
        if v < Decimal("0"):
            raise ValueError("purchase_price must be greater than or equal to 0")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        code = v.strip().upper()
        if code not in SUPPORTED_CURRENCIES:
            raise ValueError(
                f"Unsupported currency '{code}'. Supported currencies: {sorted(list(SUPPORTED_CURRENCIES))}"
            )
        return code

    @field_validator("minimum_order_quantity")
    @classmethod
    def validate_moq(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            if v <= Decimal("0"):
                raise ValueError("minimum_order_quantity must be greater than 0")
            return v
        return None

    @field_validator("lead_time_days")
    @classmethod
    def validate_lead_time(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            if v < 0:
                raise ValueError("lead_time_days must be greater than or equal to 0")
            return v
        return None

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v if v else None
        return None

    @model_validator(mode="after")
    def validate_xor_target(self) -> "SupplierCatalogItemBase":
        p_provided = self.product_id is not None and len(self.product_id) > 0
        v_provided = self.variant_id is not None and len(self.variant_id) > 0
        if (p_provided and v_provided) or (not p_provided and not v_provided):
            raise ValueError(
                "Supplier catalog item must point to exactly one target: product_id XOR variant_id"
            )
        return self


class SupplierCatalogItemCreate(SupplierCatalogItemBase):
    pass


class SupplierCatalogItemUpdate(BaseModel):
    supplier_code: Optional[str] = Field(None, max_length=100)
    supplier_product_name: Optional[str] = Field(None, max_length=255)
    purchase_price: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    minimum_order_quantity: Optional[Decimal] = None
    lead_time_days: Optional[int] = None
    is_preferred: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("supplier_code")
    @classmethod
    def validate_supplier_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v if v else None
        return None

    @field_validator("supplier_product_name")
    @classmethod
    def validate_supplier_product_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v if v else None
        return None

    @field_validator("purchase_price")
    @classmethod
    def validate_purchase_price(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            if v < Decimal("0"):
                raise ValueError("purchase_price must be greater than or equal to 0")
            return v
        return None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            code = v.strip().upper()
            if code not in SUPPORTED_CURRENCIES:
                raise ValueError(
                    f"Unsupported currency '{code}'. Supported currencies: {sorted(list(SUPPORTED_CURRENCIES))}"
                )
            return code
        return None

    @field_validator("minimum_order_quantity")
    @classmethod
    def validate_moq(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            if v <= Decimal("0"):
                raise ValueError("minimum_order_quantity must be greater than 0")
            return v
        return None

    @field_validator("lead_time_days")
    @classmethod
    def validate_lead_time(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            if v < 0:
                raise ValueError("lead_time_days must be greater than or equal to 0")
            return v
        return None

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v if v else None
        return None


class SupplierCatalogItemResponse(BaseModel):
    id: str
    business_id: str
    supplier_id: str
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    supplier_code: Optional[str] = None
    supplier_product_name: Optional[str] = None
    purchase_price: str  # String representation of Decimal for exact precision
    currency: str
    minimum_order_quantity: Optional[str] = None
    lead_time_days: Optional[int] = None
    is_preferred: bool
    status: SupplierCatalogStatus
    notes: Optional[str] = None
    created_at: str
    updated_at: str

    # Optional enriched display fields
    supplier_name: Optional[str] = None
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    variant_name: Optional[str] = None
    variant_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SupplierCatalogItemListResponse(BaseModel):
    items: List[SupplierCatalogItemResponse]
    page: int
    page_size: int
    total: int

    model_config = ConfigDict(from_attributes=True)
