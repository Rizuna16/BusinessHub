from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal
import uuid
from abc import ABC, abstractmethod

from app.modules.sales.schemas import (
    SalesInDB,
    SalesLineInDB,
    SalesStatus,
)


class AbstractSalesRepository(ABC):
    @abstractmethod
    async def create_sales(
        self,
        business_id: str,
        customer_id: Optional[str],
        branch_id: str,
        sales_number: str,
        sales_date: datetime,
        created_by_user_id: str,
        notes: Optional[str] = None,
    ) -> SalesInDB:
        pass

    @abstractmethod
    async def get_sales_by_id(self, sales_id: str, business_id: str) -> Optional[SalesInDB]:
        pass

    @abstractmethod
    async def get_sales_for_update(self, sales_id: str, business_id: str) -> Optional[SalesInDB]:
        pass

    @abstractmethod
    async def get_sales_by_number(self, business_id: str, sales_number: str) -> Optional[SalesInDB]:
        pass

    @abstractmethod
    async def list_sales(
        self,
        business_id: str,
        status: Optional[SalesStatus] = None,
        customer_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[SalesInDB], int]:
        pass

    @abstractmethod
    async def update_sales(
        self,
        sales_id: str,
        business_id: str,
        customer_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        sales_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        status: Optional[SalesStatus] = None,
        subtotal: Optional[Decimal] = None,
        discount_total: Optional[Decimal] = None,
        tax_total: Optional[Decimal] = None,
        grand_total: Optional[Decimal] = None,
        finalized_by_user_id: Optional[str] = None,
        finalized_at: Optional[datetime] = None,
        cancelled_by_user_id: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
        is_deleted: Optional[bool] = None,
    ) -> Optional[SalesInDB]:
        pass

    @abstractmethod
    async def get_next_sales_sequence(self, business_id: str) -> int:
        pass

    @abstractmethod
    async def create_line(
        self,
        sales_id: str,
        product_id: str,
        variant_id: Optional[str],
        description: Optional[str],
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        tax_amount: Decimal,
        line_subtotal: Decimal,
        line_total: Decimal,
        discount_rule_id: Optional[str] = None,
        discount_rule_name_snapshot: Optional[str] = None,
    ) -> SalesLineInDB:
        pass

    @abstractmethod
    async def get_line_by_id(self, line_id: str, sales_id: str) -> Optional[SalesLineInDB]:
        pass

    @abstractmethod
    async def list_lines_for_sales(self, sales_id: str) -> List[SalesLineInDB]:
        pass

    @abstractmethod
    async def update_line(
        self,
        line_id: str,
        sales_id: str,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
        description: Optional[str] = None,
        quantity: Optional[Decimal] = None,
        unit_price: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        tax_amount: Optional[Decimal] = None,
        line_subtotal: Optional[Decimal] = None,
        line_total: Optional[Decimal] = None,
        discount_rule_id: Optional[str] = None,
        discount_rule_name_snapshot: Optional[str] = None,
    ) -> Optional[SalesLineInDB]:
        pass

    @abstractmethod
    async def delete_line(self, line_id: str, sales_id: str) -> bool:
        pass

    @abstractmethod
    async def update_line_snapshot(self, line_id: str, sales_id: str, snapshot: Any) -> Optional[SalesLineInDB]:
        pass

    @abstractmethod
    async def update_line_cost_snapshots(
        self,
        line_id: str,
        sales_id: str,
        unit_cost_snapshot: Decimal,
        cost_total_snapshot: Decimal,
    ) -> Optional[SalesLineInDB]:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemorySalesRepository(AbstractSalesRepository):
    _sales: Dict[str, SalesInDB] = {}
    _lines: Dict[str, SalesLineInDB] = {}
    _sequences: Dict[str, int] = {}

    async def get_next_sales_sequence(self, business_id: str) -> int:
        current = self._sequences.get(business_id, 0)
        current += 1
        self._sequences[business_id] = current
        return current

    async def create_sales(
        self,
        business_id: str,
        customer_id: Optional[str],
        branch_id: str,
        sales_number: str,
        sales_date: datetime,
        created_by_user_id: str,
        notes: Optional[str] = None,
    ) -> SalesInDB:
        sales_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        sales = SalesInDB(
            id=sales_id,
            business_id=business_id,
            customer_id=customer_id,
            branch_id=branch_id,
            sales_number=sales_number,
            sales_date=sales_date,
            notes=notes,
            status=SalesStatus.DRAFT,
            subtotal=Decimal("0"),
            discount_total=Decimal("0"),
            tax_total=Decimal("0"),
            grand_total=Decimal("0"),
            created_by_user_id=created_by_user_id,
            finalized_by_user_id=None,
            cancelled_by_user_id=None,
            created_at=now,
            updated_at=now,
            finalized_at=None,
            cancelled_at=None,
        )
        self._sales[sales_id] = sales
        return sales

    async def get_sales_by_id(self, sales_id: str, business_id: str) -> Optional[SalesInDB]:
        s = self._sales.get(sales_id)
        if not s or s.business_id != business_id or s.is_deleted:
            return None
        return s

    async def get_sales_for_update(self, sales_id: str, business_id: str) -> Optional[SalesInDB]:
        return await self.get_sales_by_id(sales_id, business_id)

    async def get_sales_by_number(self, business_id: str, sales_number: str) -> Optional[SalesInDB]:
        for s in self._sales.values():
            if s.business_id == business_id and s.sales_number == sales_number and not s.is_deleted:
                return s
        return None

    async def list_sales(
        self,
        business_id: str,
        status: Optional[SalesStatus] = None,
        customer_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[SalesInDB], int]:
        filtered = []
        for s in self._sales.values():
            if s.business_id != business_id or s.is_deleted:
                continue
            if status and s.status != status:
                continue
            if customer_id and s.customer_id != customer_id:
                continue
            if branch_id and s.branch_id != branch_id:
                continue
            if date_from and s.sales_date < date_from:
                continue
            if date_to and s.sales_date > date_to:
                continue
            if search:
                s_lower = search.lower()
                if s_lower not in s.sales_number.lower():
                    continue
            filtered.append(s)

        filtered.sort(key=lambda x: (x.sales_date, x.created_at, x.id), reverse=True)

        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = filtered[start:end]
        return paginated, total

    async def update_sales(
        self,
        sales_id: str,
        business_id: str,
        customer_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        sales_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        status: Optional[SalesStatus] = None,
        subtotal: Optional[Decimal] = None,
        discount_total: Optional[Decimal] = None,
        tax_total: Optional[Decimal] = None,
        grand_total: Optional[Decimal] = None,
        finalized_by_user_id: Optional[str] = None,
        finalized_at: Optional[datetime] = None,
        cancelled_by_user_id: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
        is_deleted: Optional[bool] = None,
    ) -> Optional[SalesInDB]:
        s = await self.get_sales_by_id(sales_id, business_id)
        if not s:
            return None

        update_data = s.model_dump()
        if customer_id is not None:
            update_data["customer_id"] = customer_id
        if branch_id is not None:
            update_data["branch_id"] = branch_id
        if sales_date is not None:
            update_data["sales_date"] = sales_date
        if notes is not None:
            update_data["notes"] = notes
        if status is not None:
            update_data["status"] = status
        if subtotal is not None:
            update_data["subtotal"] = subtotal
        if discount_total is not None:
            update_data["discount_total"] = discount_total
        if tax_total is not None:
            update_data["tax_total"] = tax_total
        if grand_total is not None:
            update_data["grand_total"] = grand_total
        if finalized_by_user_id is not None:
            update_data["finalized_by_user_id"] = finalized_by_user_id
        if finalized_at is not None:
            update_data["finalized_at"] = finalized_at
        if cancelled_by_user_id is not None:
            update_data["cancelled_by_user_id"] = cancelled_by_user_id
        if cancelled_at is not None:
            update_data["cancelled_at"] = cancelled_at
        if is_deleted is not None:
            update_data["is_deleted"] = is_deleted
        update_data["updated_at"] = datetime.now(timezone.utc)

        updated = SalesInDB(**update_data)
        self._sales[sales_id] = updated
        return updated

    async def create_line(
        self,
        sales_id: str,
        product_id: str,
        variant_id: Optional[str],
        description: Optional[str],
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        tax_amount: Decimal,
        line_subtotal: Decimal,
        line_total: Decimal,
        discount_rule_id: Optional[str] = None,
        discount_rule_name_snapshot: Optional[str] = None,
    ) -> SalesLineInDB:
        line_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        line = SalesLineInDB(
            id=line_id,
            sales_id=sales_id,
            product_id=product_id,
            variant_id=variant_id,
            description=description,
            quantity=quantity,
            unit_price=unit_price,
            discount_amount=discount_amount,
            discount_rule_id=discount_rule_id,
            discount_rule_name_snapshot=discount_rule_name_snapshot,
            tax_amount=tax_amount,
            line_subtotal=line_subtotal,
            line_total=line_total,
            created_at=now,
            updated_at=now,
        )
        self._lines[line_id] = line
        return line

    async def get_line_by_id(self, line_id: str, sales_id: str) -> Optional[SalesLineInDB]:
        l = self._lines.get(line_id)
        if not l or l.sales_id != sales_id:
            return None
        return l

    async def list_lines_for_sales(self, sales_id: str) -> List[SalesLineInDB]:
        lines = [l for l in self._lines.values() if l.sales_id == sales_id]
        lines.sort(key=lambda x: (x.created_at, x.id))
        return lines

    async def update_line(
        self,
        line_id: str,
        sales_id: str,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
        description: Optional[str] = None,
        quantity: Optional[Decimal] = None,
        unit_price: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        tax_amount: Optional[Decimal] = None,
        line_subtotal: Optional[Decimal] = None,
        line_total: Optional[Decimal] = None,
        discount_rule_id: Optional[str] = None,
        discount_rule_name_snapshot: Optional[str] = None,
    ) -> Optional[SalesLineInDB]:
        l = await self.get_line_by_id(line_id, sales_id)
        if not l:
            return None

        data = l.model_dump()
        if product_id is not None:
            data["product_id"] = product_id
        if variant_id is not None:
            data["variant_id"] = variant_id
        if description is not None:
            data["description"] = description
        if quantity is not None:
            data["quantity"] = quantity
        if unit_price is not None:
            data["unit_price"] = unit_price
        if discount_amount is not None:
            data["discount_amount"] = discount_amount
        if tax_amount is not None:
            data["tax_amount"] = tax_amount
        if line_subtotal is not None:
            data["line_subtotal"] = line_subtotal
        if line_total is not None:
            data["line_total"] = line_total
        if discount_rule_id is not None:
            data["discount_rule_id"] = discount_rule_id
        if discount_rule_name_snapshot is not None:
            data["discount_rule_name_snapshot"] = discount_rule_name_snapshot
        data["updated_at"] = datetime.now(timezone.utc)

        updated = SalesLineInDB(**data)
        self._lines[line_id] = updated
        return updated

    async def delete_line(self, line_id: str, sales_id: str) -> bool:
        l = await self.get_line_by_id(line_id, sales_id)
        if not l:
            return False
        del self._lines[line_id]
        return True

    async def update_line_snapshot(self, line_id: str, sales_id: str, snapshot: Any) -> Optional[SalesLineInDB]:
        l = await self.get_line_by_id(line_id, sales_id)
        if not l:
            return None
        data = l.model_dump()
        data["tax_snapshot"] = snapshot
        data["updated_at"] = datetime.now(timezone.utc)
        updated = SalesLineInDB(**data)
        self._lines[line_id] = updated
        return updated

    async def update_line_cost_snapshots(
        self,
        line_id: str,
        sales_id: str,
        unit_cost_snapshot: Decimal,
        cost_total_snapshot: Decimal,
    ) -> Optional[SalesLineInDB]:
        l = await self.get_line_by_id(line_id, sales_id)
        if not l:
            return None
        data = l.model_dump()
        data["unit_cost_snapshot"] = unit_cost_snapshot
        data["cost_total_snapshot"] = cost_total_snapshot
        data["updated_at"] = datetime.now(timezone.utc)
        updated = SalesLineInDB(**data)
        self._lines[line_id] = updated
        return updated

    @classmethod
    def clear(cls):
        cls._sales.clear()
        cls._lines.clear()
        cls._sequences.clear()


sales_repository = InMemorySalesRepository()
