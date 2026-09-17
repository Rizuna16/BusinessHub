from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cashier_shift.models import CashierShiftInDB as CashierShiftModel
from app.modules.cashier_shift.repository import AbstractCashierShiftRepository
from app.modules.cashier_shift.schemas import (
    CashierShiftInDB,
    ShiftStatus,
)
from app.modules.sqla_base import sa_create


def _to_shift(obj: CashierShiftModel) -> CashierShiftInDB:
    return CashierShiftInDB(
        id=obj.id,
        business_id=obj.business_id,
        branch_id=obj.branch_id,
        cashier_user_id=obj.cashier_user_id,
        cash_account_id=obj.cash_account_id,
        opening_balance=obj.opening_balance,
        actual_cash_count=obj.actual_cash_count,
        discrepancy=obj.discrepancy,
        status=ShiftStatus(obj.status),
        opened_at=obj.opened_at,
        closed_at=obj.closed_at,
        closed_by_user_id=obj.closed_by_user_id,
        notes=obj.notes,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyCashierShiftRepository(AbstractCashierShiftRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_shift(
        self,
        business_id: str,
        branch_id: str,
        cashier_user_id: str,
        cash_account_id: str,
        opening_balance: Decimal,
        notes: Optional[str] = None,
    ) -> CashierShiftInDB:
        now = datetime.now(timezone.utc)
        data = {
            "business_id": business_id,
            "branch_id": branch_id,
            "cashier_user_id": cashier_user_id,
            "cash_account_id": cash_account_id,
            "opening_balance": opening_balance,
            "status": ShiftStatus.OPEN.value,
            "opened_at": now,
            "notes": notes,
        }
        obj = await sa_create(self.session, CashierShiftModel, data)
        return _to_shift(obj)

    async def get_shift_by_id(self, shift_id: str, business_id: str) -> Optional[CashierShiftInDB]:
        stmt = select(CashierShiftModel).where(
            CashierShiftModel.id == shift_id,
            CashierShiftModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_shift(obj) if obj else None

    async def get_open_shift(
        self, business_id: str, cash_account_id: str
    ) -> Optional[CashierShiftInDB]:
        stmt = select(CashierShiftModel).where(
            CashierShiftModel.business_id == business_id,
            CashierShiftModel.cash_account_id == cash_account_id,
            CashierShiftModel.status == ShiftStatus.OPEN.value,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_shift(obj) if obj else None

    async def list_shifts(
        self,
        business_id: str,
        status_filter: Optional[ShiftStatus] = None,
        branch_id: Optional[str] = None,
        cashier_user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[CashierShiftInDB], int]:
        filters = [CashierShiftModel.business_id == business_id]
        if status_filter:
            filters.append(CashierShiftModel.status == status_filter.value)
        if branch_id:
            filters.append(CashierShiftModel.branch_id == branch_id)
        if cashier_user_id:
            filters.append(CashierShiftModel.cashier_user_id == cashier_user_id)

        count_stmt = select(func.count()).select_from(CashierShiftModel).where(and_(*filters))
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            select(CashierShiftModel)
            .where(and_(*filters))
            .order_by(desc(CashierShiftModel.opened_at), desc(CashierShiftModel.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        res = await self.session.execute(stmt)
        items = [_to_shift(o) for o in res.scalars().all()]
        return items, total

    async def update_shift(
        self,
        shift_id: str,
        business_id: str,
        **kwargs,
    ) -> Optional[CashierShiftInDB]:
        stmt = select(CashierShiftModel).where(
            CashierShiftModel.id == shift_id,
            CashierShiftModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        for key, value in kwargs.items():
            if key == "status" and value is not None:
                setattr(obj, key, value.value if hasattr(value, "value") else value)
            elif hasattr(obj, key):
                setattr(obj, key, value)
        await self.session.flush()
        return _to_shift(obj)

    @classmethod
    def clear(cls):
        pass
