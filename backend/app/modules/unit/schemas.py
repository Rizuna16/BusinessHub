from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re


class UnitType(str, Enum):
    COUNT = "COUNT"
    WEIGHT = "WEIGHT"
    VOLUME = "VOLUME"
    LENGTH = "LENGTH"
    TIME = "TIME"
    OTHER = "OTHER"


class UnitStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class UnitBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    symbol: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = Field(None, max_length=500)
    unit_type: UnitType = UnitType.OTHER
    precision: int = Field(default=0, ge=0, le=6)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Unit name cannot be empty or whitespace only.")
        return v.strip()

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("Unit code cannot be empty.")
        if not re.match(r"^[A-Z0-9_]+$", v):
            raise ValueError("Unit code must be uppercase letters, numbers, and underscores only.")
        return v


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    symbol: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = Field(None, max_length=500)
    unit_type: Optional[UnitType] = None
    precision: Optional[int] = Field(None, ge=0, le=6)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Unit name cannot be empty or whitespace only.")
            return v.strip()
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().upper()
            if not v:
                raise ValueError("Unit code cannot be empty.")
            if not re.match(r"^[A-Z0-9_]+$", v):
                raise ValueError("Unit code must be uppercase letters, numbers, and underscores only.")
            return v
        return v


class UnitResponse(BaseModel):
    id: str
    business_id: str
    name: str
    code: str
    symbol: Optional[str] = None
    description: Optional[str] = None
    unit_type: UnitType
    precision: int
    status: UnitStatus
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)
