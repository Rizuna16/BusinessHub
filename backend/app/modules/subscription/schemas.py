from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class SubscriptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    SUSPENDED = "SUSPENDED"


class BillingInterval(str, Enum):
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class BillingPeriodStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PAID = "PAID"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class PaymentAttemptStatus(str, Enum):
    CREATED = "CREATED"
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class SubscriptionPlan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = ""
    price: Decimal
    currency: str = "IDR"
    billing_interval: BillingInterval = BillingInterval.MONTHLY
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class PlanCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    price: Decimal = Field(..., gt=0)
    currency: str = "IDR"
    billing_interval: BillingInterval = BillingInterval.MONTHLY


class PlanUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    is_active: Optional[bool] = None


class BillingPeriod(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., min_length=1)
    subscription_id: str = Field(..., min_length=1)
    business_id: str = Field(..., min_length=1)
    plan_id: str = Field(..., min_length=1)
    plan_name_snapshot: str = Field(..., min_length=1)
    period_start: datetime
    period_end: datetime
    price_snapshot: Decimal
    currency_snapshot: str
    billing_interval_snapshot: BillingInterval
    payment_status: BillingPeriodStatus = BillingPeriodStatus.PENDING
    payment_attempt_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PaymentAttempt(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., min_length=1)
    billing_period_id: str = Field(..., min_length=1)
    subscription_id: str = Field(..., min_length=1)
    business_id: str = Field(..., min_length=1)
    amount: Decimal
    currency: str
    provider: str = "manual_bank_transfer"
    payment_reference: Optional[str] = None
    idempotency_key: str = Field(..., min_length=1)
    provider_order_id: str = Field(..., min_length=1)
    provider_transaction_id: Optional[str] = None
    status: PaymentAttemptStatus = PaymentAttemptStatus.CREATED
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    paid_at: Optional[datetime] = None
    verification_note: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None


class VerifyPaymentInput(BaseModel):
    payment_reference: str = Field(..., min_length=3, max_length=200)
    verification_note: str = Field("", max_length=500)


class SubscriptionCreate(BaseModel):
    business_id: str
    plan_id: str = "plan_business_standard"
    plan_name: str = "Business Plan"
    price: Decimal = Decimal("50000.00")
    currency: str = "IDR"
    billing_interval: BillingInterval = BillingInterval.MONTHLY


class SubscriptionInDB(BaseModel):
    id: str = Field(..., min_length=1)
    business_id: str = Field(..., min_length=1)
    plan_id: str = Field(..., min_length=1)
    plan_name: str = Field(..., min_length=1)
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    price: Decimal
    currency: str
    billing_interval: BillingInterval
    started_at: datetime
    current_period_start: datetime
    current_period_end: datetime
    cancelled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionResponse(BaseModel):
    id: str
    business_id: str
    plan_id: str
    plan_name: str
    status: SubscriptionStatus
    price: Decimal
    currency: str
    billing_interval: BillingInterval
    started_at: datetime
    current_period_start: datetime
    current_period_end: datetime
    cancelled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionOverrideInput(BaseModel):
    action: str = Field(..., pattern=r"^(EXTEND|SET_STATUS)$")
    extend_days: Optional[int] = Field(None, gt=0)
    status: Optional[SubscriptionStatus] = None
    reason: str = Field(..., min_length=3, max_length=500)


class BillingPeriodResponse(BaseModel):
    id: str
    subscription_id: str
    business_id: str
    plan_id: str
    plan_name_snapshot: str
    period_start: datetime
    period_end: datetime
    price_snapshot: Decimal
    currency_snapshot: str
    billing_interval_snapshot: BillingInterval
    payment_status: BillingPeriodStatus
    payment_attempt_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentAttemptResponse(BaseModel):
    id: str
    billing_period_id: str
    subscription_id: str
    business_id: str
    amount: Decimal
    currency: str
    provider: str
    provider_order_id: str
    provider_transaction_id: Optional[str] = None
    payment_reference: Optional[str] = None
    status: PaymentAttemptStatus
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None
    verification_note: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PlanResponse(BaseModel):
    id: str
    code: str
    name: str
    description: str
    price: Decimal
    currency: str
    billing_interval: BillingInterval
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


SUPPORTED_ENTITLEMENT_KEYS = frozenset({"max_products", "max_members", "max_branches", "max_warehouses"})


class PlanEntitlementCreate(BaseModel):
    plan_id: str = Field(..., min_length=1)
    feature_key: str = Field(..., min_length=1)
    limit_value: int = Field(..., ge=-1)

    @field_validator("feature_key")
    @classmethod
    def validate_feature_key(cls, v: str) -> str:
        if v not in SUPPORTED_ENTITLEMENT_KEYS:
            raise ValueError(f"Unsupported feature key: {v}. Supported: {sorted(SUPPORTED_ENTITLEMENT_KEYS)}")
        return v

    model_config = ConfigDict(extra="forbid")


class PlanEntitlementUpdate(BaseModel):
    limit_value: int = Field(..., ge=-1)

    model_config = ConfigDict(extra="forbid")


class PlanEntitlementInDB(BaseModel):
    id: str
    plan_id: str
    feature_key: str
    limit_value: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlanEntitlementResponse(BaseModel):
    id: str
    plan_id: str
    feature_key: str
    limit_value: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
