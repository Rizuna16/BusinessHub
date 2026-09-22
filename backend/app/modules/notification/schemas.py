from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class NotificationScope(str, Enum):
    TENANT = "TENANT"
    PLATFORM = "PLATFORM"


class NotificationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class NotificationType(str, Enum):
    SUBSCRIPTION_RENEWAL_REMINDER = "SUBSCRIPTION_RENEWAL_REMINDER"
    PAYMENT_VERIFICATION_REQUIRED = "PAYMENT_VERIFICATION_REQUIRED"
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED"
    STOCK_LOW = "STOCK_LOW"
    SALES_FINALIZED = "SALES_FINALIZED"
    PURCHASE_RECEIVED = "PURCHASE_RECEIVED"
    CUSTOMER_CREDIT_LIMIT_WARNING = "CUSTOMER_CREDIT_LIMIT_WARNING"
    TRANSFER_COMPLETED = "TRANSFER_COMPLETED"


class Notification(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., min_length=1)
    recipient_id: str = Field(..., min_length=1)
    business_id: Optional[str] = None
    scope: NotificationScope
    type: NotificationType
    severity: NotificationSeverity
    title: str
    message: str
    is_read: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime
    metadata: Optional[dict] = None
    deduplication_key: Optional[str] = None


class NotificationResponse(BaseModel):
    id: str
    recipient_id: str
    business_id: Optional[str] = None
    scope: NotificationScope
    type: NotificationType
    severity: NotificationSeverity
    title: str
    message: str
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    metadata: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class UnreadCountResponse(BaseModel):
    count: int
