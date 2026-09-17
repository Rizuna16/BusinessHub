from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.customer_credit.models import StoreCreditLedgerEntry as LedgerEntryModel
from app.modules.customer_credit.repository import AbstractStoreCreditLedgerRepository
from app.modules.customer_credit.schemas import StoreCreditLedgerEntry
from app.modules.sqla_base import sa_create


def _to_entry(obj: LedgerEntryModel) -> StoreCreditLedgerEntry:
    return StoreCreditLedgerEntry(
        id=obj.id,
        customer_id=obj.customer_id,
        business_id=obj.business_id,
        amount=obj.amount,
        balance_after=obj.balance_after,
        direction=obj.direction,
        reference_type=obj.reference_type,
        reference_id=obj.reference_id,
        reason=obj.reason,
        created_by_user_id=obj.created_by_user_id,
        created_at=obj.created_at,
    )


class SQLAlchemyStoreCreditLedgerRepository(AbstractStoreCreditLedgerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(
        self,
        customer_id: str,
        business_id: str,
        amount: Decimal,
        balance_after: Decimal,
        direction: str,
        reference_type: Optional[str],
        reference_id: Optional[str],
        reason: Optional[str],
        created_by_user_id: str,
    ) -> StoreCreditLedgerEntry:
        data = {
            "customer_id": customer_id,
            "business_id": business_id,
            "amount": amount,
            "balance_after": balance_after,
            "direction": direction,
            "reference_type": reference_type,
            "reference_id": reference_id,
            "reason": reason,
            "created_by_user_id": created_by_user_id,
        }
        obj = await sa_create(self.session, LedgerEntryModel, data)
        return _to_entry(obj)

    async def list_by_customer(
        self,
        customer_id: str,
        business_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[StoreCreditLedgerEntry], int]:
        filters = [
            LedgerEntryModel.customer_id == customer_id,
            LedgerEntryModel.business_id == business_id,
        ]

        count_stmt = select(func.count()).select_from(LedgerEntryModel).where(and_(*filters))
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            select(LedgerEntryModel)
            .where(and_(*filters))
            .order_by(asc(LedgerEntryModel.created_at), asc(LedgerEntryModel.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        res = await self.session.execute(stmt)
        items = [_to_entry(o) for o in res.scalars().all()]
        return items, total

    async def sum_issued_not_voided(
        self, customer_id: str, business_id: str
    ) -> Decimal:
        stmt = select(func.coalesce(func.sum(LedgerEntryModel.amount), 0)).where(
            LedgerEntryModel.customer_id == customer_id,
            LedgerEntryModel.business_id == business_id,
            LedgerEntryModel.direction == "ISSUED",
        )
        res = await self.session.execute(stmt)
        return res.scalar_one() or Decimal("0")

    async def sum_redeemed_not_voided(
        self, customer_id: str, business_id: str
    ) -> Decimal:
        stmt = select(func.coalesce(func.sum(LedgerEntryModel.amount), 0)).where(
            LedgerEntryModel.customer_id == customer_id,
            LedgerEntryModel.business_id == business_id,
            LedgerEntryModel.direction == "REDEEMED",
        )
        res = await self.session.execute(stmt)
        return res.scalar_one() or Decimal("0")

    @classmethod
    def clear(cls):
        pass
