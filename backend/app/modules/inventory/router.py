from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, Path, Query, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.inventory.schemas import (
    StockBalanceResponse,
    StockMovementResponse,
    OpeningBalanceInput,
    AdjustmentInput,
    TransferInput,
    MovementType,
    TotalStockResponse,
    ValuationSummaryResponse,
    StockCardResponse,
)
from app.modules.inventory.service import (
    InventoryService,
    inventory_service,
)
from app.modules.inventory.stock_card_service import (
    StockCardService,
    stock_card_service,
)

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/inventory",
    tags=["Inventory"],
)


def get_inventory_service() -> InventoryService:
    return inventory_service


def get_stock_card_service() -> StockCardService:
    return stock_card_service


@router.post("/opening-balance", response_model=StockMovementResponse, status_code=201)
async def create_opening_balance(
    payload: OpeningBalanceInput,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: InventoryService = Depends(get_inventory_service),
) -> StockMovementResponse:
    """
    Create initial stock opening balance for a product/variant at an inventory location.
    Requires OWNER or ADMIN active membership.
    """
    return await service.create_opening_balance(
        business_id=business_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.post("/adjustments/in", response_model=StockMovementResponse, status_code=201)
async def adjust_in(
    payload: AdjustmentInput,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: InventoryService = Depends(get_inventory_service),
) -> StockMovementResponse:
    """
    Adjust stock upwards (IN) for a product/variant at an inventory location.
    Requires OWNER or ADMIN active membership.
    """
    return await service.adjust_in(
        business_id=business_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.post("/adjustments/out", response_model=StockMovementResponse, status_code=201)
async def adjust_out(
    payload: AdjustmentInput,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: InventoryService = Depends(get_inventory_service),
) -> StockMovementResponse:
    """
    Adjust stock downwards (OUT) for a product/variant at an inventory location.
    Requires OWNER or ADMIN active membership. Insufficient stock will fail.
    """
    return await service.adjust_out(
        business_id=business_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.post("/transfers", response_model=List[StockMovementResponse], status_code=201)
async def create_transfer(
    payload: TransferInput,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: InventoryService = Depends(get_inventory_service),
) -> List[StockMovementResponse]:
    """
    Transfer stock between two inventory locations within the same business.
    Requires OWNER or ADMIN active membership. Returns two movements (TRANSFER_OUT, TRANSFER_IN).
    """
    return await service.create_transfer(
        business_id=business_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.get("/stock", response_model=List[StockBalanceResponse])
async def list_stock_balances(
    business_id: str = Path(...),
    inventory_location_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    variant_id: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: InventoryService = Depends(get_inventory_service),
) -> List[StockBalanceResponse]:
    """
    List current stock balances across locations in the business.
    Allows filtering by location, product, or variant.
    Requires active membership.
    """
    return await service.list_stock_balances(
        business_id=business_id,
        user_id=current_user.id,
        inventory_location_id=inventory_location_id,
        product_id=product_id,
        variant_id=variant_id,
    )


@router.get("/stock/total", response_model=TotalStockResponse)
async def get_total_stock(
    business_id: str = Path(...),
    product_id: str = Query(...),
    variant_id: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: InventoryService = Depends(get_inventory_service),
) -> TotalStockResponse:
    """
    Get aggregated total stock for a product/variant across all locations in the business.
    Requires active membership.
    """
    return await service.get_total_stock(
        business_id=business_id,
        user_id=current_user.id,
        product_id=product_id,
        variant_id=variant_id,
    )


@router.get("/stock/{stock_id}", response_model=StockBalanceResponse)
async def get_stock_balance(
    business_id: str = Path(...),
    stock_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: InventoryService = Depends(get_inventory_service),
) -> StockBalanceResponse:
    """
    Get detail of a specific stock balance record.
    Requires active membership.
    """
    return await service.get_stock_balance(
        business_id=business_id,
        user_id=current_user.id,
        stock_id=stock_id,
    )


@router.get("/movements", response_model=List[StockMovementResponse])
async def list_movements(
    business_id: str = Path(...),
    movement_type: Optional[MovementType] = Query(None),
    inventory_location_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    variant_id: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: InventoryService = Depends(get_inventory_service),
) -> List[StockMovementResponse]:
    """
    List immutable stock movement history for audit trail.
    Supports filtering by type, location, product, or variant.
    Requires active membership.
    """
    return await service.list_movements(
        business_id=business_id,
        user_id=current_user.id,
        movement_type=movement_type,
        inventory_location_id=inventory_location_id,
        product_id=product_id,
        variant_id=variant_id,
    )


@router.get("/valuation", response_model=ValuationSummaryResponse)
async def get_valuation_summary(
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: InventoryService = Depends(get_inventory_service),
) -> ValuationSummaryResponse:
    """
    Retrieve the full inventory valuation summary (MAC-based cost state) for the business.
    Requires active membership.
    """
    return await service.get_valuation_summary(
        business_id=business_id,
        user_id=current_user.id,
    )


# --- Stock Card / Inventory Movement Ledger (Feature #42) ---

@router.get("/stock-cards", response_model=StockCardResponse, status_code=status.HTTP_200_OK)
async def get_stock_card(
    business_id: str = Path(...),
    location_id: str = Query(..., min_length=1),
    product_id: str = Query(..., min_length=1),
    variant_id: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    current_user: UserResponse = Depends(get_current_user),
    service: StockCardService = Depends(get_stock_card_service),
) -> StockCardResponse:
    """
    Retrieve chronological Stock Card / Inventory Movement Ledger for a product/variant at a location.
    Requires active membership.
    """
    return await service.get_stock_card(
        business_id=business_id,
        user_id=current_user.id,
        location_id=location_id,
        product_id=product_id,
        variant_id=variant_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )

