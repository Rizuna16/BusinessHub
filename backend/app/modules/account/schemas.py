from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl, ConfigDict, field_validator
import re


class AccountBase(BaseModel):
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    avatar_url: Optional[str] = Field(None, max_length=500)
    timezone: Optional[str] = Field("UTC", max_length=50)
    locale: Optional[str] = Field("en-US", max_length=20)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Display name cannot be empty or whitespace only.")
            return v.strip()
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() != "":
            cleaned = v.strip()
            # Reasonable phone validation: digits, spaces, plus, hyphens, parentheses, 7-20 chars
            if not re.match(r"^[\+]?[\d\s\-\(\)]{7,20}$", cleaned):
                raise ValueError("Invalid phone number format.")
            return cleaned
        return None if v == "" else v

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() != "":
            url_str = v.strip()
            if not (url_str.startswith("http://") or url_str.startswith("https://")):
                raise ValueError("Avatar URL must be a valid HTTP or HTTPS URL.")
            return url_str
        return None if v == "" else v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            tz = v.strip()
            # Reasonable check for IANA timezone identifier (contains / or is UTC)
            if tz not in ["UTC", "GMT"] and "/" not in tz:
                raise ValueError("Timezone must be a valid IANA timezone identifier (e.g. Asia/Jakarta, UTC).")
            return tz
        return "UTC"

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            loc = v.strip()
            # Reasonable check for locale format like en-US, id-ID
            if not re.match(r"^[a-z]{2}-[A-Z]{2}$", loc) and not re.match(r"^[a-z]{2}$", loc):
                raise ValueError("Locale must be in valid format (e.g. id-ID, en-US).")
            return loc
        return "en-US"


class AccountUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    avatar_url: Optional[str] = Field(None, max_length=500)
    timezone: Optional[str] = Field(None, max_length=50)
    locale: Optional[str] = Field(None, max_length=20)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Display name cannot be empty or whitespace only.")
            return v.strip()
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() != "":
            cleaned = v.strip()
            if not re.match(r"^[\+]?[\d\s\-\(\)]{7,20}$", cleaned):
                raise ValueError("Invalid phone number format.")
            return cleaned
        return None if v == "" else v

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() != "":
            url_str = v.strip()
            if not (url_str.startswith("http://") or url_str.startswith("https://")):
                raise ValueError("Avatar URL must be a valid HTTP or HTTPS URL.")
            return url_str
        return None if v == "" else v

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


class AccountResponse(BaseModel):
    id: str
    user_id: str
    display_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: str = "UTC"
    locale: str = "en-US"
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountInDB(AccountResponse):
    pass
