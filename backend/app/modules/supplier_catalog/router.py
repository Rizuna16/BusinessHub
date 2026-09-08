from typing import Optional
from fastapi import APIRouter, Depends, Path, Query, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.supplier_catalog.schemas import (
    SupplierCatalogItemCreate,
    SupplierCatalogItemUpdate,
    SupplierCatalogItemResponse,
    SupplierCatalogItemListResponse,
    SupplierCatalogStatus,
)
from app.modules.supplier_catalog.service import (
    SupplierCatalogService,
    supplier_catalog_service,
)

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/supplier-catalog",
    tags=["Supplier Catalog"],
)


def get_supplier_catalog_service() -> SupplierCatalogService:
    return supplier_catalog_service


@router.post("", response_model=SupplierCatalogItemResponse, status_code=201)
async def create_catalog_item(
    payload: SupplierCatalogItemCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SupplierCatalogService = Depends(get_supplier_catalog_service),
) -> SupplierCatalogItemResponse:
    return await service.create_catalog_item(business_id, current_user.id, payload)


@router.get("", response_model=SupplierCatalogItemListResponse)
async def list_catalog_items(
    business_id: str = Path(...),
    search: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    variant_id: Optional[str] = Query(None),
    status: Optional[SupplierCatalogStatus] = Query(None),
    is_preferred: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: SupplierCatalogService = Depends(get_supplier_catalog_service),
) -> SupplierCatalogItemListResponse:
    return await service.list_catalog_items(
        business_id=business_id,
        user_id=current_user.id,
        search=search,
        supplier_id=supplier_id,
        product_id=product_id,
        variant_id=variant_id,
        status_filter=status,
        is_preferred=is_preferred,
        page=page,
        page_size=page_size,
    )


@router.get("/{catalog_id}", response_model=SupplierCatalogItemResponse)
async def get_catalog_item(
    business_id: str = Path(...),
    catalog_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SupplierCatalogService = Depends(get_supplier_catalog_service),
) -> SupplierCatalogItemResponse:
    return await service.get_catalog_item(business_id, current_user.id, catalog_id)


@router.patch("/{catalog_id}", response_model=SupplierCatalogItemResponse)
async def update_catalog_item(
    payload: SupplierCatalogItemUpdate,
    business_id: str = Path(...),
    catalog_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SupplierCatalogService = Depends(get_supplier_catalog_service),
) -> SupplierCatalogItemResponse:
    return await service.update_catalog_item(
        business_id, current_user.id, catalog_id, payload
    )


@router.delete("/{catalog_id}", response_model=SupplierCatalogItemResponse)
async def archive_catalog_item(
    business_id: str = Path(...),
    catalog_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SupplierCatalogService = Depends(get_supplier_catalog_service),
) -> SupplierCatalogItemResponse:
    return await service.archive_catalog_item(
        business_id, current_user.id, catalog_id
    )


@router.post("/{catalog_id}/activate", response_model=SupplierCatalogItemResponse)
async def activate_catalog_item(
    business_id: str = Path(...),
    catalog_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SupplierCatalogService = Depends(get_supplier_catalog_service),
) -> SupplierCatalogItemResponse:
    return await service.activate_catalog_item(
        business_id, current_user.id, catalog_id
    )


@router.post("/{catalog_id}/deactivate", response_model=SupplierCatalogItemResponse)
async def deactivate_catalog_item(
    business_id: str = Path(...),
    catalog_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SupplierCatalogService = Depends(get_supplier_catalog_service),
) -> SupplierCatalogItemResponse:
    return await service.deactivate_catalog_item(
        business_id, current_user.id, catalog_id
    )
