from typing import List, Optional
from fastapi import HTTPException, status

from app.modules.branch.schemas import (
    BranchInDB,
    BranchCreate,
    BranchUpdate,
    BranchStatus,
)
from app.modules.branch.repository import (
    AbstractBranchRepository,
    branch_repository,
)
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import (
    BusinessMembershipRole,
    BusinessMembershipInDB,
)
from app.modules.business.repository import (
    AbstractBusinessRepository,
    business_repository,
)
from app.modules.business.schemas import BusinessStatus


class BranchService:
    def __init__(
        self,
        repository: AbstractBranchRepository = branch_repository,
        membership_service: BusinessMembershipService = business_membership_service,
        business_repo: AbstractBusinessRepository = business_repository,
    ):
        self.repository = repository
        self.membership_service = membership_service
        self.business_repo = business_repo

    async def _validate_access(
        self, business_id: str, user_id: str, required_roles: Optional[tuple[BusinessMembershipRole, ...]] = None
    ) -> BusinessMembershipInDB:
        """
        Validate that:
        1. The business exists and is active (not archived).
        2. The user has an ACTIVE membership in this business.
        3. The membership role is in required_roles (if specified).
        Raises 404 for missing/archived business or inactive membership (anti-enumeration).
        Raises 403 if role is insufficient.
        """
        business = await self.business_repo.get_by_id(business_id)
        if not business or business.status == BusinessStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found or access denied.",
            )

        membership = await self.membership_service.require_active_membership(business_id, user_id)

        if required_roles and membership.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied for this branch operation.",
            )

        return membership

    async def _pick_next_default_branch(self, business_id: str, exclude_branch_id: str) -> None:
        """
        Select another ACTIVE branch in business_id to become default deterministically.
        Order: created_at ASC, id ASC.
        If no ACTIVE branch exists, business will have 0 default branches.
        """
        branches = await self.repository.list_by_business(business_id)
        active_candidates = [
            b for b in branches
            if b.id != exclude_branch_id and b.status == BranchStatus.ACTIVE
        ]
        if active_candidates:
            # Sort deterministically by created_at ASC, id ASC
            active_candidates.sort(key=lambda x: (x.created_at, x.id))
            next_default = active_candidates[0]
            await self.repository.set_default(business_id, next_default.id)

    async def create_branch(
        self, business_id: str, user_id: str, payload: BranchCreate
    ) -> BranchInDB:

        await self._validate_access(
            business_id, user_id, (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        # Name uniqueness within business (case-insensitive)
        existing_name = await self.repository.find_by_name(business_id, payload.name)
        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A branch with name '{payload.name}' already exists in this business.",
            )

        # Code uniqueness within business (case-insensitive)
        existing_code = await self.repository.find_by_code(business_id, payload.code)
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A branch with code '{payload.code}' already exists in this business.",
            )

        # Check if first active branch in this business -> auto-set as default
        active_count = await self.repository.count_active(business_id)
        is_default = (active_count == 0)

        branch = await self.repository.create(business_id, payload, is_default=is_default)
        return branch

    async def list_branches(self, business_id: str, user_id: str) -> List[BranchInDB]:
        # OWNER, ADMIN, MEMBER all allowed to read
        await self._validate_access(business_id, user_id)
        return await self.repository.list_by_business(business_id)

    async def get_branch(
        self, business_id: str, branch_id: str, user_id: str
    ) -> BranchInDB:
        await self._validate_access(business_id, user_id)

        branch = await self.repository.get_by_id(branch_id)
        if not branch or branch.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found.",
            )

        return branch

    async def update_branch(
        self, business_id: str, branch_id: str, user_id: str, payload: BranchUpdate
    ) -> BranchInDB:
        await self._validate_access(
            business_id, user_id, (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        branch = await self.repository.get_by_id(branch_id)
        if not branch or branch.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found.",
            )

        if branch.status == BranchStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update an archived branch.",
            )

        # Check name uniqueness if updated
        if payload.name and payload.name.strip().lower() != branch.name.strip().lower():
            existing_name = await self.repository.find_by_name(business_id, payload.name)
            if existing_name and existing_name.id != branch_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A branch with name '{payload.name}' already exists in this business.",
                )

        # Check code uniqueness if updated
        if payload.code and payload.code.strip().upper() != branch.code.strip().upper():
            existing_code = await self.repository.find_by_code(business_id, payload.code)
            if existing_code and existing_code.id != branch_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A branch with code '{payload.code}' already exists in this business.",
                )

        updated = await self.repository.update(branch_id, payload)
        return updated

    async def suspend_branch(
        self, business_id: str, branch_id: str, user_id: str
    ) -> BranchInDB:
        await self._validate_access(
            business_id, user_id, (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        branch = await self.repository.get_by_id(branch_id)
        if not branch or branch.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found.",
            )

        if branch.status == BranchStatus.SUSPENDED:
            return branch

        was_default = branch.is_default
        suspended = await self.repository.suspend(branch_id)

        if was_default:
            await self._pick_next_default_branch(business_id, branch_id)

        return suspended

    async def archive_branch(
        self, business_id: str, branch_id: str, user_id: str
    ) -> BranchInDB:
        await self._validate_access(
            business_id, user_id, (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        branch = await self.repository.get_by_id(branch_id)
        if not branch or branch.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found.",
            )

        if branch.status == BranchStatus.ARCHIVED:
            return branch

        was_default = branch.is_default
        archived = await self.repository.archive(branch_id)

        if was_default:
            await self._pick_next_default_branch(business_id, branch_id)

        return archived

    async def set_default_branch(
        self, business_id: str, branch_id: str, user_id: str
    ) -> BranchInDB:
        await self._validate_access(
            business_id, user_id, (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        branch = await self.repository.get_by_id(branch_id)
        if not branch or branch.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found.",
            )

        if branch.status != BranchStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only an ACTIVE branch can be set as default.",
            )

        updated_default = await self.repository.set_default(business_id, branch_id)
        return updated_default


branch_service = BranchService()
