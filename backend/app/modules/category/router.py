from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.business_membership.service import BusinessMembershipService, business_membership_service
from app.modules.business_membership.schemas import BusinessMembershipRole, BusinessMembershipInDB
from app.modules.category.schemas import CategoryCreate, CategoryUpdate, CategoryResponse
from app.modules.category.service import CategoryService, category_service

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/categories",
    tags=["Category"],
)


def get_category_service() -> CategoryService:
    return category_service


def get_membership_service() -> BusinessMembershipService:
    return business_membership_service


async def require_business_member(
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    ms: BusinessMembershipService = Depends(get_membership_service),
) -> BusinessMembershipInDB:
    return await ms.require_active_membership(business_id, current_user.id)


async def require_business_admin(
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    ms: BusinessMembershipService = Depends(get_membership_service),
) -> BusinessMembershipInDB:
    membership = await ms.require_active_membership(business_id, current_user.id)
    if membership.role not in (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="OWNER or ADMIN role required.",
        )
    return membership


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    payload: CategoryCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    return await service.create_category(business_id, current_user.id, payload)


@router.get("", response_model=List[CategoryResponse])
async def list_categories(
    business_id: str = Path(...),
    parent_id: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    current_user: UserResponse = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
) -> List[CategoryResponse]:
    return await service.list_categories(
        business_id, current_user.id,
        parent_id=parent_id,
        include_archived=include_archived,
    )


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    business_id: str = Path(...),
    category_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    return await service.get_category(business_id, current_user.id, category_id)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    payload: CategoryUpdate,
    business_id: str = Path(...),
    category_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    return await service.update_category(business_id, current_user.id, category_id, payload)


@router.delete("/{category_id}", response_model=CategoryResponse)
async def archive_category(
    business_id: str = Path(...),
    category_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    return await service.archive_category(business_id, current_user.id, category_id)
