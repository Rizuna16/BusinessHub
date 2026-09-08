from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ProductType(str, Enum):
    GOODS = "GOODS"
    SERVICE = "SERVICE"


class ProductStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ProductTaxTreatment(str, Enum):
    STANDARD_NON_LUXURY = "STANDARD_NON_LUXURY"
    NON_TAXABLE = "NON_TAXABLE"


class ProductCreate(BaseModel):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    category_id: Optional[str] = None
    unit_id: str
    product_type: ProductType
    tax_treatment: ProductTaxTreatment = ProductTaxTreatment.STANDARD_NON_LUXURY

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Product name cannot be empty or whitespace-only")
        return v.strip()

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Product code cannot be empty or whitespace-only")
        return v.strip().upper()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return None


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    code: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    category_id: Optional[str] = None
    unit_id: Optional[str] = None
    product_type: Optional[ProductType] = None
    tax_treatment: Optional[ProductTaxTreatment] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Product name cannot be empty or whitespace-only")
            return v.strip()
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Product code cannot be empty or whitespace-only")
            return v.strip().upper()
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() if v.strip() else None
        return v


class ProductResponse(BaseModel):
    id: str
    business_id: str
    category_id: Optional[str] = None
    unit_id: str
    name: str
    code: str
    description: Optional[str] = None
    product_type: ProductType
    tax_treatment: ProductTaxTreatment = ProductTaxTreatment.STANDARD_NON_LUXURY
    status: ProductStatus
    created_at: str
    updated_at: str

    @classmethod
    def from_db(cls, db_obj) -> "ProductResponse":
        return cls(
            id=db_obj.id,
            business_id=db_obj.business_id,
            category_id=db_obj.category_id,
            unit_id=db_obj.unit_id,
            name=db_obj.name,
            code=db_obj.code,
            description=db_obj.description,
            product_type=db_obj.product_type,
            tax_treatment=getattr(db_obj, 'tax_treatment', ProductTaxTreatment.STANDARD_NON_LUXURY),
            status=db_obj.status,
            created_at=db_obj.created_at.isoformat(),
            updated_at=db_obj.updated_at.isoformat(),
        )


class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    page: int
    page_size: int
    total: int
