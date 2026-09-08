from datetime import datetime, timezone
from typing import Dict, List, Optional
from decimal import Decimal
import uuid
from abc import ABC, abstractmethod

from app.modules.expense.schemas import (
    ExpenseInDB,
    ExpenseCategoryInDB,
    ExpenseStatus,
    ExpenseCategoryStatus,
)


class AbstractExpenseRepository(ABC):
    @abstractmethod
    async def create_category(
        self, business_id: str, name: str, code: str, description: Optional[str] = None
    ) -> ExpenseCategoryInDB:
        pass

    @abstractmethod
    async def get_category_by_id(
        self, category_id: str, business_id: str
    ) -> Optional[ExpenseCategoryInDB]:
        pass

    @abstractmethod
    async def get_category_by_code(
        self, business_id: str, code: str
    ) -> Optional[ExpenseCategoryInDB]:
        pass

    @abstractmethod
    async def list_categories(
        self,
        business_id: str,
        status: Optional[ExpenseCategoryStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[ExpenseCategoryInDB], int]:
        pass

    @abstractmethod
    async def update_category(
        self,
        category_id: str,
        business_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[ExpenseCategoryStatus] = None,
    ) -> Optional[ExpenseCategoryInDB]:
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def get_expense_by_id(
        self, expense_id: str, business_id: str
    ) -> Optional[ExpenseInDB]:
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def get_next_expense_sequence(self, business_id: str) -> int:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryExpenseRepository(AbstractExpenseRepository):
    _categories: Dict[str, ExpenseCategoryInDB] = {}
    _expenses: Dict[str, ExpenseInDB] = {}
    _sequences: Dict[str, int] = {}

    async def get_next_expense_sequence(self, business_id: str) -> int:
        current = self._sequences.get(business_id, 0)
        current += 1
        self._sequences[business_id] = current
        return current

    async def create_category(
        self, business_id: str, name: str, code: str, description: Optional[str] = None
    ) -> ExpenseCategoryInDB:
        cat_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        cat = ExpenseCategoryInDB(
            id=cat_id,
            business_id=business_id,
            name=name,
            code=code.upper(),
            description=description,
            status=ExpenseCategoryStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self._categories[cat_id] = cat
        return cat

    async def get_category_by_id(
        self, category_id: str, business_id: str
    ) -> Optional[ExpenseCategoryInDB]:
        c = self._categories.get(category_id)
        if not c or c.business_id != business_id:
            return None
        return c

    async def get_category_by_code(
        self, business_id: str, code: str
    ) -> Optional[ExpenseCategoryInDB]:
        code_upper = code.upper()
        for c in self._categories.values():
            if c.business_id == business_id and c.code == code_upper and c.status == ExpenseCategoryStatus.ACTIVE:
                return c
        return None

    async def list_categories(
        self,
        business_id: str,
        status: Optional[ExpenseCategoryStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[ExpenseCategoryInDB], int]:
        filtered = []
        for c in self._categories.values():
            if c.business_id != business_id:
                continue
            if status and c.status != status:
                continue
            if search:
                s_lower = search.lower()
                if s_lower not in c.name.lower() and s_lower not in c.code.lower():
                    continue
            filtered.append(c)

        filtered.sort(key=lambda x: (x.created_at, x.id), reverse=True)
        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        return filtered[start:end], total

    async def update_category(
        self,
        category_id: str,
        business_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[ExpenseCategoryStatus] = None,
    ) -> Optional[ExpenseCategoryInDB]:
        c = await self.get_category_by_id(category_id, business_id)
        if not c:
            return None

        data = c.model_dump()
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if status is not None:
            data["status"] = status
        data["updated_at"] = datetime.now(timezone.utc)

        updated = ExpenseCategoryInDB(**data)
        self._categories[category_id] = updated
        return updated

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
        exp_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        exp = ExpenseInDB(
            id=exp_id,
            business_id=business_id,
            expense_number=expense_number,
            expense_date=expense_date,
            category_id=category_id,
            cash_account_id=cash_account_id,
            supplier_id=supplier_id,
            amount=amount,
            currency=currency,
            description=description,
            status=ExpenseStatus.DRAFT,
            created_by_user_id=created_by_user_id,
            created_at=now,
            updated_at=now,
        )
        self._expenses[exp_id] = exp
        return exp

    async def get_expense_by_id(
        self, expense_id: str, business_id: str
    ) -> Optional[ExpenseInDB]:
        e = self._expenses.get(expense_id)
        if not e or e.business_id != business_id:
            return None
        return e

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
        filtered = []
        for e in self._expenses.values():
            if e.business_id != business_id:
                continue
            if category_id and e.category_id != category_id:
                continue
            if cash_account_id and e.cash_account_id != cash_account_id:
                continue
            if supplier_id and e.supplier_id != supplier_id:
                continue
            if status and e.status != status:
                continue
            if date_from and e.expense_date < date_from:
                continue
            if date_to and e.expense_date > date_to:
                continue
            if search:
                s_lower = search.lower()
                if s_lower not in e.expense_number.lower() and (not e.description or s_lower not in e.description.lower()):
                    continue
            filtered.append(e)

        filtered.sort(key=lambda x: (x.expense_date, x.created_at, x.id), reverse=True)
        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        return filtered[start:end], total

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
        e = await self.get_expense_by_id(expense_id, business_id)
        if not e:
            return None

        data = e.model_dump()
        if category_id is not None:
            data["category_id"] = category_id
        if cash_account_id is not None:
            data["cash_account_id"] = cash_account_id
        if supplier_id is not None:
            data["supplier_id"] = supplier_id
        if expense_date is not None:
            data["expense_date"] = expense_date
        if amount is not None:
            data["amount"] = amount
        if currency is not None:
            data["currency"] = currency
        if description is not None:
            data["description"] = description
        if status is not None:
            data["status"] = status
        if finalized_by_user_id is not None:
            data["finalized_by_user_id"] = finalized_by_user_id
        if finalized_at is not None:
            data["finalized_at"] = finalized_at
        if cancelled_by_user_id is not None:
            data["cancelled_by_user_id"] = cancelled_by_user_id
        if cancelled_at is not None:
            data["cancelled_at"] = cancelled_at

        data["updated_at"] = datetime.now(timezone.utc)
        updated = ExpenseInDB(**data)
        self._expenses[expense_id] = updated
        return updated

    @classmethod
    def clear(cls):
        cls._categories.clear()
        cls._expenses.clear()
        cls._sequences.clear()


expense_repository = InMemoryExpenseRepository()
