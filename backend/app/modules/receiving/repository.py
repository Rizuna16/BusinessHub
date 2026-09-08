from datetime import datetime, timezone
from typing import Dict, List, Optional
from decimal import Decimal
import uuid
from abc import ABC, abstractmethod

from app.modules.receiving.schemas import (
    ReceivingInDB,
    ReceivingLineInDB,
    ReceivingStatus,
)


class AbstractReceivingRepository(ABC):
    @abstractmethod
    async def create_receiving(
        self,
        business_id: str,
        purchase_id: str,
        inventory_location_id: str,
        receiving_number: str,
        created_by_user_id: str,
        notes: Optional[str] = None,
    ) -> ReceivingInDB:
        pass

    @abstractmethod
    async def get_receiving_by_id(
        self, receiving_id: str, business_id: str
    ) -> Optional[ReceivingInDB]:
        pass

    @abstractmethod
    async def get_next_receiving_sequence(self, business_id: str) -> int:
        pass

    @abstractmethod
    async def list_receivings(
        self,
        business_id: str,
        status: Optional[ReceivingStatus] = None,
        purchase_id: Optional[str] = None,
        inventory_location_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[ReceivingInDB], int]:
        pass

    @abstractmethod
    async def update_receiving(
        self,
        receiving_id: str,
        business_id: str,
        notes: Optional[str] = None,
        status: Optional[ReceivingStatus] = None,
        finalized_by_user_id: Optional[str] = None,
        finalized_at: Optional[datetime] = None,
        cancelled_by_user_id: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
        is_deleted: Optional[bool] = None,
    ) -> Optional[ReceivingInDB]:
        pass

    @abstractmethod
    async def create_line(
        self,
        receiving_id: str,
        purchase_line_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
    ) -> ReceivingLineInDB:
        pass

    @abstractmethod
    async def get_line_by_id(
        self, line_id: str, receiving_id: str
    ) -> Optional[ReceivingLineInDB]:
        pass

    @abstractmethod
    async def list_lines_for_receiving(self, receiving_id: str) -> List[ReceivingLineInDB]:
        pass

    @abstractmethod
    async def update_line(
        self,
        line_id: str,
        receiving_id: str,
        quantity: Optional[Decimal] = None,
    ) -> Optional[ReceivingLineInDB]:
        pass

    @abstractmethod
    async def delete_line(self, line_id: str, receiving_id: str) -> bool:
        pass

    @abstractmethod
    async def sum_received_quantity_for_purchase_line(
        self, purchase_line_id: str
    ) -> Decimal:
        pass

    @abstractmethod
    async def sum_finalized_received_quantity_for_purchase_line(
        self, purchase_line_id: str
    ) -> Decimal:
        pass

    @abstractmethod
    async def sum_received_quantity_for_purchase_line_excluding(
        self, purchase_line_id: str, exclude_receiving_id: str
    ) -> Decimal:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryReceivingRepository(AbstractReceivingRepository):
    _receivings: Dict[str, ReceivingInDB] = {}
    _lines: Dict[str, ReceivingLineInDB] = {}
    _sequences: Dict[str, int] = {}

    async def get_next_receiving_sequence(self, business_id: str) -> int:
        current = self._sequences.get(business_id, 0)
        current += 1
        self._sequences[business_id] = current
        return current

    async def create_receiving(
        self,
        business_id: str,
        purchase_id: str,
        inventory_location_id: str,
        receiving_number: str,
        created_by_user_id: str,
        notes: Optional[str] = None,
    ) -> ReceivingInDB:
        receiving_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        receiving = ReceivingInDB(
            id=receiving_id,
            business_id=business_id,
            purchase_id=purchase_id,
            inventory_location_id=inventory_location_id,
            receiving_number=receiving_number,
            status=ReceivingStatus.DRAFT,
            notes=notes,
            created_by_user_id=created_by_user_id,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
        self._receivings[receiving_id] = receiving
        return receiving

    async def get_receiving_by_id(
        self, receiving_id: str, business_id: str
    ) -> Optional[ReceivingInDB]:
        r = self._receivings.get(receiving_id)
        if not r or r.business_id != business_id or r.is_deleted:
            return None
        return r

    async def list_receivings(
        self,
        business_id: str,
        status: Optional[ReceivingStatus] = None,
        purchase_id: Optional[str] = None,
        inventory_location_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[ReceivingInDB], int]:
        filtered = []
        for r in self._receivings.values():
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
                if s_lower not in r.receiving_number.lower():
                    continue
            filtered.append(r)

        filtered.sort(key=lambda x: (x.created_at, x.id), reverse=True)
        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        return filtered[start:end], total

    async def update_receiving(
        self,
        receiving_id: str,
        business_id: str,
        notes: Optional[str] = None,
        status: Optional[ReceivingStatus] = None,
        finalized_by_user_id: Optional[str] = None,
        finalized_at: Optional[datetime] = None,
        cancelled_by_user_id: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
        is_deleted: Optional[bool] = None,
    ) -> Optional[ReceivingInDB]:
        r = await self.get_receiving_by_id(receiving_id, business_id)
        if not r:
            return None

        data = r.model_dump()
        if notes is not None:
            data["notes"] = notes
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
        if is_deleted is not None:
            data["is_deleted"] = is_deleted

        data["updated_at"] = datetime.now(timezone.utc)
        updated = ReceivingInDB(**data)
        self._receivings[receiving_id] = updated
        return updated

    async def create_line(
        self,
        receiving_id: str,
        purchase_line_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
    ) -> ReceivingLineInDB:
        line_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        line = ReceivingLineInDB(
            id=line_id,
            receiving_id=receiving_id,
            purchase_line_id=purchase_line_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
            created_at=now,
            updated_at=now,
        )
        self._lines[line_id] = line
        return line

    async def get_line_by_id(
        self, line_id: str, receiving_id: str
    ) -> Optional[ReceivingLineInDB]:
        l = self._lines.get(line_id)
        if not l or l.receiving_id != receiving_id:
            return None
        return l

    async def list_lines_for_receiving(self, receiving_id: str) -> List[ReceivingLineInDB]:
        return [l for l in self._lines.values() if l.receiving_id == receiving_id]

    async def update_line(
        self,
        line_id: str,
        receiving_id: str,
        quantity: Optional[Decimal] = None,
    ) -> Optional[ReceivingLineInDB]:
        l = await self.get_line_by_id(line_id, receiving_id)
        if not l:
            return None

        data = l.model_dump()
        if quantity is not None:
            data["quantity"] = quantity
        data["updated_at"] = datetime.now(timezone.utc)
        updated = ReceivingLineInDB(**data)
        self._lines[line_id] = updated
        return updated

    async def delete_line(self, line_id: str, receiving_id: str) -> bool:
        l = await self.get_line_by_id(line_id, receiving_id)
        if not l:
            return False
        del self._lines[line_id]
        return True

    async def sum_received_quantity_for_purchase_line(
        self, purchase_line_id: str
    ) -> Decimal:
        total = Decimal("0")
        for l in self._lines.values():
            if l.purchase_line_id != purchase_line_id:
                continue
            r = self._receivings.get(l.receiving_id)
            if not r or r.is_deleted:
                continue
            if r.status in (ReceivingStatus.DRAFT, ReceivingStatus.FINALIZED):
                total += l.quantity
        return total

    async def sum_finalized_received_quantity_for_purchase_line(
        self, purchase_line_id: str
    ) -> Decimal:
        total = Decimal("0")
        for l in self._lines.values():
            if l.purchase_line_id != purchase_line_id:
                continue
            r = self._receivings.get(l.receiving_id)
            if not r or r.is_deleted:
                continue
            if r.status == ReceivingStatus.FINALIZED:
                total += l.quantity
        return total

    async def sum_received_quantity_for_purchase_line_excluding(
        self, purchase_line_id: str, exclude_receiving_id: str
    ) -> Decimal:
        total = Decimal("0")
        for l in self._lines.values():
            if l.purchase_line_id != purchase_line_id:
                continue
            r = self._receivings.get(l.receiving_id)
            if not r or r.is_deleted:
                continue
            if r.id == exclude_receiving_id:
                continue
            if r.status in (ReceivingStatus.DRAFT, ReceivingStatus.FINALIZED):
                total += l.quantity
        return total

    @classmethod
    def clear(cls):
        cls._receivings.clear()
        cls._lines.clear()
        cls._sequences.clear()


receiving_repository = InMemoryReceivingRepository()
