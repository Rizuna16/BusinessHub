from fastapi import APIRouter, Depends, Path, Query, status
from typing import Optional
from datetime import datetime, date

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.sales_receivable.schemas import (
    SalesReceivableResponse,
    SalesReceivableListResponse,
    SalesReceivableSummaryResponse,
    CustomerReceivableSummaryListResponse,
    CustomerStatementResponse,
    ReceivableStatus,
)
from app.modules.sales_receivable.service import (
    SalesReceivableService,
    sales_receivable_service,
)
from app.modules.aging.schemas import ARAgingResponse
from app.modules.aging.utils import AgingBucket
from app.modules.aging.service import aging_service

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/receivables",
    tags=["Sales Receivables"],
)


def get_sales_receivable_service() -> SalesReceivableService:
    return sales_receivable_service


@router.get("", response_model=SalesReceivableListResponse, status_code=status.HTTP_200_OK)
async def list_receivables(
    business_id: str = Path(...),
    status: Optional[ReceivableStatus] = Query(None),
    customer_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesReceivableService = Depends(get_sales_receivable_service),
):
    return await service.list_receivables(
        business_id=business_id,
        user_id=current_user.id,
        status_filter=status,
        customer_id=customer_id,
        branch_id=branch_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=SalesReceivableSummaryResponse, status_code=status.HTTP_200_OK)
async def get_receivable_summary(
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesReceivableService = Depends(get_sales_receivable_service),
):
    return await service.get_summary(business_id=business_id, user_id=current_user.id)


@router.get("/customer-summary", response_model=CustomerReceivableSummaryListResponse, status_code=status.HTTP_200_OK)
async def get_customer_receivable_summary(
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesReceivableService = Depends(get_sales_receivable_service),
):
    return await service.get_customer_summary(business_id=business_id, user_id=current_user.id)


@router.get("/aging", response_model=ARAgingResponse, status_code=status.HTTP_200_OK)
async def get_ar_aging(
    business_id: str = Path(...),
    as_of_date: Optional[datetime] = Query(None),
    customer_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    bucket: Optional[AgingBucket] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
):
    return await aging_service.get_ar_aging(
        business_id=business_id,
        user_id=current_user.id,
        as_of_date=as_of_date,
        customer_id=customer_id,
        branch_id=branch_id,
        bucket_filter=bucket,
    )


# --- Customer Statement of Account (Feature #41) ---

@router.get("/statements", response_model=CustomerStatementResponse, status_code=status.HTTP_200_OK)
async def get_customer_statement(
    business_id: str = Path(...),
    customer_id: str = Query(..., min_length=1),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesReceivableService = Depends(get_sales_receivable_service),
):
    return await service.get_customer_statement(
        business_id=business_id,
        user_id=current_user.id,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.get("/{sales_id}", response_model=SalesReceivableResponse, status_code=status.HTTP_200_OK)
async def get_receivable_by_sales(
    business_id: str = Path(...),
    sales_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesReceivableService = Depends(get_sales_receivable_service),
):
    return await service.get_receivable_by_sales_id(
        business_id=business_id, sales_id=sales_id, user_id=current_user.id
    )
