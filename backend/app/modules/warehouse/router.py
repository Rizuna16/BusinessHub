from typing import List
from fastapi import APIRouter, Depends, Path, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.warehouse.schemas import (
    WarehouseResponse,
    WarehouseCreate,
    WarehouseUpdate,
    InventoryLocationResponse,
    InventoryLocationCreate,
    InventoryLocationUpdate,
)
from app.modules.warehouse.service import (
    WarehouseService,
    warehouse_service,
)

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/warehouses",
    tags=["Warehouse"],
)


def get_warehouse_service() -> WarehouseService:
    return warehouse_service


# --- Warehouse Endpoints ---

@router.post("", response_model=WarehouseResponse, status_code=201)
async def create_warehouse(
    payload: WarehouseCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: WarehouseService = Depends(get_warehouse_service),
) -> WarehouseResponse:
    """
    Create a new warehouse under the specified business.
    Requires OWNER or ADMIN active membership.
    """
    return await service.create_warehouse(
        business_id=business_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.get("", response_model=List[WarehouseResponse])
async def list_warehouses(
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: WarehouseService = Depends(get_warehouse_service),
) -> List[WarehouseResponse]:
    """
    List warehouses belonging to the specified business.
    Requires active membership.
    """
    return await service.list_warehouses(
        business_id=business_id,
        user_id=current_user.id,
    )


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
async def get_warehouse(
    business_id: str = Path(...),
    warehouse_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: WarehouseService = Depends(get_warehouse_service),
) -> WarehouseResponse:
    """
    Get details of a specific warehouse.
    Requires active membership. Enforces business boundary.
    """
    return await service.get_warehouse(
        business_id=business_id,
        warehouse_id=warehouse_id,
        user_id=current_user.id,
    )


@router.patch("/{warehouse_id}", response_model=WarehouseResponse)
async def update_warehouse(
    payload: WarehouseUpdate,
    business_id: str = Path(...),
    warehouse_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: WarehouseService = Depends(get_warehouse_service),
) -> WarehouseResponse:
    """
    Update details of a warehouse.
    Requires OWNER or ADMIN active membership.
    """
    return await service.update_warehouse(
        business_id=business_id,
        warehouse_id=warehouse_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.post("/{warehouse_id}/suspend", response_model=WarehouseResponse)
async def suspend_warehouse(
    business_id: str = Path(...),
    warehouse_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: WarehouseService = Depends(get_warehouse_service),
) -> WarehouseResponse:
    """
    Suspend a warehouse.
    Requires OWNER or ADMIN active membership.
    """
    return await service.suspend_warehouse(
        business_id=business_id,
        warehouse_id=warehouse_id,
        user_id=current_user.id,
    )


@router.post("/{warehouse_id}/activate", response_model=WarehouseResponse)
async def activate_warehouse(
    business_id: str = Path(...),
    warehouse_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: WarehouseService = Depends(get_warehouse_service),
) -> WarehouseResponse:
    """
    Activate a suspended warehouse.
    Requires OWNER or ADMIN active membership.
    """
    return await service.activate_warehouse(
        business_id=business_id,
        warehouse_id=warehouse_id,
        user_id=current_user.id,
    )


@router.delete("/{warehouse_id}", response_model=WarehouseResponse)
async def archive_warehouse(
    business_id: str = Path(...),
    warehouse_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: WarehouseService = Depends(get_warehouse_service),
) -> WarehouseResponse:
    """
    Soft-archive a warehouse.
    Requires OWNER or ADMIN active membership.
    """
    return await service.archive_warehouse(
        business_id=business_id,
        warehouse_id=warehouse_id,
        user_id=current_user.id,
    )


# --- Inventory Location Endpoints ---

@router.post("/{warehouse_id}/locations", response_model=InventoryLocationResponse, status_code=201)
async def create_location(
    payload: InventoryLocationCreate,
    business_id: str = Path(...),
    warehouse_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: WarehouseService = Depends(get_warehouse_service),
) -> InventoryLocationResponse:
    """
    Create a new inventory location within a warehouse.
    Requires OWNER or ADMIN active membership.
    """
    return await service.create_location(
        business_id=business_id,
        warehouse_id=warehouse_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.get("/{warehouse_id}/locations", response_model=List[InventoryLocationResponse])
async def list_locations(
    business_id: str = Path(...),
    warehouse_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: WarehouseService = Depends(get_warehouse_service),
) -> List[InventoryLocationResponse]:
    """
    List inventory locations for a specific warehouse.
    Requires active membership. Excludes archived locations.
    """
    return await service.list_locations(
        business_id=business_id,
        warehouse_id=warehouse_id,
        user_id=current_user.id,
    )


@router.get("/{warehouse_id}/locations/{location_id}", response_model=InventoryLocationResponse)
async def get_location(
    business_id: str = Path(...),
    warehouse_id: str = Path(...),
    location_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: WarehouseService = Depends(get_warehouse_service),
) -> InventoryLocationResponse:
    """
    Get details of a specific inventory location.
    Requires active membership.
    """
    return await service.get_location(
        business_id=business_id,
        warehouse_id=warehouse_id,
        location_id=location_id,
        user_id=current_user.id,
    )


@router.patch("/{warehouse_id}/locations/{location_id}", response_model=InventoryLocationResponse)
async def update_location(
    payload: InventoryLocationUpdate,
    business_id: str = Path(...),
    warehouse_id: str = Path(...),
    location_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: WarehouseService = Depends(get_warehouse_service),
) -> InventoryLocationResponse:
    """
    Update details of an inventory location.
    Requires OWNER or ADMIN active membership.
    """
    return await service.update_location(
        business_id=business_id,
        warehouse_id=warehouse_id,
        location_id=location_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.delete("/{warehouse_id}/locations/{location_id}", response_model=InventoryLocationResponse)
async def archive_location(
    business_id: str = Path(...),
    warehouse_id: str = Path(...),
    location_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: WarehouseService = Depends(get_warehouse_service),
) -> InventoryLocationResponse:
    """
    Soft-archive an inventory location.
    Requires OWNER or ADMIN active membership.
    """
    return await service.archive_location(
        business_id=business_id,
        warehouse_id=warehouse_id,
        location_id=location_id,
        user_id=current_user.id,
    )
