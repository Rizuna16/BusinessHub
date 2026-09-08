from typing import Optional
from fastapi import APIRouter, Depends, Path, Query, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.business_membership.service import BusinessMembershipService, business_membership_service
from app.modules.supplier.schemas import (
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
    SupplierListResponse,
    SupplierStatus,
    SupplierType,
)
from app.modules.supplier.service import SupplierService, supplier_service

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/suppliers",
    tags=["Supplier"],
)


def get_supplier_service() -> SupplierService:
    return supplier_service


def get_membership_service() -> BusinessMembershipService:
    return business_membership_service


@router.post("", response_model=SupplierResponse, status_code=201)
async def create_supplier(
    payload: SupplierCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SupplierService = Depends(get_supplier_service),
) -> SupplierResponse:
    return await service.create_supplier(business_id, current_user.id, payload)


@router.get("", response_model=SupplierListResponse)
async def list_suppliers(
    business_id: str = Path(...),
    search: Optional[str] = Query(None),
    status: Optional[SupplierStatus] = Query(None),
    supplier_type: Optional[SupplierType] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: SupplierService = Depends(get_supplier_service),
) -> SupplierListResponse:
    return await service.list_suppliers(
        business_id=business_id,
        user_id=current_user.id,
        search=search,
        status_filter=status,
        supplier_type=supplier_type,
        page=page,
        page_size=page_size,
    )


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    business_id: str = Path(...),
    supplier_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SupplierService = Depends(get_supplier_service),
) -> SupplierResponse:
    return await service.get_supplier(business_id, current_user.id, supplier_id)


@router.patch("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    payload: SupplierUpdate,
    business_id: str = Path(...),
    supplier_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SupplierService = Depends(get_supplier_service),
) -> SupplierResponse:
    return await service.update_supplier(business_id, current_user.id, supplier_id, payload)


@router.delete("/{supplier_id}", response_model=SupplierResponse)
async def archive_supplier(
    business_id: str = Path(...),
    supplier_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SupplierService = Depends(get_supplier_service),
) -> SupplierResponse:
    return await service.archive_supplier(business_id, current_user.id, supplier_id)


@router.post("/{supplier_id}/activate", response_model=SupplierResponse)
async def activate_supplier(
    business_id: str = Path(...),
    supplier_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SupplierService = Depends(get_supplier_service),
) -> SupplierResponse:
    return await service.activate_supplier(business_id, current_user.id, supplier_id)


@router.post("/{supplier_id}/deactivate", response_model=SupplierResponse)
async def deactivate_supplier(
    business_id: str = Path(...),
    supplier_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SupplierService = Depends(get_supplier_service),
) -> SupplierResponse:
    return await service.deactivate_supplier(business_id, current_user.id, supplier_id)
