"""
Notification service with operation-scoped production persistence.

Feature #66: Notification Expansion + Production Persistence

Production notification writes use operation-scoped AsyncSession.
InMemory notification repository remains for tests only.
"""
from datetime import datetime, timezone
from typing import List, Optional
import uuid
import logging
from fastapi import HTTPException, status

from app.modules.notification.schemas import (
    Notification,
    NotificationResponse,
    NotificationScope,
    NotificationSeverity,
    NotificationType,
    UnreadCountResponse,
)
from app.modules.notification.repository import AbstractNotificationRepository, notification_repository

logger = logging.getLogger("notification")


async def _send_notification(
    recipient_id: str,
    scope: NotificationScope,
    notif_type: NotificationType,
    severity: NotificationSeverity,
    title: str,
    message: str,
    business_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    deduplication_key: Optional[str] = None,
) -> None:
    """
    Operation-scoped notification write.

    Opens its own AsyncSession, persists notification, commits, closes.
    Primary business transaction is never affected by notification failure.
    """
    from app.core.database import async_session_factory
    from app.modules.notification.sqla_repository import SQLAlchemyNotificationRepository

    async with async_session_factory() as session:
        svc = NotificationService(SQLAlchemyNotificationRepository(session))
        await svc.create_if_not_exists(
            recipient_id=recipient_id,
            scope=scope,
            type=notif_type,
            severity=severity,
            title=title,
            message=message,
            business_id=business_id,
            metadata=metadata,
            deduplication_key=deduplication_key,
        )
        await session.commit()


class NotificationService:
    def __init__(self, repository: AbstractNotificationRepository = notification_repository):
        self.repository = repository

    async def create_notification(
        self,
        recipient_id: str,
        scope: NotificationScope,
        type: NotificationType,
        severity: NotificationSeverity,
        title: str,
        message: str,
        business_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        deduplication_key: Optional[str] = None,
    ) -> Notification:
        if scope == NotificationScope.TENANT:
            if not business_id:
                raise HTTPException(status_code=400, detail="business_id required for TENANT scope.")
            if not recipient_id:
                raise HTTPException(status_code=400, detail="recipient_id required for TENANT scope.")
        if scope == NotificationScope.PLATFORM:
            if business_id is not None:
                raise HTTPException(status_code=400, detail="business_id must be null for PLATFORM scope.")
            if not recipient_id:
                raise HTTPException(status_code=400, detail="recipient_id required for PLATFORM scope.")

        now = datetime.now(timezone.utc)
        notification = Notification(
            id=str(uuid.uuid4()),
            recipient_id=recipient_id,
            business_id=business_id,
            scope=scope,
            type=type,
            severity=severity,
            title=title,
            message=message,
            is_read=False,
            read_at=None,
            created_at=now,
            metadata=metadata,
            deduplication_key=deduplication_key,
        )
        return await self.repository.create(notification)

    async def create_if_not_exists(
        self,
        recipient_id: str,
        scope: NotificationScope,
        type: NotificationType,
        severity: NotificationSeverity,
        title: str,
        message: str,
        business_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        deduplication_key: Optional[str] = None,
    ) -> Notification:
        if deduplication_key:
            existing = await self.repository.find_by_deduplication_key(deduplication_key)
            if existing:
                return existing
        return await self.create_notification(
            recipient_id=recipient_id,
            scope=scope,
            type=type,
            severity=severity,
            title=title,
            message=message,
            business_id=business_id,
            metadata=metadata,
            deduplication_key=deduplication_key,
        )

    async def list_notifications(
        self,
        recipient_id: str,
        scope: Optional[NotificationScope] = None,
        business_id: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[NotificationResponse]:
        notifications = await self.repository.list_for_recipient(
            recipient_id=recipient_id,
            scope=scope,
            business_id=business_id,
            unread_only=unread_only,
            limit=limit,
        )
        return [NotificationResponse.model_validate(n) for n in notifications]

    async def get_unread_count(
        self,
        recipient_id: str,
        scope: Optional[NotificationScope] = None,
        business_id: Optional[str] = None,
    ) -> int:
        return await self.repository.count_unread(
            recipient_id=recipient_id,
            scope=scope,
            business_id=business_id,
        )

    async def mark_as_read(self, notification_id: str, recipient_id: str) -> NotificationResponse:
        n = await self.repository.get_by_id(notification_id)
        if not n:
            raise HTTPException(status_code=404, detail="Notification not found.")
        if n.recipient_id != recipient_id:
            raise HTTPException(status_code=404, detail="Notification not found.")
        updated = await self.repository.mark_read(notification_id, recipient_id)
        if not updated:
            raise HTTPException(status_code=404, detail="Notification not found.")
        return NotificationResponse.model_validate(updated)

    async def mark_all_as_read(
        self,
        recipient_id: str,
        scope: Optional[NotificationScope] = None,
        business_id: Optional[str] = None,
    ) -> int:
        return await self.repository.mark_all_read(
            recipient_id=recipient_id,
            scope=scope,
            business_id=business_id,
        )

    async def notify_super_admins(
        self,
        super_admin_ids: List[str],
        type: NotificationType,
        severity: NotificationSeverity,
        title: str,
        message: str,
        metadata: Optional[dict] = None,
        deduplication_key: Optional[str] = None,
    ) -> None:
        for admin_id in super_admin_ids:
            dedup = f"{deduplication_key}:{admin_id}" if deduplication_key else None
            try:
                await _send_notification(
                    recipient_id=admin_id,
                    scope=NotificationScope.PLATFORM,
                    notif_type=type,
                    severity=severity,
                    title=title,
                    message=message,
                    business_id=None,
                    metadata=metadata,
                    deduplication_key=dedup,
                )
            except Exception:
                logger.exception(
                    "notification_send_failed recipient=%s type=%s",
                    admin_id, type.value,
                )

    async def notify_business_members(
        self,
        member_ids: List[str],
        business_id: str,
        type: NotificationType,
        severity: NotificationSeverity,
        title: str,
        message: str,
        metadata: Optional[dict] = None,
        deduplication_key: Optional[str] = None,
    ) -> None:
        for member_id in member_ids:
            dedup = f"{deduplication_key}:{member_id}" if deduplication_key else None
            try:
                await _send_notification(
                    recipient_id=member_id,
                    scope=NotificationScope.TENANT,
                    notif_type=type,
                    severity=severity,
                    title=title,
                    message=message,
                    business_id=business_id,
                    metadata=metadata,
                    deduplication_key=dedup,
                )
            except Exception:
                logger.exception(
                    "notification_send_failed recipient=%s type=%s business=%s",
                    member_id, type.value, business_id,
                )


notification_service = NotificationService()
