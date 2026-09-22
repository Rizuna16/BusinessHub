"""
Feature #65 — Product Image Management Tests
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from io import BytesIO

from app.main import app
from app.modules.product_image.schemas import ProductImageInDB, ProductImageStatus
from app.modules.product_image.repository import InMemoryProductImageRepository
from app.modules.product_image.service import ProductImageService
from app.modules.business_membership.schemas import BusinessMembershipRole


@pytest.fixture(autouse=True)
def clear_images():
    InMemoryProductImageRepository.clear()
    yield
    InMemoryProductImageRepository.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def image_service():
    return ProductImageService()


# ── Helpers ──────────────────────────────────────────────────────────────

def _make_jpeg_bytes():
    """Create minimal valid JPEG bytes using Pillow."""
    from PIL import Image as PILImage
    import io
    img = PILImage.new("RGB", (2, 2), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_png_bytes():
    """Create minimal valid PNG bytes using Pillow."""
    from PIL import Image as PILImage
    import io
    img = PILImage.new("RGB", (2, 2), color=(0, 128, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Upload Tests ─────────────────────────────────────────────────────────

class TestUpload:
    @pytest.mark.asyncio
    async def test_upload_jpeg(self, image_service):
        """Upload a valid JPEG image."""
        mock_membership = MagicMock()
        mock_membership.role = BusinessMembershipRole.OWNER
        with patch.object(image_service.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=mock_membership):
            with patch("app.modules.product_image.service.product_repository") as mock_prod:
                mock_product = MagicMock()
                mock_product.status.value = "ACTIVE"
                mock_prod.get_by_id = AsyncMock(return_value=mock_product)

                with patch("app.modules.product_image.service._get_storage_service") as mock_storage_cls:
                    mock_storage = MagicMock()
                    mock_storage.generate_storage_key.return_value = "biz1/products/prod1/uuid.jpg"
                    mock_storage_cls.return_value = mock_storage

                    file_content = _make_jpeg_bytes()
                    mock_file = MagicMock()
                    mock_file.filename = "test.jpg"
                    mock_file.content_type = "image/jpeg"
                    mock_file.read = AsyncMock(return_value=file_content)

                    result = await image_service.upload_image(
                        "biz1", "user1", "prod1", None, mock_file
                    )
                    assert result.mime_type == "image/jpeg"
                    assert result.variant_id is None
                    assert result.is_primary is True

    @pytest.mark.asyncio
    async def test_upload_invalid_mime_rejected(self, image_service):
        """Non-image file must be rejected."""
        mock_membership = MagicMock()
        mock_membership.role = BusinessMembershipRole.OWNER
        with patch.object(image_service.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=mock_membership):
            with patch("app.modules.product_image.service.product_repository") as mock_prod:
                mock_product = MagicMock()
                mock_product.status.value = "ACTIVE"
                mock_prod.get_by_id = AsyncMock(return_value=mock_product)

                mock_file = MagicMock()
                mock_file.filename = "malware.exe"
                mock_file.content_type = "application/octet-stream"
                mock_file.read = AsyncMock(return_value=b'\x00' * 100)

                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc_info:
                    await image_service.upload_image("biz1", "user1", "prod1", None, mock_file)
                assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_oversized_rejected(self, image_service):
        """File exceeding 5MB must be rejected."""
        mock_membership = MagicMock()
        mock_membership.role = BusinessMembershipRole.OWNER
        with patch.object(image_service.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=mock_membership):
            with patch("app.modules.product_image.service.product_repository") as mock_prod:
                mock_product = MagicMock()
                mock_product.status.value = "ACTIVE"
                mock_prod.get_by_id = AsyncMock(return_value=mock_product)

                mock_file = MagicMock()
                mock_file.filename = "big.jpg"
                mock_file.content_type = "image/jpeg"
                mock_file.read = AsyncMock(return_value=b'\xff\xd8\xff' + b'\x00' * (5 * 1024 * 1024 + 1))

                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc_info:
                    await image_service.upload_image("biz1", "user1", "prod1", None, mock_file)
                assert exc_info.value.status_code == 400
                assert "size" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_upload_cannot_add_to_archived_product(self, image_service):
        """Cannot upload image to archived product."""
        mock_membership = MagicMock()
        mock_membership.role = BusinessMembershipRole.OWNER
        with patch.object(image_service.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=mock_membership):
            with patch("app.modules.product_image.service.product_repository") as mock_prod:
                mock_product = MagicMock()
                mock_product.status.value = "ARCHIVED"
                mock_prod.get_by_id = AsyncMock(return_value=mock_product)

                mock_file = MagicMock()
                mock_file.filename = "test.jpg"
                mock_file.content_type = "image/jpeg"
                mock_file.read = AsyncMock(return_value=_make_jpeg_bytes())

                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc_info:
                    await image_service.upload_image("biz1", "user1", "prod1", None, mock_file)
                assert exc_info.value.status_code == 400
                assert "archived" in exc_info.value.detail.lower()


# ── Primary Tests ────────────────────────────────────────────────────────

class TestPrimaryImage:
    @pytest.mark.asyncio
    async def test_first_upload_becomes_primary(self, image_service):
        """First image for a product should be primary."""
        await image_service.image_repo.create("biz1", {
            "product_id": "prod1", "variant_id": None,
            "storage_key": "biz1/products/prod1/old.jpg",
            "original_filename": "old.jpg", "mime_type": "image/jpeg",
            "file_size": 1000, "sort_order": 0, "is_primary": True, "status": "ACTIVE",
        })
        images = await image_service.image_repo.list_by_owner("biz1", "prod1")
        assert len(images) == 1
        assert images[0].is_primary is True

    @pytest.mark.asyncio
    async def test_set_primary_switches(self, image_service):
        """Setting primary on another image unsets the old primary."""
        img1 = await image_service.image_repo.create("biz1", {
            "product_id": "prod1", "variant_id": None,
            "storage_key": "a", "original_filename": "a.jpg",
            "mime_type": "image/jpeg", "file_size": 100, "sort_order": 0,
            "is_primary": True, "status": "ACTIVE",
        })
        img2 = await image_service.image_repo.create("biz1", {
            "product_id": "prod1", "variant_id": None,
            "storage_key": "b", "original_filename": "b.jpg",
            "mime_type": "image/jpeg", "file_size": 100, "sort_order": 1,
            "is_primary": False, "status": "ACTIVE",
        })

        mock_membership = MagicMock()
        mock_membership.role = BusinessMembershipRole.OWNER
        with patch.object(image_service.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=mock_membership):
            result = await image_service.set_primary("biz1", "user1", img2.id)
            assert result.is_primary is True

            old = await image_service.image_repo.get_by_id(img1.id, "biz1")
            assert old.is_primary is False


# ── Archive Tests ────────────────────────────────────────────────────────

class TestArchive:
    @pytest.mark.asyncio
    async def test_archive_image(self, image_service):
        """Archive an image."""
        img = await image_service.image_repo.create("biz1", {
            "product_id": "prod1", "variant_id": None,
            "storage_key": "x", "original_filename": "x.jpg",
            "mime_type": "image/jpeg", "file_size": 100, "sort_order": 0,
            "is_primary": False, "status": "ACTIVE",
        })

        mock_membership = MagicMock()
        mock_membership.role = BusinessMembershipRole.OWNER
        with patch.object(image_service.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=mock_membership):
            result = await image_service.archive_image("biz1", "user1", img.id)
            assert result.status == "ARCHIVED"

    @pytest.mark.asyncio
    async def test_archived_image_cannot_become_primary(self, image_service):
        """Archived image cannot be set as primary."""
        img = await image_service.image_repo.create("biz1", {
            "product_id": "prod1", "variant_id": None,
            "storage_key": "x", "original_filename": "x.jpg",
            "mime_type": "image/jpeg", "file_size": 100, "sort_order": 0,
            "is_primary": False, "status": "ARCHIVED",
        })

        mock_membership = MagicMock()
        mock_membership.role = BusinessMembershipRole.OWNER
        with patch.object(image_service.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=mock_membership):
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await image_service.set_primary("biz1", "user1", img.id)
            assert exc_info.value.status_code == 400
            assert "archived" in exc_info.value.detail.lower()


# ── Tenant Isolation Tests ──────────────────────────────────────────────

class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_cannot_access_other_business_image(self, image_service):
        """Business A cannot retrieve Business B's image."""
        await image_service.image_repo.create("biz-a", {
            "product_id": "prod1", "variant_id": None,
            "storage_key": "x", "original_filename": "x.jpg",
            "mime_type": "image/jpeg", "file_size": 100, "sort_order": 0,
            "is_primary": True, "status": "ACTIVE",
        })

        img = await image_service.image_repo.get_by_id(
            list(image_service.image_repo._images.keys())[0], "biz-b"
        )
        assert img is None


# ── RBAC Tests ───────────────────────────────────────────────────────────

class TestRBAC:
    @pytest.mark.asyncio
    async def test_cashier_cannot_upload(self, image_service):
        """MEMBER role cannot upload images."""
        mock_membership = MagicMock()
        mock_membership.role = BusinessMembershipRole.MEMBER
        with patch.object(image_service.membership_service, "require_active_membership", new_callable=AsyncMock, return_value=mock_membership):
            mock_file = MagicMock()
            mock_file.filename = "test.jpg"
            mock_file.content_type = "image/jpeg"
            mock_file.read = AsyncMock(return_value=_make_jpeg_bytes())

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await image_service.upload_image("biz1", "user1", "prod1", None, mock_file)
            assert exc_info.value.status_code == 403
