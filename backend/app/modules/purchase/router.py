from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.container import RepositoryContainer
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.business_membership.service import BusinessMembershipService
from app.modules.purchase.schemas import (
    PurchaseResponse,
    PurchaseLineResponse,
    PurchaseListResponse,
    PurchaseCreate,
    PurchaseUpdate,
    PurchaseLineCreate,
    PurchaseLineUpdate,
    PurchaseStatus,
    DerivedReceivingStatus,
    PurchaseAnalyticsSummaryResponse,
    PurchaseAnalyticsBySupplierResponse,
    PurchaseAnalyticsByCategoryResponse,
)
from app.modules.purchase.service import (
    PurchaseService,
    purchase_service,
)
from app.modules.inventory.service import InventoryService
from app.modules.accounting.integration import AccountingIntegrationService
from app.modules.accounting.service import AccountingService

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/purchases",
    tags=["Purchases"],
)


def get_purchase_service() -> PurchaseService:
    return purchase_service


async def get_scoped_purchase_service(session: AsyncSession = Depends(get_db_session)) -> PurchaseService:
    """
    Request-scoped PurchaseService wired to the same AsyncSession for transaction boundary.
    """
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
    acct_svc = AccountingService(
        repository=container.accounting,
        membership_service=membership_svc,
        branch_repo=container.branch,
    )
    acct_int = AccountingIntegrationService(accounting_srv=acct_svc)
    return PurchaseService(
        purchase_repo=container.purchase,
        membership_service=membership_svc,
        receiving_repo=container.receiving,
        catalog_repo=container.supplier_catalog,
        purchase_return_repo=container.purchase_return,
        inv_service=inv_svc,
        supplier_repo=container.supplier,
        branch_repo=container.branch,
        product_repo=container.product,
        category_repo=container.category,
        accounting_repo=container.accounting,
        accounting_integration=acct_int,
        session=session,
    )


