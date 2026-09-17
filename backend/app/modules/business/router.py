from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.container import RepositoryContainer
from app.modules.business.schemas import BusinessCreate, BusinessResponse, BusinessUpdate
from app.modules.business.service import BusinessService, business_service
from app.modules.business_membership.service import BusinessMembershipService
from app.modules.subscription.service import SubscriptionService
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse

router = APIRouter(prefix=settings.api_v1_prefix + "/businesses", tags=["Business"])


def get_business_service() -> BusinessService:
    return business_service


async def get_scoped_business_service(session: AsyncSession = Depends(get_db_session)) -> BusinessService:
    """
    Request-scoped BusinessService wired to the same AsyncSession for transaction boundary.
    All repositories share the same AsyncSession for consistency.
    """
    container = RepositoryContainer(session)
    membership_svc = BusinessMembershipService(
        repository=container.business_membership,
        user_repo=container.user,
        account_repo=container.account,
        business_repo=container.business,
    )
    subscription_svc = SubscriptionService(
        repository=container.subscription,
    )
    return BusinessService(
        repository=container.business,
        membership_service=membership_svc,
        subscription_service_instance=subscription_svc,
        session=session,
    )


@router.post("", response_model=BusinessResponse, status_code=201)
async def create_business(
    business_data: BusinessCreate,
    current_user: UserResponse = Depends(get_current_user),
    biz_service: BusinessService = Depends(get_scoped_business_service),
) -> BusinessResponse:
    """
    Create a new Business.
    The authenticated user becomes the owner_user_id automatically.
    Any owner_user_id in the request body is ignored.
    """
    business = await biz_service.create_business(business_data, current_user.id)
    return business


@router.get("", response_model=list[BusinessResponse])
async def list_businesses(
    current_user: UserResponse = Depends(get_current_user),
    biz_service: BusinessService = Depends(get_scoped_business_service),
) -> list[BusinessResponse]:
    """
    List all active businesses owned by the current authenticated user.
    Cross-user isolation: only the authenticated user's businesses are returned.
    """
    businesses = await biz_service.list_my_businesses(current_user.id)
    return businesses


@router.get("/{business_id}", response_model=BusinessResponse)
async def get_business(
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    biz_service: BusinessService = Depends(get_scoped_business_service),
) -> BusinessResponse:
    """
    Get a single business by ID.
    Enforced ownership: only the owner can access this business.
    """
    business = await biz_service.get_business(business_id, current_user.id)
    return business


@router.patch("/{business_id}", response_model=BusinessResponse)
async def update_business(
    business_update: BusinessUpdate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    biz_service: BusinessService = Depends(get_scoped_business_service),
) -> BusinessResponse:
    """
    Update a business owned by the current user.
    Only name, description, timezone, and locale can be changed.
    business_type, slug, owner_user_id, status, and created_at are immutable.
    """
    business = await biz_service.update_business(business_id, current_user.id, business_update)
    return business


@router.delete("/{business_id}", response_model=BusinessResponse)
async def archive_business(
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    biz_service: BusinessService = Depends(get_scoped_business_service),
) -> BusinessResponse:
    """
    Soft-archive a business owned by the current user.
    The business is marked ARCHIVED (not deleted) and will not appear in the default list.
    """
    business = await biz_service.archive_business(business_id, current_user.id)
    return business
