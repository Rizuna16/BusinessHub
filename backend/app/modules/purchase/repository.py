from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal
import uuid
from abc import ABC, abstractmethod

from app.modules.purchase.schemas import (
    PurchaseInDB,
    PurchaseLineInDB,
    PurchaseStatus,
)


class AbstractPurchaseRepository(ABC):
    @abstractmethod
    async def create_purchase(
        self,
        business_id: str,
        supplier_id: str,
        branch_id: str,
        purchase_number: str,
        purchase_date: datetime,
        created_by_user_id: str,
        notes: Optional[str] = None,
    ) -> PurchaseInDB:
        pass

    @abstractmethod
    async def get_purchase_by_id(
        self, purchase_id: str, business_id: str
    ) -> Optional[PurchaseInDB]:
        pass

    @abstractmethod
    async def get_purchase_by_number(
        self, business_id: str, purchase_number: str
    ) -> Optional[PurchaseInDB]:
        pass

    @abstractmethod
    async def list_purchases(
        self,
        business_id: str,
        status: Optional[PurchaseStatus] = None,
        supplier_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[PurchaseInDB], int]:
        pass

    @abstractmethod
    async def update_purchase(
        self,
        purchase_id: str,
        business_id: str,
        supplier_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        purchase_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        status: Optional[PurchaseStatus] = None,
        subtotal: Optional[Decimal] = None,
        discount_total: Optional[Decimal] = None,
        tax_total: Optional[Decimal] = None,
        grand_total: Optional[Decimal] = None,
        finalized_by_user_id: Optional[str] = None,
        finalized_at: Optional[datetime] = None,
        cancelled_by_user_id: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
        is_deleted: Optional[bool] = None,
    ) -> Optional[PurchaseInDB]:
        pass

    @abstractmethod
    async def get_next_purchase_sequence(self, business_id: str) -> int:
        pass

    @abstractmethod
    async def create_line(
        self,
        purchase_id: str,
        product_id: str,
        variant_id: Optional[str],
        description: Optional[str],
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        tax_amount: Decimal,
        line_subtotal: Decimal,
        line_total: Decimal,
    ) -> PurchaseLineInDB:
        pass

    @abstractmethod
    async def get_line_by_id(
        self, line_id: str, purchase_id: str
    ) -> Optional[PurchaseLineInDB]:
        pass

    @abstractmethod
    async def list_lines_for_purchase(self, purchase_id: str) -> List[PurchaseLineInDB]:
        pass

    @abstractmethod
    async def update_line(
        self,
        line_id: str,
        purchase_id: str,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
        description: Optional[str] = None,
        quantity: Optional[Decimal] = None,
        unit_price: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        tax_amount: Optional[Decimal] = None,
        line_subtotal: Optional[Decimal] = None,
        line_total: Optional[Decimal] = None,
    ) -> Optional[PurchaseLineInDB]:
        pass

    @abstractmethod
    async def delete_line(self, line_id: str, purchase_id: str) -> bool:
        pass

    @abstractmethod
    async def update_line_snapshot(self, line_id: str, purchase_id: str, snapshot: Any) -> Optional[PurchaseLineInDB]:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryPurchaseRepository(AbstractPurchaseRepository):
    _purchases: Dict[str, PurchaseInDB] = {}
    _lines: Dict[str, PurchaseLineInDB] = {}
    _sequences: Dict[str, int] = {}

    async def get_next_purchase_sequence(self, business_id: str) -> int:
        current = self._sequences.get(business_id, 0)
        current += 1
        self._sequences[business_id] = current
        return current

    async def create_purchase(
        self,
        business_id: str,
        supplier_id: str,
        branch_id: str,
        purchase_number: str,
        purchase_date: datetime,
        created_by_user_id: str,
        notes: Optional[str] = None,
        input_vat_creditable: bool = False,
    ) -> PurchaseInDB:
        purchase_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        purchase = PurchaseInDB(
            id=purchase_id,
            business_id=business_id,
            supplier_id=supplier_id,
            branch_id=branch_id,
            purchase_number=purchase_number,
            purchase_date=purchase_date,
            notes=notes,
            status=PurchaseStatus.DRAFT,
            subtotal=Decimal("0"),
            discount_total=Decimal("0"),
            tax_total=Decimal("0"),
            grand_total=Decimal("0"),
            input_vat_creditable=input_vat_creditable,
            created_by_user_id=created_by_user_id,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
        self._purchases[purchase_id] = purchase
        return purchase

    async def get_purchase_by_id(
        self, purchase_id: str, business_id: str
    ) -> Optional[PurchaseInDB]:
        p = self._purchases.get(purchase_id)
        if not p or p.business_id != business_id or p.is_deleted:
            return None
        return p

    async def get_purchase_by_number(
        self, business_id: str, purchase_number: str
    ) -> Optional[PurchaseInDB]:
        for p in self._purchases.values():
            if p.business_id == business_id and p.purchase_number == purchase_number and not p.is_deleted:
                return p
        return None

    async def list_purchases(
        self,
        business_id: str,
        status: Optional[PurchaseStatus] = None,
        supplier_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[PurchaseInDB], int]:
        filtered = []
        for p in self._purchases.values():
            if p.business_id != business_id or p.is_deleted:
                continue
            if status and p.status != status:
                continue
            if supplier_id and p.supplier_id != supplier_id:
                continue
            if branch_id and p.branch_id != branch_id:
                continue
            if search:
                s_lower = search.lower()
                if s_lower not in p.purchase_number.lower():
                    # check supplier name if needed, but repository might just check number or we filter in service
                    continue
            filtered.append(p)

        # Sort: purchase_date DESC, created_at DESC, id DESC
        filtered.sort(key=lambda x: (x.purchase_date, x.created_at, x.id), reverse=True)

        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = filtered[start:end]
        return paginated, total

    async def update_purchase(
        self,
        purchase_id: str,
        business_id: str,
        supplier_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        purchase_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        status: Optional[PurchaseStatus] = None,
        subtotal: Optional[Decimal] = None,
        discount_total: Optional[Decimal] = None,
        tax_total: Optional[Decimal] = None,
        grand_total: Optional[Decimal] = None,
        finalized_by_user_id: Optional[str] = None,
        finalized_at: Optional[datetime] = None,
        cancelled_by_user_id: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
        is_deleted: Optional[bool] = None,
    ) -> Optional[PurchaseInDB]:
        p = await self.get_purchase_by_id(purchase_id, business_id)
        if not p:
            return None

        update_data = p.model_dump()
        if supplier_id is not None:
            update_data["supplier_id"] = supplier_id
        if branch_id is not None:
            update_data["branch_id"] = branch_id
        if purchase_date is not None:
            update_data["purchase_date"] = purchase_date
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
        updated = PurchaseInDB(**update_data)
        self._purchases[purchase_id] = updated
        return updated

    async def create_line(
        self,
        purchase_id: str,
        product_id: str,
        variant_id: Optional[str],
        description: Optional[str],
        quantity: Decimal,
        unit_price: Decimal,
        discount_amount: Decimal,
        tax_amount: Decimal,
        line_subtotal: Decimal,
        line_total: Decimal,
    ) -> PurchaseLineInDB:
        line_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        line = PurchaseLineInDB(
            id=line_id,
            purchase_id=purchase_id,
            product_id=product_id,
            variant_id=variant_id,
            description=description,
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
        self, line_id: str, purchase_id: str
    ) -> Optional[PurchaseLineInDB]:
        l = self._lines.get(line_id)
        if not l or l.purchase_id != purchase_id:
            return None
        return l

    async def list_lines_for_purchase(self, purchase_id: str) -> List[PurchaseLineInDB]:
        return [l for l in self._lines.values() if l.purchase_id == purchase_id]

    async def update_line(
        self,
        line_id: str,
        purchase_id: str,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
        description: Optional[str] = None,
        quantity: Optional[Decimal] = None,
        unit_price: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        tax_amount: Optional[Decimal] = None,
        line_subtotal: Optional[Decimal] = None,
        line_total: Optional[Decimal] = None,
    ) -> Optional[PurchaseLineInDB]:
        l = await self.get_line_by_id(line_id, purchase_id)
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

        data["updated_at"] = datetime.now(timezone.utc)
        updated = PurchaseLineInDB(**data)
        self._lines[line_id] = updated
        return updated

    async def delete_line(self, line_id: str, purchase_id: str) -> bool:
        l = await self.get_line_by_id(line_id, purchase_id)
        if not l:
            return False
        del self._lines[line_id]
        return True

    async def update_line_snapshot(self, line_id: str, purchase_id: str, snapshot: Any) -> Optional[PurchaseLineInDB]:
        l = await self.get_line_by_id(line_id, purchase_id)
        if not l:
            return None
        data = l.model_dump()
        data["tax_snapshot"] = snapshot
        data["updated_at"] = datetime.now(timezone.utc)
        updated = PurchaseLineInDB(**data)
        self._lines[line_id] = updated
        return updated

    @classmethod
    def clear(cls):
        cls._purchases.clear()
        cls._lines.clear()
        cls._sequences.clear()


purchase_repository = InMemoryPurchaseRepository()
