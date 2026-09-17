from datetime import datetime, timezone
from typing import Dict, List, Optional
from decimal import Decimal
import uuid
from abc import ABC, abstractmethod

from app.modules.sales_return.schemas import (
    SalesReturnInDB,
    SalesReturnLineInDB,
    SalesReturnStatus,
)


class AbstractSalesReturnRepository(ABC):
    @abstractmethod
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
        pass

    @abstractmethod
    async def get_return_by_id(
        self, return_id: str, business_id: str
    ) -> Optional[SalesReturnInDB]:
        pass

    @abstractmethod
    async def get_next_return_sequence(self, business_id: str) -> int:
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def get_line_by_id(
        self, line_id: str, sales_return_id: str
    ) -> Optional[SalesReturnLineInDB]:
        pass

    @abstractmethod
    async def list_lines_for_return(self, sales_return_id: str) -> List[SalesReturnLineInDB]:
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def delete_line(self, line_id: str, sales_return_id: str) -> bool:
        pass

    @abstractmethod
    async def sum_returned_quantity_for_sales_line(
        self, sales_line_id: str
    ) -> Decimal:
        pass

    @abstractmethod
    async def sum_returned_quantity_for_delivery_note_line(
        self, delivery_note_line_id: str
    ) -> Decimal:
        pass

    @abstractmethod
    async def sum_unlinked_returned_quantity_for_sales_line(
        self, sales_line_id: str
    ) -> Decimal:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemorySalesReturnRepository(AbstractSalesReturnRepository):
    _returns: Dict[str, SalesReturnInDB] = {}
    _lines: Dict[str, SalesReturnLineInDB] = {}
    _sequences: Dict[str, int] = {}

    async def get_next_return_sequence(self, business_id: str) -> int:
        current = self._sequences.get(business_id, 0)
        current += 1
        self._sequences[business_id] = current
        return current

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
        return_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        ret = SalesReturnInDB(
            id=return_id,
            business_id=business_id,
            sales_id=sales_id,
            inventory_location_id=inventory_location_id,
            return_number=return_number,
            return_date=return_date,
            status=SalesReturnStatus.DRAFT,
            refund_destination=refund_destination,
            notes=notes,
            subtotal=Decimal("0"),
            discount_total=Decimal("0"),
            tax_total=Decimal("0"),
            grand_total=Decimal("0"),
            created_by_user_id=created_by_user_id,
            created_at=now,
            updated_at=now,
        )
        self._returns[return_id] = ret
        return ret

    async def get_return_by_id(
        self, return_id: str, business_id: str
    ) -> Optional[SalesReturnInDB]:
        r = self._returns.get(return_id)
        if not r or r.business_id != business_id:
            return None
        return r

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
        filtered = []
        for r in self._returns.values():
            if r.business_id != business_id:
                continue
            if status and r.status != status:
                continue
            if sales_id and r.sales_id != sales_id:
                continue
            if inventory_location_id and r.inventory_location_id != inventory_location_id:
                continue
            if search:
                s_lower = search.lower()
                if s_lower not in r.return_number.lower():
                    continue
            filtered.append(r)

        filtered.sort(key=lambda x: (x.created_at, x.id), reverse=True)
        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        return filtered[start:end], total

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
        r = await self.get_return_by_id(return_id, business_id)
        if not r:
            return None

        data = r.model_dump()
        if notes is not None:
            data["notes"] = notes
        if status is not None:
            data["status"] = status
        if subtotal is not None:
            data["subtotal"] = subtotal
        if discount_total is not None:
            data["discount_total"] = discount_total
        if tax_total is not None:
            data["tax_total"] = tax_total
        if grand_total is not None:
            data["grand_total"] = grand_total
        if finalized_by_user_id is not None:
            data["finalized_by_user_id"] = finalized_by_user_id
        if finalized_at is not None:
            data["finalized_at"] = finalized_at
        if cancelled_by_user_id is not None:
            data["cancelled_by_user_id"] = cancelled_by_user_id
        if cancelled_at is not None:
            data["cancelled_at"] = cancelled_at

        data["updated_at"] = datetime.now(timezone.utc)
        updated = SalesReturnInDB(**data)
        self._returns[return_id] = updated
        return updated

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
        line_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        line = SalesReturnLineInDB(
            id=line_id,
            sales_return_id=sales_return_id,
            sales_line_id=sales_line_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
            unit_price=unit_price,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            line_subtotal=line_subtotal,
            line_total=line_total,
            delivery_note_id=delivery_note_id,
            delivery_note_line_id=delivery_note_line_id,
            created_at=now,
            updated_at=now,
        )
        self._lines[line_id] = line
        return line

    async def get_line_by_id(
        self, line_id: str, sales_return_id: str
    ) -> Optional[SalesReturnLineInDB]:
        l = self._lines.get(line_id)
        if not l or l.sales_return_id != sales_return_id:
            return None
        return l

    async def list_lines_for_return(self, sales_return_id: str) -> List[SalesReturnLineInDB]:
        lines = [l for l in self._lines.values() if l.sales_return_id == sales_return_id]
        lines.sort(key=lambda x: (x.created_at, x.id))
        return lines

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
        l = await self.get_line_by_id(line_id, sales_return_id)
        if not l:
            return None

        data = l.model_dump()
        data["quantity"] = quantity
        data["unit_price"] = unit_price
        data["discount_amount"] = discount_amount
        data["tax_amount"] = tax_amount
        data["line_subtotal"] = line_subtotal
        data["line_total"] = line_total
        if delivery_note_id is not None:
            data["delivery_note_id"] = delivery_note_id
        if delivery_note_line_id is not None:
            data["delivery_note_line_id"] = delivery_note_line_id
        data["updated_at"] = datetime.now(timezone.utc)

        updated = SalesReturnLineInDB(**data)
        self._lines[line_id] = updated
        return updated

    async def delete_line(self, line_id: str, sales_return_id: str) -> bool:
        l = await self.get_line_by_id(line_id, sales_return_id)
        if not l:
            return False
        del self._lines[line_id]
        return True

    async def sum_returned_quantity_for_sales_line(
        self, sales_line_id: str
    ) -> Decimal:
        total = Decimal("0")
        for l in self._lines.values():
            if l.sales_line_id != sales_line_id:
                continue
            r = self._returns.get(l.sales_return_id)
            if not r:
                continue
            if r.status in (SalesReturnStatus.DRAFT, SalesReturnStatus.FINALIZED):
                total += l.quantity
        return total

    async def sum_returned_quantity_for_delivery_note_line(
        self, delivery_note_line_id: str
    ) -> Decimal:
        total = Decimal("0")
        for l in self._lines.values():
            if l.delivery_note_line_id != delivery_note_line_id:
                continue
            r = self._returns.get(l.sales_return_id)
            if not r:
                continue
            if r.status in (SalesReturnStatus.DRAFT, SalesReturnStatus.FINALIZED):
                total += l.quantity
        return total

    async def sum_unlinked_returned_quantity_for_sales_line(
        self, sales_line_id: str
    ) -> Decimal:
        total = Decimal("0")
        for l in self._lines.values():
            if l.sales_line_id != sales_line_id:
                continue
            if l.delivery_note_line_id is not None:
                continue
            r = self._returns.get(l.sales_return_id)
            if not r:
                continue
            if r.status in (SalesReturnStatus.DRAFT, SalesReturnStatus.FINALIZED):
                total += l.quantity
        return total

    @classmethod
    def clear(cls):
        cls._returns.clear()
        cls._lines.clear()
        cls._sequences.clear()


sales_return_repository = InMemorySalesReturnRepository()
