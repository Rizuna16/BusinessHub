from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid
from abc import ABC, abstractmethod
from pydantic import BaseModel

from app.modules.unit.schemas import (
    UnitCreate,
    UnitUpdate,
    UnitStatus,
    UnitResponse,
    UnitType,
)


class UnitInDB(BaseModel):
    id: str
    business_id: str
    name: str
    code: str
    symbol: Optional[str] = None
    description: Optional[str] = None
    unit_type: UnitType
    precision: int = 0
    status: UnitStatus = UnitStatus.ACTIVE
    created_at: datetime
    updated_at: datetime


class AbstractUnitRepository(ABC):
    @abstractmethod
    async def create(
        self,
        business_id: str,
        unit_data: UnitCreate,
    ) -> UnitInDB:
        pass

    @abstractmethod
    async def get_by_id(self, unit_id: str, business_id: str) -> Optional[UnitInDB]:
        pass

    @abstractmethod
    async def list_by_business(
        self,
        business_id: str,
        unit_type: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[UnitInDB]:
        pass

    @abstractmethod
    async def update(
        self,
        unit_id: str,
        business_id: str,
        update_data: UnitUpdate,
    ) -> Optional[UnitInDB]:
        pass

    @abstractmethod
    async def archive(self, unit_id: str, business_id: str) -> Optional[UnitInDB]:
        pass

    @abstractmethod
    async def find_by_code(self, business_id: str, code: str) -> Optional[UnitInDB]:
        pass

    @abstractmethod
    async def find_by_name(self, business_id: str, name: str) -> Optional[UnitInDB]:
        pass

    @abstractmethod
    async def exists(self, unit_id: str, business_id: str) -> bool:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryUnitRepository(AbstractUnitRepository):
    """
    In-memory repository for Unit entities.
    All queries are strictly scoped by business_id.
    Access control is enforced at the service layer.
    """
    _units: Dict[str, UnitInDB] = {}  # keyed by "business_id:unit_id"

    def _key(self, business_id: str, unit_id: str) -> str:
        return f"{business_id}:{unit_id}"

    async def create(
        self,
        business_id: str,
        unit_data: UnitCreate,
    ) -> UnitInDB:
        unit_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        unit = UnitInDB(
            id=unit_id,
            business_id=business_id,
            name=unit_data.name,
            code=unit_data.code.upper(),
            symbol=unit_data.symbol,
            description=unit_data.description,
            unit_type=unit_data.unit_type,
            precision=unit_data.precision,
            status=UnitStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self._units[self._key(business_id, unit_id)] = unit
        return unit

    async def get_by_id(self, unit_id: str, business_id: str) -> Optional[UnitInDB]:
        return self._units.get(self._key(business_id, unit_id))

    async def list_by_business(
        self,
        business_id: str,
        unit_type: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[UnitInDB]:
        results = []
        for unit in self._units.values():
            if unit.business_id != business_id:
                continue
            if unit_type is not None and unit.unit_type.value != unit_type:
                continue
            if not include_archived and unit.status == UnitStatus.ARCHIVED:
                continue
            results.append(unit)
        results.sort(key=lambda u: (u.name.lower(), u.code, u.id))
        return results

    async def update(
        self,
        unit_id: str,
        business_id: str,
        update_data: UnitUpdate,
    ) -> Optional[UnitInDB]:
        key = self._key(business_id, unit_id)
        unit = self._units.get(key)
        if not unit:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return unit

        current = unit.model_dump()
        for field, value in update_dict.items():
            if field == "code" and value is not None:
                current[field] = value.upper()
            else:
                current[field] = value
        current["updated_at"] = datetime.now(timezone.utc)

        updated = UnitInDB(**current)
        self._units[key] = updated
        return updated

    async def archive(self, unit_id: str, business_id: str) -> Optional[UnitInDB]:
        key = self._key(business_id, unit_id)
        unit = self._units.get(key)
        if not unit:
            return None
        updated = unit.model_copy(
            update={
                "status": UnitStatus.ARCHIVED,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._units[key] = updated
        return updated

    async def find_by_code(self, business_id: str, code: str) -> Optional[UnitInDB]:
        norm = code.strip().upper()
        for unit in self._units.values():
            if unit.business_id == business_id and unit.code.upper() == norm:
                return unit
        return None

    async def find_by_name(self, business_id: str, name: str) -> Optional[UnitInDB]:
        norm = name.strip().lower()
        for unit in self._units.values():
            if unit.business_id == business_id and unit.name.lower() == norm:
                return unit
        return None

    async def exists(self, unit_id: str, business_id: str) -> bool:
        return self._key(business_id, unit_id) in self._units

    @classmethod
    def clear(cls):
        cls._units.clear()


unit_repository = InMemoryUnitRepository()
