from typing import List, Optional
from fastapi import HTTPException, status

from app.modules.business_membership.schemas import (
    BusinessMembershipInDB,
    BusinessMembershipResponse,
    BusinessMembershipRole,
    BusinessMembershipStatus,
    AddBusinessMemberInput,
    UpdateBusinessMemberInput,
)
from app.modules.business_membership.repository import (
    AbstractBusinessMembershipRepository,
    business_membership_repository,
)
from app.modules.authentication.repository import user_repository, AbstractUserRepository
from app.modules.account.repository import account_repository, AbstractAccountRepository


class BusinessMembershipService:
    def __init__(
        self,
        repository: AbstractBusinessMembershipRepository = business_membership_repository,
        user_repo: AbstractUserRepository = user_repository,
        account_repo: AbstractAccountRepository = account_repository,
    ):
        self.repository = repository
        self.user_repo = user_repo
        self.account_repo = account_repo

    async def create_owner_membership(self, business_id: str, user_id: str) -> BusinessMembershipInDB:
        """Create the mandatory initial OWNER membership when a Business is created."""
        existing = await self.repository.get_by_business_and_user(business_id, user_id)
        if existing:
            return existing
        return await self.repository.create(
            business_id=business_id,
            user_id=user_id,
            role=BusinessMembershipRole.OWNER,
            status=BusinessMembershipStatus.ACTIVE,
        )

    async def get_active_membership(
        self, business_id: str, user_id: str
    ) -> Optional[BusinessMembershipInDB]:
        """Fetch active membership for user in business, returns None if non-existent or inactive."""
        membership = await self.repository.get_by_business_and_user(business_id, user_id)
        if not membership or membership.status != BusinessMembershipStatus.ACTIVE:
            return None
        return membership

    async def require_active_membership(
        self, business_id: str, user_id: str
    ) -> BusinessMembershipInDB:
        """Enforce active membership or raise 404 (for anti-enumeration / access denial)."""
        membership = await self.get_active_membership(business_id, user_id)
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found or access denied.",
            )
        return membership

    async def _enrich_membership(
        self, membership: BusinessMembershipInDB
    ) -> BusinessMembershipResponse:
        user = await self.user_repo.get_by_id(membership.user_id)
        account = await self.account_repo.get_by_user_id(membership.user_id)
        
        email = user.email if user else None
        display_name = account.display_name if account else (user.full_name if user else None)

        return BusinessMembershipResponse(
            id=membership.id,
            business_id=membership.business_id,
            user_id=membership.user_id,
            role=membership.role,
            status=membership.status,
            created_at=membership.created_at,
            updated_at=membership.updated_at,
            email=email,
            display_name=display_name,
        )

    async def add_member(
        self, requester_id: str, business_id: str, payload: AddBusinessMemberInput
    ) -> BusinessMembershipResponse:
        requester_membership = await self.require_active_membership(business_id, requester_id)

        # Only OWNER or ADMIN can add member
        if requester_membership.role not in (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only business OWNER or ADMIN can add members.",
            )

        # Cannot assign OWNER role via add_member
        if payload.role == BusinessMembershipRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign OWNER role. A business must have exactly one OWNER.",
            )

        # Target user must exist
        target_user = await self.user_repo.get_by_id(payload.user_id)
        if not target_user or not target_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target user not found or inactive.",
            )

        # Target user must not already have a membership record in this business
        existing = await self.repository.get_by_business_and_user(business_id, payload.user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has a membership record in this business.",
            )

        new_membership = await self.repository.create(
            business_id=business_id,
            user_id=payload.user_id,
            role=payload.role,
            status=BusinessMembershipStatus.ACTIVE,
        )
        return await self._enrich_membership(new_membership)

    async def list_members(
        self, requester_id: str, business_id: str
    ) -> List[BusinessMembershipResponse]:
        requester_membership = await self.require_active_membership(business_id, requester_id)

        # OWNER and ADMIN allowed, MEMBER denied
        if requester_membership.role not in (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied to list business members.",
            )

        memberships = await self.repository.list_by_business(business_id)
        enriched = []
        for m in memberships:
            enriched.append(await self._enrich_membership(m))
        return enriched

    async def get_membership(
        self, requester_id: str, business_id: str, membership_id: str
    ) -> BusinessMembershipResponse:
        requester_membership = await self.require_active_membership(business_id, requester_id)

        if requester_membership.role not in (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied to view membership.",
            )

        target = await self.repository.get_by_id(membership_id)
        if not target or target.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Membership not found in this business.",
            )

        return await self._enrich_membership(target)

    async def update_member(
        self,
        requester_id: str,
        business_id: str,
        membership_id: str,
        payload: UpdateBusinessMemberInput,
    ) -> BusinessMembershipResponse:
        requester_membership = await self.require_active_membership(business_id, requester_id)

        if requester_membership.role not in (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied to update members.",
            )

        target = await self.repository.get_by_id(membership_id)
        if not target or target.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Membership not found in this business.",
            )

        # OWNER Invariants & Rules:
        # 1. Cannot modify OWNER membership (role, status, suspend, demote, remove)
        if target.role == BusinessMembershipRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify, demote, suspend, or remove the Business OWNER.",
            )

        # 2. Cannot promote anyone to OWNER
        if payload.role == BusinessMembershipRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot promote a member to OWNER. A business must have exactly one OWNER.",
            )

        # 3. ADMIN cannot modify another ADMIN or OWNER if restrictions apply, but minimum requirement:
        # ADMIN can update non-owner member. If target is OWNER, blocked above.
        
        updated = await self.repository.update(
            membership_id=membership_id,
            role=payload.role,
            status=payload.status,
        )
        return await self._enrich_membership(updated)

    async def suspend_member(
        self, requester_id: str, business_id: str, membership_id: str
    ) -> BusinessMembershipResponse:
        return await self.update_member(
            requester_id=requester_id,
            business_id=business_id,
            membership_id=membership_id,
            payload=UpdateBusinessMemberInput(status=BusinessMembershipStatus.SUSPENDED),
        )

    async def remove_member(
        self, requester_id: str, business_id: str, membership_id: str
    ) -> BusinessMembershipResponse:
        return await self.update_member(
            requester_id=requester_id,
            business_id=business_id,
            membership_id=membership_id,
            payload=UpdateBusinessMemberInput(status=BusinessMembershipStatus.REMOVED),
        )

    async def get_active_businesses_for_user(self, user_id: str) -> List[str]:
        """Returns list of business_ids where user has an ACTIVE membership."""
        memberships = await self.repository.list_by_user(user_id)
        return [
            m.business_id for m in memberships
            if m.status == BusinessMembershipStatus.ACTIVE
        ]


business_membership_service = BusinessMembershipService()
