from typing import Optional
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.container import RepositoryContainer
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.business_membership.service import BusinessMembershipService
from app.modules.customer_credit.schemas import (
    CreditLimitUpdate,
    StoreCreditAdjust,
    CustomerCreditSummaryResponse,
    CreditExposureResponse,
    StoreCreditLedgerResponse,
)
from app.modules.customer_credit.service import (
    CustomerCreditService,
    customer_credit_service,
)


router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/customers/{customer_id}/credit",
    tags=["Customer Credit"],
)


def get_customer_credit_service() -> CustomerCreditService:
    return customer_credit_service


async def get_scoped_customer_credit_service(session: AsyncSession = Depends(get_db_session)) -> CustomerCreditService:
    container = RepositoryContainer(session)
    membership_svc = BusinessMembershipService(
        repository=container.business_membership,
        user_repo=container.user,
        account_repo=container.account,
        business_repo=container.business,
    )
    return CustomerCreditService(
        customer_repo=container.customer,
        ledger_repo=container.store_credit_ledger,
        membership_service=membership_svc,
        session=session,
    )


@router.get("/summary", response_model=CustomerCreditSummaryResponse)
async def get_credit_summary(
    business_id: str = Path(...),
    customer_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CustomerCreditService = Depends(get_scoped_customer_credit_service),
) -> CustomerCreditSummaryResponse:
    return await service.get_credit_summary(business_id, current_user.id, customer_id)


@router.get("/exposure", response_model=CreditExposureResponse)
async def get_credit_exposure(
    business_id: str = Path(...),
    customer_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CustomerCreditService = Depends(get_scoped_customer_credit_service),
) -> CreditExposureResponse:
    return await service.get_credit_exposure(business_id, current_user.id, customer_id)


@router.put("/limit", response_model=CustomerCreditSummaryResponse)
async def set_credit_limit(
    payload: CreditLimitUpdate,
    business_id: str = Path(...),
    customer_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CustomerCreditService = Depends(get_scoped_customer_credit_service),
) -> CustomerCreditSummaryResponse:
    return await service.set_credit_limit(business_id, current_user.id, customer_id, payload)


@router.post("/store-credit/issue", response_model=CustomerCreditSummaryResponse)
async def issue_store_credit(
    payload: StoreCreditAdjust,
    business_id: str = Path(...),
    customer_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CustomerCreditService = Depends(get_scoped_customer_credit_service),
) -> CustomerCreditSummaryResponse:
    return await service.issue_store_credit(business_id, current_user.id, customer_id, payload)


@router.get("/store-credit/ledger", response_model=StoreCreditLedgerResponse)
async def get_store_credit_ledger(
    business_id: str = Path(...),
    customer_id: str = Path(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: CustomerCreditService = Depends(get_scoped_customer_credit_service),
) -> StoreCreditLedgerResponse:
    return await service.get_store_credit_ledger(
        business_id, current_user.id, customer_id, page, page_size
    )
