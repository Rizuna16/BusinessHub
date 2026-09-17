import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from decimal import Decimal

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sales_return.models import (
    SalesReturn as SalesReturnModel,
    SalesReturnLine as SalesReturnLineModel,
)
from app.modules.sales_return.repository import AbstractSalesReturnRepository
from app.modules.sales_return.schemas import (
    SalesReturnInDB,
    SalesReturnLineInDB,
    SalesReturnStatus,
)
from app.modules.sqla_base import sa_create


def _to_sales_return_in_db(obj: SalesReturnModel) -> SalesReturnInDB:
    return SalesReturnInDB(
        id=obj.id,
        business_id=obj.business_id,
        sales_id=obj.sales_id,
        inventory_location_id=obj.inventory_location_id,
        return_number=obj.return_number,
        return_date=obj.return_date,
        status=SalesReturnStatus(obj.status),
        refund_destination=obj.refund_destination,
        notes=obj.notes,
        subtotal=obj.subtotal,
        discount_total=obj.discount_total,
        tax_total=obj.tax_total,
        grand_total=obj.grand_total,
        created_by_user_id=obj.created_by_user_id,
        finalized_by_user_id=obj.finalized_by_user_id,
        cancelled_by_user_id=obj.cancelled_by_user_id,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        finalized_at=obj.finalized_at,
        cancelled_at=obj.cancelled_at,
    )


