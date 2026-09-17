from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import select, func, and_, desc, asc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.expense.models import ExpenseCategoryInDB as ExpenseCategoryModel, ExpenseInDB as ExpenseModel
from app.modules.expense.repository import AbstractExpenseRepository
from app.modules.expense.schemas import (
    ExpenseInDB,
    ExpenseCategoryInDB,
    ExpenseStatus,
    ExpenseCategoryStatus,
)
from app.modules.sqla_base import sa_create


def _to_category(obj: ExpenseCategoryModel) -> ExpenseCategoryInDB:
    return ExpenseCategoryInDB(
        id=obj.id,
        business_id=obj.business_id,
        name=obj.name,
        code=obj.code,
        description=obj.description,
        status=ExpenseCategoryStatus(obj.status),
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_expense(obj: ExpenseModel) -> ExpenseInDB:
    return ExpenseInDB(
        id=obj.id,
        business_id=obj.business_id,
        expense_number=obj.expense_number,
        expense_date=obj.expense_date,
        category_id=obj.category_id,
        cash_account_id=obj.cash_account_id,
        supplier_id=obj.supplier_id,
        amount=obj.amount,
        currency=obj.currency,
        description=obj.description,
        status=ExpenseStatus(obj.status),
        created_by_user_id=obj.created_by_user_id,
        finalized_by_user_id=obj.finalized_by_user_id,
        cancelled_by_user_id=obj.cancelled_by_user_id,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        finalized_at=obj.finalized_at,
        cancelled_at=obj.cancelled_at,
    )


class SQLAlchemyExpenseRepository(AbstractExpenseRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_category(
        self, business_id: str, name: str, code: str, description: Optional[str] = None
    ) -> ExpenseCategoryInDB:
        data = {
            "business_id": business_id,
            "name": name,
            "code": code.upper(),
            "description": description,
            "status": ExpenseCategoryStatus.ACTIVE.value,
        }
        obj = await sa_create(self.session, ExpenseCategoryModel, data)
        return _to_category(obj)

    async def get_category_by_id(
        self, category_id: str, business_id: str
    ) -> Optional[ExpenseCategoryInDB]:
        stmt = select(ExpenseCategoryModel).where(
            ExpenseCategoryModel.id == category_id,
            ExpenseCategoryModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_category(obj) if obj else None

    async def get_category_by_code(
        self, business_id: str, code: str
    ) -> Optional[ExpenseCategoryInDB]:
        code_upper = code.upper()
        stmt = select(ExpenseCategoryModel).where(
            ExpenseCategoryModel.business_id == business_id,
            func.upper(ExpenseCategoryModel.code) == code_upper,
            ExpenseCategoryModel.status == ExpenseCategoryStatus.ACTIVE.value,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_category(obj) if obj else None

    async def list_categories(
        self,
        business_id: str,
        status: Optional[ExpenseCategoryStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[ExpenseCategoryInDB], int]:
        filters = [ExpenseCategoryModel.business_id == business_id]
        if status:
            filters.append(ExpenseCategoryModel.status == status.value)
        if search:
            s_lower = search.lower()
            filters.append(
                or_(
                    func.lower(ExpenseCategoryModel.name).like(f"%{s_lower}%"),
                    func.lower(ExpenseCategoryModel.code).like(f"%{s_lower}%"),
                )
            )

        count_stmt = select(func.count()).select_from(ExpenseCategoryModel).where(and_(*filters))
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            select(ExpenseCategoryModel)
            .where(and_(*filters))
            .order_by(desc(ExpenseCategoryModel.created_at), desc(ExpenseCategoryModel.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        res = await self.session.execute(stmt)
        items = [_to_category(o) for o in res.scalars().all()]
        return items, total

    async def update_category(
        self,
        category_id: str,
        business_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[ExpenseCategoryStatus] = None,
    ) -> Optional[ExpenseCategoryInDB]:
        stmt = select(ExpenseCategoryModel).where(
            ExpenseCategoryModel.id == category_id,
            ExpenseCategoryModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        if name is not None:
            obj.name = name
        if description is not None:
            obj.description = description
        if status is not None:
            obj.status = status.value
        await self.session.flush()
        return _to_category(obj)

    async def create_expense(
        self,
        business_id: str,
        expense_number: str,
        expense_date: datetime,
        category_id: str,
        amount: Decimal,
        currency: str,
        created_by_user_id: str,
        cash_account_id: Optional[str] = None,
        supplier_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ExpenseInDB:
        data = {
            "business_id": business_id,
            "expense_number": expense_number,
            "expense_date": expense_date,
            "category_id": category_id,
            "cash_account_id": cash_account_id,
            "supplier_id": supplier_id,
            "amount": amount,
            "currency": currency,
            "description": description,
            "status": ExpenseStatus.DRAFT.value,
            "created_by_user_id": created_by_user_id,
        }
        obj = await sa_create(self.session, ExpenseModel, data)
        return _to_expense(obj)

    async def get_expense_by_id(
        self, expense_id: str, business_id: str
    ) -> Optional[ExpenseInDB]:
        stmt = select(ExpenseModel).where(
            ExpenseModel.id == expense_id,
            ExpenseModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_expense(obj) if obj else None

    async def list_expenses(
        self,
        business_id: str,
        category_id: Optional[str] = None,
        cash_account_id: Optional[str] = None,
        supplier_id: Optional[str] = None,
        status: Optional[ExpenseStatus] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[ExpenseInDB], int]:
        filters = [ExpenseModel.business_id == business_id]
        if category_id:
            filters.append(ExpenseModel.category_id == category_id)
        if cash_account_id:
            filters.append(ExpenseModel.cash_account_id == cash_account_id)
        if supplier_id:
            filters.append(ExpenseModel.supplier_id == supplier_id)
        if status:
            filters.append(ExpenseModel.status == status.value)
        if date_from:
            filters.append(ExpenseModel.expense_date >= date_from)
        if date_to:
            filters.append(ExpenseModel.expense_date <= date_to)
        if search:
            s_lower = search.lower()
            filters.append(
                or_(
                    func.lower(ExpenseModel.expense_number).like(f"%{s_lower}%"),
                    func.lower(ExpenseModel.description).like(f"%{s_lower}%"),
                )
            )

        count_stmt = select(func.count()).select_from(ExpenseModel).where(and_(*filters))
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            select(ExpenseModel)
            .where(and_(*filters))
            .order_by(desc(ExpenseModel.expense_date), desc(ExpenseModel.created_at), desc(ExpenseModel.id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        res = await self.session.execute(stmt)
        items = [_to_expense(o) for o in res.scalars().all()]
        return items, total

    async def update_expense(
        self,
        expense_id: str,
        business_id: str,
        category_id: Optional[str] = None,
        cash_account_id: Optional[str] = None,
        supplier_id: Optional[str] = None,
        expense_date: Optional[datetime] = None,
        amount: Optional[Decimal] = None,
        currency: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[ExpenseStatus] = None,
        finalized_by_user_id: Optional[str] = None,
        finalized_at: Optional[datetime] = None,
        cancelled_by_user_id: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
    ) -> Optional[ExpenseInDB]:
        stmt = select(ExpenseModel).where(
            ExpenseModel.id == expense_id,
            ExpenseModel.business_id == business_id,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        if category_id is not None:
            obj.category_id = category_id
        if cash_account_id is not None:
            obj.cash_account_id = cash_account_id
        if supplier_id is not None:
            obj.supplier_id = supplier_id
        if expense_date is not None:
            obj.expense_date = expense_date
        if amount is not None:
            obj.amount = amount
        if currency is not None:
            obj.currency = currency
        if description is not None:
            obj.description = description
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
        await self.session.flush()
        return _to_expense(obj)

    async def get_next_expense_sequence(self, business_id: str) -> int:
        stmt = select(func.count()).select_from(ExpenseModel).where(ExpenseModel.business_id == business_id)
        res = await self.session.execute(stmt)
        count = res.scalar_one() or 0
        return count + 1

    @classmethod
    def clear(cls):
        pass
