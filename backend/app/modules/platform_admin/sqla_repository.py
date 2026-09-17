from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.platform_admin.models import PlatformAuditLogInDB as AuditLogModel
from app.modules.platform_admin.repository import AbstractPlatformAuditRepository
from app.modules.platform_admin.schemas import (
    PlatformAuditLogInDB,
    PlatformAuditLogCreate,
)
from app.modules.sqla_base import sa_create


def _to_log(obj: AuditLogModel) -> PlatformAuditLogInDB:
    return PlatformAuditLogInDB(
        id=obj.id,
        actor_account_id=obj.actor_account_id,
        actor_email=obj.actor_email,
        action=obj.action,
        target_type=obj.target_type,
        target_id=obj.target_id,
        target_business_id=obj.target_business_id,
        reason=obj.reason,
        before_state=obj.before_state,
        after_state=obj.after_state,
        result=obj.result,
        metadata=obj.metadata_json,
        timestamp=obj.timestamp,
    )


class SQLAlchemyPlatformAuditRepository(AbstractPlatformAuditRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, entry: PlatformAuditLogCreate) -> PlatformAuditLogInDB:
        from app.modules.platform_admin.repository import _sanitize_snapshot

        data = {
            "actor_account_id": entry.actor_account_id,
            "actor_email": entry.actor_email,
            "action": entry.action,
            "target_type": entry.target_type,
            "target_id": entry.target_id,
            "target_business_id": entry.target_business_id,
            "reason": entry.reason,
            "before_state": _sanitize_snapshot(entry.before_state),
            "after_state": _sanitize_snapshot(entry.after_state),
            "result": entry.result,
            "metadata_json": _sanitize_snapshot(entry.metadata),
        }
        obj = await sa_create(self.session, AuditLogModel, data)
        return _to_log(obj)

    async def list_all(
        self,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        target_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[PlatformAuditLogInDB]:
        filters = []
        if actor_id:
            filters.append(AuditLogModel.actor_account_id == actor_id)
        if action:
            filters.append(func.lower(AuditLogModel.action) == action.lower())
        if target_type:
            filters.append(func.lower(AuditLogModel.target_type) == target_type.lower())
        if from_date:
            filters.append(AuditLogModel.timestamp >= from_date)
        if to_date:
            filters.append(AuditLogModel.timestamp <= to_date)

        stmt = select(AuditLogModel)
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(desc(AuditLogModel.timestamp))
        res = await self.session.execute(stmt)
        return [_to_log(o) for o in res.scalars().all()]

    async def get_by_id(self, log_id: str) -> Optional[PlatformAuditLogInDB]:
        stmt = select(AuditLogModel).where(AuditLogModel.id == log_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_log(obj) if obj else None

    @classmethod
    def clear(cls):
        pass
