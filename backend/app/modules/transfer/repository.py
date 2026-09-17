from datetime import datetime, timezone
from typing import Dict, List, Optional
from decimal import Decimal
import uuid
from abc import ABC, abstractmethod

from app.modules.transfer.schemas import (
    TransferInDB,
    TransferLineInDB,
    TransferStatus,
)


class AbstractTransferRepository(ABC):
    @abstractmethod
    async def create_transfer(
        self,
        business_id: str,
        transfer_number: str,
        source_location_id: str,
        destination_location_id: str,
        created_by_user_id: str,
        notes: Optional[str] = None,
    ) -> TransferInDB:
        pass

    @abstractmethod
    async def get_transfer_by_id(
        self, transfer_id: str, business_id: str
    ) -> Optional[TransferInDB]:
        pass

    @abstractmethod
    async def get_next_transfer_sequence(self, business_id: str) -> int:
        pass

    @abstractmethod
    async def list_transfers(
        self,
        business_id: str,
        status: Optional[TransferStatus] = None,
        source_location_id: Optional[str] = None,
        destination_location_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[TransferInDB], int]:
        pass

    @abstractmethod
    async def update_transfer(
        self,
        transfer_id: str,
        business_id: str,
        notes: Optional[str] = None,
        status: Optional[TransferStatus] = None,
        dispatched_by_user_id: Optional[str] = None,
        dispatched_at: Optional[datetime] = None,
        received_by_user_id: Optional[str] = None,
        received_at: Optional[datetime] = None,
        cancelled_by_user_id: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
    ) -> Optional[TransferInDB]:
        pass

    @abstractmethod
    async def create_line(
        self,
        transfer_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
    ) -> TransferLineInDB:
        pass

    @abstractmethod
    async def get_line_by_id(
        self, line_id: str, transfer_id: str
    ) -> Optional[TransferLineInDB]:
        pass

    @abstractmethod
    async def list_lines_for_transfer(self, transfer_id: str) -> List[TransferLineInDB]:
        pass

    @abstractmethod
    async def update_line_cost_snapshot(
        self,
        line_id: str,
        transfer_id: str,
        unit_cost_snapshot: Decimal,
    ) -> Optional[TransferLineInDB]:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryTransferRepository(AbstractTransferRepository):
    _transfers: Dict[str, TransferInDB] = {}
    _lines: Dict[str, TransferLineInDB] = {}
    _sequences: Dict[str, int] = {}

    async def get_next_transfer_sequence(self, business_id: str) -> int:
        current = self._sequences.get(business_id, 0)
        current += 1
        self._sequences[business_id] = current
        return current

    async def create_transfer(
        self,
        business_id: str,
        transfer_number: str,
        source_location_id: str,
        destination_location_id: str,
        created_by_user_id: str,
        notes: Optional[str] = None,
    ) -> TransferInDB:
        transfer_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        t = TransferInDB(
            id=transfer_id,
            business_id=business_id,
            transfer_number=transfer_number,
            source_location_id=source_location_id,
            destination_location_id=destination_location_id,
            status=TransferStatus.DRAFT,
            notes=notes,
            created_by_user_id=created_by_user_id,
            created_at=now,
            updated_at=now,
        )
        self._transfers[transfer_id] = t
        return t

    async def get_transfer_by_id(
        self, transfer_id: str, business_id: str
    ) -> Optional[TransferInDB]:
        t = self._transfers.get(transfer_id)
        if not t or t.business_id != business_id:
            return None
        return t

    async def list_transfers(
        self,
        business_id: str,
        status: Optional[TransferStatus] = None,
        source_location_id: Optional[str] = None,
        destination_location_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[TransferInDB], int]:
        items = []
        for t in self._transfers.values():
            if t.business_id != business_id:
                continue
            if status and t.status != status:
                continue
            if source_location_id and t.source_location_id != source_location_id:
                continue
            if destination_location_id and t.destination_location_id != destination_location_id:
                continue
            if search:
                search_lower = search.lower()
                if search_lower not in t.transfer_number.lower() and (not t.notes or search_lower not in t.notes.lower()):
                    continue
            items.append(t)
        items.sort(key=lambda x: x.created_at, reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total

    async def update_transfer(
        self,
        transfer_id: str,
        business_id: str,
        notes: Optional[str] = None,
        status: Optional[TransferStatus] = None,
        dispatched_by_user_id: Optional[str] = None,
        dispatched_at: Optional[datetime] = None,
        received_by_user_id: Optional[str] = None,
        received_at: Optional[datetime] = None,
        cancelled_by_user_id: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
    ) -> Optional[TransferInDB]:
        t = self._transfers.get(transfer_id)
        if not t or t.business_id != business_id:
            return None
        now = datetime.now(timezone.utc)
        if notes is not None:
            t.notes = notes
        if status is not None:
            t.status = status
        if dispatched_by_user_id is not None:
            t.dispatched_by_user_id = dispatched_by_user_id
        if dispatched_at is not None:
            t.dispatched_at = dispatched_at
        if received_by_user_id is not None:
            t.received_by_user_id = received_by_user_id
        if received_at is not None:
            t.received_at = received_at
        if cancelled_by_user_id is not None:
            t.cancelled_by_user_id = cancelled_by_user_id
        if cancelled_at is not None:
            t.cancelled_at = cancelled_at
        t.updated_at = now
        return t

    async def create_line(
        self,
        transfer_id: str,
        product_id: str,
        variant_id: Optional[str],
        quantity: Decimal,
    ) -> TransferLineInDB:
        line_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        line = TransferLineInDB(
            id=line_id,
            transfer_id=transfer_id,
            product_id=product_id,
            variant_id=variant_id,
            quantity=quantity,
            unit_cost_snapshot=Decimal("0"),
            created_at=now,
            updated_at=now,
        )
        self._lines[line_id] = line
        return line

    async def get_line_by_id(
        self, line_id: str, transfer_id: str
    ) -> Optional[TransferLineInDB]:
        line = self._lines.get(line_id)
        if not line or line.transfer_id != transfer_id:
            return None
        return line

    async def list_lines_for_transfer(self, transfer_id: str) -> List[TransferLineInDB]:
        return [l for l in self._lines.values() if l.transfer_id == transfer_id]

    async def update_line_cost_snapshot(
        self,
        line_id: str,
        transfer_id: str,
        unit_cost_snapshot: Decimal,
    ) -> Optional[TransferLineInDB]:
        line = self._lines.get(line_id)
        if not line or line.transfer_id != transfer_id:
            return None
        line.unit_cost_snapshot = unit_cost_snapshot
        line.updated_at = datetime.now(timezone.utc)
        return line

    @classmethod
    def clear(cls):
        cls._transfers = {}
        cls._lines = {}
        cls._sequences = {}


transfer_repository = InMemoryTransferRepository()
