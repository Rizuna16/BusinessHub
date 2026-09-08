from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re


class BranchStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"


class BranchBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)
    description: Optional[str] = Field(None, max_length=500)
    address: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=100)
    timezone: str = Field("UTC", min_length=1, max_length=50)
    locale: str = Field("en-US", min_length=1, max_length=20)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Branch name cannot be empty or whitespace only.")
        return v.strip()

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("Branch code cannot be empty or whitespace only.")
        if not re.match(r"^[A-Z0-9_\-]+$", cleaned):
            raise ValueError("Branch code must contain only alphanumeric characters, hyphens, or underscores.")
        return cleaned

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        tz = v.strip()
        if tz not in ["UTC", "GMT"] and "/" not in tz:
            raise ValueError("Timezone must be a valid IANA timezone identifier (e.g. Asia/Jakarta, UTC).")
        return tz

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, v: str) -> str:
        loc = v.strip()
        if not re.match(r"^[a-z]{2}-[A-Z]{2}$", loc) and not re.match(r"^[a-z]{2}$", loc):
            raise ValueError("Locale must be in valid format (e.g. id-ID, en-US).")
        return loc


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    description: Optional[str] = Field(None, max_length=500)
    address: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, min_length=1, max_length=50)
    locale: Optional[str] = Field(None, min_length=1, max_length=20)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Branch name cannot be empty or whitespace only.")
            return v.strip()
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip().upper()
            if not cleaned:
                raise ValueError("Branch code cannot be empty or whitespace only.")
            if not re.match(r"^[A-Z0-9_\-]+$", cleaned):
                raise ValueError("Branch code must contain only alphanumeric characters, hyphens, or underscores.")
            return cleaned
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            tz = v.strip()
            if tz not in ["UTC", "GMT"] and "/" not in tz:
                raise ValueError("Timezone must be a valid IANA timezone identifier (e.g. Asia/Jakarta, UTC).")
            return tz
        return v

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            loc = v.strip()
            if not re.match(r"^[a-z]{2}-[A-Z]{2}$", loc) and not re.match(r"^[a-z]{2}$", loc):
                raise ValueError("Locale must be in valid format (e.g. id-ID, en-US).")
            return loc
        return v


class BranchResponse(BaseModel):
    id: str
    business_id: str
    name: str
    code: str
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    timezone: str
    locale: str
    status: BranchStatus
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BranchInDB(BranchResponse):
    pass
