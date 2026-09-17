from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from decimal import Decimal
import uuid

from app.modules.delivery_note.schemas import (
    DeliveryNoteInDB,
    DeliveryNoteLineInDB,
    DeliveryNoteStatus,
)


class AbstractDeliveryNoteRepository(ABC):
    @abstractmethod
    async def create_delivery_note(self, business_id: str, branch_id: str, delivery_number: str, sales_order_id: str, customer_id: Optional[str], delivery_date: datetime, shipping_address: Optional[str], recipient_name: Optional[str], recipient_phone: Optional[str], notes: Optional[str], created_by_user_id: str) -> DeliveryNoteInDB:
        pass

    @abstractmethod
    async def get_by_id(self, delivery_note_id: str, business_id: str) -> Optional[DeliveryNoteInDB]:
        pass

    @abstractmethod
    async def get_by_number(self, business_id: str, delivery_number: str) -> Optional[DeliveryNoteInDB]:
        pass

    @abstractmethod
    async def list_delivery_notes(self, business_id: str, status: Optional[DeliveryNoteStatus], sales_order_id: Optional[str], search: Optional[str], page: int, page_size: int) -> Tuple[List[DeliveryNoteInDB], int]:
        pass

    @abstractmethod
    async def update_delivery_note(self, delivery_note_id: str, business_id: str, **kwargs) -> Optional[DeliveryNoteInDB]:
        pass

    @abstractmethod
    async def get_next_sequence(self, business_id: str) -> int:
        pass

    @abstractmethod
    async def create_line(self, delivery_note_id: str, sales_order_line_id: str, product_id: str, variant_id: Optional[str], product_name_snapshot: str, variant_snapshot: Optional[str], ordered_quantity_snapshot: Decimal, fulfilled_quantity_snapshot: Decimal, delivery_quantity: Decimal, unit: Optional[str], notes: Optional[str]) -> DeliveryNoteLineInDB:
        pass

    @abstractmethod
    async def get_line_by_id(self, line_id: str, delivery_note_id: str) -> Optional[DeliveryNoteLineInDB]:
        pass

    @abstractmethod
    async def list_lines_for_delivery_note(self, delivery_note_id: str) -> List[DeliveryNoteLineInDB]:
        pass

    @abstractmethod
    async def update_line(self, line_id: str, delivery_note_id: str, **kwargs) -> Optional[DeliveryNoteLineInDB]:
        pass

    @abstractmethod
    async def delete_line(self, line_id: str, delivery_note_id: str) -> bool:
        pass

    @abstractmethod
    async def get_active_documented_quantity(self, business_id: str, sales_order_line_id: str, exclude_dn_id: Optional[str] = None) -> Decimal:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryDeliveryNoteRepository(AbstractDeliveryNoteRepository):
    _delivery_notes: Dict[str, DeliveryNoteInDB] = {}
    _lines: Dict[str, DeliveryNoteLineInDB] = {}
    _sequences: Dict[str, int] = {}

    async def create_delivery_note(
        self,
        business_id: str,
        branch_id: str,
        delivery_number: str,
        sales_order_id: str,
        customer_id: Optional[str],
        delivery_date: datetime,
        shipping_address: Optional[str],
        recipient_name: Optional[str],
        recipient_phone: Optional[str],
        notes: Optional[str],
        created_by_user_id: str,
    ) -> DeliveryNoteInDB:
        did = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        dn = DeliveryNoteInDB(
            id=did,
            business_id=business_id,
            branch_id=branch_id,
            delivery_number=delivery_number,
            sales_order_id=sales_order_id,
            customer_id=customer_id,
            delivery_date=delivery_date,
            status=DeliveryNoteStatus.DRAFT,
            shipping_address=shipping_address,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            notes=notes,
            created_by_user_id=created_by_user_id,
            created_at=now,
            updated_at=now,
        )
        self._delivery_notes[did] = dn
        return dn

    async def get_by_id(self, delivery_note_id: str, business_id: str) -> Optional[DeliveryNoteInDB]:
        dn = self._delivery_notes.get(delivery_note_id)
        if not dn or dn.business_id != business_id:
            return None
        return dn

    async def get_by_number(self, business_id: str, delivery_number: str) -> Optional[DeliveryNoteInDB]:
        for dn in self._delivery_notes.values():
            if dn.business_id == business_id and dn.delivery_number == delivery_number:
                return dn
        return None

    async def list_delivery_notes(
        self,
        business_id: str,
        status: Optional[DeliveryNoteStatus],
        sales_order_id: Optional[str],
        search: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[List[DeliveryNoteInDB], int]:
        items = []
        for dn in self._delivery_notes.values():
            if dn.business_id != business_id:
                continue
            if status and dn.status != status:
                continue
            if sales_order_id and dn.sales_order_id != sales_order_id:
                continue
            if search:
                s = search.lower()
                if (s not in dn.delivery_number.lower() and
                    (not dn.recipient_name or s not in dn.recipient_name.lower()) and
                    (not dn.notes or s not in dn.notes.lower())):
                    continue
            items.append(dn)

        items.sort(key=lambda x: x.created_at, reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        return items[start:end], total

    async def update_delivery_note(self, delivery_note_id: str, business_id: str, **kwargs) -> Optional[DeliveryNoteInDB]:
        dn = await self.get_by_id(delivery_note_id, business_id)
        if not dn:
            return None
        data = dn.model_dump()
        for k, v in kwargs.items():
            if v is not None or k in ["customer_id", "notes", "shipping_address", "recipient_name", "recipient_phone", "ready_by_user_id", "ready_at", "delivered_by_user_id", "delivered_at", "cancelled_by_user_id", "cancelled_at", "status"]:
                data[k] = v
        data["updated_at"] = datetime.now(timezone.utc)
        updated = DeliveryNoteInDB(**data)
        self._delivery_notes[delivery_note_id] = updated
        return updated

    async def get_next_sequence(self, business_id: str) -> int:
        cur = self._sequences.get(business_id, 0) + 1
        self._sequences[business_id] = cur
        return cur

    async def create_line(
        self,
        delivery_note_id: str,
        sales_order_line_id: str,
        product_id: str,
        variant_id: Optional[str],
        product_name_snapshot: str,
        variant_snapshot: Optional[str],
        ordered_quantity_snapshot: Decimal,
        fulfilled_quantity_snapshot: Decimal,
        delivery_quantity: Decimal,
        unit: Optional[str],
        notes: Optional[str],
    ) -> DeliveryNoteLineInDB:
        lid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        line = DeliveryNoteLineInDB(
            id=lid,
            delivery_note_id=delivery_note_id,
            sales_order_line_id=sales_order_line_id,
            product_id=product_id,
            variant_id=variant_id,
            product_name_snapshot=product_name_snapshot,
            variant_snapshot=variant_snapshot,
            ordered_quantity_snapshot=ordered_quantity_snapshot,
            fulfilled_quantity_snapshot=fulfilled_quantity_snapshot,
            delivery_quantity=delivery_quantity,
            unit=unit,
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        self._lines[lid] = line
        return line

    async def get_line_by_id(self, line_id: str, delivery_note_id: str) -> Optional[DeliveryNoteLineInDB]:
        l = self._lines.get(line_id)
        if not l or l.delivery_note_id != delivery_note_id:
            return None
        return l

    async def list_lines_for_delivery_note(self, delivery_note_id: str) -> List[DeliveryNoteLineInDB]:
        return [l for l in self._lines.values() if l.delivery_note_id == delivery_note_id]

    async def update_line(self, line_id: str, delivery_note_id: str, **kwargs) -> Optional[DeliveryNoteLineInDB]:
        l = await self.get_line_by_id(line_id, delivery_note_id)
        if not l:
            return None
        data = l.model_dump()
        for k, v in kwargs.items():
            if v is not None:
                data[k] = v
        data["updated_at"] = datetime.now(timezone.utc)
        updated = DeliveryNoteLineInDB(**data)
        self._lines[line_id] = updated
        return updated

    async def delete_line(self, line_id: str, delivery_note_id: str) -> bool:
        l = await self.get_line_by_id(line_id, delivery_note_id)
        if not l:
            return False
        del self._lines[line_id]
        return True

    async def get_active_documented_quantity(self, business_id: str, sales_order_line_id: str, exclude_dn_id: Optional[str] = None) -> Decimal:
        total = Decimal("0")
        for dn in self._delivery_notes.values():
            if dn.business_id != business_id or dn.status in (DeliveryNoteStatus.CANCELLED, DeliveryNoteStatus.DELIVERED):
                continue
            if exclude_dn_id and dn.id == exclude_dn_id:
                continue
            for l in self._lines.values():
                if l.delivery_note_id == dn.id and l.sales_order_line_id == sales_order_line_id:
                    total += l.delivery_quantity
        return total

    @classmethod
    def clear(cls):
        cls._delivery_notes.clear()
        cls._lines.clear()
        cls._sequences.clear()


delivery_note_repository = InMemoryDeliveryNoteRepository()
