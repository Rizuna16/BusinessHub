from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re


class BusinessType(str, Enum):
    HOTEL = "hotel"
    RETAIL = "retail"
    UMKM = "umkm"
    RESTAURANT = "restaurant"
    SERVICE = "service"
    PRODUCTION = "production"
    GARMENT = "garment"
    DISTRIBUTOR = "distributor"
    WORKSHOP = "workshop"
    SALON = "salon"


class BusinessStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class BusinessBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    business_type: BusinessType
    timezone: str = Field(..., min_length=1, max_length=50)
    locale: str = Field(..., min_length=1, max_length=20)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Business name cannot be empty or whitespace only.")
        return v.strip()

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


class BusinessCreate(BusinessBase):
    pass


class BusinessUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    timezone: Optional[str] = Field(None, min_length=1, max_length=50)
    locale: Optional[str] = Field(None, min_length=1, max_length=20)

    # business_type is immutable after creation per requirement 12
    # owner_user_id, slug, is immutable

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Business name cannot be empty or whitespace only.")
            return v.strip()
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


class BusinessResponse(BaseModel):
    id: str
    owner_user_id: str
    name: str
    slug: str
    description: Optional[str] = None
    business_type: BusinessType
    status: BusinessStatus
    timezone: str
    locale: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BusinessInDB(BusinessResponse):
    pass
