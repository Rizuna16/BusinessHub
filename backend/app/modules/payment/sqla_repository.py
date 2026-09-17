import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from decimal import Decimal

from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.payment.models import PaymentInDB as PaymentModel
from app.modules.payment.repository import AbstractPaymentRepository
from app.modules.payment.schemas import (
    PaymentInDB as PaymentSchema,
    PaymentDirection,
    PaymentTargetType,
    PaymentMethod,
    PaymentStatus,
)
from app.modules.sqla_base import sa_create


def _to_payment_in_db(obj: PaymentModel) -> PaymentSchema:
    return PaymentSchema(
        id=obj.id,
        business_id=obj.business_id,
        branch_id=obj.branch_id,
        direction=PaymentDirection(obj.direction),
        target_type=PaymentTargetType(obj.target_type),
        target_id=obj.target_id,
        payment_number=obj.payment_number,
        payment_date=obj.payment_date,
        payment_method=PaymentMethod(obj.payment_method),
        amount=obj.amount,
        currency=obj.currency,
        cash_account_id=obj.cash_account_id,
        reference_number=obj.reference_number,
        notes=obj.notes,
        status=PaymentStatus(obj.status),
        created_by_user_id=obj.created_by_user_id,
        voided_by_user_id=obj.voided_by_user_id,
        idempotency_key=obj.idempotency_key,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        voided_at=obj.voided_at,
    )


class SQLAlchemyPaymentRepository(AbstractPaymentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_payment(self, payment_data: dict) -> PaymentSchema:
        data = dict(payment_data)
        if "id" not in data or not data["id"]:
            data["id"] = str(uuid.uuid4())
        # ensure enums are serialized to values if present
        for k in ["direction", "target_type", "payment_method", "status"]:
            if k in data and hasattr(data[k], "value"):
                data[k] = data[k].value
        obj = await sa_create(self.session, PaymentModel, data)
        return _to_payment_in_db(obj)

    async def get_payment_by_id(self, payment_id: str, business_id: str) -> Optional[PaymentSchema]:
        stmt = select(PaymentModel).where(
            PaymentModel.id == payment_id,
            PaymentModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_payment_in_db(obj) if obj else None

    async def get_payment_by_idempotency_key(self, idempotency_key: str, business_id: str) -> Optional[PaymentSchema]:
        stmt = select(PaymentModel).where(
            PaymentModel.business_id == business_id,
            PaymentModel.idempotency_key == idempotency_key,
            PaymentModel.status == PaymentStatus.RECORDED.value,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        return _to_payment_in_db(obj) if obj else None

    async def list_payments(
        self,
        business_id: str,
        direction: Optional[PaymentDirection] = None,
        target_type: Optional[PaymentTargetType] = None,
        target_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[PaymentSchema], int]:
        filters = [PaymentModel.business_id == business_id]
        if direction is not None:
            filters.append(PaymentModel.direction == direction.value)
        if target_type is not None:
            filters.append(PaymentModel.target_type == target_type.value)
        if target_id is not None:
            filters.append(PaymentModel.target_id == target_id)

        count_stmt = select(func.count()).select_from(PaymentModel).where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(PaymentModel)
            .where(and_(*filters))
            .order_by(desc(PaymentModel.payment_date), desc(PaymentModel.created_at), desc(PaymentModel.id))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        result = await self.session.execute(stmt)
        items = [_to_payment_in_db(o) for o in result.scalars().all()]
        return items, total

    async def get_active_payments_total_for_target(self, business_id: str, target_type: PaymentTargetType, target_id: str) -> Decimal:
        stmt = select(func.coalesce(func.sum(PaymentModel.amount), 0)).where(
            PaymentModel.business_id == business_id,
            PaymentModel.target_type == (target_type.value if hasattr(target_type, "value") else target_type),
            PaymentModel.target_id == target_id,
            PaymentModel.status == PaymentStatus.RECORDED.value,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def void_payment(self, payment_id: str, business_id: str, voided_by_user_id: str) -> Optional[PaymentSchema]:
        stmt = select(PaymentModel).where(
            PaymentModel.id == payment_id,
            PaymentModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        now = datetime.now(timezone.utc)
        obj.status = PaymentStatus.VOIDED.value
        obj.voided_by_user_id = voided_by_user_id
        obj.voided_at = now
        obj.updated_at = now
        await self.session.flush()
        return _to_payment_in_db(obj)

    async def delete_payment(self, payment_id: str, business_id: str) -> bool:
        stmt = select(PaymentModel).where(
            PaymentModel.id == payment_id,
            PaymentModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True

    async def reset_to_recorded(self, payment_id: str, business_id: str) -> Optional[PaymentSchema]:
        stmt = select(PaymentModel).where(
            PaymentModel.id == payment_id,
            PaymentModel.business_id == business_id,
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if not obj:
            return None
        now = datetime.now(timezone.utc)
        obj.status = PaymentStatus.RECORDED.value
        obj.voided_by_user_id = None
        obj.voided_at = None
        obj.updated_at = now
        await self.session.flush()
        return _to_payment_in_db(obj)

    async def get_next_payment_sequence(self, business_id: str) -> int:
        from sqlalchemy import Integer
        stmt = select(func.max(func.cast(PaymentModel.payment_number, Integer))).where(
            PaymentModel.business_id == business_id,
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
