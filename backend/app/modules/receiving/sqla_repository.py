import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from decimal import Decimal

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.receiving.models import (
    Receiving as ReceivingModel,
    ReceivingLine as ReceivingLineModel,
)
from app.modules.receiving.repository import AbstractReceivingRepository
from app.modules.receiving.schemas import (
    ReceivingInDB,
    ReceivingLineInDB,
    ReceivingStatus,
)
from app.modules.sqla_base import sa_create


def _to_receiving_in_db(obj: ReceivingModel) -> ReceivingInDB:
    return ReceivingInDB(
        id=obj.id,
        business_id=obj.business_id,
        purchase_id=obj.purchase_id,
        inventory_location_id=obj.inventory_location_id,
        receiving_number=obj.receiving_number,
        status=ReceivingStatus(obj.status),
        notes=obj.notes,
        created_by_user_id=obj.created_by_user_id,
        finalized_by_user_id=obj.finalized_by_user_id,
        cancelled_by_user_id=obj.cancelled_by_user_id,
        is_deleted=obj.is_deleted,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        finalized_at=obj.finalized_at,
        cancelled_at=obj.cancelled_at,
    )


def _to_receiving_line_in_db(obj: ReceivingLineModel) -> ReceivingLineInDB:
    return ReceivingLineInDB(
        id=obj.id,
        receiving_id=obj.receiving_id,
        purchase_line_id=obj.purchase_line_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        quantity=obj.quantity,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyReceivingRepository(AbstractReceivingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_receiving(
        self,
        business_id: str,
        purchase_id: str,
        inventory_location_id: str,
        receiving_number: str,
        created_by_user_id: str,
        notes: Optional[str] = None,
    ) -> ReceivingInDB:
        data = {
            "id": str(uuid.uuid4()),
            "business_id": business_id,
            "purchase_id": purchase_id,
            "inventory_location_id": inventory_location_id,
            "receiving_number": receiving_number,
            "status": ReceivingStatus.DRAFT.value,
            "notes": notes,
            "created_by_user_id": created_by_user_id,
            "is_deleted": False,
        }
        obj = await sa_create(self.session, ReceivingModel, data)
        return _to_receiving_in_db(obj)

    async def get_receiving_by_id(
        self, receiving_id: str, business_id: str
    ) -> Optional[ReceivingInDB]:
        stmt = select(ReceivingModel).where(
            ReceivingModel.id == receiving_id,
            ReceivingModel.business_id == business_id,
            ReceivingModel.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_receiving_in_db(obj) if obj else None

    async def get_next_receiving_sequence(self, business_id: str) -> int:
        from sqlalchemy import Integer
        stmt = select(func.max(func.cast(ReceivingModel.receiving_number, Integer))).where(
            ReceivingModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        max_num = result.scalar_one()
        if max_num is None:
            return 1
        try:
            return int(max_num) + 1
        except (ValueError, TypeError):
            return 1

    async def list_receivings(
        self,
        business_id: str,
        status: Optional[ReceivingStatus] = None,
        purchase_id: Optional[str] = None,
        inventory_location_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[ReceivingInDB], int]:
        filters = [
            ReceivingModel.business_id == business_id,
            ReceivingModel.is_deleted == False,
        ]
        if status is not None:
            filters.append(ReceivingModel.status == status.value)
        if purchase_id is not None:
            filters.append(ReceivingModel.purchase_id == purchase_id)
        if inventory_location_id is not None:
            filters.append(ReceivingModel.inventory_location_id == inventory_location_id)
        if search:
            filters.append(ReceivingModel.receiving_number.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(ReceivingModel).where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(ReceivingModel)
            .where(and_(*filters))
            .order_by(desc(ReceivingModel.created_at), desc(ReceivingModel.id))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        result = await self.session.execute(stmt)
        items = [_to_receiving_in_db(o) for o in result.scalars().all()]
        return items, total

    async def update_receiving(
        self,
        receiving_id: str,
        business_id: str,
        notes: Optional[str] = None,
        status: Optional[ReceivingStatus] = None,
        finalized_by_user_id: Optional[str] = None,
        finalized_at: Optional[datetime] = None,
        cancelled_by_user_id: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
        is_deleted: Optional[bool] = None,
    ) -> Optional[ReceivingInDB]:
        stmt = select(ReceivingModel).where(
            ReceivingModel.id == receiving_id,
            ReceivingModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        if notes is not None:
            obj.notes = notes
        if status is not None:
            obj.status = status.value
        if finalized_by_user_id is not None:
            obj.finalized_by_user_id = finalized_by_user_id
        if finalized_at is not None:
            obj.finalized_at = finalized_at
        if cancelled_by_user_id is not None:
            obj.cancelled_by_user_id = cancelled_by_user_id
        if cancelled_at is not None:
            obj.cancelled_at = cancelled_at
        if is_deleted is not None:
            obj.is_deleted = is_deleted
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_receiving_in_db(obj)

    async def create_line(
        self,
        receiving_id: str,
        purchase_line_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
    ) -> ReceivingLineInDB:
        data = {
            "id": str(uuid.uuid4()),
            "receiving_id": receiving_id,
            "purchase_line_id": purchase_line_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "quantity": quantity,
        }
        obj = await sa_create(self.session, ReceivingLineModel, data)
        return _to_receiving_line_in_db(obj)

    async def get_line_by_id(
        self, line_id: str, receiving_id: str
    ) -> Optional[ReceivingLineInDB]:
        stmt = select(ReceivingLineModel).where(
            ReceivingLineModel.id == line_id,
            ReceivingLineModel.receiving_id == receiving_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_receiving_line_in_db(obj) if obj else None

    async def list_lines_for_receiving(self, receiving_id: str) -> List[ReceivingLineInDB]:
        stmt = (
            select(ReceivingLineModel)
            .where(ReceivingLineModel.receiving_id == receiving_id)
            .order_by(ReceivingLineModel.created_at, ReceivingLineModel.id)
        )
        result = await self.session.execute(stmt)
        return [_to_receiving_line_in_db(o) for o in result.scalars().all()]

    async def update_line(
        self,
        line_id: str,
        receiving_id: str,
        quantity: Optional[Decimal] = None,
    ) -> Optional[ReceivingLineInDB]:
        stmt = select(ReceivingLineModel).where(
            ReceivingLineModel.id == line_id,
            ReceivingLineModel.receiving_id == receiving_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        if quantity is not None:
            obj.quantity = quantity
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_receiving_line_in_db(obj)

    async def delete_line(self, line_id: str, receiving_id: str) -> bool:
        stmt = select(ReceivingLineModel).where(
            ReceivingLineModel.id == line_id,
            ReceivingLineModel.receiving_id == receiving_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True

    async def sum_received_quantity_for_purchase_line(
        self, purchase_line_id: str
    ) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(ReceivingLineModel.quantity), 0))
            .join(ReceivingModel, ReceivingLineModel.receiving_id == ReceivingModel.id)
            .where(
                ReceivingLineModel.purchase_line_id == purchase_line_id,
                ReceivingModel.is_deleted == False,
                ReceivingModel.status.in_(["DRAFT", "FINALIZED"]),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def sum_finalized_received_quantity_for_purchase_line(
        self, purchase_line_id: str
    ) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(ReceivingLineModel.quantity), 0))
            .join(ReceivingModel, ReceivingLineModel.receiving_id == ReceivingModel.id)
            .where(
                ReceivingLineModel.purchase_line_id == purchase_line_id,
                ReceivingModel.is_deleted == False,
                ReceivingModel.status == "FINALIZED",
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def sum_received_quantity_for_purchase_line_excluding(
        self, purchase_line_id: str, exclude_receiving_id: str
    ) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(ReceivingLineModel.quantity), 0))
            .join(ReceivingModel, ReceivingLineModel.receiving_id == ReceivingModel.id)
            .where(
                ReceivingLineModel.purchase_line_id == purchase_line_id,
                ReceivingModel.is_deleted == False,
                ReceivingModel.id != exclude_receiving_id,
                ReceivingModel.status.in_(["DRAFT", "FINALIZED"]),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    @classmethod
    def clear(cls):
        pass
