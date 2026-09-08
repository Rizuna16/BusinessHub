from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re

class BarcodeType(str, Enum):
    EAN13 = "EAN13"
    EAN8 = "EAN8"
    UPC_A = "UPC_A"
    CODE128 = "CODE128"
    OTHER = "OTHER"

class BarcodeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"

class BarcodeCreate(BaseModel):
    code: str = Field(..., max_length=100)
    barcode_type: BarcodeType = BarcodeType.CODE128
    product_id: Optional[str] = None
    variant_id: Optional[str] = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Barcode code cannot be empty or whitespace-only")
        # Preserve leading zeros, normalize
        return v.strip()

    @field_validator("barcode_type")
    @classmethod
    def validate_barcode_type_and_code(cls, v, info):
        # We can validate length if data is accessible or in model validator
        return v

    def model_post_init(self, __context) -> None:
        # Target exclusivity validation: exactly one of product_id or variant_id must be provided
        p_provided = self.product_id is not None and self.product_id != ""
        v_provided = self.variant_id is not None and self.variant_id != ""
        if (p_provided and v_provided) or (not p_provided and not v_provided):
            raise ValueError("Barcode must point to exactly one target: either product_id OR variant_id")

        code = self.code
        b_type = self.barcode_type

        if b_type == BarcodeType.EAN13:
            if not re.match(r"^\d{13}$", code):
                raise ValueError("EAN13 barcode must be exactly 13 numeric digits")
        elif b_type == BarcodeType.EAN8:
            if not re.match(r"^\d{8}$", code):
                raise ValueError("EAN8 barcode must be exactly 8 numeric digits")
        elif b_type == BarcodeType.UPC_A:
            if not re.match(r"^\d{12}$", code):
                raise ValueError("UPC_A barcode must be exactly 12 numeric digits")
        else:
            if len(code) > 100:
                raise ValueError("Barcode code too long (max 100 characters)")

class BarcodeUpdate(BaseModel):
    code: Optional[str] = Field(None, max_length=100)
    barcode_type: Optional[BarcodeType] = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Barcode code cannot be empty or whitespace-only")
            return v.strip()
        return v

class BarcodeResponse(BaseModel):
    id: str
    business_id: str
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    code: str
    barcode_type: BarcodeType
    status: BarcodeStatus
    created_at: str
    updated_at: str

    @classmethod
    def from_db(cls, db_obj) -> "BarcodeResponse":
        return cls(
            id=db_obj.id,
            business_id=db_obj.business_id,
            product_id=db_obj.product_id,
            variant_id=db_obj.variant_id,
            code=db_obj.code,
            barcode_type=db_obj.barcode_type,
            status=db_obj.status,
            created_at=db_obj.created_at.isoformat(),
            updated_at=db_obj.updated_at.isoformat(),
        )

class BarcodeListResponse(BaseModel):
    items: List[BarcodeResponse]
    total: int
