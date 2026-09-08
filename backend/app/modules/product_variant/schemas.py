from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
import json


class ProductVariantStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ProductVariantCreate(BaseModel):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=100)
    attributes: Optional[Dict[str, Any]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Variant name cannot be empty or whitespace-only")
        return v.strip()

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Variant code cannot be empty or whitespace-only")
        return v.strip().upper()

    @field_validator("attributes")
    @classmethod
    def validate_attributes(cls, v):
        if v is not None:
            if not isinstance(v, dict):
                raise ValueError("Attributes must be a JSON object/dictionary")
            if len(json.dumps(v)) > 2000:
                raise ValueError("Attributes payload too large (max 2000 characters)")
            for key, val in v.items():
                if not isinstance(key, str):
                    raise ValueError("Attribute keys must be strings")
                if val is not None and not isinstance(val, (str, int, float, bool)):
                    raise ValueError("Attribute values must be JSON-safe primitives")
        return v


class ProductVariantUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    code: Optional[str] = Field(None, max_length=100)
    attributes: Optional[Dict[str, Any]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError("Variant name cannot be empty or whitespace-only")
            return v.strip()
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError("Variant code cannot be empty or whitespace-only")
            return v.strip().upper()
        return v

    @field_validator("attributes")
    @classmethod
    def validate_attributes(cls, v):
        if v is not None:
            if not isinstance(v, dict):
                raise ValueError("Attributes must be a JSON object/dictionary")
            if len(json.dumps(v)) > 2000:
                raise ValueError("Attributes payload too large (max 2000 characters)")
            for key, val in v.items():
                if not isinstance(key, str):
                    raise ValueError("Attribute keys must be strings")
                if val is not None and not isinstance(val, (str, int, float, bool)):
                    raise ValueError("Attribute values must be JSON-safe primitives")
        return v


class ProductVariantResponse(BaseModel):
    id: str
    business_id: str
    product_id: str
    name: str
    code: str
    attributes: Optional[Dict[str, Any]] = None
    status: ProductVariantStatus
    created_at: str
    updated_at: str

    @classmethod
    def from_db(cls, db_obj) -> "ProductVariantResponse":
        return cls(
            id=db_obj.id,
            business_id=db_obj.business_id,
            product_id=db_obj.product_id,
            name=db_obj.name,
            code=db_obj.code,
            attributes=db_obj.attributes,
            status=db_obj.status,
            created_at=db_obj.created_at.isoformat(),
            updated_at=db_obj.updated_at.isoformat(),
        )


class ProductVariantListResponse(BaseModel):
    items: List[ProductVariantResponse]
    total: int
