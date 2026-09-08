from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.receiving.schemas import (
    ReceivingResponse,
    ReceivingLineResponse,
    ReceivingListResponse,
    ReceivingCreate,
    ReceivingUpdate,
    ReceivingLineCreate,
    ReceivingLineUpdate,
    ReceivingStatus,
)
from app.modules.receiving.service import (
    ReceivingService,
    receiving_service,
)

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/receivings",
    tags=["Receivings"],
)


def get_receiving_service() -> ReceivingService:
    return receiving_service


@router.post("", response_model=ReceivingResponse, status_code=status.HTTP_201_CREATED)
async def create_receiving(
    payload: ReceivingCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ReceivingService = Depends(get_receiving_service),
) -> ReceivingResponse:
    """
    Create a new receiving in DRAFT status for a FINALIZED purchase.
    Requires OWNER or ADMIN active membership.
    """
    return await service.create_receiving(
        business_id=business_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.get("", response_model=ReceivingListResponse)
async def list_receivings(
    business_id: str = Path(...),
    status: Optional[ReceivingStatus] = Query(None),
    purchase_id: Optional[str] = Query(None),
    inventory_location_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: ReceivingService = Depends(get_receiving_service),
) -> ReceivingListResponse:
    """
    List receivings for a business with optional filtering and pagination.
    Requires active membership.
    """
    return await service.list_receivings(
        business_id=business_id,
        user_id=current_user.id,
        status_filter=status,
        purchase_id=purchase_id,
        inventory_location_id=inventory_location_id,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/{receiving_id}", response_model=ReceivingResponse)
async def get_receiving(
    business_id: str = Path(...),
    receiving_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ReceivingService = Depends(get_receiving_service),
) -> ReceivingResponse:
    """
    Get detailed information of a receiving including all lines.
    Requires active membership.
    """
    return await service.get_receiving(
        business_id=business_id,
        receiving_id=receiving_id,
        user_id=current_user.id,
    )


@router.patch("/{receiving_id}", response_model=ReceivingResponse)
async def update_receiving(
    payload: ReceivingUpdate,
    business_id: str = Path(...),
    receiving_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ReceivingService = Depends(get_receiving_service),
) -> ReceivingResponse:
    """
    Update notes of a DRAFT receiving.
    Requires OWNER or ADMIN active membership.
    """
    return await service.update_receiving(
        business_id=business_id,
        receiving_id=receiving_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.delete("/{receiving_id}")
async def delete_receiving(
    business_id: str = Path(...),
    receiving_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ReceivingService = Depends(get_receiving_service),
) -> dict:
    """
    Delete a DRAFT receiving.
    Requires OWNER or ADMIN active membership.
    """
    return await service.delete_receiving(
        business_id=business_id,
        receiving_id=receiving_id,
        user_id=current_user.id,
    )


@router.post("/{receiving_id}/lines", response_model=ReceivingLineResponse, status_code=status.HTTP_201_CREATED)
async def add_receiving_line(
    payload: ReceivingLineCreate,
    business_id: str = Path(...),
    receiving_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ReceivingService = Depends(get_receiving_service),
) -> ReceivingLineResponse:
    """
    Add a line to a DRAFT receiving.
    Validates against over-receiving.
    Requires OWNER or ADMIN active membership.
    """
    return await service.add_line(
        business_id=business_id,
        receiving_id=receiving_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.patch("/{receiving_id}/lines/{line_id}", response_model=ReceivingLineResponse)
async def update_receiving_line(
    payload: ReceivingLineUpdate,
    business_id: str = Path(...),
    receiving_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ReceivingService = Depends(get_receiving_service),
) -> ReceivingLineResponse:
    """
    Update a line in a DRAFT receiving.
    Validates against over-receiving.
    Requires OWNER or ADMIN active membership.
    """
    return await service.update_line(
        business_id=business_id,
        receiving_id=receiving_id,
        line_id=line_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.delete("/{receiving_id}/lines/{line_id}")
async def delete_receiving_line(
    business_id: str = Path(...),
    receiving_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ReceivingService = Depends(get_receiving_service),
) -> dict:
    """
    Delete a line from a DRAFT receiving.
    Requires OWNER or ADMIN active membership.
    """
    return await service.delete_line(
        business_id=business_id,
        receiving_id=receiving_id,
        line_id=line_id,
        user_id=current_user.id,
    )


@router.post("/{receiving_id}/finalize", response_model=ReceivingResponse)
async def finalize_receiving(
    business_id: str = Path(...),
    receiving_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ReceivingService = Depends(get_receiving_service),
) -> ReceivingResponse:
    """
    Finalize a DRAFT receiving.
    Locks the receiving as read-only FINALIZED record. No stock mutation.
    Validates over-receiving at finalization time.
    Requires OWNER or ADMIN active membership.
    """
    return await service.finalize_receiving(
        business_id=business_id,
        receiving_id=receiving_id,
        user_id=current_user.id,
    )


@router.post("/{receiving_id}/cancel", response_model=ReceivingResponse)
async def cancel_receiving(
    business_id: str = Path(...),
    receiving_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ReceivingService = Depends(get_receiving_service),
) -> ReceivingResponse:
    """
    Cancel a DRAFT receiving.
    Requires OWNER or ADMIN active membership.
    """
    return await service.cancel_receiving(
        business_id=business_id,
        receiving_id=receiving_id,
        user_id=current_user.id,
    )