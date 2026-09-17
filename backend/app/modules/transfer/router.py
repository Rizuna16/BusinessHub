from fastapi import APIRouter, Depends, Path, Query, status
from typing import Optional
from decimal import Decimal

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.transfer.schemas import (
    TransferResponse,
    TransferListResponse,
    TransferCreate,
    TransferLineResponse,
    TransferLineCreate,
    TransferStatus,
)
from app.modules.transfer.service import (
    TransferService,
    transfer_service,
)

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/transfer-orders",
    tags=["Transfer Orders"],
)


def get_transfer_service() -> TransferService:
    return transfer_service


@router.post("", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def create_transfer_order(
    payload: TransferCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: TransferService = Depends(get_transfer_service),
):
    return await service.create_transfer(business_id, current_user.id, payload)


@router.get("", response_model=TransferListResponse, status_code=status.HTTP_200_OK)
async def list_transfer_orders(
    business_id: str = Path(...),
    status: Optional[TransferStatus] = Query(None),
    source_location_id: Optional[str] = Query(None),
    destination_location_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: TransferService = Depends(get_transfer_service),
):
    return await service.list_transfers(
        business_id=business_id,
        user_id=current_user.id,
        status_filter=status,
        source_location_id=source_location_id,
        destination_location_id=destination_location_id,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/{transfer_id}", response_model=TransferResponse, status_code=status.HTTP_200_OK)
async def get_transfer_order(
    business_id: str = Path(...),
    transfer_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: TransferService = Depends(get_transfer_service),
):
    return await service.get_transfer(business_id, transfer_id, current_user.id)


@router.post("/{transfer_id}/lines", response_model=TransferLineResponse, status_code=status.HTTP_201_CREATED)
async def add_transfer_line(
    payload: TransferLineCreate,
    business_id: str = Path(...),
    transfer_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: TransferService = Depends(get_transfer_service),
):
    return await service.add_line(business_id, transfer_id, current_user.id, payload)


@router.patch("/{transfer_id}/lines/{line_id}", response_model=TransferLineResponse, status_code=status.HTTP_200_OK)
async def update_transfer_line(
    business_id: str = Path(...),
    transfer_id: str = Path(...),
    line_id: str = Path(...),
    quantity: Decimal = Query(..., gt=0),
    current_user: UserResponse = Depends(get_current_user),
    service: TransferService = Depends(get_transfer_service),
):
    return await service.update_line(business_id, transfer_id, line_id, current_user.id, quantity)


@router.delete("/{transfer_id}/lines/{line_id}", status_code=status.HTTP_200_OK)
async def delete_transfer_line(
    business_id: str = Path(...),
    transfer_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: TransferService = Depends(get_transfer_service),
):
    return await service.delete_line(business_id, transfer_id, line_id, current_user.id)


@router.post("/{transfer_id}/dispatch", response_model=TransferResponse, status_code=status.HTTP_200_OK)
async def dispatch_transfer_order(
    business_id: str = Path(...),
    transfer_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: TransferService = Depends(get_transfer_service),
):
    return await service.dispatch_transfer(business_id, transfer_id, current_user.id)


@router.post("/{transfer_id}/receive", response_model=TransferResponse, status_code=status.HTTP_200_OK)
async def receive_transfer_order(
    business_id: str = Path(...),
    transfer_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: TransferService = Depends(get_transfer_service),
):
    return await service.receive_transfer(business_id, transfer_id, current_user.id)


@router.post("/{transfer_id}/cancel", response_model=TransferResponse, status_code=status.HTTP_200_OK)
async def cancel_transfer_order(
    business_id: str = Path(...),
    transfer_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: TransferService = Depends(get_transfer_service),
):
    return await service.cancel_transfer(business_id, transfer_id, current_user.id)
