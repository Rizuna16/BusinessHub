from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ProductImageStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ProductImageInDB(BaseModel):
    id: str
    business_id: str
    product_id: str
    variant_id: Optional[str] = None
    storage_key: str
    original_filename: str
    mime_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    sort_order: int
    is_primary: bool
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductImageResponse(BaseModel):
    id: str
    business_id: str
    product_id: str
    variant_id: Optional[str] = None
    storage_key: str
    original_filename: str
    mime_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    sort_order: int
    is_primary: bool
    status: str
    created_at: str
    updated_at: str


class ProductImageListResponse(BaseModel):
    items: List[ProductImageResponse]
    total: int


class ProductImageUpdate(BaseModel):
    sort_order: Optional[int] = None
    is_primary: Optional[bool] = None
