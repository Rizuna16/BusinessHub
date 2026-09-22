from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from app.modules.product_image.schemas import ProductImageInDB


class AbstractProductImageRepository(ABC):
    @abstractmethod
    async def create(self, business_id: str, data: dict) -> ProductImageInDB: ...

    @abstractmethod
    async def get_by_id(self, image_id: str, business_id: str) -> Optional[ProductImageInDB]: ...

    @abstractmethod
    async def list_by_owner(self, business_id: str, product_id: str, variant_id: Optional[str] = None) -> List[ProductImageInDB]: ...

    @abstractmethod
    async def update(self, image_id: str, business_id: str, updates: dict) -> Optional[ProductImageInDB]: ...

    @abstractmethod
    async def delete(self, image_id: str, business_id: str) -> bool: ...

    @classmethod
    @abstractmethod
    def clear(cls): ...


class InMemoryProductImageRepository(AbstractProductImageRepository):
    _images: dict[str, ProductImageInDB] = {}
    _lock = None

    @classmethod
    def clear(cls):
        cls._images.clear()

    async def create(self, business_id: str, data: dict) -> ProductImageInDB:
        now = datetime.now(timezone.utc)
        image = ProductImageInDB(
            id=str(uuid.uuid4()),
            business_id=business_id,
            product_id=data["product_id"],
            variant_id=data.get("variant_id"),
            storage_key=data["storage_key"],
            original_filename=data["original_filename"],
            mime_type=data["mime_type"],
            file_size=data["file_size"],
            width=data.get("width"),
            height=data.get("height"),
            sort_order=data.get("sort_order", 0),
            is_primary=data.get("is_primary", False),
            status=data.get("status", "ACTIVE"),
            created_at=now,
            updated_at=now,
        )
        self._images[image.id] = image
        return image

    async def get_by_id(self, image_id: str, business_id: str) -> Optional[ProductImageInDB]:
        img = self._images.get(image_id)
        if img and img.business_id == business_id:
            return img
        return None

    async def list_by_owner(self, business_id: str, product_id: str, variant_id: Optional[str] = None) -> List[ProductImageInDB]:
        results = []
        for img in self._images.values():
            if img.business_id != business_id:
                continue
            if img.product_id != product_id:
                continue
            if variant_id is None and img.variant_id is not None:
                continue
            if variant_id is not None and img.variant_id != variant_id:
                continue
            if img.status != "ACTIVE":
                continue
            results.append(img)
        results.sort(key=lambda x: (x.sort_order, x.id))
        return results

    async def update(self, image_id: str, business_id: str, updates: dict) -> Optional[ProductImageInDB]:
        img = self._images.get(image_id)
        if not img or img.business_id != business_id:
            return None
        current = img.model_dump()
        for k, v in updates.items():
            if v is not None:
                current[k] = v
        current["updated_at"] = datetime.now(timezone.utc)
        updated = ProductImageInDB(**current)
        self._images[image_id] = updated
        return updated

    async def delete(self, image_id: str, business_id: str) -> bool:
        img = self._images.get(image_id)
        if not img or img.business_id != business_id:
            return False
        del self._images[image_id]
        return True
