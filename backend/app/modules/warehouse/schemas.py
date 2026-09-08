from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re


class WarehouseStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"


class InventoryLocationType(str, Enum):
    GENERAL = "GENERAL"
    RECEIVING = "RECEIVING"
    STORAGE = "STORAGE"
    PICKING = "PICKING"
    SHIPPING = "SHIPPING"
    DAMAGED = "DAMAGED"
    QUARANTINE = "QUARANTINE"
    OTHER = "OTHER"


class InventoryLocationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


# --- Warehouse Schemas ---

class WarehouseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    address: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=100)
    branch_id: Optional[str] = Field(None, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Warehouse name cannot be empty or whitespace only.")
        return v.strip()

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("Warehouse code cannot be empty or whitespace only.")
        if not re.match(r"^[A-Z0-9_\-]+$", cleaned):
            raise ValueError("Warehouse code must contain only alphanumeric characters, hyphens, or underscores.")
        return cleaned


class WarehouseCreate(WarehouseBase):
    model_config = ConfigDict(extra="forbid")


class WarehouseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    address: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=100)
    branch_id: Optional[str] = Field(None, max_length=100)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Warehouse name cannot be empty or whitespace only.")
            return v.strip()
        return v


class WarehouseResponse(BaseModel):
    id: str
    business_id: str
    branch_id: Optional[str] = None
    name: str
    code: str
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: WarehouseStatus
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WarehouseInDB(WarehouseResponse):
    pass


# --- Inventory Location Schemas ---

class InventoryLocationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    location_type: InventoryLocationType = InventoryLocationType.GENERAL

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Location name cannot be empty or whitespace only.")
        return v.strip()

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("Location code cannot be empty or whitespace only.")
        if not re.match(r"^[A-Z0-9_\-]+$", cleaned):
            raise ValueError("Location code must contain only alphanumeric characters, hyphens, or underscores.")
        return cleaned


class InventoryLocationCreate(InventoryLocationBase):
    model_config = ConfigDict(extra="forbid")


class InventoryLocationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    location_type: Optional[InventoryLocationType] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Location name cannot be empty or whitespace only.")
            return v.strip()
        return v


class InventoryLocationResponse(BaseModel):
    id: str
    business_id: str
    warehouse_id: str
    name: str
    code: str
    description: Optional[str] = None
    location_type: InventoryLocationType
    status: InventoryLocationStatus
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryLocationInDB(InventoryLocationResponse):
    pass
