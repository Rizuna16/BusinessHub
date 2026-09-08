from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid
from abc import ABC, abstractmethod
from pydantic import BaseModel

from app.modules.barcode.schemas import (
    BarcodeCreate,
    BarcodeUpdate,
    BarcodeStatus,
    BarcodeType,
)

class BarcodeInDB(BaseModel):
    id: str
    business_id: str
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    code: str
    barcode_type: BarcodeType
    status: BarcodeStatus
    created_at: datetime
    updated_at: datetime

class AbstractBarcodeRepository(ABC):
    @abstractmethod
    async def create(self, business_id: str, data: BarcodeCreate) -> BarcodeInDB:
        pass

    @abstractmethod
    async def get_by_id(self, barcode_id: str, business_id: str) -> Optional[BarcodeInDB]:
        pass

    @abstractmethod
    async def list_by_business(
        self,
        business_id: str,
        include_archived: bool = False,
    ) -> List[BarcodeInDB]:
        pass

    @abstractmethod
    async def list_by_product(self, business_id: str, product_id: str) -> List[BarcodeInDB]:
        pass

    @abstractmethod
    async def list_by_variant(self, business_id: str, variant_id: str) -> List[BarcodeInDB]:
        pass

    @abstractmethod
    async def update(
        self,
        barcode_id: str,
        business_id: str,
        data: BarcodeUpdate,
    ) -> Optional[BarcodeInDB]:
        pass

    @abstractmethod
    async def archive(self, barcode_id: str, business_id: str) -> Optional[BarcodeInDB]:
        pass

    @abstractmethod
    async def find_by_code(self, business_id: str, code: str) -> Optional[BarcodeInDB]:
        pass

    @abstractmethod
    async def exists(self, barcode_id: str, business_id: str) -> bool:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass

class InMemoryBarcodeRepository(AbstractBarcodeRepository):
    _barcodes: Dict[str, BarcodeInDB] = {}  # keyed by "business_id:barcode_id"

    def _key(self, business_id: str, barcode_id: str) -> str:
        return f"{business_id}:{barcode_id}"

    async def create(self, business_id: str, data: BarcodeCreate) -> BarcodeInDB:
        barcode_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        db_obj = BarcodeInDB(
            id=barcode_id,
            business_id=business_id,
            product_id=data.product_id,
            variant_id=data.variant_id,
            code=data.code,
            barcode_type=data.barcode_type,
            status=BarcodeStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self._barcodes[self._key(business_id, barcode_id)] = db_obj
        return db_obj

    async def get_by_id(self, barcode_id: str, business_id: str) -> Optional[BarcodeInDB]:
        key = self._key(business_id, barcode_id)
        return self._barcodes.get(key)

    async def list_by_business(
        self,
        business_id: str,
        include_archived: bool = False,
    ) -> List[BarcodeInDB]:
        result = []
        for k, b in self._barcodes.items():
            if b.business_id == business_id:
                if not include_archived and b.status == BarcodeStatus.ARCHIVED:
                    continue
                result.append(b)
        return result

    async def list_by_product(self, business_id: str, product_id: str) -> List[BarcodeInDB]:
        result = []
        for k, b in self._barcodes.items():
            if b.business_id == business_id and b.product_id == product_id:
                if b.status == BarcodeStatus.ACTIVE:
                    result.append(b)
        return result

    async def list_by_variant(self, business_id: str, variant_id: str) -> List[BarcodeInDB]:
        result = []
        for k, b in self._barcodes.items():
            if b.business_id == business_id and b.variant_id == variant_id:
                if b.status == BarcodeStatus.ACTIVE:
                    result.append(b)
        return result

    async def update(
        self,
        barcode_id: str,
        business_id: str,
        data: BarcodeUpdate,
    ) -> Optional[BarcodeInDB]:
        key = self._key(business_id, barcode_id)
        b = self._barcodes.get(key)
        if not b:
            return None
        
        update_dict = data.model_dump(exclude_unset=True)
        updated_data = b.model_dump()
        for field, value in update_dict.items():
            if value is not None:
                updated_data[field] = value
        updated_data["updated_at"] = datetime.now(timezone.utc)
        
        new_obj = BarcodeInDB(**updated_data)
        self._barcodes[key] = new_obj
        return new_obj

    async def archive(self, barcode_id: str, business_id: str) -> Optional[BarcodeInDB]:
        key = self._key(business_id, barcode_id)
        b = self._barcodes.get(key)
        if not b:
            return None
        updated_data = b.model_dump()
        updated_data["status"] = BarcodeStatus.ARCHIVED
        updated_data["updated_at"] = datetime.now(timezone.utc)
        new_obj = BarcodeInDB(**updated_data)
        self._barcodes[key] = new_obj
        return new_obj

    async def find_by_code(self, business_id: str, code: str) -> Optional[BarcodeInDB]:
        lower_code = code.lower()
        for k, b in self._barcodes.items():
            if b.business_id == business_id and b.code.lower() == lower_code:
                if b.status == BarcodeStatus.ACTIVE:
                    return b
        return None

    async def exists(self, barcode_id: str, business_id: str) -> bool:
        key = self._key(business_id, barcode_id)
        return key in self._barcodes

    @classmethod
    def clear(cls):
        cls._barcodes.clear()

barcode_repository = InMemoryBarcodeRepository()
