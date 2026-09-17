import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from decimal import Decimal

from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.transfer.models import (
    Transfer as TransferModel,
    TransferLine as TransferLineModel,
)
from app.modules.transfer.repository import AbstractTransferRepository
from app.modules.transfer.schemas import (
    TransferInDB,
    TransferLineInDB,
    TransferStatus,
)
from app.modules.sqla_base import sa_create


def _to_transfer_in_db(obj: TransferModel) -> TransferInDB:
    return TransferInDB(
        id=obj.id,
        business_id=obj.business_id,
        transfer_number=obj.transfer_number,
        source_location_id=obj.source_location_id,
        destination_location_id=obj.destination_location_id,
        status=TransferStatus(obj.status),
        notes=obj.notes,
        created_by_user_id=obj.created_by_user_id,
        dispatched_by_user_id=obj.dispatched_by_user_id,
        received_by_user_id=obj.received_by_user_id,
        cancelled_by_user_id=obj.cancelled_by_user_id,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        dispatched_at=obj.dispatched_at,
        received_at=obj.received_at,
        cancelled_at=obj.cancelled_at,
    )


def _to_transfer_line_in_db(obj: TransferLineModel) -> TransferLineInDB:
    return TransferLineInDB(
        id=obj.id,
        transfer_id=obj.transfer_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        quantity=obj.quantity,
        unit_cost_snapshot=obj.unit_cost_snapshot,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyTransferRepository(AbstractTransferRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_transfer(
        self,
        business_id: str,
        transfer_number: str,
        source_location_id: str,
        destination_location_id: str,
        created_by_user_id: str,
        notes: Optional[str] = None,
    ) -> TransferInDB:
        data = {
            "id": str(uuid.uuid4()),
            "business_id": business_id,
            "transfer_number": transfer_number,
            "source_location_id": source_location_id,
            "destination_location_id": destination_location_id,
            "status": TransferStatus.DRAFT.value,
            "notes": notes,
            "created_by_user_id": created_by_user_id,
        }
        obj = await sa_create(self.session, TransferModel, data)
        return _to_transfer_in_db(obj)

    async def get_transfer_by_id(
        self, transfer_id: str, business_id: str
    ) -> Optional[TransferInDB]:
        stmt = select(TransferModel).where(
            TransferModel.id == transfer_id,
            TransferModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_transfer_in_db(obj) if obj else None

    async def get_next_transfer_sequence(self, business_id: str) -> int:
        from sqlalchemy import Integer
        stmt = select(func.max(func.cast(TransferModel.transfer_number, Integer))).where(
            TransferModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        max_num = result.scalar_one()
        if max_num is None:
            return 1
        try:
            return int(max_num) + 1
        except (ValueError, TypeError):
            return 1

    async def list_transfers(
        self,
        business_id: str,
        status: Optional[TransferStatus] = None,
        source_location_id: Optional[str] = None,
        destination_location_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[TransferInDB], int]:
        filters = [TransferModel.business_id == business_id]
        if status is not None:
            filters.append(TransferModel.status == status.value)
        if source_location_id is not None:
            filters.append(TransferModel.source_location_id == source_location_id)
        if destination_location_id is not None:
            filters.append(TransferModel.destination_location_id == destination_location_id)
        if search:
            filters.append(
                or_(
                    TransferModel.transfer_number.ilike(f"%{search}%"),
                    TransferModel.notes.ilike(f"%{search}%"),
                )
            )

        count_stmt = select(func.count()).select_from(TransferModel).where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(TransferModel)
            .where(and_(*filters))
            .order_by(desc(TransferModel.created_at))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        result = await self.session.execute(stmt)
        items = [_to_transfer_in_db(o) for o in result.scalars().all()]
        return items, total

    async def update_transfer(
        self,
        transfer_id: str,
        business_id: str,
        notes: Optional[str] = None,
        status: Optional[TransferStatus] = None,
        dispatched_by_user_id: Optional[str] = None,
        dispatched_at: Optional[datetime] = None,
        received_by_user_id: Optional[str] = None,
        received_at: Optional[datetime] = None,
        cancelled_by_user_id: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
    ) -> Optional[TransferInDB]:
        stmt = select(TransferModel).where(
            TransferModel.id == transfer_id,
            TransferModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        if notes is not None:
            obj.notes = notes
        if status is not None:
            obj.status = status.value if hasattr(status, "value") else status
        if dispatched_by_user_id is not None:
            obj.dispatched_by_user_id = dispatched_by_user_id
        if dispatched_at is not None:
            obj.dispatched_at = dispatched_at
        if received_by_user_id is not None:
            obj.received_by_user_id = received_by_user_id
        if received_at is not None:
            obj.received_at = received_at
        if cancelled_by_user_id is not None:
            obj.cancelled_by_user_id = cancelled_by_user_id
        if cancelled_at is not None:
            obj.cancelled_at = cancelled_at
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_transfer_in_db(obj)

    async def create_line(
        self,
        transfer_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
    ) -> TransferLineInDB:
        data = {
            "id": str(uuid.uuid4()),
            "transfer_id": transfer_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "quantity": quantity,
            "unit_cost_snapshot": Decimal("0"),
        }
        obj = await sa_create(self.session, TransferLineModel, data)
        return _to_transfer_line_in_db(obj)

    async def get_line_by_id(
        self, line_id: str, transfer_id: str
    ) -> Optional[TransferLineInDB]:
        stmt = select(TransferLineModel).where(
            TransferLineModel.id == line_id,
            TransferLineModel.transfer_id == transfer_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_transfer_line_in_db(obj) if obj else None

    async def list_lines_for_transfer(self, transfer_id: str) -> List[TransferLineInDB]:
        stmt = (
            select(TransferLineModel)
            .where(TransferLineModel.transfer_id == transfer_id)
            .order_by(TransferLineModel.created_at, TransferLineModel.id)
        )
        result = await self.session.execute(stmt)
        return [_to_transfer_line_in_db(o) for o in result.scalars().all()]

    async def update_line_cost_snapshot(
        self,
        line_id: str,
        transfer_id: str,
        unit_cost_snapshot: Decimal,
    ) -> Optional[TransferLineInDB]:
        stmt = select(TransferLineModel).where(
            TransferLineModel.id == line_id,
            TransferLineModel.transfer_id == transfer_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.unit_cost_snapshot = unit_cost_snapshot
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_transfer_line_in_db(obj)

    @classmethod
    def clear(cls):
        pass
