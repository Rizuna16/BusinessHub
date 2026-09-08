from typing import Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, Path, Query, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.purchase_payable.schemas import (
    PurchasePayableResponse,
    PurchasePayableListResponse,
    PurchasePayableSummaryResponse,
    SupplierPayableSummaryListResponse,
    SupplierStatementResponse,
    PayableStatus,
)
from app.modules.purchase_payable.service import (
    PurchasePayableService,
    purchase_payable_service,
)
from app.modules.aging.schemas import APAgingResponse
from app.modules.aging.utils import AgingBucket
from app.modules.aging.service import aging_service


router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/purchases/payables",
    tags=["Purchase Payables"],
)


def get_purchase_payable_service() -> PurchasePayableService:
    return purchase_payable_service


# --- Supplier Statement of Account (Feature #41) ---

@router.get("/statements", response_model=SupplierStatementResponse, status_code=status.HTTP_200_OK)
async def get_supplier_statement(
    business_id: str = Path(...),
    supplier_id: str = Query(..., min_length=1),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchasePayableService = Depends(get_purchase_payable_service),
):
    return await service.get_supplier_statement(
        business_id=business_id,
        user_id=current_user.id,
        supplier_id=supplier_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


# --- List Payables ---

@router.get("", response_model=PurchasePayableListResponse, status_code=status.HTTP_200_OK)
async def list_payables(
    business_id: str = Path(...),
    status_filter: Optional[PayableStatus] = Query(None, alias="status"),
    supplier_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchasePayableService = Depends(get_purchase_payable_service),
):
    return await service.list_payables(
        business_id=business_id,
        user_id=current_user.id,
        status_filter=status_filter,
        supplier_id=supplier_id,
        branch_id=branch_id,
        search=search,
        currency=currency,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=PurchasePayableSummaryResponse, status_code=status.HTTP_200_OK)
async def get_payables_summary(
    business_id: str = Path(...),
    supplier_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchasePayableService = Depends(get_purchase_payable_service),
):
    return await service.get_summary(
        business_id=business_id,
        user_id=current_user.id,
        supplier_id=supplier_id,
        branch_id=branch_id,
        currency=currency,
    )


@router.get("/suppliers/summary", response_model=SupplierPayableSummaryListResponse, status_code=status.HTTP_200_OK)
async def get_supplier_payables_summary(
    business_id: str = Path(...),
    currency: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchasePayableService = Depends(get_purchase_payable_service),
):
    return await service.get_supplier_summaries(
        business_id=business_id,
        user_id=current_user.id,
        currency=currency,
    )


@router.get("/aging", response_model=APAgingResponse, status_code=status.HTTP_200_OK)
async def get_ap_aging(
    business_id: str = Path(...),
    as_of_date: Optional[datetime] = Query(None),
    supplier_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    bucket: Optional[AgingBucket] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
):
    return await aging_service.get_ap_aging(
        business_id=business_id,
        user_id=current_user.id,
        as_of_date=as_of_date,
        supplier_id=supplier_id,
        branch_id=branch_id,
        bucket_filter=bucket,
    )


@router.get("/{purchase_id}", response_model=PurchasePayableResponse, status_code=status.HTTP_200_OK)
async def get_payable_detail(
    business_id: str = Path(...),
    purchase_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchasePayableService = Depends(get_purchase_payable_service),
):
    return await service.get_payable_by_purchase_id(
        business_id=business_id,
        purchase_id=purchase_id,
        user_id=current_user.id,
    )
