from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserInDB
from app.modules.inventory_batch.schemas import (
    InventoryBatchCreate, InventoryBatchUpdate,
    InventoryBatchResponse, InventoryBatchListResponse,
    BatchLedgerResponse, FEFOCandidateListResponse,
)
from app.modules.inventory_batch.service import inventory_batch_service

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/inventory/batches",
    tags=["Inventory Batches"],
)


@router.post("", response_model=InventoryBatchResponse, status_code=status.HTTP_201_CREATED, summary="Create inventory batch")
async def create_batch(
    business_id: str,
    payload: InventoryBatchCreate,
    current_user: UserInDB = Depends(get_current_user),
) -> InventoryBatchResponse:
    return await inventory_batch_service.create_batch(business_id, current_user.id, payload)


@router.get("", response_model=InventoryBatchListResponse, summary="List inventory batches")
async def list_batches(
    business_id: str,
    inventory_location_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    variant_id: Optional[str] = Query(None),
    expired_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: UserInDB = Depends(get_current_user),
) -> InventoryBatchListResponse:
    return await inventory_batch_service.list_batches(
        business_id, current_user.id, inventory_location_id,
        product_id, variant_id, expired_only, page, page_size,
    )


@router.get("/fefo-candidates", response_model=FEFOCandidateListResponse, summary="Get FEFO batch candidates for product")
async def get_fefo_candidates(
    business_id: str,
    inventory_location_id: str = Query(...),
    product_id: str = Query(...),
    variant_id: Optional[str] = Query(None),
    current_user: UserInDB = Depends(get_current_user),
) -> FEFOCandidateListResponse:
    return await inventory_batch_service.get_fefo_candidates(
        business_id, current_user.id, inventory_location_id, product_id, variant_id,
    )


@router.get("/{batch_id}", response_model=InventoryBatchResponse, summary="Get batch details")
async def get_batch(
    business_id: str,
    batch_id: str,
    current_user: UserInDB = Depends(get_current_user),
) -> InventoryBatchResponse:
    return await inventory_batch_service.get_batch(business_id, current_user.id, batch_id)


@router.get("/{batch_id}/ledger", response_model=BatchLedgerResponse, summary="Get batch stock ledger and movements")
async def get_batch_ledger(
    business_id: str,
    batch_id: str,
    current_user: UserInDB = Depends(get_current_user),
) -> BatchLedgerResponse:
    return await inventory_batch_service.get_batch_ledger(business_id, current_user.id, batch_id)


@router.patch("/{batch_id}", response_model=InventoryBatchResponse, summary="Update batch dates")
async def update_batch(
    business_id: str,
    batch_id: str,
    payload: InventoryBatchUpdate,
    current_user: UserInDB = Depends(get_current_user),
) -> InventoryBatchResponse:
    return await inventory_batch_service.update_batch_dates(
        business_id, current_user.id, batch_id,
        payload.manufacture_date, payload.expiry_date,
    )
