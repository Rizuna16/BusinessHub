from datetime import datetime, timezone
from typing import Dict, List, Optional
from decimal import Decimal
import uuid
from abc import ABC, abstractmethod

from app.modules.stock_opname.schemas import (
    StockOpnameInDB,
    StockOpnameLineInDB,
    StockOpnameStatus,
)


class AbstractStockOpnameRepository(ABC):
    @abstractmethod
    async def create_opname(
        self,
        business_id: str,
        inventory_location_id: str,
        created_by_user_id: str,
        notes: Optional[str] = None,
    ) -> StockOpnameInDB:
        pass

    @abstractmethod
    async def get_opname_by_id(
        self, opname_id: str, business_id: str
    ) -> Optional[StockOpnameInDB]:
        pass

    @abstractmethod
    async def list_opnames(
        self,
        business_id: str,
        status: Optional[StockOpnameStatus] = None,
        inventory_location_id: Optional[str] = None,
    ) -> List[StockOpnameInDB]:
        pass

    @abstractmethod
    async def update_opname_status(
        self,
        opname_id: str,
        business_id: str,
        status: StockOpnameStatus,
        finalized_by_user_id: str,
        finalized_at: datetime,
    ) -> Optional[StockOpnameInDB]:
        pass

    @abstractmethod
    async def delete_opname(self, opname_id: str, business_id: str) -> bool:
        pass

    @abstractmethod
    async def create_line(
        self,
        opname_id: str,
        inventory_location_id: str,
        product_id: str,
        variant_id: Optional[str],
        system_quantity: Decimal,
    ) -> StockOpnameLineInDB:
        pass

    @abstractmethod
    async def get_line_by_id(
        self, line_id: str, opname_id: str
    ) -> Optional[StockOpnameLineInDB]:
        pass

    @abstractmethod
    async def list_lines_for_opname(self, opname_id: str) -> List[StockOpnameLineInDB]:
        pass

    @abstractmethod
    async def update_line_count(
        self,
        line_id: str,
        opname_id: str,
        counted_quantity: Decimal,
        variance: Decimal,
    ) -> Optional[StockOpnameLineInDB]:
        pass

    @abstractmethod
    async def delete_line(self, line_id: str, opname_id: str) -> bool:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryStockOpnameRepository(AbstractStockOpnameRepository):
    _opnames: Dict[str, StockOpnameInDB] = {}
    _lines: Dict[str, StockOpnameLineInDB] = {}

    async def create_opname(
        self,
        business_id: str,
        inventory_location_id: str,
        created_by_user_id: str,
        notes: Optional[str] = None,
    ) -> StockOpnameInDB:
        opname_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        opname = StockOpnameInDB(
            id=opname_id,
            business_id=business_id,
            inventory_location_id=inventory_location_id,
            status=StockOpnameStatus.DRAFT,
            notes=notes,
            created_by_user_id=created_by_user_id,
            finalized_by_user_id=None,
            created_at=now,
            updated_at=now,
            finalized_at=None,
        )
        self._opnames[opname_id] = opname
        return opname

    async def get_opname_by_id(
        self, opname_id: str, business_id: str
    ) -> Optional[StockOpnameInDB]:
        opname = self._opnames.get(opname_id)
        if opname and opname.business_id == business_id:
            return opname
        return None

    async def list_opnames(
        self,
        business_id: str,
        status: Optional[StockOpnameStatus] = None,
        inventory_location_id: Optional[str] = None,
    ) -> List[StockOpnameInDB]:
        results = []
        for opname in self._opnames.values():
            if opname.business_id != business_id:
                continue
            if status and opname.status != status:
                continue
            if inventory_location_id and opname.inventory_location_id != inventory_location_id:
                continue
            results.append(opname)
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results

    async def update_opname_status(
        self,
        opname_id: str,
        business_id: str,
        status: StockOpnameStatus,
        finalized_by_user_id: str,
        finalized_at: datetime,
    ) -> Optional[StockOpnameInDB]:
        opname = await self.get_opname_by_id(opname_id, business_id)
        if not opname:
            return None
        updated = StockOpnameInDB(
            id=opname.id,
            business_id=opname.business_id,
            inventory_location_id=opname.inventory_location_id,
            status=status,
            notes=opname.notes,
            created_by_user_id=opname.created_by_user_id,
            finalized_by_user_id=finalized_by_user_id,
            created_at=opname.created_at,
            updated_at=datetime.now(timezone.utc),
            finalized_at=finalized_at,
        )
        self._opnames[opname_id] = updated
        return updated

    async def delete_opname(self, opname_id: str, business_id: str) -> bool:
        opname = await self.get_opname_by_id(opname_id, business_id)
        if not opname:
            return False
        # Remove lines for this opname
        lines_to_remove = [l_id for l_id, line in self._lines.items() if line.opname_id == opname_id]
        for l_id in lines_to_remove:
            del self._lines[l_id]
        del self._opnames[opname_id]
        return True

    async def create_line(
        self,
        opname_id: str,
        inventory_location_id: str,
        product_id: str,
        variant_id: Optional[str],
        system_quantity: Decimal,
    ) -> StockOpnameLineInDB:
        line_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        line = StockOpnameLineInDB(
            id=line_id,
            opname_id=opname_id,
            inventory_location_id=inventory_location_id,
            product_id=product_id,
            variant_id=variant_id,
            system_quantity=system_quantity,
            counted_quantity=None,
            variance=None,
            created_at=now,
            updated_at=now,
        )
        self._lines[line_id] = line
        return line

    async def get_line_by_id(
        self, line_id: str, opname_id: str
    ) -> Optional[StockOpnameLineInDB]:
        line = self._lines.get(line_id)
        if line and line.opname_id == opname_id:
            return line
        return None

    async def list_lines_for_opname(self, opname_id: str) -> List[StockOpnameLineInDB]:
        lines = [l for l in self._lines.values() if l.opname_id == opname_id]
        lines.sort(key=lambda x: x.created_at)
        return lines

    async def update_line_count(
        self,
        line_id: str,
        opname_id: str,
        counted_quantity: Decimal,
        variance: Decimal,
    ) -> Optional[StockOpnameLineInDB]:
        line = await self.get_line_by_id(line_id, opname_id)
        if not line:
            return None
        now = datetime.now(timezone.utc)
        updated = StockOpnameLineInDB(
            id=line.id,
            opname_id=line.opname_id,
            inventory_location_id=line.inventory_location_id,
            product_id=line.product_id,
            variant_id=line.variant_id,
            system_quantity=line.system_quantity,
            counted_quantity=counted_quantity,
            variance=variance,
            created_at=line.created_at,
            updated_at=now,
        )
        self._lines[line_id] = updated
        return updated

    async def delete_line(self, line_id: str, opname_id: str) -> bool:
        line = await self.get_line_by_id(line_id, opname_id)
        if not line:
            return False
        del self._lines[line_id]
        return True

    @classmethod
    def clear(cls):
        cls._opnames.clear()
        cls._lines.clear()


stock_opname_repository = InMemoryStockOpnameRepository()
