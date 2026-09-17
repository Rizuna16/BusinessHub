import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from decimal import Decimal

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sales_payment.models import SalesPaymentInDB as SalesPaymentModel
from app.modules.sales_payment.repository import AbstractSalesPaymentRepository
from app.modules.sales_payment.schemas import (
    SalesPaymentInDB as SalesPaymentSchema,
    PaymentMethod,
    PaymentStatus,
)
from app.modules.sqla_base import sa_create


def _to_sales_payment_in_db(obj: SalesPaymentModel) -> SalesPaymentSchema:
    return SalesPaymentSchema(
        id=obj.id,
        business_id=obj.business_id,
        sales_id=obj.sales_id,
        payment_number=obj.payment_number,
        payment_date=obj.payment_date,
        payment_method=PaymentMethod(obj.payment_method),
        amount=obj.amount,
        reference_number=obj.reference_number,
        notes=obj.notes,
        status=PaymentStatus(obj.status),
        created_by_user_id=obj.created_by_user_id,
        cancelled_by_user_id=obj.cancelled_by_user_id,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        cancelled_at=obj.cancelled_at,
    )


class SQLAlchemySalesPaymentRepository(AbstractSalesPaymentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_payment(
        self,
        business_id: str,
        sales_id: str,
        payment_number: str,
        payment_date: datetime,
        payment_method: PaymentMethod,
        amount: Decimal,
        created_by_user_id: str,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> SalesPaymentSchema:
        data = {
            "id": str(uuid.uuid4()),
            "business_id": business_id,
            "sales_id": sales_id,
            "payment_number": payment_number,
            "payment_date": payment_date,
            "payment_method": payment_method.value,
            "amount": amount,
            "reference_number": reference_number,
            "notes": notes,
            "status": PaymentStatus.RECORDED.value,
            "created_by_user_id": created_by_user_id,
        }
        obj = await sa_create(self.session, SalesPaymentModel, data)
        return _to_sales_payment_in_db(obj)

    async def get_payment_by_id(self, payment_id: str, business_id: str) -> Optional[SalesPaymentSchema]:
        stmt = select(SalesPaymentModel).where(
            SalesPaymentModel.id == payment_id,
            SalesPaymentModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_sales_payment_in_db(obj) if obj else None

    async def list_payments_for_sales(
        self,
        business_id: str,
        sales_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[SalesPaymentSchema], int]:
        filters = [
            SalesPaymentModel.business_id == business_id,
            SalesPaymentModel.sales_id == sales_id,
        ]
        count_stmt = select(func.count()).select_from(SalesPaymentModel).where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(SalesPaymentModel)
            .where(and_(*filters))
            .order_by(desc(SalesPaymentModel.payment_date), desc(SalesPaymentModel.created_at), desc(SalesPaymentModel.id))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        result = await self.session.execute(stmt)
        items = [_to_sales_payment_in_db(o) for o in result.scalars().all()]
        return items, total

    async def get_active_payments_total(self, business_id: str, sales_id: str) -> Decimal:
        stmt = select(func.coalesce(func.sum(SalesPaymentModel.amount), 0)).where(
            SalesPaymentModel.business_id == business_id,
            SalesPaymentModel.sales_id == sales_id,
            SalesPaymentModel.status == PaymentStatus.RECORDED.value,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def cancel_payment(
        self,
        payment_id: str,
        business_id: str,
        cancelled_by_user_id: str,
        cancelled_at: datetime,
    ) -> Optional[SalesPaymentSchema]:
        stmt = select(SalesPaymentModel).where(
            SalesPaymentModel.id == payment_id,
            SalesPaymentModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        obj.status = PaymentStatus.CANCELLED.value
        obj.cancelled_by_user_id = cancelled_by_user_id
        obj.cancelled_at = cancelled_at
        obj.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return _to_sales_payment_in_db(obj)

    async def get_next_payment_sequence(self, business_id: str) -> int:
        from sqlalchemy import Integer
        stmt = select(func.max(func.cast(SalesPaymentModel.payment_number, Integer))).where(
            SalesPaymentModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        max_num = result.scalar_one()
        if max_num is None:
            return 1
        try:
            return int(max_num) + 1
        except (ValueError, TypeError):
            return 1

    @classmethod
    def clear(cls):
        pass
