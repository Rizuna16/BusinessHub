from typing import List, Optional
from fastapi import HTTPException, status

from app.modules.product_variant.repository import (
    AbstractProductVariantRepository,
    InMemoryProductVariantRepository,
    ProductVariantInDB,
    product_variant_repository,
)
from app.modules.product_variant.schemas import (
    ProductVariantCreate,
    ProductVariantUpdate,
    ProductVariantStatus,
    ProductVariantResponse,
    ProductVariantListResponse,
)
from app.modules.product.repository import (
    AbstractProductRepository,
    InMemoryProductRepository,
)
from app.modules.product.schemas import ProductStatus, ProductType
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole


class ProductVariantService:
    def __init__(
        self,
        repository: AbstractProductVariantRepository = product_variant_repository,
        membership_service: BusinessMembershipService = business_membership_service,
        product_repository: AbstractProductRepository = InMemoryProductRepository(),
    ):
        self.repository = repository
        self.membership_service = membership_service
        self.product_repository = product_repository

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

    async def _validate_product(self, business_id: str, product_id: str):
        product = await self.product_repository.get_by_id(product_id, business_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found in this business.",
            )
        if product.status == ProductStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot manage variants for an archived product.",
            )
        if product.product_type != ProductType.GOODS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Variants are only supported for GOODS product type.",
            )
        return product

    async def create_variant(
        self, business_id: str, product_id: str, user_id: str, data: ProductVariantCreate
    ) -> ProductVariantResponse:
        await self._require_admin_or_owner(business_id, user_id)
        await self._validate_product(business_id, product_id)

        # Validate code uniqueness (case-insensitive) within Business
        existing_code = await self.repository.find_by_code(business_id, data.code)
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Variant code '{data.code.upper()}' already exists in this business.",
            )

        variant = await self.repository.create(
            business_id=business_id,
            product_id=product_id,
            variant_data=data,
        )
        return ProductVariantResponse.from_db(variant)

    async def get_variant(
        self, business_id: str, user_id: str, product_id: str, variant_id: str
    ) -> ProductVariantResponse:
        await self._require_active_membership(business_id, user_id)
        variant = await self.repository.get_by_id(variant_id, business_id)
        if not variant or variant.product_id != product_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Variant not found.",
            )
        return ProductVariantResponse.from_db(variant)

    async def list_variants(
        self, business_id: str, user_id: str, product_id: str
    ) -> ProductVariantListResponse:
        await self._require_active_membership(business_id, user_id)
        await self._validate_product(business_id, product_id)

        variants = await self.repository.list_by_product(
            business_id=business_id,
            product_id=product_id,
            include_archived=False,
        )
        return ProductVariantListResponse(
            items=[ProductVariantResponse.from_db(v) for v in variants],
            total=len(variants),
        )

    async def update_variant(
        self,
        business_id: str,
        user_id: str,
        product_id: str,
        variant_id: str,
        data: ProductVariantUpdate,
    ) -> ProductVariantResponse:
        await self._require_admin_or_owner(business_id, user_id)
        await self._validate_product(business_id, product_id)

        variant = await self.repository.get_by_id(variant_id, business_id)
        if not variant or variant.product_id != product_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Variant not found.",
            )

        if variant.status == ProductVariantStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update an archived variant.",
            )

        if data.code is not None:
            existing = await self.repository.find_by_code(business_id, data.code)
            if existing and existing.id != variant_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Variant code '{data.code.upper()}' already exists in this business.",
                )

        updated = await self.repository.update(variant_id, business_id, data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Variant not found.",
            )
        return ProductVariantResponse.from_db(updated)

    async def archive_variant(
        self, business_id: str, user_id: str, product_id: str, variant_id: str
    ) -> ProductVariantResponse:
        await self._require_admin_or_owner(business_id, user_id)

        variant = await self.repository.get_by_id(variant_id, business_id)
        if not variant or variant.product_id != product_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Variant not found.",
            )

        if variant.status == ProductVariantStatus.ARCHIVED:
            return ProductVariantResponse.from_db(variant)

        archived = await self.repository.archive(variant_id, business_id)
        if not archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Variant not found.",
            )
        return ProductVariantResponse.from_db(archived)


product_variant_service = ProductVariantService()