def _to_sales_return_line_in_db(obj: SalesReturnLineModel) -> SalesReturnLineInDB:
    return SalesReturnLineInDB(
        id=obj.id,
        sales_return_id=obj.sales_return_id,
        sales_line_id=obj.sales_line_id,
        product_id=obj.product_id,
        variant_id=obj.variant_id,
        quantity=obj.quantity,
        unit_price=obj.unit_price,
        discount_amount=obj.discount_amount,
        tax_amount=obj.tax_amount,
        line_subtotal=obj.line_subtotal,
        line_total=obj.line_total,
        delivery_note_id=obj.delivery_note_id,
        delivery_note_line_id=obj.delivery_note_line_id,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemySalesReturnRepository(AbstractSalesReturnRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_return(
        self,
        business_id: str,
        sales_id: str,
        inventory_location_id: str,
        return_number: str,
        return_date: datetime,
        created_by_user_id: str,
        refund_destination: str = "CASH",
        notes: Optional[str] = None,
    ) -> SalesReturnInDB:
        data = {
            "id": str(uuid.uuid4()),
            "business_id": business_id,
            "sales_id": sales_id,
            "inventory_location_id": inventory_location_id,
            "return_number": return_number,
            "return_date": return_date,
            "status": SalesReturnStatus.DRAFT.value,
            "refund_destination": refund_destination,
            "notes": notes,
            "subtotal": Decimal("0"),
            "discount_total": Decimal("0"),
            "tax_total": Decimal("0"),
            "grand_total": Decimal("0"),
            "created_by_user_id": created_by_user_id,
        }
        obj = await sa_create(self.session, SalesReturnModel, data)
        return _to_sales_return_in_db(obj)

    async def get_return_by_id(
        self, return_id: str, business_id: str
    ) -> Optional[SalesReturnInDB]:
        stmt = select(SalesReturnModel).where(
            SalesReturnModel.id == return_id,
            SalesReturnModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_sales_return_in_db(obj) if obj else None

    async def get_next_return_sequence(self, business_id: str) -> int:
        from sqlalchemy import Integer
        stmt = select(func.max(func.cast(SalesReturnModel.return_number, Integer))).where(
            SalesReturnModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        max_num = result.scalar_one()
        if max_num is None:
            return 1
        try:
            return int(max_num) + 1
        except (ValueError, TypeError):
            return 1

    async def list_returns(
        self,
        business_id: str,
        status: Optional[SalesReturnStatus] = None,
        sales_id: Optional[str] = None,
        inventory_location_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[SalesReturnInDB], int]:
        filters = [SalesReturnModel.business_id == business_id]
        if status is not None:
            filters.append(SalesReturnModel.status == status.value)
        if sales_id is not None:
            filters.append(SalesReturnModel.sales_id == sales_id)
        if inventory_location_id is not None:
            filters.append(SalesReturnModel.inventory_location_id == inventory_location_id)
        if search:
            filters.append(SalesReturnModel.return_number.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(SalesReturnModel).where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(SalesReturnModel)
            .where(and_(*filters))
            .order_by(desc(SalesReturnModel.created_at), desc(SalesReturnModel.id))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        result = await self.session.execute(stmt)
        items = [_to_sales_return_in_db(o) for o in result.scalars().all()]
        return items, total

    async def update_return(
        self,
        return_id: str,
        business_id: str,
        notes: Optional[str] = None,
        status: Optional[SalesReturnStatus] = None,
        subtotal: Optional[Decimal] = None,
        discount_total: Optional[Decimal] = None,
        tax_total: Optional[Decimal] = None,
        grand_total: Optional[Decimal] = None,
        finalized_by_user_id: Optional[str] = None,
        finalized_at: Optional[datetime] = None,
        cancelled_by_user_id: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
    ) -> Optional[SalesReturnInDB]:
        stmt = select(SalesReturnModel).where(
            SalesReturnModel.id == return_id,
            SalesReturnModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        if notes is not None:
            obj.notes = notes
        if status is not None:
            obj.status = status.value
        if subtotal is not None:
            obj.subtotal = subtotal
        if discount_total is not None:
            obj.discount_total = discount_total
        if tax_total is not None:
            obj.tax_total = tax_total
        if grand_total is not None:
            obj.grand_total = grand_total
        if finalized_by_user_id is not None:
            obj.finalized_by_user_id = finalized_by_user_id
        if finalized_at is not None:
            obj.finalized_at = finalized_at
        if cancelled_by_user_id is not None:
            obj.cancelled_by_user_id = cancelled_by_user_id
        if cancelled_at is not None:
            obj.cancelled_at = cancelled_at
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_sales_return_in_db(obj)

    async def create_line(
        self,
        sales_return_id: str,
        sales_line_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        tax_amount: Decimal,
        line_subtotal: Decimal,
        line_total: Decimal,
        delivery_note_id: Optional[str] = None,
        delivery_note_line_id: Optional[str] = None,
    ) -> SalesReturnLineInDB:
        data = {
            "id": str(uuid.uuid4()),
            "sales_return_id": sales_return_id,
            "sales_line_id": sales_line_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "discount_amount": discount_amount,
            "tax_amount": tax_amount,
            "line_subtotal": line_subtotal,
            "line_total": line_total,
            "delivery_note_id": delivery_note_id,
            "delivery_note_line_id": delivery_note_line_id,
        }
        obj = await sa_create(self.session, SalesReturnLineModel, data)
        return _to_sales_return_line_in_db(obj)

    async def get_line_by_id(
        self, line_id: str, sales_return_id: str
    ) -> Optional[SalesReturnLineInDB]:
        stmt = select(SalesReturnLineModel).where(
            SalesReturnLineModel.id == line_id,
            SalesReturnLineModel.sales_return_id == sales_return_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_sales_return_line_in_db(obj) if obj else None

    async def list_lines_for_return(self, sales_return_id: str) -> List[SalesReturnLineInDB]:
        stmt = (
            select(SalesReturnLineModel)
            .where(SalesReturnLineModel.sales_return_id == sales_return_id)
            .order_by(SalesReturnLineModel.created_at, SalesReturnLineModel.id)
        )
        result = await self.session.execute(stmt)
        return [_to_sales_return_line_in_db(o) for o in result.scalars().all()]

    async def update_line(
        self,
        line_id: str,
        sales_return_id: str,
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        tax_amount: Decimal,
        line_subtotal: Decimal,
        line_total: Decimal,
        delivery_note_id: Optional[str] = None,
        delivery_note_line_id: Optional[str] = None,
    ) -> Optional[SalesReturnLineInDB]:
        stmt = select(SalesReturnLineModel).where(
            SalesReturnLineModel.id == line_id,
            SalesReturnLineModel.sales_return_id == sales_return_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.quantity = quantity
        obj.unit_price = unit_price
        obj.discount_amount = discount_amount
        obj.tax_amount = tax_amount
        obj.line_subtotal = line_subtotal
        obj.line_total = line_total
        if delivery_note_id is not None:
            obj.delivery_note_id = delivery_note_id
        if delivery_note_line_id is not None:
            obj.delivery_note_line_id = delivery_note_line_id
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_sales_return_line_in_db(obj)

    async def delete_line(self, line_id: str, sales_return_id: str) -> bool:
        stmt = select(SalesReturnLineModel).where(
            SalesReturnLineModel.id == line_id,
            SalesReturnLineModel.sales_return_id == sales_return_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True

    async def sum_returned_quantity_for_sales_line(
        self, sales_line_id: str
    ) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(SalesReturnLineModel.quantity), 0))
            .join(SalesReturnModel, SalesReturnLineModel.sales_return_id == SalesReturnModel.id)
            .where(
                SalesReturnLineModel.sales_line_id == sales_line_id,
                SalesReturnModel.status.in_(["DRAFT", "FINALIZED"]),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def sum_returned_quantity_for_delivery_note_line(
        self, delivery_note_line_id: str
    ) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(SalesReturnLineModel.quantity), 0))
            .join(SalesReturnModel, SalesReturnLineModel.sales_return_id == SalesReturnModel.id)
            .where(
                SalesReturnLineModel.delivery_note_line_id == delivery_note_line_id,
                SalesReturnModel.status.in_(["DRAFT", "FINALIZED"]),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def sum_unlinked_returned_quantity_for_sales_line(
        self, sales_line_id: str
    ) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(SalesReturnLineModel.quantity), 0))
            .join(SalesReturnModel, SalesReturnLineModel.sales_return_id == SalesReturnModel.id)
            .where(
                SalesReturnLineModel.sales_line_id == sales_line_id,
                SalesReturnLineModel.delivery_note_line_id.is_(None),
                SalesReturnModel.status.in_(["DRAFT", "FINALIZED"]),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    @classmethod
    def clear(cls):
        pass
