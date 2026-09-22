import io
from typing import Optional, List
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import HTTPException, status, UploadFile

from app.modules.product_image.schemas import (
    ProductImageInDB, ProductImageResponse, ProductImageListResponse, ProductImageUpdate,
)
from app.modules.product_image.repository import AbstractProductImageRepository, InMemoryProductImageRepository
from app.modules.product.repository import product_repository
from app.modules.product_variant.repository import product_variant_repository
from app.modules.business_membership.service import business_membership_service, BusinessMembershipService
from app.modules.business_membership.schemas import BusinessMembershipRole

# MIME whitelist
ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def _get_storage_service():
    from app.core.config import settings
    from app.core.storage import StorageService
    return StorageService(settings.upload_dir)


class ProductImageService:
    def __init__(
        self,
        image_repo: AbstractProductImageRepository = InMemoryProductImageRepository(),
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.image_repo = image_repo
        self.membership_service = membership_service

    async def _validate_access(self, business_id: str, user_id: str, required_roles=None):
        membership = await self.membership_service.require_active_membership(business_id, user_id)
        if required_roles and membership.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of roles: {[r.value for r in required_roles]}",
            )
        return membership

    async def _validate_product(self, business_id: str, product_id: str):
        product = await product_repository.get_by_id(product_id, business_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found.")
        if product.status.value == "ARCHIVED":
            raise HTTPException(status_code=400, detail="Cannot add images to archived product.")
        return product

    async def _validate_variant(self, business_id: str, product_id: str, variant_id: str):
        variant = await product_variant_repository.get_by_id(variant_id, business_id)
        if not variant:
            raise HTTPException(status_code=404, detail="Variant not found.")
        if variant.product_id != product_id:
            raise HTTPException(status_code=400, detail="Variant does not belong to this product.")
        if variant.status.value == "ARCHIVED":
            raise HTTPException(status_code=400, detail="Cannot add images to archived variant.")
        return variant

    async def _validate_image_file(self, file: UploadFile):
        max_size = 5 * 1024 * 1024  # 5MB
        content = await file.read()
        file_size = len(content)
        if file_size > max_size:
            raise HTTPException(status_code=400, detail="File exceeds maximum size (5MB).")
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Empty file not allowed.")

        mime = file.content_type
        if mime not in ALLOWED_MIMES:
            raise HTTPException(status_code=400, detail=f"Unsupported image format: {mime}")

        # Validate magic bytes
        ext = None
        if content[:3] == b'\xff\xd8\xff':
            ext = "jpg"
            mime = "image/jpeg"
        elif content[:8] == b'\x89PNG\r\n\x1a\n':
            ext = "png"
            mime = "image/png"
        elif content[:4] == b'RIFF' and content[8:12] == b'WEBP':
            ext = "webp"
            mime = "image/webp"
        else:
            raise HTTPException(status_code=400, detail="Invalid image content.")

        # Pillow validation - mandatory dependency
        from PIL import Image as PILImage
        try:
            img = PILImage.open(io.BytesIO(content))
            img.verify()
            width, height = img.size
        except ImportError:
            raise RuntimeError(
                "Pillow is required for image validation. "
                "Install with: pip install Pillow"
            )
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file.")

        return content, mime, ext, file_size, width, height

    async def upload_image(
        self, business_id: str, user_id: str, product_id: str, variant_id: Optional[str], file: UploadFile
    ) -> ProductImageResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        await self._validate_product(business_id, product_id)
        if variant_id:
            await self._validate_variant(business_id, product_id, variant_id)

        content, mime, ext, file_size, width, height = await self._validate_image_file(file)

        storage_service = _get_storage_service()
        storage_key = storage_service.generate_storage_key(business_id, product_id, variant_id, ext)

        # Write to storage
        try:
            storage_service.save_sync(storage_key, content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Storage write failed: {e}")

        # DB insert
        try:
            existing = await self.image_repo.list_by_owner(business_id, product_id, variant_id)
            is_first = len(existing) == 0
            max_sort = max((img.sort_order for img in existing), default=-1)

            image_data = {
                "product_id": product_id,
                "variant_id": variant_id,
                "storage_key": storage_key,
                "original_filename": file.filename or "unknown",
                "mime_type": mime,
                "file_size": file_size,
                "width": width,
                "height": height,
                "sort_order": max_sort + 1,
                "is_primary": is_first,
                "status": "ACTIVE",
            }
            image = await self.image_repo.create(business_id, image_data)
        except Exception as db_error:
            # Compensation: delete storage on DB failure
            try:
                storage_service.delete_sync(storage_key)
            except Exception as cleanup_error:
                import logging
                logger = logging.getLogger("product_image")
                logger.error(
                    f"COMPENSATION FAILURE: DB insert failed ({db_error}), "
                    f"storage cleanup also failed ({cleanup_error}), "
                    f"orphan storage_key={storage_key}"
                )
            raise

        return self._to_response(image)

    async def list_images(
        self, business_id: str, user_id: str, product_id: str, variant_id: Optional[str] = None
    ) -> ProductImageListResponse:
        await self._validate_access(business_id, user_id)
        images = await self.image_repo.list_by_owner(business_id, product_id, variant_id)
        return ProductImageListResponse(
            items=[self._to_response(img) for img in images],
            total=len(images),
        )

    async def get_image(
        self, business_id: str, user_id: str, image_id: str
    ) -> ProductImageResponse:
        await self._validate_access(business_id, user_id)
        image = await self.image_repo.get_by_id(image_id, business_id)
        if not image:
            raise HTTPException(status_code=404, detail="Image not found.")
        return self._to_response(image)

    async def set_primary(
        self, business_id: str, user_id: str, image_id: str
    ) -> ProductImageResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        image = await self.image_repo.get_by_id(image_id, business_id)
        if not image:
            raise HTTPException(status_code=404, detail="Image not found.")
        if image.status == "ARCHIVED":
            raise HTTPException(status_code=400, detail="Cannot set archived image as primary.")

        # Unset current primary
        all_images = await self.image_repo.list_by_owner(business_id, image.product_id, image.variant_id)
        for img in all_images:
            if img.is_primary and img.id != image_id:
                await self.image_repo.update(img.id, business_id, {"is_primary": False})

        # Set new primary
        updated = await self.image_repo.update(image_id, business_id, {"is_primary": True})
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update primary image.")
        return self._to_response(updated)

    async def archive_image(
        self, business_id: str, user_id: str, image_id: str
    ) -> ProductImageResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        image = await self.image_repo.get_by_id(image_id, business_id)
        if not image:
            raise HTTPException(status_code=404, detail="Image not found.")
        if image.status == "ARCHIVED":
            raise HTTPException(status_code=400, detail="Image is already archived.")
        if image.is_primary:
            # Unset primary before archiving
            await self.image_repo.update(image_id, business_id, {"is_primary": False})

        updated = await self.image_repo.update(image_id, business_id, {"status": "ARCHIVED"})
        return self._to_response(updated)

    async def update_sort_order(
        self, business_id: str, user_id: str, image_id: str, sort_order: int
    ) -> ProductImageResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        image = await self.image_repo.get_by_id(image_id, business_id)
        if not image:
            raise HTTPException(status_code=404, detail="Image not found.")
        if image.status == "ARCHIVED":
            raise HTTPException(status_code=400, detail="Cannot reorder archived image.")
        updated = await self.image_repo.update(image_id, business_id, {"sort_order": sort_order})
        return self._to_response(updated)

    def _to_response(self, image: ProductImageInDB) -> ProductImageResponse:
        return ProductImageResponse(
            id=image.id,
            business_id=image.business_id,
            product_id=image.product_id,
            variant_id=image.variant_id,
            storage_key=image.storage_key,
            original_filename=image.original_filename,
            mime_type=image.mime_type,
            file_size=image.file_size,
            width=image.width,
            height=image.height,
            sort_order=image.sort_order,
            is_primary=image.is_primary,
            status=image.status,
            created_at=image.created_at.isoformat(),
            updated_at=image.updated_at.isoformat(),
        )


product_image_service = ProductImageService()
