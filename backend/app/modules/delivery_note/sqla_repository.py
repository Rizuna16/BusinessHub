import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from decimal import Decimal

from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.delivery_note.models import (
    DeliveryNote as DeliveryNoteModel,
    DeliveryNoteLine as DeliveryNoteLineModel,
)
from app.modules.delivery_note.repository import AbstractDeliveryNoteRepository
from app.modules.delivery_note.schemas import (
    DeliveryNoteInDB,
    DeliveryNoteLineInDB,
    DeliveryNoteStatus,
)
from app.modules.sqla_base import sa_create


def _to_delivery_note_in_db(obj: DeliveryNoteModel) -> DeliveryNoteInDB:
    return DeliveryNoteInDB(
        id=obj.id,
        business_id=obj.business_id,
        branch_id=obj.branch_id,
        delivery_number=obj.delivery_number,
        sales_order_id=obj.sales_order_id,
        customer_id=obj.customer_id,
        delivery_date=obj.delivery_date,
        status=DeliveryNoteStatus(obj.status),
        shipping_address=obj.shipping_address,
        recipient_name=obj.recipient_name,
        recipient_phone=obj.recipient_phone,
        notes=obj.notes,
        created_by_user_id=obj.created_by_user_id,
        ready_by_user_id=obj.ready_by_user_id,
        ready_at=obj.ready_at,
        delivered_by_user_id=obj.delivered_by_user_id,
        delivered_at=obj.delivered_at,
        cancelled_by_user_id=obj.cancelled_by_user_id,
        cancelled_at=obj.cancelled_at,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_delivery_note_line_in_db(obj: DeliveryNoteLineModel) -> DeliveryNoteLineInDB:
    return DeliveryNoteLineInDB(
        id=obj.id,
        delivery_note_id=obj.delivery_note_id,
        sales_order_line_id=obj.sales_order_line_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        product_name_snapshot=obj.product_name_snapshot,
        variant_snapshot=obj.variant_snapshot,
        ordered_quantity_snapshot=obj.ordered_quantity_snapshot,
        fulfilled_quantity_snapshot=obj.fulfilled_quantity_snapshot,
        delivery_quantity=obj.delivery_quantity,
        unit=obj.unit,
        notes=obj.notes,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyDeliveryNoteRepository(AbstractDeliveryNoteRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_delivery_note(
        self,
        business_id: str,
        branch_id: str,
        delivery_number: str,
        sales_order_id: str,
        customer_id: Optional[str],
        delivery_date: datetime,
        shipping_address: Optional[str],
        recipient_name: Optional[str],
        recipient_phone: Optional[str],
        notes: Optional[str],
        created_by_user_id: str,
    ) -> DeliveryNoteInDB:
        data = {
            "id": str(uuid.uuid4()),
            "business_id": business_id,
            "branch_id": branch_id,
            "delivery_number": delivery_number,
            "sales_order_id": sales_order_id,
            "customer_id": customer_id,
            "delivery_date": delivery_date,
            "status": DeliveryNoteStatus.DRAFT.value,
            "shipping_address": shipping_address,
            "recipient_name": recipient_name,
            "recipient_phone": recipient_phone,
            "notes": notes,
            "created_by_user_id": created_by_user_id,
        }
        obj = await sa_create(self.session, DeliveryNoteModel, data)
        return _to_delivery_note_in_db(obj)

    async def get_by_id(self, delivery_note_id: str, business_id: str) -> Optional[DeliveryNoteInDB]:
        stmt = select(DeliveryNoteModel).where(
            DeliveryNoteModel.id == delivery_note_id,
            DeliveryNoteModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_delivery_note_in_db(obj) if obj else None

    async def get_by_number(self, business_id: str, delivery_number: str) -> Optional[DeliveryNoteInDB]:
        stmt = select(DeliveryNoteModel).where(
            DeliveryNoteModel.business_id == business_id,
            DeliveryNoteModel.delivery_number == delivery_number,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_delivery_note_in_db(obj) if obj else None

    async def list_delivery_notes(
        self,
        business_id: str,
        status: Optional[DeliveryNoteStatus],
        sales_order_id: Optional[str],
        search: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[List[DeliveryNoteInDB], int]:
        filters = [DeliveryNoteModel.business_id == business_id]
        if status is not None:
            filters.append(DeliveryNoteModel.status == status.value)
        if sales_order_id is not None:
            filters.append(DeliveryNoteModel.sales_order_id == sales_order_id)
        if search:
            filters.append(
                or_(
                    DeliveryNoteModel.delivery_number.ilike(f"%{search}%"),
                    DeliveryNoteModel.recipient_name.ilike(f"%{search}%"),
                    DeliveryNoteModel.notes.ilike(f"%{search}%"),
                )
            )

        count_stmt = select(func.count()).select_from(DeliveryNoteModel).where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(DeliveryNoteModel)
            .where(and_(*filters))
            .order_by(desc(DeliveryNoteModel.created_at))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        result = await self.session.execute(stmt)
        items = [_to_delivery_note_in_db(o) for o in result.scalars().all()]
        return items, total

    async def update_delivery_note(self, delivery_note_id: str, business_id: str, **kwargs) -> Optional[DeliveryNoteInDB]:
        stmt = select(DeliveryNoteModel).where(
            DeliveryNoteModel.id == delivery_note_id,
            DeliveryNoteModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        for key, value in kwargs.items():
            if key == "status" and value is not None:
                obj.status = value.value if hasattr(value, "value") else value
            elif hasattr(obj, key) and (value is not None or key in [
                "customer_id", "notes", "shipping_address", "recipient_name",
                "recipient_phone", "ready_by_user_id", "ready_at", "delivered_by_user_id",
                "delivered_at", "cancelled_by_user_id", "cancelled_at", "status",
            ]):
                setattr(obj, key, value)
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_delivery_note_in_db(obj)

    async def get_next_sequence(self, business_id: str) -> int:
        from sqlalchemy import Integer
        stmt = select(func.max(func.cast(DeliveryNoteModel.delivery_number, Integer))).where(
            DeliveryNoteModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        max_num = result.scalar_one()
        if max_num is None:
            return 1
        try:
            return int(max_num) + 1
        except (ValueError, TypeError):
            return 1

    async def create_line(
        self,
        delivery_note_id: str,
        sales_order_line_id: str,
        product_id: str,
        variant_id: Optional[str],
        product_name_snapshot: str,
        variant_snapshot: Optional[str],
        ordered_quantity_snapshot: Decimal,
        fulfilled_quantity_snapshot: Decimal,
        delivery_quantity: Decimal,
        unit: Optional[str],
        notes: Optional[str],
    ) -> DeliveryNoteLineInDB:
        data = {
            "id": str(uuid.uuid4()),
            "delivery_note_id": delivery_note_id,
            "sales_order_line_id": sales_order_line_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "product_name_snapshot": product_name_snapshot,
            "variant_snapshot": variant_snapshot,
            "ordered_quantity_snapshot": ordered_quantity_snapshot,
            "fulfilled_quantity_snapshot": fulfilled_quantity_snapshot,
            "delivery_quantity": delivery_quantity,
            "unit": unit,
            "notes": notes,
        }
        obj = await sa_create(self.session, DeliveryNoteLineModel, data)
        return _to_delivery_note_line_in_db(obj)

    async def get_line_by_id(self, line_id: str, delivery_note_id: str) -> Optional[DeliveryNoteLineInDB]:
        stmt = select(DeliveryNoteLineModel).where(
            DeliveryNoteLineModel.id == line_id,
            DeliveryNoteLineModel.delivery_note_id == delivery_note_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_delivery_note_line_in_db(obj) if obj else None

    async def list_lines_for_delivery_note(self, delivery_note_id: str) -> List[DeliveryNoteLineInDB]:
        stmt = (
            select(DeliveryNoteLineModel)
            .where(DeliveryNoteLineModel.delivery_note_id == delivery_note_id)
            .order_by(DeliveryNoteLineModel.created_at, DeliveryNoteLineModel.id)
        )
        result = await self.session.execute(stmt)
        return [_to_delivery_note_line_in_db(o) for o in result.scalars().all()]

    async def update_line(self, line_id: str, delivery_note_id: str, **kwargs) -> Optional[DeliveryNoteLineInDB]:
        stmt = select(DeliveryNoteLineModel).where(
            DeliveryNoteLineModel.id == line_id,
            DeliveryNoteLineModel.delivery_note_id == delivery_note_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(obj, key):
                setattr(obj, key, value)
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_delivery_note_line_in_db(obj)

    async def delete_line(self, line_id: str, delivery_note_id: str) -> bool:
        stmt = select(DeliveryNoteLineModel).where(
            DeliveryNoteLineModel.id == line_id,
            DeliveryNoteLineModel.delivery_note_id == delivery_note_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True

    async def get_active_documented_quantity(self, business_id: str, sales_order_line_id: str, exclude_dn_id: Optional[str] = None) -> Decimal:
        filters = [
            DeliveryNoteModel.business_id == business_id,
            DeliveryNoteModel.status.not_in([DeliveryNoteStatus.CANCELLED.value, DeliveryNoteStatus.DELIVERED.value]),
            DeliveryNoteLineModel.sales_order_line_id == sales_order_line_id,
        ]
        if exclude_dn_id is not None:
            filters.append(DeliveryNoteModel.id != exclude_dn_id)

        stmt = (
            select(func.coalesce(func.sum(DeliveryNoteLineModel.delivery_quantity), 0))
            .join(DeliveryNoteModel, DeliveryNoteLineModel.delivery_note_id == DeliveryNoteModel.id)
            .where(and_(*filters))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    @classmethod
    def clear(cls):
        pass
