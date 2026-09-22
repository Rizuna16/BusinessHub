from typing import List, Optional
from fastapi import HTTPException, status

from app.modules.product.repository import (
    AbstractProductRepository,
    InMemoryProductRepository,
    ProductInDB,
)
from app.modules.product.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductStatus,
    ProductType,
    ProductResponse,
    ProductListResponse,
)
from app.modules.category.repository import category_repository, CategoryStatus
from app.modules.unit.repository import unit_repository, UnitStatus
from app.modules.business_membership.service import BusinessMembershipService, business_membership_service
from app.modules.business_membership.schemas import BusinessMembershipRole


class ProductService:
    def __init__(
        self,
        repository: AbstractProductRepository = InMemoryProductRepository(),
        membership_service: BusinessMembershipService = business_membership_service,
        category_repo=category_repository,
        unit_repo=unit_repository,
    ):
        self.repository = repository
        self.membership_service = membership_service
        self.category_repo = category_repo
        self.unit_repo = unit_repo

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

    async def _validate_category(self, business_id: str, category_id: Optional[str]):
        if category_id is not None:
            category = await self.category_repo.get_by_id(category_id, business_id)
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category not found in this business.",
                )
            if category.status == CategoryStatus.ARCHIVED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot assign an archived category to a product.",
                )

    async def _validate_unit(self, business_id: str, unit_id: str):
        if not unit_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unit ID is required.",
            )
        unit = await self.unit_repo.get_by_id(unit_id, business_id)
        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found in this business.",
            )
        if unit.status == UnitStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign an archived unit to a product.",
            )

    async def create_product(
        self, business_id: str, user_id: str, data: ProductCreate
    ) -> ProductResponse:
        await self._require_admin_or_owner(business_id, user_id)

        # Feature #63: quota enforcement
        from app.modules.subscription.service import SubscriptionService
        await SubscriptionService().check_quota(business_id, "max_products")

        # Validate code uniqueness (case-insensitive) within Business
        existing_code = await self.repository.find_by_code(business_id, data.code)
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product code '{data.code.upper()}' already exists in this business.",
            )

        # Validate category ownership and status
        await self._validate_category(business_id, data.category_id)

        # Validate unit ownership and status
        await self._validate_unit(business_id, data.unit_id)

        product = await self.repository.create(business_id=business_id, product_data=data)
        return ProductResponse.from_db(product)

    async def get_product(
        self, business_id: str, user_id: str, product_id: str
    ) -> ProductResponse:
        await self._require_active_membership(business_id, user_id)
        product = await self.repository.get_by_id(product_id, business_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found.",
            )
        return ProductResponse.from_db(product)

    async def list_products(
        self,
        business_id: str,
        user_id: str,
        status: Optional[ProductStatus] = None,
        product_type: Optional[ProductType] = None,
        category_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> ProductListResponse:
        await self._require_active_membership(business_id, user_id)

        # Bound page_size
        if page_size < 1:
            page_size = 50
        elif page_size > 100:
            page_size = 100

        if page < 1:
            page = 1

        all_items = await self.repository.list_by_business(
            business_id=business_id,
            status=status,
            product_type=product_type,
            category_id=category_id,
            search=search,
            include_archived=False,
        )

        total = len(all_items)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = all_items[start_idx:end_idx]

        return ProductListResponse(
            items=[ProductResponse.from_db(item) for item in paginated_items],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def update_product(
        self,
        business_id: str,
        user_id: str,
        product_id: str,
        data: ProductUpdate,
    ) -> ProductResponse:
        await self._require_admin_or_owner(business_id, user_id)

        product = await self.repository.get_by_id(product_id, business_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found.",
            )

        if product.status == ProductStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update an archived product.",
            )

        # If code is updated, check uniqueness
        if data.code is not None:
            existing = await self.repository.find_by_code(business_id, data.code)
            if existing and existing.id != product_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Product code '{data.code.upper()}' already exists.",
                )

        # Validate category if changed
        if data.category_id is not None:
            await self._validate_category(business_id, data.category_id)

        # Validate unit if changed
        if data.unit_id is not None:
            await self._validate_unit(business_id, data.unit_id)

        updated = await self.repository.update(product_id, business_id, data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found.",
            )
        return ProductResponse.from_db(updated)

    async def archive_product(
        self, business_id: str, user_id: str, product_id: str
    ) -> ProductResponse:
        await self._require_admin_or_owner(business_id, user_id)

        product = await self.repository.get_by_id(product_id, business_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found.",
            )

        if product.status == ProductStatus.ARCHIVED:
            # Idempotent or return current
            return ProductResponse.from_db(product)

        archived = await self.repository.archive(product_id, business_id)
        if not archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found.",
            )
        return ProductResponse.from_db(archived)


product_service = ProductService()
