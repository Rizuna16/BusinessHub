from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
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
)
from app.modules.purchase.service import (
    PurchaseService,
    purchase_service,
)

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/purchases",
    tags=["Purchases"],
)


def get_purchase_service() -> PurchaseService:
    return purchase_service


@router.post("", response_model=PurchaseResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase(
    payload: PurchaseCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseService = Depends(get_purchase_service),
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
    service: PurchaseService = Depends(get_purchase_service),
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
    service: PurchaseService = Depends(get_purchase_service),
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
    service: PurchaseService = Depends(get_purchase_service),
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
    service: PurchaseService = Depends(get_purchase_service),
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
    service: PurchaseService = Depends(get_purchase_service),
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
    service: PurchaseService = Depends(get_purchase_service),
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
    service: PurchaseService = Depends(get_purchase_service),
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
    service: PurchaseService = Depends(get_purchase_service),
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
    service: PurchaseService = Depends(get_purchase_service),
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
