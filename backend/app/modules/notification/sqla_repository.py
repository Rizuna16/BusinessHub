from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func, and_, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notification.models import Notification as NotificationModel
from app.modules.notification.repository import AbstractNotificationRepository
from app.modules.notification.schemas import (
    Notification,
    NotificationScope,
)
from app.modules.sqla_base import sa_create


def _to_notification(obj: NotificationModel) -> Notification:
    return Notification(
        id=obj.id,
        recipient_id=obj.recipient_id,
        business_id=obj.business_id,
        scope=NotificationScope(obj.scope),
        type=obj.type,
        severity=obj.severity,
        title=obj.title,
        message=obj.message,
        is_read=obj.is_read,
        read_at=obj.read_at,
        created_at=obj.created_at,
        metadata=obj.metadata_json,
        deduplication_key=obj.deduplication_key,
    )


class SQLAlchemyNotificationRepository(AbstractNotificationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, notification: Notification) -> Notification:
        data = {
            "id": notification.id,
            "recipient_id": notification.recipient_id,
            "business_id": notification.business_id,
            "scope": notification.scope.value,
            "type": notification.type.value,
            "severity": notification.severity.value,
            "title": notification.title,
            "message": notification.message,
            "is_read": notification.is_read,
            "read_at": notification.read_at,
            "metadata_json": notification.metadata,
            "deduplication_key": notification.deduplication_key,
        }
        try:
            obj = await sa_create(self.session, NotificationModel, data)
            return _to_notification(obj)
        except IntegrityError:
            # Concurrent deduplication: another request inserted first.
            # Rollback the failed transaction, then re-query.
            await self.session.rollback()
            if notification.deduplication_key:
                existing = await self.find_by_deduplication_key(notification.deduplication_key)
                if existing:
                    return existing
            raise

    async def get_by_id(self, notification_id: str) -> Optional[Notification]:
        stmt = select(NotificationModel).where(NotificationModel.id == notification_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_notification(obj) if obj else None

    async def list_for_recipient(
        self,
        recipient_id: str,
        scope: Optional[NotificationScope] = None,
        business_id: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[Notification]:
        filters = [NotificationModel.recipient_id == recipient_id]
        if scope is not None:
            filters.append(NotificationModel.scope == scope.value)
        if business_id is not None:
            filters.append(NotificationModel.business_id == business_id)
        if unread_only:
            filters.append(NotificationModel.is_read == False)
        stmt = (
            select(NotificationModel)
            .where(and_(*filters))
            .order_by(desc(NotificationModel.created_at))
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return [_to_notification(o) for o in res.scalars().all()]

    async def count_unread(
        self,
        recipient_id: str,
        scope: Optional[NotificationScope] = None,
        business_id: Optional[str] = None,
    ) -> int:
        filters = [
            NotificationModel.recipient_id == recipient_id,
            NotificationModel.is_read == False,
        ]
        if scope is not None:
            filters.append(NotificationModel.scope == scope.value)
        if business_id is not None:
            filters.append(NotificationModel.business_id == business_id)
        stmt = select(func.count()).select_from(NotificationModel).where(and_(*filters))
        res = await self.session.execute(stmt)
        return res.scalar_one() or 0

    async def mark_read(self, notification_id: str, recipient_id: str) -> Optional[Notification]:
        stmt = select(NotificationModel).where(
            NotificationModel.id == notification_id,
            NotificationModel.recipient_id == recipient_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        if obj.is_read:
            return _to_notification(obj)
        obj.is_read = True
        obj.read_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_notification(obj)

    async def mark_all_read(
        self,
        recipient_id: str,
        scope: Optional[NotificationScope] = None,
        business_id: Optional[str] = None,
    ) -> int:
        filters = [
            NotificationModel.recipient_id == recipient_id,
            NotificationModel.is_read == False,
        ]
        if scope is not None:
            filters.append(NotificationModel.scope == scope.value)
        if business_id is not None:
            filters.append(NotificationModel.business_id == business_id)
        stmt = select(NotificationModel).where(and_(*filters))
        res = await self.session.execute(stmt)
        now = datetime.now(timezone.utc)
        count = 0
        for obj in res.scalars().all():
            obj.is_read = True
            obj.read_at = now
            count += 1
        if count > 0:
            await self.session.flush()
        return count

    async def find_by_deduplication_key(self, deduplication_key: str) -> Optional[Notification]:
        stmt = select(NotificationModel).where(
            NotificationModel.deduplication_key == deduplication_key
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_notification(obj) if obj else None

    @classmethod
    def clear(cls):
        pass
