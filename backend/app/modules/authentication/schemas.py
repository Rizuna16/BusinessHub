from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class PlatformRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    password_confirmation: str = Field(..., min_length=8)


class UserResponse(UserBase):
    id: str
    is_active: bool
    platform_role: Optional[PlatformRole] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserInDB(UserResponse):
    password_hash: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AdminResetPasswordRequest(BaseModel):
    target_user_id: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)
    password_confirmation: str = Field(..., min_length=8)


class TokenPayload(BaseModel):
    sub: str
    platform_role: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    type: str = "access"
