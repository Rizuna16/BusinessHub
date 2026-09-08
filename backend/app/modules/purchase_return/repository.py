from datetime import datetime, timezone
from typing import Dict, List, Optional
from decimal import Decimal
import uuid
from abc import ABC, abstractmethod

from app.modules.purchase_return.schemas import (
    PurchaseReturnInDB,
    PurchaseReturnLineInDB,
    PurchaseReturnStatus,
)


class AbstractPurchaseReturnRepository(ABC):
    @abstractmethod
    async def create_return(
        self,
        business_id: str,
        purchase_id: str,
        inventory_location_id: str,
        return_number: str,
        created_by_user_id: str,
        notes: Optional[str] = None,
    ) -> PurchaseReturnInDB:
        pass

    @abstractmethod
    async def get_return_by_id(
        self, return_id: str, business_id: str
    ) -> Optional[PurchaseReturnInDB]:
        pass

    @abstractmethod
    async def get_next_return_sequence(self, business_id: str) -> int:
        pass

    @abstractmethod
    async def list_returns(
        self,
        business_id: str,
        status: Optional[PurchaseReturnStatus] = None,
        purchase_id: Optional[str] = None,
        inventory_location_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[PurchaseReturnInDB], int]:
        pass

    @abstractmethod
    async def update_return(
        self,
        return_id: str,
        business_id: str,
        notes: Optional[str] = None,
        status: Optional[PurchaseReturnStatus] = None,
        subtotal: Optional[Decimal] = None,
        discount_total: Optional[Decimal] = None,
        tax_total: Optional[Decimal] = None,
        grand_total: Optional[Decimal] = None,
        finalized_by_user_id: Optional[str] = None,
        finalized_at: Optional[datetime] = None,
        cancelled_by_user_id: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
        is_deleted: Optional[bool] = None,
    ) -> Optional[PurchaseReturnInDB]:
        pass

    @abstractmethod
    async def create_line(
        self,
        return_id: str,
        purchase_line_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        tax_amount: Decimal,
        line_subtotal: Decimal,
        line_total: Decimal,
    ) -> PurchaseReturnLineInDB:
        pass

    @abstractmethod
    async def get_line_by_id(
        self, line_id: str, return_id: str
    ) -> Optional[PurchaseReturnLineInDB]:
        pass

    @abstractmethod
    async def list_lines_for_return(self, return_id: str) -> List[PurchaseReturnLineInDB]:
        pass

    @abstractmethod
    async def update_line(
        self,
        line_id: str,
        return_id: str,
        quantity: Optional[Decimal] = None,
        unit_price: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        tax_amount: Optional[Decimal] = None,
        line_subtotal: Optional[Decimal] = None,
        line_total: Optional[Decimal] = None,
    ) -> Optional[PurchaseReturnLineInDB]:
        pass

    @abstractmethod
    async def delete_line(self, line_id: str, return_id: str) -> bool:
        pass

    @abstractmethod
    async def sum_returned_quantity_for_purchase_line(
        self, purchase_line_id: str
    ) -> Decimal:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryPurchaseReturnRepository(AbstractPurchaseReturnRepository):
    _returns: Dict[str, PurchaseReturnInDB] = {}
    _lines: Dict[str, PurchaseReturnLineInDB] = {}
    _sequences: Dict[str, int] = {}

    async def get_next_return_sequence(self, business_id: str) -> int:
        current = self._sequences.get(business_id, 0)
        current += 1
        self._sequences[business_id] = current
        return current

    async def create_return(
        self,
        business_id: str,
        purchase_id: str,
        inventory_location_id: str,
        return_number: str,
        created_by_user_id: str,
        notes: Optional[str] = None,
    ) -> PurchaseReturnInDB:
        return_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        ret = PurchaseReturnInDB(
            id=return_id,
            business_id=business_id,
            purchase_id=purchase_id,
            inventory_location_id=inventory_location_id,
            return_number=return_number,
            status=PurchaseReturnStatus.DRAFT,
            notes=notes,
            subtotal=Decimal("0"),
            discount_total=Decimal("0"),
            tax_total=Decimal("0"),
            grand_total=Decimal("0"),
            created_by_user_id=created_by_user_id,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
        self._returns[return_id] = ret
        return ret

    async def get_return_by_id(
        self, return_id: str, business_id: str
    ) -> Optional[PurchaseReturnInDB]:
        r = self._returns.get(return_id)
        if not r or r.business_id != business_id or r.is_deleted:
            return None
        return r

    async def list_returns(
        self,
        business_id: str,
        status: Optional[PurchaseReturnStatus] = None,
        purchase_id: Optional[str] = None,
        inventory_location_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[PurchaseReturnInDB], int]:
        filtered = []
        for r in self._returns.values():
            if r.business_id != business_id or r.is_deleted:
                continue
            if status and r.status != status:
                continue
            if purchase_id and r.purchase_id != purchase_id:
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
        status: Optional[PurchaseReturnStatus] = None,
        subtotal: Optional[Decimal] = None,
        discount_total: Optional[Decimal] = None,
        tax_total: Optional[Decimal] = None,
        grand_total: Optional[Decimal] = None,
        finalized_by_user_id: Optional[str] = None,
        finalized_at: Optional[datetime] = None,
        cancelled_by_user_id: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
        is_deleted: Optional[bool] = None,
    ) -> Optional[PurchaseReturnInDB]:
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
        if is_deleted is not None:
            data["is_deleted"] = is_deleted

        data["updated_at"] = datetime.now(timezone.utc)
        updated = PurchaseReturnInDB(**data)
        self._returns[return_id] = updated
        return updated

    async def create_line(
        self,
        return_id: str,
        purchase_line_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        tax_amount: Decimal,
        line_subtotal: Decimal,
        line_total: Decimal,
    ) -> PurchaseReturnLineInDB:
        line_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        line = PurchaseReturnLineInDB(
            id=line_id,
            return_id=return_id,
            purchase_line_id=purchase_line_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
            unit_price=unit_price,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            line_subtotal=line_subtotal,
            line_total=line_total,
            created_at=now,
            updated_at=now,
        )
        self._lines[line_id] = line
        return line

    async def get_line_by_id(
        self, line_id: str, return_id: str
    ) -> Optional[PurchaseReturnLineInDB]:
        l = self._lines.get(line_id)
        if not l or l.return_id != return_id:
            return None
        return l

    async def list_lines_for_return(self, return_id: str) -> List[PurchaseReturnLineInDB]:
        return [l for l in self._lines.values() if l.return_id == return_id]

    async def update_line(
        self,
        line_id: str,
        return_id: str,
        quantity: Optional[Decimal] = None,
        unit_price: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        tax_amount: Optional[Decimal] = None,
        line_subtotal: Optional[Decimal] = None,
        line_total: Optional[Decimal] = None,
    ) -> Optional[PurchaseReturnLineInDB]:
        l = await self.get_line_by_id(line_id, return_id)
        if not l:
            return None

        data = l.model_dump()
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

        data["updated_at"] = datetime.now(timezone.utc)
        updated = PurchaseReturnLineInDB(**data)
        self._lines[line_id] = updated
        return updated

    async def delete_line(self, line_id: str, return_id: str) -> bool:
        l = await self.get_line_by_id(line_id, return_id)
        if not l:
            return False
        del self._lines[line_id]
        return True

    async def sum_returned_quantity_for_purchase_line(
        self, purchase_line_id: str
    ) -> Decimal:
        total = Decimal("0")
        for l in self._lines.values():
            if l.purchase_line_id != purchase_line_id:
                continue
            r = self._returns.get(l.return_id)
            if not r or r.is_deleted:
                continue
            if r.status in (PurchaseReturnStatus.DRAFT, PurchaseReturnStatus.FINALIZED):
                total += l.quantity
        return total

    @classmethod
    def clear(cls):
        cls._returns.clear()
        cls._lines.clear()
        cls._sequences.clear()


purchase_return_repository = InMemoryPurchaseReturnRepository()
