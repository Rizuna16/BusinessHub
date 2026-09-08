from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.purchase_return.schemas import (
    PurchaseReturnResponse,
    PurchaseReturnLineResponse,
    PurchaseReturnListResponse,
    PurchaseReturnCreate,
    PurchaseReturnUpdate,
    PurchaseReturnLineCreate,
    PurchaseReturnLineUpdate,
    PurchaseReturnStatus,
)
from app.modules.purchase_return.service import (
    PurchaseReturnService,
    purchase_return_service,
)

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/purchase-returns",
    tags=["Purchase Returns"],
)


def get_purchase_return_service() -> PurchaseReturnService:
    return purchase_return_service


@router.post("", response_model=PurchaseReturnResponse, status_code=status.HTTP_201_CREATED)
async def create_return(
    payload: PurchaseReturnCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseReturnService = Depends(get_purchase_return_service),
) -> PurchaseReturnResponse:
    """
    Create a new purchase return in DRAFT status for a FINALIZED purchase.
    Requires OWNER or ADMIN active membership.
    """
    return await service.create_return(
        business_id=business_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.get("", response_model=PurchaseReturnListResponse)
async def list_returns(
    business_id: str = Path(...),
    status: Optional[PurchaseReturnStatus] = Query(None),
    purchase_id: Optional[str] = Query(None),
    inventory_location_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseReturnService = Depends(get_purchase_return_service),
) -> PurchaseReturnListResponse:
    """
    List purchase returns for a business with optional filtering and pagination.
    Requires active membership.
    """
    return await service.list_returns(
        business_id=business_id,
        user_id=current_user.id,
        status_filter=status,
        purchase_id=purchase_id,
        inventory_location_id=inventory_location_id,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/{return_id}", response_model=PurchaseReturnResponse)
async def get_return(
    business_id: str = Path(...),
    return_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseReturnService = Depends(get_purchase_return_service),
) -> PurchaseReturnResponse:
    """
    Get detailed information of a purchase return including all lines.
    Requires active membership.
    """
    return await service.get_return(
        business_id=business_id,
        return_id=return_id,
        user_id=current_user.id,
    )


@router.patch("/{return_id}", response_model=PurchaseReturnResponse)
async def update_return(
    payload: PurchaseReturnUpdate,
    business_id: str = Path(...),
    return_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseReturnService = Depends(get_purchase_return_service),
) -> PurchaseReturnResponse:
    """
    Update notes of a DRAFT purchase return.
    Requires OWNER or ADMIN active membership.
    """
    return await service.update_return(
        business_id=business_id,
        return_id=return_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.delete("/{return_id}")
async def delete_return(
    business_id: str = Path(...),
    return_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseReturnService = Depends(get_purchase_return_service),
) -> dict:
    """
    Delete a DRAFT purchase return.
    Requires OWNER or ADMIN active membership.
    """
    return await service.delete_return(
        business_id=business_id,
        return_id=return_id,
        user_id=current_user.id,
    )


@router.post("/{return_id}/lines", response_model=PurchaseReturnLineResponse, status_code=status.HTTP_201_CREATED)
async def add_return_line(
    payload: PurchaseReturnLineCreate,
    business_id: str = Path(...),
    return_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseReturnService = Depends(get_purchase_return_service),
) -> PurchaseReturnLineResponse:
    """
    Add a line to a DRAFT purchase return.
    Validates against over-returning finalized received quantity.
    Requires OWNER or ADMIN active membership.
    """
    return await service.add_line(
        business_id=business_id,
        return_id=return_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.patch("/{return_id}/lines/{line_id}", response_model=PurchaseReturnLineResponse)
async def update_return_line(
    payload: PurchaseReturnLineUpdate,
    business_id: str = Path(...),
    return_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseReturnService = Depends(get_purchase_return_service),
) -> PurchaseReturnLineResponse:
    """
    Update a line in a DRAFT purchase return.
    Validates against over-returning.
    Requires OWNER or ADMIN active membership.
    """
    return await service.update_line(
        business_id=business_id,
        return_id=return_id,
        line_id=line_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.delete("/{return_id}/lines/{line_id}")
async def delete_return_line(
    business_id: str = Path(...),
    return_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseReturnService = Depends(get_purchase_return_service),
) -> dict:
    """
    Delete a line from a DRAFT purchase return.
    Requires OWNER or ADMIN active membership.
    """
    return await service.delete_line(
        business_id=business_id,
        return_id=return_id,
        line_id=line_id,
        user_id=current_user.id,
    )


@router.post("/{return_id}/finalize", response_model=PurchaseReturnResponse)
async def finalize_return(
    business_id: str = Path(...),
    return_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseReturnService = Depends(get_purchase_return_service),
) -> PurchaseReturnResponse:
    """
    Finalize a DRAFT purchase return.
    Locks the return as read-only FINALIZED record. No stock mutation.
    Validates over-returning at finalization time.
    Requires OWNER or ADMIN active membership.
    """
    return await service.finalize_return(
        business_id=business_id,
        return_id=return_id,
        user_id=current_user.id,
    )


@router.post("/{return_id}/cancel", response_model=PurchaseReturnResponse)
async def cancel_return(
    business_id: str = Path(...),
    return_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PurchaseReturnService = Depends(get_purchase_return_service),
) -> PurchaseReturnResponse:
    """
    Cancel a DRAFT purchase return.
    Requires OWNER or ADMIN active membership.
    """
    return await service.cancel_return(
        business_id=business_id,
        return_id=return_id,
        user_id=current_user.id,
    )
