from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

from app.modules.warehouse.schemas import (
    WarehouseInDB,
    WarehouseCreate,
    WarehouseUpdate,
    WarehouseStatus,
    InventoryLocationInDB,
    InventoryLocationCreate,
    InventoryLocationUpdate,
    InventoryLocationStatus,
)


class AbstractWarehouseRepository(ABC):
    @abstractmethod
    async def create(
        self, business_id: str, warehouse_data: WarehouseCreate, is_default: bool = False
    ) -> WarehouseInDB:
        pass

    @abstractmethod
    async def get_by_id(self, warehouse_id: str) -> Optional[WarehouseInDB]:
        pass

    @abstractmethod
    async def list_by_business(self, business_id: str) -> List[WarehouseInDB]:
        pass

    @abstractmethod
    async def list_by_branch(self, business_id: str, branch_id: str) -> List[WarehouseInDB]:
        pass

    @abstractmethod
    async def update(
        self, warehouse_id: str, update_data: WarehouseUpdate
    ) -> Optional[WarehouseInDB]:
        pass

    @abstractmethod
    async def suspend(self, warehouse_id: str) -> Optional[WarehouseInDB]:
        pass

    @abstractmethod
    async def activate(self, warehouse_id: str) -> Optional[WarehouseInDB]:
        pass

    @abstractmethod
    async def archive(self, warehouse_id: str) -> Optional[WarehouseInDB]:
        pass

    @abstractmethod
    async def find_by_code(self, business_id: str, code: str) -> Optional[WarehouseInDB]:
        pass

    @abstractmethod
    async def exists_by_code(self, business_id: str, code: str) -> bool:
        pass

    @abstractmethod
    async def get_default(self, business_id: str) -> Optional[WarehouseInDB]:
        pass

    @abstractmethod
    async def set_default(self, business_id: str, warehouse_id: str) -> Optional[WarehouseInDB]:
        pass

    @abstractmethod
    async def count_active(self, business_id: str) -> int:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryWarehouseRepository(AbstractWarehouseRepository):
    """In-memory repository for Warehouse entities."""

    _warehouses: Dict[str, WarehouseInDB] = {}

    async def create(
        self, business_id: str, warehouse_data: WarehouseCreate, is_default: bool = False
    ) -> WarehouseInDB:
        warehouse_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        warehouse = WarehouseInDB(
            id=warehouse_id,
            business_id=business_id,
            branch_id=warehouse_data.branch_id,
            name=warehouse_data.name,
            code=warehouse_data.code.upper(),
            description=warehouse_data.description,
            address=warehouse_data.address,
            phone=warehouse_data.phone,
            email=warehouse_data.email,
            status=WarehouseStatus.ACTIVE,
            is_default=is_default,
            created_at=now,
            updated_at=now,
        )
        self._warehouses[warehouse_id] = warehouse
        return warehouse

    async def get_by_id(self, warehouse_id: str) -> Optional[WarehouseInDB]:
        return self._warehouses.get(warehouse_id)

    async def list_by_business(self, business_id: str) -> List[WarehouseInDB]:
        all_wh = [w for w in self._warehouses.values() if w.business_id == business_id]
        def sort_key(w: WarehouseInDB):
            status_order = 0 if w.status == WarehouseStatus.ACTIVE else (1 if w.status == WarehouseStatus.SUSPENDED else 2)
            default_order = 0 if w.is_default else 1
            return (status_order, default_order, w.created_at, w.id)

        return sorted(all_wh, key=sort_key)

    async def list_by_branch(self, business_id: str, branch_id: str) -> List[WarehouseInDB]:
        all_wh = [w for w in self._warehouses.values() if w.business_id == business_id and w.branch_id == branch_id]
        def sort_key(w: WarehouseInDB):
            status_order = 0 if w.status == WarehouseStatus.ACTIVE else (1 if w.status == WarehouseStatus.SUSPENDED else 2)
            default_order = 0 if w.is_default else 1
            return (status_order, default_order, w.created_at, w.id)

        return sorted(all_wh, key=sort_key)

    async def update(
        self, warehouse_id: str, update_data: WarehouseUpdate
    ) -> Optional[WarehouseInDB]:
        warehouse = self._warehouses.get(warehouse_id)
        if not warehouse:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return warehouse

        current = warehouse.model_dump()
        for field, value in update_dict.items():
            current[field] = value
        current["updated_at"] = datetime.now(timezone.utc)

        updated = WarehouseInDB(**current)
        self._warehouses[warehouse_id] = updated
        return updated

    async def suspend(self, warehouse_id: str) -> Optional[WarehouseInDB]:
        warehouse = self._warehouses.get(warehouse_id)
        if not warehouse:
            return None
        updated = warehouse.model_copy(
            update={
                "status": WarehouseStatus.SUSPENDED,
                "is_default": False,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._warehouses[warehouse_id] = updated
        return updated

    async def activate(self, warehouse_id: str) -> Optional[WarehouseInDB]:
        warehouse = self._warehouses.get(warehouse_id)
        if not warehouse:
            return None
        updated = warehouse.model_copy(
            update={
                "status": WarehouseStatus.ACTIVE,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._warehouses[warehouse_id] = updated
        return updated

    async def archive(self, warehouse_id: str) -> Optional[WarehouseInDB]:
        warehouse = self._warehouses.get(warehouse_id)
        if not warehouse:
            return None
        updated = warehouse.model_copy(
            update={
                "status": WarehouseStatus.ARCHIVED,
                "is_default": False,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._warehouses[warehouse_id] = updated
        return updated

    async def find_by_code(self, business_id: str, code: str) -> Optional[WarehouseInDB]:
        norm_code = code.strip().upper()
        for w in self._warehouses.values():
            if (
                w.business_id == business_id
                and w.code.upper() == norm_code
                and w.status != WarehouseStatus.ARCHIVED
            ):
                return w
        return None

    async def exists_by_code(self, business_id: str, code: str) -> bool:
        return (await self.find_by_code(business_id, code)) is not None

    async def get_default(self, business_id: str) -> Optional[WarehouseInDB]:
        for w in self._warehouses.values():
            if w.business_id == business_id and w.is_default and w.status == WarehouseStatus.ACTIVE:
                return w
        return None

    async def set_default(self, business_id: str, warehouse_id: str) -> Optional[WarehouseInDB]:
        now = datetime.now(timezone.utc)
        for w_id, w in self._warehouses.items():
            if w.business_id == business_id and w.is_default:
                self._warehouses[w_id] = w.model_copy(
                    update={"is_default": False, "updated_at": now}
                )

        target = self._warehouses.get(warehouse_id)
        if not target or target.business_id != business_id:
            return None

        updated_target = target.model_copy(
            update={"is_default": True, "updated_at": now}
        )
        self._warehouses[warehouse_id] = updated_target
        return updated_target

    async def count_active(self, business_id: str) -> int:
        return len([w for w in self._warehouses.values() if w.business_id == business_id and w.status == WarehouseStatus.ACTIVE])

    @classmethod
    def clear(cls):
        cls._warehouses.clear()


class AbstractInventoryLocationRepository(ABC):
    @abstractmethod
    async def create(
        self, business_id: str, warehouse_id: str, location_data: InventoryLocationCreate, is_default: bool = False
    ) -> InventoryLocationInDB:
        pass

    @abstractmethod
    async def get_by_id(self, location_id: str) -> Optional[InventoryLocationInDB]:
        pass

    @abstractmethod
    async def list_by_business(self, business_id: str) -> List[InventoryLocationInDB]:
        pass

    @abstractmethod
    async def list_by_warehouse(self, warehouse_id: str, include_archived: bool = False) -> List[InventoryLocationInDB]:
        pass

    @abstractmethod
    async def update(
        self, location_id: str, update_data: InventoryLocationUpdate
    ) -> Optional[InventoryLocationInDB]:
        pass

    @abstractmethod
    async def archive(self, location_id: str) -> Optional[InventoryLocationInDB]:
        pass

    @abstractmethod
    async def find_by_code(self, warehouse_id: str, code: str) -> Optional[InventoryLocationInDB]:
        pass

    @abstractmethod
    async def exists_by_code(self, warehouse_id: str, code: str) -> bool:
        pass

    @abstractmethod
    async def get_default(self, warehouse_id: str) -> Optional[InventoryLocationInDB]:
        pass

    @abstractmethod
    async def set_default(self, warehouse_id: str, location_id: str) -> Optional[InventoryLocationInDB]:
        pass

    @abstractmethod
    async def count_active(self, warehouse_id: str) -> int:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemoryInventoryLocationRepository(AbstractInventoryLocationRepository):
    """In-memory repository for InventoryLocation entities."""

    _locations: Dict[str, InventoryLocationInDB] = {}

    async def create(
        self, business_id: str, warehouse_id: str, location_data: InventoryLocationCreate, is_default: bool = False
    ) -> InventoryLocationInDB:
        location_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        loc = InventoryLocationInDB(
            id=location_id,
            business_id=business_id,
            warehouse_id=warehouse_id,
            name=location_data.name,
            code=location_data.code.upper(),
            description=location_data.description,
            location_type=location_data.location_type,
            status=InventoryLocationStatus.ACTIVE,
            is_default=is_default,
            created_at=now,
            updated_at=now,
        )
        self._locations[location_id] = loc
        return loc

    async def get_by_id(self, location_id: str) -> Optional[InventoryLocationInDB]:
        return self._locations.get(location_id)

    async def list_by_business(self, business_id: str) -> List[InventoryLocationInDB]:
        all_locs = [l for l in self._locations.values() if l.business_id == business_id]
        def sort_key(l: InventoryLocationInDB):
            status_order = 0 if l.status == InventoryLocationStatus.ACTIVE else 1
            default_order = 0 if l.is_default else 1
            return (status_order, default_order, l.created_at, l.id)

        return sorted(all_locs, key=sort_key)

    async def list_by_warehouse(self, warehouse_id: str, include_archived: bool = False) -> List[InventoryLocationInDB]:
        all_locs = [
            l for l in self._locations.values()
            if l.warehouse_id == warehouse_id and (include_archived or l.status != InventoryLocationStatus.ARCHIVED)
        ]
        def sort_key(l: InventoryLocationInDB):
            status_order = 0 if l.status == InventoryLocationStatus.ACTIVE else 1
            default_order = 0 if l.is_default else 1
            return (status_order, default_order, l.created_at, l.id)

        return sorted(all_locs, key=sort_key)

    async def update(
        self, location_id: str, update_data: InventoryLocationUpdate
    ) -> Optional[InventoryLocationInDB]:
        loc = self._locations.get(location_id)
        if not loc:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return loc

        current = loc.model_dump()
        for field, value in update_dict.items():
            current[field] = value
        current["updated_at"] = datetime.now(timezone.utc)

        updated = InventoryLocationInDB(**current)
        self._locations[location_id] = updated
        return updated

    async def archive(self, location_id: str) -> Optional[InventoryLocationInDB]:
        loc = self._locations.get(location_id)
        if not loc:
            return None
        updated = loc.model_copy(
            update={
                "status": InventoryLocationStatus.ARCHIVED,
                "is_default": False,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._locations[location_id] = updated
        return updated

    async def find_by_code(self, warehouse_id: str, code: str) -> Optional[InventoryLocationInDB]:
        norm_code = code.strip().upper()
        for l in self._locations.values():
            if (
                l.warehouse_id == warehouse_id
                and l.code.upper() == norm_code
                and l.status != InventoryLocationStatus.ARCHIVED
            ):
                return l
        return None

    async def exists_by_code(self, warehouse_id: str, code: str) -> bool:
        return (await self.find_by_code(warehouse_id, code)) is not None

    async def get_default(self, warehouse_id: str) -> Optional[InventoryLocationInDB]:
        for l in self._locations.values():
            if l.warehouse_id == warehouse_id and l.is_default and l.status == InventoryLocationStatus.ACTIVE:
                return l
        return None

    async def set_default(self, warehouse_id: str, location_id: str) -> Optional[InventoryLocationInDB]:
        now = datetime.now(timezone.utc)
        for l_id, l in self._locations.items():
            if l.warehouse_id == warehouse_id and l.is_default:
                self._locations[l_id] = l.model_copy(
                    update={"is_default": False, "updated_at": now}
                )

        target = self._locations.get(location_id)
        if not target or target.warehouse_id != warehouse_id:
            return None

        updated_target = target.model_copy(
            update={"is_default": True, "updated_at": now}
        )
        self._locations[location_id] = updated_target
        return updated_target

    async def count_active(self, warehouse_id: str) -> int:
        return len([l for l in self._locations.values() if l.warehouse_id == warehouse_id and l.status == InventoryLocationStatus.ACTIVE])

    @classmethod
    def clear(cls):
        cls._locations.clear()


warehouse_repository = InMemoryWarehouseRepository()
inventory_location_repository = InMemoryInventoryLocationRepository()
