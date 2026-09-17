from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.container import RepositoryContainer
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.business_membership.schemas import (
    BusinessMembershipResponse,
    AddBusinessMemberInput,
    UpdateBusinessMemberInput,
    BusinessMembershipRole,
    BusinessMembershipInDB,
)
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/members",
    tags=["BusinessMembership"],
)


def get_membership_service() -> BusinessMembershipService:
    return business_membership_service


async def get_scoped_membership_service(session: AsyncSession = Depends(get_db_session)) -> BusinessMembershipService:
    """
    Request-scoped BusinessMembershipService wired to the same AsyncSession.
    All repositories share the same AsyncSession for consistency.
    """
    container = RepositoryContainer(session)
    return BusinessMembershipService(
        repository=container.business_membership,
        user_repo=container.user,
        account_repo=container.account,
        business_repo=container.business,
        session=session,
    )


# Reusable Guards for Business Endpoints
async def require_business_membership(
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: BusinessMembershipService = Depends(get_scoped_membership_service),
) -> BusinessMembershipInDB:
    """Dependency ensuring requester has an ACTIVE membership in the specified business."""
    return await service.require_active_membership(business_id, current_user.id)


async def require_business_member(
    membership: BusinessMembershipInDB = Depends(require_business_membership),
) -> BusinessMembershipInDB:
    """Guard allowing OWNER, ADMIN, and MEMBER with active membership."""
    return membership


async def require_business_admin(
    membership: BusinessMembershipInDB = Depends(require_business_membership),
) -> BusinessMembershipInDB:
    """Guard allowing only OWNER and ADMIN with active membership."""
    if membership.role not in (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Business ADMIN or OWNER access required.",
        )
    return membership


async def require_business_owner(
    membership: BusinessMembershipInDB = Depends(require_business_membership),
) -> BusinessMembershipInDB:
    """Guard allowing only OWNER with active membership."""
    if membership.role != BusinessMembershipRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Business OWNER access required.",
        )
    return membership


@router.post("", response_model=BusinessMembershipResponse, status_code=201)
async def add_member(
    payload: AddBusinessMemberInput,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: BusinessMembershipService = Depends(get_scoped_membership_service),
) -> BusinessMembershipResponse:
    """
    Add a new member to the business.
    Requester must be an active OWNER or ADMIN in the business.
    """
    return await service.add_member(
        requester_id=current_user.id,
        business_id=business_id,
        payload=payload,
    )


@router.get("", response_model=List[BusinessMembershipResponse])
async def list_members(
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: BusinessMembershipService = Depends(get_scoped_membership_service),
) -> List[BusinessMembershipResponse]:
    """
    List members of the business.
    Requester must be an active OWNER or ADMIN in the business. MEMBER is denied.
    """
    return await service.list_members(
        requester_id=current_user.id,
        business_id=business_id,
    )


@router.get("/{membership_id}", response_model=BusinessMembershipResponse)
async def get_member(
    business_id: str = Path(...),
    membership_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: BusinessMembershipService = Depends(get_scoped_membership_service),
) -> BusinessMembershipResponse:
    """
    Get a specific membership in the business.
    Requester must be an active OWNER or ADMIN.
    """
    return await service.get_membership(
        requester_id=current_user.id,
        business_id=business_id,
        membership_id=membership_id,
    )


@router.patch("/{membership_id}", response_model=BusinessMembershipResponse)
async def update_member(
    payload: UpdateBusinessMemberInput,
    business_id: str = Path(...),
    membership_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: BusinessMembershipService = Depends(get_scoped_membership_service),
) -> BusinessMembershipResponse:
    """
    Update member role or status.
    Requester must be an active OWNER or ADMIN.
    OWNER cannot be modified, demoted, suspended, or removed.
    """
    return await service.update_member(
        requester_id=current_user.id,
        business_id=business_id,
        membership_id=membership_id,
        payload=payload,
    )


@router.delete("/{membership_id}", response_model=BusinessMembershipResponse)
async def remove_member(
    business_id: str = Path(...),
    membership_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: BusinessMembershipService = Depends(get_scoped_membership_service),
) -> BusinessMembershipResponse:
    """
    Soft-remove a member (status set to REMOVED).
    Requester must be an active OWNER or ADMIN.
    OWNER cannot be removed.
    """
    return await service.remove_member(
        requester_id=current_user.id,
        business_id=business_id,
        membership_id=membership_id,
    )
