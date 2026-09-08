from typing import List, Optional
from fastapi import HTTPException, status

from app.modules.supplier_catalog.repository import (
    AbstractSupplierCatalogRepository,
    supplier_catalog_repository,
    SupplierCatalogItemInDB,
)
from app.modules.supplier_catalog.schemas import (
    SupplierCatalogItemCreate,
    SupplierCatalogItemUpdate,
    SupplierCatalogStatus,
    SupplierCatalogItemResponse,
    SupplierCatalogItemListResponse,
)
from app.modules.supplier.repository import (
    AbstractSupplierRepository,
    supplier_repository,
    SupplierStatus,
)
from app.modules.product.repository import (
    AbstractProductRepository,
    product_repository,
    ProductStatus,
    ProductType,
)
from app.modules.product_variant.repository import (
    AbstractProductVariantRepository,
    product_variant_repository,
    ProductVariantStatus,
)
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole


class SupplierCatalogService:
    def __init__(
        self,
        repository: AbstractSupplierCatalogRepository = supplier_catalog_repository,
        sup_repo: AbstractSupplierRepository = supplier_repository,
        prod_repo: AbstractProductRepository = product_repository,
        var_repo: AbstractProductVariantRepository = product_variant_repository,
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.repository = repository
        self.sup_repo = sup_repo
        self.prod_repo = prod_repo
        self.var_repo = var_repo
        self.membership_service = membership_service

    async def _require_active_membership(self, business_id: str, user_id: str):
        return await self.membership_service.require_active_membership(
            business_id, user_id
        )

    async def _require_admin_or_owner(self, business_id: str, user_id: str):
        membership = await self._require_active_membership(business_id, user_id)
        if membership.role not in (
            BusinessMembershipRole.OWNER,
            BusinessMembershipRole.ADMIN,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="OWNER or ADMIN role required.",
            )
        return membership

    async def create_catalog_item(
        self, business_id: str, user_id: str, data: SupplierCatalogItemCreate
    ) -> SupplierCatalogItemResponse:
        await self._require_admin_or_owner(business_id, user_id)

        # 1. Supplier Validation
        supplier = await self.sup_repo.get_by_id(data.supplier_id, business_id)
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplier not found in this business.",
            )
        if supplier.status != SupplierStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot create catalog item for supplier with status '{supplier.status}'. Supplier must be ACTIVE.",
            )

        # 2. XOR Target Validation
        if data.product_id:
            product = await self.prod_repo.get_by_id(data.product_id, business_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product not found in this business.",
                )
            if product.status == ProductStatus.ARCHIVED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot create catalog item for archived product.",
                )
            if product.product_type != ProductType.GOODS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Supplier catalog item can only be created for GOODS products.",
                )
        elif data.variant_id:
            variant = await self.var_repo.get_by_id(data.variant_id, business_id)
            if not variant:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product variant not found in this business.",
                )
            if variant.status == ProductVariantStatus.ARCHIVED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot create catalog item for archived product variant.",
                )
            parent_product = await self.prod_repo.get_by_id(
                variant.product_id, business_id
            )
            if not parent_product or parent_product.status == ProductStatus.ARCHIVED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent product for variant is inactive or archived.",
                )
            if parent_product.product_type != ProductType.GOODS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Supplier catalog item can only be created for GOODS product variants.",
                )

        # 3. Duplicate check
        existing = await self.repository.find_existing_item(
            business_id=business_id,
            supplier_id=data.supplier_id,
            product_id=data.product_id,
            variant_id=data.variant_id,
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplier catalog item already exists for this supplier and product/variant.",
            )

        # 4. Preferred supplier invariant
        if data.is_preferred:
            await self.repository.unset_preferred_for_target(
                business_id=business_id,
                product_id=data.product_id,
                variant_id=data.variant_id,
            )

        item = await self.repository.create(business_id=business_id, item_data=data)
        return await self._to_response(item)

    async def get_catalog_item(
        self, business_id: str, user_id: str, item_id: str
    ) -> SupplierCatalogItemResponse:
        await self._require_active_membership(business_id, user_id)

        item = await self.repository.get_by_id(item_id, business_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier catalog item not found.",
            )
        return await self._to_response(item)

    async def list_catalog_items(
        self,
        business_id: str,
        user_id: str,
        search: Optional[str] = None,
        supplier_id: Optional[str] = None,
        product_id: Optional[str] = None,
        variant_id: Optional[str] = None,
        status_filter: Optional[SupplierCatalogStatus] = None,
        is_preferred: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SupplierCatalogItemListResponse:
        await self._require_active_membership(business_id, user_id)

        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page must be >= 1.",
            )
        if page_size < 1 or page_size > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page size must be between 1 and 100.",
            )

        items, total = await self.repository.list_by_business(
            business_id=business_id,
            search=search,
            supplier_id=supplier_id,
            product_id=product_id,
            variant_id=variant_id,
            status=status_filter,
            is_preferred=is_preferred,
            page=page,
            page_size=page_size,
        )

        responses = [await self._to_response(item) for item in items]
        return SupplierCatalogItemListResponse(
            items=responses,
            page=page,
            page_size=page_size,
            total=total,
        )

    async def update_catalog_item(
        self,
        business_id: str,
        user_id: str,
        item_id: str,
        data: SupplierCatalogItemUpdate,
    ) -> SupplierCatalogItemResponse:
        await self._require_admin_or_owner(business_id, user_id)

        item = await self.repository.get_by_id(item_id, business_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier catalog item not found.",
            )

        if item.status == SupplierCatalogStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archived catalog item cannot be updated.",
            )

        if data.is_preferred is True:
            await self.repository.unset_preferred_for_target(
                business_id=business_id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                exclude_item_id=item_id,
            )

        updated = await self.repository.update(item_id, business_id, data)
        return await self._to_response(updated)

    async def archive_catalog_item(
        self, business_id: str, user_id: str, item_id: str
    ) -> SupplierCatalogItemResponse:
        await self._require_admin_or_owner(business_id, user_id)

        item = await self.repository.get_by_id(item_id, business_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier catalog item not found.",
            )

        if item.status == SupplierCatalogStatus.ARCHIVED:
            return await self._to_response(item)

        updated = await self.repository.update_status(
            item_id, business_id, SupplierCatalogStatus.ARCHIVED
        )
        return await self._to_response(updated)

    async def activate_catalog_item(
        self, business_id: str, user_id: str, item_id: str
    ) -> SupplierCatalogItemResponse:
        await self._require_admin_or_owner(business_id, user_id)

        item = await self.repository.get_by_id(item_id, business_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier catalog item not found.",
            )

        if item.status == SupplierCatalogStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archived catalog item cannot be reactivated.",
            )

        if item.status == SupplierCatalogStatus.ACTIVE:
            return await self._to_response(item)

        updated = await self.repository.update_status(
            item_id, business_id, SupplierCatalogStatus.ACTIVE
        )
        return await self._to_response(updated)

    async def deactivate_catalog_item(
        self, business_id: str, user_id: str, item_id: str
    ) -> SupplierCatalogItemResponse:
        await self._require_admin_or_owner(business_id, user_id)

        item = await self.repository.get_by_id(item_id, business_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier catalog item not found.",
            )

        if item.status == SupplierCatalogStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archived catalog item cannot be deactivated.",
            )

        if item.status == SupplierCatalogStatus.INACTIVE:
            return await self._to_response(item)

        updated = await self.repository.update_status(
            item_id, business_id, SupplierCatalogStatus.INACTIVE
        )
        return await self._to_response(updated)

    async def _to_response(
        self, item: SupplierCatalogItemInDB
    ) -> SupplierCatalogItemResponse:
        supplier_name = None
        supplier = await self.sup_repo.get_by_id(item.supplier_id, item.business_id)
        if supplier:
            supplier_name = supplier.name

        product_name = None
        product_code = None
        if item.product_id:
            prod = await self.prod_repo.get_by_id(item.product_id, item.business_id)
            if prod:
                product_name = prod.name
                product_code = prod.code

        variant_name = None
        variant_code = None
        if item.variant_id:
            var = await self.var_repo.get_by_id(item.variant_id, item.business_id)
            if var:
                variant_name = var.name
                variant_code = var.code
                if not product_name:
                    parent = await self.prod_repo.get_by_id(
                        var.product_id, item.business_id
                    )
                    if parent:
                        product_name = parent.name
                        product_code = parent.code

        return SupplierCatalogItemResponse(
            id=item.id,
            business_id=item.business_id,
            supplier_id=item.supplier_id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            supplier_code=item.supplier_code,
            supplier_product_name=item.supplier_product_name,
            purchase_price=str(item.purchase_price),
            currency=item.currency,
            minimum_order_quantity=(
                str(item.minimum_order_quantity)
                if item.minimum_order_quantity is not None
                else None
            ),
            lead_time_days=item.lead_time_days,
            is_preferred=item.is_preferred,
            status=item.status,
            notes=item.notes,
            created_at=item.created_at.isoformat(),
            updated_at=item.updated_at.isoformat(),
            supplier_name=supplier_name,
            product_name=product_name,
            product_code=product_code,
            variant_name=variant_name,
            variant_code=variant_code,
        )


supplier_catalog_service = SupplierCatalogService()