@router.post("", response_model=PurchaseResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase(
    payload: PurchaseCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseService = Depends(get_scoped_purchase_service),
) -> PurchaseResponse:
    """
    Create a new purchase in DRAFT status.
    Requires OWNER or ADMIN active membership.
    """
    return await service.create_purchase(
        business_id=business_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.get("", response_model=PurchaseListResponse)
async def list_purchases(
    business_id: str = Path(...),
    status: Optional[PurchaseStatus] = Query(None),
    supplier_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    receiving_status: Optional[DerivedReceivingStatus] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseService = Depends(get_scoped_purchase_service),
) -> PurchaseListResponse:
    """
    List purchases for a business with optional filtering and pagination.
    Requires active membership.
    """
    return await service.list_purchases(
        business_id=business_id,
        user_id=current_user.id,
        status_filter=status,
        supplier_id=supplier_id,
        branch_id=branch_id,
        receiving_status=receiving_status,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/{purchase_id}", response_model=PurchaseResponse)
async def get_purchase(
    business_id: str = Path(...),
    purchase_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseService = Depends(get_scoped_purchase_service),
) -> PurchaseResponse:
    """
    Get detailed information of a purchase including all lines.
    Requires active membership.
    """
    return await service.get_purchase(
        business_id=business_id,
        purchase_id=purchase_id,
        user_id=current_user.id,
    )


@router.patch("/{purchase_id}", response_model=PurchaseResponse)
async def update_purchase(
    payload: PurchaseUpdate,
    business_id: str = Path(...),
    purchase_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseService = Depends(get_scoped_purchase_service),
) -> PurchaseResponse:
    """
    Update header fields of a DRAFT purchase.
    Requires OWNER or ADMIN active membership.
    """
    return await service.update_purchase(
        business_id=business_id,
        purchase_id=purchase_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.delete("/{purchase_id}")
async def delete_purchase(
    business_id: str = Path(...),
    purchase_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseService = Depends(get_scoped_purchase_service),
) -> dict:
    """
    Delete a DRAFT purchase.
    Requires OWNER or ADMIN active membership.
    """
    return await service.delete_purchase_draft(
        business_id=business_id,
        purchase_id=purchase_id,
        user_id=current_user.id,
    )


@router.post("/{purchase_id}/lines", response_model=PurchaseLineResponse, status_code=status.HTTP_201_CREATED)
async def add_purchase_line(
    payload: PurchaseLineCreate,
    business_id: str = Path(...),
    purchase_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseService = Depends(get_scoped_purchase_service),
) -> PurchaseLineResponse:
    """
    Add a line to a DRAFT purchase.
    Requires OWNER or ADMIN active membership.
    """
    return await service.add_line(
        business_id=business_id,
        purchase_id=purchase_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.patch("/{purchase_id}/lines/{line_id}", response_model=PurchaseLineResponse)
async def update_purchase_line(
    payload: PurchaseLineUpdate,
    business_id: str = Path(...),
    purchase_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseService = Depends(get_scoped_purchase_service),
) -> PurchaseLineResponse:
    """
    Update a line in a DRAFT purchase.
    Requires OWNER or ADMIN active membership.
    """
    return await service.update_line(
        business_id=business_id,
        purchase_id=purchase_id,
        line_id=line_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.delete("/{purchase_id}/lines/{line_id}")
async def delete_purchase_line(
    business_id: str = Path(...),
    purchase_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseService = Depends(get_scoped_purchase_service),
) -> dict:
    """
    Delete a line from a DRAFT purchase.
    Requires OWNER or ADMIN active membership.
    """
    return await service.delete_line(
        business_id=business_id,
        purchase_id=purchase_id,
        line_id=line_id,
        user_id=current_user.id,
    )


@router.post("/{purchase_id}/finalize", response_model=PurchaseResponse)
async def finalize_purchase(
    business_id: str = Path(...),
    purchase_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseService = Depends(get_scoped_purchase_service),
) -> PurchaseResponse:
    """
    Finalize a DRAFT purchase.
    Locks the purchase as read-only FINALIZED record. No stock mutation.
    Requires OWNER or ADMIN active membership.
    """
    return await service.finalize_purchase(
        business_id=business_id,
        purchase_id=purchase_id,
        user_id=current_user.id,
    )


@router.post("/{purchase_id}/cancel", response_model=PurchaseResponse)
async def cancel_purchase(
    business_id: str = Path(...),
    purchase_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseService = Depends(get_scoped_purchase_service),
) -> PurchaseResponse:
    """
    Cancel a DRAFT purchase.
    Requires OWNER or ADMIN active membership.
    """
    return await service.cancel_purchase(
        business_id=business_id,
        purchase_id=purchase_id,
        user_id=current_user.id,
    )


# --- Purchase Analytics ---

@router.get("/analytics/summary", response_model=PurchaseAnalyticsSummaryResponse, status_code=status.HTTP_200_OK)
async def get_purchase_analytics_summary(
    business_id: str = Path(...),
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    category_id: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseService = Depends(get_scoped_purchase_service),
):
    return await service.get_purchase_analytics_summary(
        business_id=business_id, user_id=current_user.id,
        date_from=date_from, date_to=date_to,
        category_id=category_id, supplier_id=supplier_id, branch_id=branch_id,
    )


@router.get("/analytics/by-supplier", response_model=PurchaseAnalyticsBySupplierResponse, status_code=status.HTTP_200_OK)
async def get_purchase_analytics_by_supplier(
    business_id: str = Path(...),
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    category_id: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseService = Depends(get_scoped_purchase_service),
):
    return await service.get_purchase_analytics_by_supplier(
        business_id=business_id, user_id=current_user.id,
        date_from=date_from, date_to=date_to,
        category_id=category_id, supplier_id=supplier_id, branch_id=branch_id,
    )


@router.get("/analytics/by-category", response_model=PurchaseAnalyticsByCategoryResponse, status_code=status.HTTP_200_OK)
async def get_purchase_analytics_by_category(
    business_id: str = Path(...),
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    category_id: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseService = Depends(get_scoped_purchase_service),
):
    return await service.get_purchase_analytics_by_category(
        business_id=business_id, user_id=current_user.id,
        date_from=date_from, date_to=date_to,
        category_id=category_id, supplier_id=supplier_id, branch_id=branch_id,
    )
