from typing import List, Optional
from fastapi import HTTPException, status

from app.modules.business.schemas import BusinessInDB, BusinessCreate, BusinessUpdate, BusinessStatus
from app.modules.business.repository import AbstractBusinessRepository, business_repository, _generate_slug
from app.modules.business_membership.service import BusinessMembershipService, business_membership_service
from app.modules.business_membership.schemas import BusinessMembershipRole


class BusinessService:
    def __init__(
        self,
        repository: AbstractBusinessRepository = business_repository,
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.repository = repository
        self.membership_service = membership_service

    async def create_business(self, business_data: BusinessCreate, owner_user_id: str) -> BusinessInDB:
        """
        Create a new Business.
        - owner_user_id comes ONLY from authenticated context.
        - Slug generated server-side with collision handling.
        - Automatically creates corresponding OWNER BusinessMembership.
        """
        used_slugs = self.repository.get_used_slugs()
        slug = _generate_slug(business_data.name, used_slugs)
        business = await self.repository.create(business_data, owner_user_id, slug)

        # Create mandatory OWNER membership
        await self.membership_service.create_owner_membership(business.id, owner_user_id)

        # Initialize BusinessConfiguration snapshot based on template resolution
        try:
            from app.modules.business_template.service import business_configuration_service
            await business_configuration_service.initialize_configuration_for_business(
                business_id=business.id,
                business_type=business_data.business_type.value,
            )
        except Exception:
            # Configuration initialization is non-critical; business must be created
            pass

        return business

    async def get_business(self, business_id: str, user_id: str) -> BusinessInDB:
        """
        Get a business by ID, enforcing active membership access (tenant isolation).
        Archives are still retrievable by active members (soft-delete semantics).
        Raises 404 if the user has no active membership or the business record does not exist.
        """
        # Ensure user has active membership in this business
        await self.membership_service.require_active_membership(business_id, user_id)

        business = await self.repository.get_by_id(business_id)
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found.",
            )
        return business

    async def list_my_businesses(self, user_id: str) -> List[BusinessInDB]:
        """
        List active businesses where the authenticated user has an ACTIVE membership.
        """
        active_business_ids = await self.membership_service.get_active_businesses_for_user(user_id)
        if not active_business_ids:
            return []
        return await self.repository.list_by_ids(active_business_ids)

    async def update_business(
        self, business_id: str, user_id: str, update_data: BusinessUpdate
    ) -> BusinessInDB:
        """
        Update a business.
        - Requester must have active membership.
        - Role must be OWNER or ADMIN (MEMBER is read-only).
        """
        membership = await self.membership_service.require_active_membership(business_id, user_id)
        if membership.role not in (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Business MEMBER role is read-only. ADMIN or OWNER role required to update.",
            )

        business = await self.repository.get_by_id(business_id)
        if not business or business.status == BusinessStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found.",
            )

        updated_business = await self.repository.update(business_id, update_data)
        return updated_business

    async def archive_business(self, business_id: str, user_id: str) -> BusinessInDB:
        """
        Soft-archive a business.
        - Requester must have active membership.
        - Only OWNER can archive a business.
        """
        membership = await self.membership_service.require_active_membership(business_id, user_id)
        if membership.role != BusinessMembershipRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only business OWNER can archive a business.",
            )

        business = await self.repository.get_by_id(business_id)
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found.",
            )

        archived_business = await self.repository.archive(business_id)
        return archived_business

    async def count_businesses(self) -> int:
        return await self.repository.count()


business_service = BusinessService()
