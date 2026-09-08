from typing import List, Optional
from fastapi import HTTPException, status

from app.modules.category.repository import (
    AbstractCategoryRepository,
    category_repository,
    CategoryInDB,
)
from app.modules.category.schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryStatus,
    CategoryResponse,
)
from app.modules.business_membership.service import BusinessMembershipService, business_membership_service
from app.modules.business_membership.schemas import BusinessMembershipRole


class CategoryService:
    def __init__(
        self,
        repository: AbstractCategoryRepository = category_repository,
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.repository = repository
        self.membership_service = membership_service

    async def _require_admin_or_owner(self, business_id: str, user_id: str):
        membership = await self.membership_service.require_active_membership(business_id, user_id)
        if membership.role not in (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="OWNER or ADMIN role required.",
            )
        return membership

    async def create_category(
        self, business_id: str, user_id: str, data: CategoryCreate
    ) -> CategoryResponse:
        await self._require_admin_or_owner(business_id, user_id)

        # Code uniqueness (case-insensitive) within Business
        existing_code = await self.repository.find_by_code(business_id, data.code)
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Category code '{data.code.upper()}' already exists in this business.",
            )

        # Name uniqueness (case-insensitive) within Business
        existing_name = await self.repository.find_by_name(business_id, data.name)
        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Category name '{data.name}' already exists in this business.",
            )

        # Parent validation
        parent = None
        if data.parent_id:
            parent = await self.repository.get_by_id(data.parent_id, business_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent category not found.",
                )
            if parent.status == CategoryStatus.ARCHIVED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot assign a child category to an archived parent.",
                )

            # Max depth check (3 levels)
            depth = 1
            current = parent
            while current and current.parent_id and depth < 10:
                next_parent = await self.repository.get_by_id(current.parent_id, business_id)
                if not next_parent:
                    break
                current = next_parent
                depth += 1
            if depth >= 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Maximum category depth of 3 levels exceeded.",
                )

            # Prevent circular reference
            if await self._is_descendant(data.parent_id, data.parent_id, business_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Circular reference detected in category hierarchy.",
                )

        category = await self.repository.create(business_id=business_id, category_data=data)
        return self._to_response(category, False)

    async def _is_descendant(self, category_id: str, target_id: str, business_id: str) -> bool:
        """Check if target_id is a descendant of category_id (for circular check)."""
        children = await self.repository.list_children(business_id, category_id)
        for child in children:
            if child.id == target_id:
                return True
            if await self._is_descendant(child.id, target_id, business_id):
                return True
        return False

    async def get_category(self, business_id: str, user_id: str, category_id: str) -> CategoryResponse:
        await self.membership_service.require_active_membership(business_id, user_id)
        category = await self.repository.get_by_id(category_id, business_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )
        has_children = await self.repository.count_children(business_id, category_id) > 0
        return self._to_response(category, has_children)

    async def list_categories(
        self, business_id: str, user_id: str,
        parent_id: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[CategoryResponse]:
        await self.membership_service.require_active_membership(business_id, user_id)
        categories = await self.repository.list_by_business(
            business_id, parent_id=parent_id, include_archived=include_archived
        )
        results = []
        for cat in categories:
            has_children = await self.repository.count_children(business_id, cat.id) > 0
            results.append(self._to_response(cat, has_children))
        return results

    async def update_category(
        self, business_id: str, user_id: str, category_id: str, data: CategoryUpdate
    ) -> CategoryResponse:
        await self._require_admin_or_owner(business_id, user_id)

        category = await self.repository.get_by_id(category_id, business_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )

        # If changing code, check uniqueness
        if data.code:
            existing = await self.repository.find_by_code(business_id, data.code)
            if existing and existing.id != category_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Category code '{data.code.upper()}' already exists.",
                )

        # If changing name, check uniqueness
        if data.name:
            existing = await self.repository.find_by_name(business_id, data.name)
            if existing and existing.id != category_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Category name '{data.name}' already exists.",
                )

        # If changing parent, validate
        if data.parent_id is not None:
            if data.parent_id == category_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category cannot be parent of itself.",
                )
            parent = await self.repository.get_by_id(data.parent_id, business_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent category not found.",
                )
            if parent.status == CategoryStatus.ARCHIVED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot assign to an archived parent.",
                )

            # Check circular reference
            if await self._is_descendant(category_id, data.parent_id, business_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Circular reference detected in category hierarchy.",
                )

            # Max depth check
            depth = 1
            current = parent
            while current and current.parent_id and depth < 10:
                next_parent = await self.repository.get_by_id(current.parent_id, business_id)
                if not next_parent:
                    break
                current = next_parent
                depth += 1
            # category itself adds 1 level
            if depth >= 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Maximum category depth of 3 levels exceeded.",
                )

        updated = await self.repository.update(category_id, business_id, data)
        has_children = await self.repository.count_children(business_id, category_id) > 0
        return self._to_response(updated, has_children)

    async def archive_category(self, business_id: str, user_id: str, category_id: str) -> CategoryResponse:
        await self._require_admin_or_owner(business_id, user_id)

        category = await self.repository.get_by_id(category_id, business_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )

        # Check if has children
        child_count = await self.repository.count_children(business_id, category_id)
        if child_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot archive a category that has children. Archive children first.",
            )

        # Check if any existing child categories reference this as parent
        # Already covered by child_count above

        archived = await self.repository.archive(category_id, business_id)
        has_children = await self.repository.count_children(business_id, category_id) > 0
        return self._to_response(archived, has_children)

    def _to_response(self, category: CategoryInDB, has_children: bool) -> CategoryResponse:
        return CategoryResponse(
            id=category.id,
            business_id=category.business_id,
            name=category.name,
            code=category.code,
            description=category.description,
            parent_id=category.parent_id,
            status=category.status,
            sort_order=category.sort_order,
            created_at=category.created_at.isoformat(),
            updated_at=category.updated_at.isoformat(),
            has_children=has_children,
        )


category_service = CategoryService()
