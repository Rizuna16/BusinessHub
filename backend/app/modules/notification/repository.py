from datetime import datetime, timezone
from typing import Dict, List, Optional
from abc import ABC, abstractmethod
import uuid

from app.modules.notification.schemas import (
    Notification,
    NotificationScope,
)


class AbstractNotificationRepository(ABC):
    @abstractmethod
    async def create(self, notification: Notification) -> Notification:
        pass

    @abstractmethod
    async def get_by_id(self, notification_id: str) -> Optional[Notification]:
        pass

    @abstractmethod
    async def list_for_recipient(
        self,
        recipient_id: str,
        scope: Optional[NotificationScope] = None,
        business_id: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[Notification]:
        pass

    @abstractmethod
    async def count_unread(
        self,
        recipient_id: str,
        scope: Optional[NotificationScope] = None,
        business_id: Optional[str] = None,
    ) -> int:
        pass

    @abstractmethod
    async def mark_read(self, notification_id: str, recipient_id: str) -> Optional[Notification]:
        pass

    @abstractmethod
    async def mark_all_read(
        self,
        recipient_id: str,
        scope: Optional[NotificationScope] = None,
        business_id: Optional[str] = None,
    ) -> int:
        pass

    @abstractmethod
    async def find_by_deduplication_key(self, deduplication_key: str) -> Optional[Notification]:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryNotificationRepository(AbstractNotificationRepository):
    _notifications: Dict[str, Notification] = {}
    _dedup_index: Dict[str, str] = {}

    async def create(self, notification: Notification) -> Notification:
        self._notifications[notification.id] = notification
        if notification.deduplication_key:
            self._dedup_index[notification.deduplication_key] = notification.id
        return notification

    async def get_by_id(self, notification_id: str) -> Optional[Notification]:
        return self._notifications.get(notification_id)

    async def list_for_recipient(
        self,
        recipient_id: str,
        scope: Optional[NotificationScope] = None,
        business_id: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[Notification]:
        results = []
        for n in self._notifications.values():
            if n.recipient_id != recipient_id:
                continue
            if scope is not None and n.scope != scope:
                continue
            if business_id is not None and n.business_id != business_id:
                continue
            if unread_only and n.is_read:
                continue
            results.append(n)
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[:limit]

    async def count_unread(
        self,
        recipient_id: str,
        scope: Optional[NotificationScope] = None,
        business_id: Optional[str] = None,
    ) -> int:
        count = 0
        for n in self._notifications.values():
            if n.recipient_id != recipient_id:
                continue
            if n.is_read:
                continue
            if scope is not None and n.scope != scope:
                continue
            if business_id is not None and n.business_id != business_id:
                continue
            count += 1
        return count

    async def mark_read(self, notification_id: str, recipient_id: str) -> Optional[Notification]:
        n = self._notifications.get(notification_id)
        if not n:
            return None
        if n.recipient_id != recipient_id:
            return None
        if n.is_read:
            return n
        now = datetime.now(timezone.utc)
        updated = n.model_copy(update={"is_read": True, "read_at": now})
        self._notifications[notification_id] = updated
        return updated

    async def mark_all_read(
        self,
        recipient_id: str,
        scope: Optional[NotificationScope] = None,
        business_id: Optional[str] = None,
    ) -> int:
        count = 0
        now = datetime.now(timezone.utc)
        for nid, n in self._notifications.items():
            if n.recipient_id != recipient_id:
                continue
            if n.is_read:
                continue
            if scope is not None and n.scope != scope:
                continue
            if business_id is not None and n.business_id != business_id:
                continue
            updated = n.model_copy(update={"is_read": True, "read_at": now})
            self._notifications[nid] = updated
            count += 1
        return count

    async def find_by_deduplication_key(self, deduplication_key: str) -> Optional[Notification]:
        nid = self._dedup_index.get(deduplication_key)
        if nid:
            return self._notifications.get(nid)
        return None

    @classmethod
    def clear(cls):
        cls._notifications.clear()
        cls._dedup_index.clear()


notification_repository = InMemoryNotificationRepository()
