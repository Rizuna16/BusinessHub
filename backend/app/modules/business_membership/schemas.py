from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class BusinessMembershipRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class BusinessMembershipStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REMOVED = "REMOVED"


class BusinessMembershipBase(BaseModel):
    role: BusinessMembershipRole
    status: BusinessMembershipStatus = BusinessMembershipStatus.ACTIVE


class AddBusinessMemberInput(BaseModel):
    user_id: str = Field(..., min_length=1)
    role: BusinessMembershipRole

    model_config = ConfigDict(extra="forbid")


class UpdateBusinessMemberInput(BaseModel):
    role: Optional[BusinessMembershipRole] = None
    status: Optional[BusinessMembershipStatus] = None

    model_config = ConfigDict(extra="forbid")


class BusinessMembershipResponse(BaseModel):
    id: str
    business_id: str
    user_id: str
    role: BusinessMembershipRole
    status: BusinessMembershipStatus
    created_at: datetime
    updated_at: datetime
    # Profile details from User/Account if available
    email: Optional[str] = None
    display_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BusinessMembershipInDB(BusinessMembershipResponse):
    pass
