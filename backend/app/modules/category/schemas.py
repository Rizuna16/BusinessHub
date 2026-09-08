from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re


class CategoryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[str] = None
    sort_order: int = Field(default=0, ge=0)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Category name cannot be empty or whitespace only.")
        return v.strip()

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("Category code cannot be empty.")
        if not re.match(r"^[A-Z0-9_]+$", v):
            raise ValueError("Category code must be uppercase letters, numbers, and underscores only.")
        return v


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[str] = Field(None)
    sort_order: Optional[int] = Field(None, ge=0)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Category name cannot be empty or whitespace only.")
            return v.strip()
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().upper()
            if not v:
                raise ValueError("Category code cannot be empty.")
            if not re.match(r"^[A-Z0-9_]+$", v):
                raise ValueError("Category code must be uppercase letters, numbers, and underscores only.")
            return v
        return v


class CategoryResponse(BaseModel):
    id: str
    business_id: str
    name: str
    code: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    status: CategoryStatus
    sort_order: int
    created_at: str
    updated_at: str
    has_children: bool = False

    model_config = ConfigDict(from_attributes=True)
