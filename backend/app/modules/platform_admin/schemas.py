from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from app.modules.authentication.schemas import PlatformRole
from app.modules.business.schemas import BusinessStatus, BusinessType


class PlatformAuditLogInDB(BaseModel):
    id: str = Field(..., min_length=1)
    actor_account_id: str
    actor_email: str
    action: str
    target_type: str
    target_id: str
    target_business_id: Optional[str] = None
    reason: Optional[str] = None
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    result: str = "SUCCESS"
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class PlatformAuditLogResponse(BaseModel):
    id: str
    actor_account_id: str
    actor_email: str
    action: str
    target_type: str
    target_id: str
    target_business_id: Optional[str] = None
    reason: Optional[str] = None
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    result: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class PlatformAuditLogCreate(BaseModel):
    actor_account_id: str
    actor_email: str
    action: str
    target_type: str
    target_id: str
    target_business_id: Optional[str] = None
    reason: Optional[str] = None
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    result: str = "SUCCESS"
    metadata: Optional[Dict[str, Any]] = None


class BusinessActionInput(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class PlatformDashboardResponse(BaseModel):
    total_businesses: int
    active_businesses: int
    suspended_businesses: int
    archived_businesses: int
    total_accounts: int
    active_subscriptions: int
    expired_subscriptions: int
    mrr_idr: Decimal = Decimal("0.00")


class PlatformUserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    is_active: bool
    platform_role: Optional[PlatformRole] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlatformBusinessDetailResponse(BaseModel):
    id: str
    owner_user_id: str
    owner_email: Optional[str] = None
    owner_name: Optional[str] = None
    name: str
    slug: str
    description: Optional[str] = None
    business_type: BusinessType
    status: BusinessStatus
    timezone: str
    locale: str
    membership_count: int
    branch_count: int
    created_at: datetime
    updated_at: datetime
    subscription_status: Optional[str] = None
    subscription_plan_name: Optional[str] = None
    subscription_current_period_end: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
