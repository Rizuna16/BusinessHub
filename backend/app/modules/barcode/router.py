from typing import Optional
from fastapi import APIRouter, Depends, Path, Query, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.barcode.schemas import (
    BarcodeCreate,
    BarcodeUpdate,
    BarcodeResponse,
    BarcodeListResponse,
)
from app.modules.barcode.service import BarcodeService, barcode_service

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/barcodes",
    tags=["Barcode"],
)

def get_barcode_service() -> BarcodeService:
    return barcode_service

@router.post("", response_model=BarcodeResponse, status_code=status.HTTP_201_CREATED)
async def create_barcode(
    payload: BarcodeCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: BarcodeService = Depends(get_barcode_service),
) -> BarcodeResponse:
    return await service.create_barcode(business_id, current_user.id, payload)

@router.get("", response_model=BarcodeListResponse)
async def list_barcodes(
    business_id: str = Path(...),
    product_id: Optional[str] = Query(None),
    variant_id: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: BarcodeService = Depends(get_barcode_service),
) -> BarcodeListResponse:
    return await service.list_barcodes(
        business_id,
        current_user.id,
        product_id=product_id,
        variant_id=variant_id,
    )

@router.get("/{barcode_id}", response_model=BarcodeResponse)
async def get_barcode(
    business_id: str = Path(...),
    barcode_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: BarcodeService = Depends(get_barcode_service),
) -> BarcodeResponse:
    return await service.get_barcode(business_id, current_user.id, barcode_id)

@router.patch("/{barcode_id}", response_model=BarcodeResponse)
async def update_barcode(
    payload: BarcodeUpdate,
    business_id: str = Path(...),
    barcode_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: BarcodeService = Depends(get_barcode_service),
) -> BarcodeResponse:
    return await service.update_barcode(business_id, current_user.id, barcode_id, payload)

@router.delete("/{barcode_id}", response_model=BarcodeResponse)
async def archive_barcode(
    business_id: str = Path(...),
    barcode_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: BarcodeService = Depends(get_barcode_service),
) -> BarcodeResponse:
    return await service.archive_barcode(business_id, current_user.id, barcode_id)
