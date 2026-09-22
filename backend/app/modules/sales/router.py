from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.sales.schemas import (
    SalesResponse,
    SalesLineResponse,
    SalesListResponse,
    SalesCreate,
    SalesUpdate,
    SalesFinalize,
    SalesLineCreate,
    SalesLineUpdate,
    SalesStatus,
    SalesAnalyticsSummaryResponse,
    SalesAnalyticsByCategoryResponse,
    SalesAnalyticsByCustomerResponse,
)
from app.modules.sales.service import (
    SalesService,
    sales_service,
)
from app.modules.business_membership.service import BusinessMembershipService
from app.modules.inventory.service import InventoryService
from app.modules.pricing.repository import price_list_repository, price_entry_repository

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/sales",
    tags=["Sales"],
)


def get_sales_service() -> SalesService:
    return sales_service


async def get_scoped_sales_service(session: AsyncSession = Depends(get_db_session)) -> SalesService:
    """
    Request-scoped SalesService wired to the same AsyncSession for transaction boundary.
    """
    from app.core.container import RepositoryContainer

    container = RepositoryContainer(session)
    membership_svc = BusinessMembershipService(
        repository=container.business_membership,
        user_repo=container.user,
        account_repo=container.account,
        business_repo=container.business,
    )
    inv_svc = InventoryService(
        balance_repo=container.stock_balance,
        movement_repo=container.stock_movement,
        cost_repo=container.inventory_cost,
    )
    return SalesService(
        sales_repo=container.sales,
        membership_service=membership_svc,
        price_list_repo=container.price_list,
        price_entry_repo=container.price_entry,
        inventory_srv=inv_svc,
        session=session,
    )


@router.post("", response_model=SalesResponse, status_code=status.HTTP_201_CREATED)
async def create_sales(
    payload: SalesCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesService = Depends(get_scoped_sales_service),
) -> SalesResponse:
    return await service.create_sales(business_id, current_user.id, payload)


@router.get("", response_model=SalesListResponse)
async def list_sales(
    business_id: str = Path(...),
    status: Optional[SalesStatus] = Query(None),
    customer_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesService = Depends(get_scoped_sales_service),
) -> SalesListResponse:
    return await service.list_sales(
        business_id=business_id,
        user_id=current_user.id,
        status=status,
        customer_id=customer_id,
        branch_id=branch_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.get("/{sales_id}", response_model=SalesResponse)
async def get_sales(
    business_id: str = Path(...),
    sales_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesService = Depends(get_scoped_sales_service),
) -> SalesResponse:
    return await service.get_sales(business_id, sales_id, current_user.id)


@router.patch("/{sales_id}", response_model=SalesResponse)
async def update_sales(
    payload: SalesUpdate,
    business_id: str = Path(...),
    sales_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesService = Depends(get_scoped_sales_service),
) -> SalesResponse:
    return await service.update_sales(business_id, sales_id, current_user.id, payload)


@router.delete("/{sales_id}")
async def delete_sales_draft(
    business_id: str = Path(...),
    sales_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesService = Depends(get_scoped_sales_service),
) -> dict:
    return await service.delete_sales_draft(business_id, sales_id, current_user.id)


@router.post("/{sales_id}/lines", response_model=SalesLineResponse, status_code=status.HTTP_201_CREATED)
async def add_line(
    payload: SalesLineCreate,
    business_id: str = Path(...),
    sales_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesService = Depends(get_scoped_sales_service),
) -> SalesLineResponse:
    return await service.add_line(business_id, sales_id, current_user.id, payload)


@router.patch("/{sales_id}/lines/{line_id}", response_model=SalesLineResponse)
async def update_line(
    payload: SalesLineUpdate,
    business_id: str = Path(...),
    sales_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesService = Depends(get_scoped_sales_service),
) -> SalesLineResponse:
    return await service.update_line(business_id, sales_id, line_id, current_user.id, payload)


@router.delete("/{sales_id}/lines/{line_id}")
async def delete_line(
    business_id: str = Path(...),
    sales_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesService = Depends(get_scoped_sales_service),
) -> dict:
    return await service.delete_line(business_id, sales_id, line_id, current_user.id)


@router.post("/{sales_id}/finalize", response_model=SalesResponse)
async def finalize_sales(
    payload: SalesFinalize = Depends(),
    business_id: str = Path(...),
    sales_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesService = Depends(get_scoped_sales_service),
) -> SalesResponse:
    return await service.finalize_sales(business_id, sales_id, current_user.id, payload)


@router.post("/{sales_id}/cancel", response_model=SalesResponse)
async def cancel_sales(
    business_id: str = Path(...),
    sales_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesService = Depends(get_scoped_sales_service),
) -> SalesResponse:
    return await service.cancel_sales(business_id, sales_id, current_user.id)


# --- Sales Analytics ---

@router.get("/analytics/summary", response_model=SalesAnalyticsSummaryResponse, status_code=status.HTTP_200_OK)
async def get_sales_analytics_summary(
    business_id: str = Path(...),
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    category_id: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesService = Depends(get_scoped_sales_service),
):
    return await service.get_sales_analytics_summary(
        business_id=business_id,
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        customer_id=customer_id,
        branch_id=branch_id,
    )


@router.get("/analytics/by-category", response_model=SalesAnalyticsByCategoryResponse, status_code=status.HTTP_200_OK)
async def get_sales_analytics_by_category(
    business_id: str = Path(...),
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    category_id: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesService = Depends(get_scoped_sales_service),
):
    return await service.get_sales_analytics_by_category(
        business_id=business_id,
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        customer_id=customer_id,
        branch_id=branch_id,
    )


@router.get("/analytics/by-customer", response_model=SalesAnalyticsByCustomerResponse, status_code=status.HTTP_200_OK)
async def get_sales_analytics_by_customer(
    business_id: str = Path(...),
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    category_id: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesService = Depends(get_scoped_sales_service),
):
    return await service.get_sales_analytics_by_customer(
        business_id=business_id,
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        customer_id=customer_id,
        branch_id=branch_id,
    )