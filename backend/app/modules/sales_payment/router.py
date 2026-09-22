from typing import Optional
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.sales_payment.schemas import (
    SalesPaymentResponse,
    SalesPaymentListResponse,
    SalesPaymentCreate,
)
from app.modules.sales_payment.service import (
    SalesPaymentService,
    sales_payment_service,
)
from app.modules.business_membership.service import BusinessMembershipService

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/sales/{sales_id}/payments",
    tags=["Sales Payment"],
)


def get_sales_payment_service() -> SalesPaymentService:
    return sales_payment_service


async def get_scoped_sales_payment_service(session: AsyncSession = Depends(get_db_session)) -> SalesPaymentService:
    """
    Request-scoped SalesPaymentService wired to the same AsyncSession for transaction boundary.
    """
    from app.core.container import RepositoryContainer

    container = RepositoryContainer(session)
    membership_svc = BusinessMembershipService(
        repository=container.business_membership,
        user_repo=container.user,
        account_repo=container.account,
        business_repo=container.business,
    )
    return SalesPaymentService(
        payment_repo=container.sales_payment,
        sales_repo=container.sales,
        membership_service=membership_svc,
        session=session,
    )


@router.post("", response_model=SalesPaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: SalesPaymentCreate,
    business_id: str = Path(...),
    sales_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesPaymentService = Depends(get_scoped_sales_payment_service),
) -> SalesPaymentResponse:
    return await service.create_payment(business_id, sales_id, current_user.id, payload)


@router.get("", response_model=SalesPaymentListResponse)
async def list_payments(
    business_id: str = Path(...),
    sales_id: str = Path(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesPaymentService = Depends(get_scoped_sales_payment_service),
) -> SalesPaymentListResponse:
    return await service.list_payments(
        business_id=business_id,
        sales_id=sales_id,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )


@router.get("/{payment_id}", response_model=SalesPaymentResponse)
async def get_payment(
    business_id: str = Path(...),
    sales_id: str = Path(...),
    payment_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesPaymentService = Depends(get_scoped_sales_payment_service),
) -> SalesPaymentResponse:
    return await service.get_payment(business_id, sales_id, payment_id, current_user.id)


@router.post("/{payment_id}/cancel", response_model=SalesPaymentResponse)
async def cancel_payment(
    business_id: str = Path(...),
    sales_id: str = Path(...),
    payment_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesPaymentService = Depends(get_scoped_sales_payment_service),
) -> SalesPaymentResponse:
    return await service.cancel_payment(business_id, sales_id, payment_id, current_user.id)
