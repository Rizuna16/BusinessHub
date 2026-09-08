from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.business_membership.service import BusinessMembershipService, business_membership_service
from app.modules.business_membership.schemas import BusinessMembershipRole, BusinessMembershipInDB
from app.modules.unit.schemas import UnitCreate, UnitUpdate, UnitResponse
from app.modules.unit.service import UnitService, unit_service

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/units",
    tags=["Unit"],
)


def get_unit_service() -> UnitService:
    return unit_service


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


@router.post("", response_model=UnitResponse, status_code=201)
async def create_unit(
    payload: UnitCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: UnitService = Depends(get_unit_service),
) -> UnitResponse:
    return await service.create_unit(business_id, current_user.id, payload)


@router.get("", response_model=List[UnitResponse])
async def list_units(
    business_id: str = Path(...),
    unit_type: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    current_user: UserResponse = Depends(get_current_user),
    service: UnitService = Depends(get_unit_service),
) -> List[UnitResponse]:
    return await service.list_units(
        business_id, current_user.id,
        unit_type=unit_type,
        include_archived=include_archived,
    )


@router.get("/{unit_id}", response_model=UnitResponse)
async def get_unit(
    business_id: str = Path(...),
    unit_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: UnitService = Depends(get_unit_service),
) -> UnitResponse:
    return await service.get_unit(business_id, current_user.id, unit_id)


@router.patch("/{unit_id}", response_model=UnitResponse)
async def update_unit(
    payload: UnitUpdate,
    business_id: str = Path(...),
    unit_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: UnitService = Depends(get_unit_service),
) -> UnitResponse:
    return await service.update_unit(business_id, current_user.id, unit_id, payload)


@router.delete("/{unit_id}", response_model=UnitResponse)
async def archive_unit(
    business_id: str = Path(...),
    unit_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: UnitService = Depends(get_unit_service),
) -> UnitResponse:
    return await service.archive_unit(business_id, current_user.id, unit_id)
