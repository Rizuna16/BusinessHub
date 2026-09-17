from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

from app.modules.platform_admin.schemas import PlatformAuditLogInDB, PlatformAuditLogCreate


def _sanitize_snapshot(data: Optional[Dict]) -> Optional[Dict]:
    if not data:
        return data
    sensitive_keys = {
        "password", "password_hash", "jwt", "access_token",
        "refresh_token", "secret", "api_key", "payment_credentials"
    }
    clean = {}
    for k, v in data.items():
        if k.lower() in sensitive_keys:
            clean[k] = "[REDACTED]"
        elif isinstance(v, dict):
            clean[k] = _sanitize_snapshot(v)
        else:
            clean[k] = v
    return clean


class AbstractPlatformAuditRepository(ABC):
    @abstractmethod
    async def create(self, entry: PlatformAuditLogCreate) -> PlatformAuditLogInDB:
        pass

    @abstractmethod
    async def list_all(
        self,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        target_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[PlatformAuditLogInDB]:
        pass

    @abstractmethod
    async def get_by_id(self, log_id: str) -> Optional[PlatformAuditLogInDB]:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryPlatformAuditRepository(AbstractPlatformAuditRepository):
    """
    Append-only in-memory platform audit store.
    Strictly forbids update() and delete() operations to guarantee immutability.
    """
    _logs: List[PlatformAuditLogInDB] = []

    async def create(self, entry: PlatformAuditLogCreate) -> PlatformAuditLogInDB:
        log_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        sanitized_before = _sanitize_snapshot(entry.before_state)
        sanitized_after = _sanitize_snapshot(entry.after_state)
        sanitized_meta = _sanitize_snapshot(entry.metadata)

        log_item = PlatformAuditLogInDB(
            id=log_id,
            actor_account_id=entry.actor_account_id,
            actor_email=entry.actor_email,
            action=entry.action,
            target_type=entry.target_type,
            target_id=entry.target_id,
            target_business_id=entry.target_business_id,
            reason=entry.reason,
            before_state=sanitized_before,
            after_state=sanitized_after,
            result=entry.result,
            metadata=sanitized_meta,
            timestamp=now,
        )
        self._logs.append(log_item)
        return log_item

    async def list_all(
        self,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        target_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[PlatformAuditLogInDB]:
        filtered = list(self._logs)
        if actor_id:
            filtered = [l for l in filtered if l.actor_account_id == actor_id]
        if action:
            filtered = [l for l in filtered if l.action.lower() == action.lower()]
        if target_type:
            filtered = [l for l in filtered if l.target_type.lower() == target_type.lower()]
        if from_date:
            filtered = [l for l in filtered if l.timestamp >= from_date]
        if to_date:
            filtered = [l for l in filtered if l.timestamp <= to_date]

        # Reverse chronological ordering (newest first)
        filtered.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered

    async def get_by_id(self, log_id: str) -> Optional[PlatformAuditLogInDB]:
        for log in self._logs:
            if log.id == log_id:
                return log
        return None

    @classmethod
    def clear(cls):
        cls._logs.clear()


platform_audit_repository = InMemoryPlatformAuditRepository()
