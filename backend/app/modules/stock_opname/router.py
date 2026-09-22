from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.container import RepositoryContainer
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.business_membership.service import BusinessMembershipService
from app.modules.inventory.service import InventoryService
from app.modules.stock_opname.schemas import (
    StockOpnameResponse,
    StockOpnameLineResponse,
    StockOpnameCreate,
    StockOpnameLineCreate,
    StockOpnameLineUpdateCount,
    StockOpnameStatus,
)
from app.modules.stock_opname.service import (
    StockOpnameService,
    stock_opname_service,
)

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/inventory/stock-opnames",
    tags=["Stock Opname"],
)


def get_stock_opname_service() -> StockOpnameService:
    return stock_opname_service


async def get_scoped_stock_opname_service(session: AsyncSession = Depends(get_db_session)) -> StockOpnameService:
    container = RepositoryContainer(session)
    inv_svc = InventoryService(
        balance_repo=container.stock_balance,
        movement_repo=container.stock_movement,
        cost_repo=container.inventory_cost,
    )
    return StockOpnameService(
        opname_repo=container.stock_opname,
        inv_service=inv_svc,
        session=session,
    )


@router.post("", response_model=StockOpnameResponse, status_code=status.HTTP_201_CREATED)
async def create_stock_opname(
    payload: StockOpnameCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: StockOpnameService = Depends(get_scoped_stock_opname_service),
) -> StockOpnameResponse:
    """
    Create a new stock opname session in DRAFT status for a specific inventory location.
    Requires OWNER or ADMIN active membership.
    """
    return await service.create_opname(
        business_id=business_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.get("", response_model=List[StockOpnameResponse])
async def list_stock_opnames(
    business_id: str = Path(...),
    status: Optional[StockOpnameStatus] = Query(None),
    inventory_location_id: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: StockOpnameService = Depends(get_scoped_stock_opname_service),
) -> List[StockOpnameResponse]:
    """
    List stock opnames for a business with optional filtering by status and location.
    Requires active membership.
    """
    return await service.list_opnames(
        business_id=business_id,
        user_id=current_user.id,
        status_filter=status,
        inventory_location_id=inventory_location_id,
    )


@router.get("/{opname_id}", response_model=StockOpnameResponse)
async def get_stock_opname(
    business_id: str = Path(...),
    opname_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: StockOpnameService = Depends(get_scoped_stock_opname_service),
) -> StockOpnameResponse:
    """
    Get detailed information of a stock opname session including all lines.
    Requires active membership.
    """
    return await service.get_opname(
        business_id=business_id,
        opname_id=opname_id,
        user_id=current_user.id,
    )


@router.delete("/{opname_id}")
async def delete_stock_opname(
    business_id: str = Path(...),
    opname_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: StockOpnameService = Depends(get_scoped_stock_opname_service),
) -> dict:
    """
    Delete a DRAFT stock opname session.
    Requires OWNER or ADMIN active membership. FINALIZED opnames cannot be deleted.
    """
    return await service.delete_opname(
        business_id=business_id,
        opname_id=opname_id,
        user_id=current_user.id,
    )


@router.post("/{opname_id}/lines", response_model=StockOpnameLineResponse, status_code=status.HTTP_201_CREATED)
async def add_stock_opname_line(
    payload: StockOpnameLineCreate,
    business_id: str = Path(...),
    opname_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: StockOpnameService = Depends(get_scoped_stock_opname_service),
) -> StockOpnameLineResponse:
    """
    Add a product/variant line to a DRAFT stock opname session.
    Automatically captures a system_quantity snapshot of the current stock balance.
    Requires OWNER or ADMIN active membership.
    """
    return await service.add_line(
        business_id=business_id,
        opname_id=opname_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.patch("/{opname_id}/lines/{line_id}", response_model=StockOpnameLineResponse)
async def update_stock_opname_line_count(
    payload: StockOpnameLineUpdateCount,
    business_id: str = Path(...),
    opname_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: StockOpnameService = Depends(get_scoped_stock_opname_service),
) -> StockOpnameLineResponse:
    """
    Update the physical counted quantity for a stock opname line.
    Calculates variance (counted_quantity - system_quantity) server-side.
    Requires OWNER or ADMIN active membership on a DRAFT opname.
    """
    return await service.update_line_count(
        business_id=business_id,
        opname_id=opname_id,
        line_id=line_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.delete("/{opname_id}/lines/{line_id}")
async def delete_stock_opname_line(
    business_id: str = Path(...),
    opname_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: StockOpnameService = Depends(get_scoped_stock_opname_service),
) -> dict:
    """
    Remove a line from a DRAFT stock opname session.
    Requires OWNER or ADMIN active membership.
    """
    return await service.delete_line(
        business_id=business_id,
        opname_id=opname_id,
        line_id=line_id,
        user_id=current_user.id,
    )


@router.post("/{opname_id}/finalize", response_model=StockOpnameResponse)
async def finalize_stock_opname(
    business_id: str = Path(...),
    opname_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: StockOpnameService = Depends(get_scoped_stock_opname_service),
) -> StockOpnameResponse:
    """
    Finalize a stock opname session.
    Performs stale-stock validation, generates required ADJUSTMENT_IN / ADJUSTMENT_OUT movements,
    and locks the opname as read-only FINALIZED.
    Requires OWNER or ADMIN active membership.
    """
    return await service.finalize_opname(
        business_id=business_id,
        opname_id=opname_id,
        user_id=current_user.id,
    )
