from typing import List
from fastapi import APIRouter, Depends, Path, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.branch.schemas import (
    BranchResponse,
    BranchCreate,
    BranchUpdate,
)
from app.modules.branch.service import (
    BranchService,
    branch_service,
)

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/branches",
    tags=["Branch"],
)


def get_branch_service() -> BranchService:
    return branch_service


@router.post("", response_model=BranchResponse, status_code=201)
async def create_branch(
    payload: BranchCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    """
    Create a new branch under the specified business.
    Requires OWNER or ADMIN active membership.
    """
    return await service.create_branch(
        business_id=business_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.get("", response_model=List[BranchResponse])
async def list_branches(
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service),
) -> List[BranchResponse]:
    """
    List branches belonging to the specified business.
    Requires active membership (OWNER, ADMIN, or MEMBER).
    """
    return await service.list_branches(
        business_id=business_id,
        user_id=current_user.id,
    )


@router.get("/{branch_id}", response_model=BranchResponse)
async def get_branch(
    business_id: str = Path(...),
    branch_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    """
    Get details of a specific branch.
    Requires active membership. Enforces business boundary.
    """
    return await service.get_branch(
        business_id=business_id,
        branch_id=branch_id,
        user_id=current_user.id,
    )


@router.patch("/{branch_id}", response_model=BranchResponse)
async def update_branch(
    payload: BranchUpdate,
    business_id: str = Path(...),
    branch_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    """
    Update details of a branch.
    Requires OWNER or ADMIN active membership.
    """
    return await service.update_branch(
        business_id=business_id,
        branch_id=branch_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.post("/{branch_id}/suspend", response_model=BranchResponse)
async def suspend_branch(
    business_id: str = Path(...),
    branch_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    """
    Suspend a branch.
    If the branch was default, another active branch is selected as default.
    Requires OWNER or ADMIN active membership.
    """
    return await service.suspend_branch(
        business_id=business_id,
        branch_id=branch_id,
        user_id=current_user.id,
    )


@router.delete("/{branch_id}", response_model=BranchResponse)
async def archive_branch(
    business_id: str = Path(...),
    branch_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    """
    Soft-archive a branch (status set to ARCHIVED).
    If the branch was default, another active branch is selected as default.
    Requires OWNER or ADMIN active membership.
    """
    return await service.archive_branch(
        business_id=business_id,
        branch_id=branch_id,
        user_id=current_user.id,
    )


@router.post("/{branch_id}/default", response_model=BranchResponse)
async def set_default_branch(
    business_id: str = Path(...),
    branch_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service),
) -> BranchResponse:
    """
    Set a branch as the default branch for the business.
    Target branch must be ACTIVE.
    Requires OWNER or ADMIN active membership.
    """
    return await service.set_default_branch(
        business_id=business_id,
        branch_id=branch_id,
        user_id=current_user.id,
    )
