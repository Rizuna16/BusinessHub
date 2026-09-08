from typing import List, Optional
from fastapi import HTTPException, status

from app.modules.barcode.repository import (
    AbstractBarcodeRepository,
    barcode_repository,
    BarcodeInDB,
)
from app.modules.barcode.schemas import (
    BarcodeCreate,
    BarcodeUpdate,
    BarcodeStatus,
    BarcodeResponse,
    BarcodeListResponse,
)
from app.modules.business_membership.service import BusinessMembershipService, business_membership_service
from app.modules.business_membership.schemas import BusinessMembershipRole
from app.modules.product.repository import product_repository, AbstractProductRepository
from app.modules.product.schemas import ProductStatus
from app.modules.product_variant.repository import product_variant_repository, AbstractProductVariantRepository
from app.modules.product_variant.schemas import ProductVariantStatus


class BarcodeService:
    def __init__(
        self,
        repository: AbstractBarcodeRepository = barcode_repository,
        membership_service: BusinessMembershipService = business_membership_service,
        product_repo: AbstractProductRepository = product_repository,
        variant_repo: AbstractProductVariantRepository = product_variant_repository,
    ):
        self.repository = repository
        self.membership_service = membership_service
        self.product_repo = product_repo
        self.variant_repo = variant_repo

    async def _require_active_membership(self, business_id: str, user_id: str):
        return await self.membership_service.require_active_membership(business_id, user_id)

    async def _require_admin_or_owner(self, business_id: str, user_id: str):
        membership = await self._require_active_membership(business_id, user_id)
        if membership.role not in (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="OWNER or ADMIN role required.",
            )
        return membership

    async def _validate_target(self, business_id: str, product_id: Optional[str], variant_id: Optional[str]):
        if product_id:
            product = await self.product_repo.get_by_id(product_id, business_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Product not found.",
                )
            if product.status == ProductStatus.ARCHIVED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot assign barcode to an archived product.",
                )
        if variant_id:
            variant = await self.variant_repo.get_by_id(variant_id, business_id)
            if not variant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Product variant not found.",
                )
            if variant.status == ProductVariantStatus.ARCHIVED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot assign barcode to an archived variant.",
                )
            product = await self.product_repo.get_by_id(variant.product_id, business_id)
            if not product or product.status == ProductStatus.ARCHIVED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent product must exist and be active.",
                )

    async def create_barcode(
        self, business_id: str, user_id: str, data: BarcodeCreate
    ) -> BarcodeResponse:
        await self._require_admin_or_owner(business_id, user_id)
        await self._validate_target(business_id, data.product_id, data.variant_id)

        # Code uniqueness (case-insensitive) within business
        existing = await self.repository.find_by_code(business_id, data.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Barcode '{data.code}' already exists in this business.",
            )

        barcode = await self.repository.create(business_id, data)
        return BarcodeResponse.from_db(barcode)

    async def get_barcode(
        self, business_id: str, user_id: str, barcode_id: str
    ) -> BarcodeResponse:
        await self._require_active_membership(business_id, user_id)
        barcode = await self.repository.get_by_id(barcode_id, business_id)
        if not barcode or barcode.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Barcode not found.",
            )
        return BarcodeResponse.from_db(barcode)

    async def list_barcodes(
        self,
        business_id: str,
        user_id: str,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
    ) -> BarcodeListResponse:
        await self._require_active_membership(business_id, user_id)

        if product_id:
            items = await self.repository.list_by_product(business_id, product_id)
        elif variant_id:
            items = await self.repository.list_by_variant(business_id, variant_id)
        else:
            items = await self.repository.list_by_business(business_id)

        responses = [BarcodeResponse.from_db(item) for item in items]
        return BarcodeListResponse(items=responses, total=len(responses))

    async def update_barcode(
        self,
        business_id: str,
        user_id: str,
        barcode_id: str,
        data: BarcodeUpdate,
    ) -> BarcodeResponse:
        await self._require_admin_or_owner(business_id, user_id)
        barcode = await self.repository.get_by_id(barcode_id, business_id)
        if not barcode or barcode.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Barcode not found.",
            )

        if data.code and data.code.lower() != barcode.code.lower():
            existing = await self.repository.find_by_code(business_id, data.code)
            if existing and existing.id != barcode_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Barcode '{data.code}' already exists in this business.",
                )

        updated = await self.repository.update(barcode_id, business_id, data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Barcode not found.",
            )
        return BarcodeResponse.from_db(updated)

    async def archive_barcode(
        self, business_id: str, user_id: str, barcode_id: str
    ) -> BarcodeResponse:
        await self._require_admin_or_owner(business_id, user_id)
        barcode = await self.repository.get_by_id(barcode_id, business_id)
        if not barcode or barcode.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Barcode not found.",
            )

        archived = await self.repository.archive(barcode_id, business_id)
        if not archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Barcode not found.",
            )
        return BarcodeResponse.from_db(archived)


barcode_service = BarcodeService()
