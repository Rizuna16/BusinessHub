from typing import Optional
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.container import RepositoryContainer
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.sales_order.schemas import (
    QuotationResponse,
    QuotationListResponse,
    QuotationCreate,
    QuotationUpdate,
    QuotationAction,
    QuotationConvert,
    QuotationLineCreate,
    QuotationLineUpdate,
    QuotationLineResponse,
    QuotationStatus,
    SalesOrderResponse,
    SalesOrderListResponse,
    SalesOrderCreate,
    SalesOrderUpdate,
    SalesOrderAction,
    SalesOrderFulfill,
    SalesOrderStatus,
    SalesOrderLineCreate,
    SalesOrderLineUpdate,
    SalesOrderLineResponse,
    SalesOrderLineFulfill,
    AvailableStockResponse,
    AvailabilityCheckRequest,
    AvailabilityCheckResponse,
)
from app.modules.sales_order.quotation_service import QuotationService, quotation_service
from app.modules.sales_order.order_service import SalesOrderService, sales_order_service
from app.modules.sales_order.availability import AvailabilityService, availability_service
from app.modules.business_membership.service import BusinessMembershipService
from app.modules.inventory.service import InventoryService
from app.modules.sales_order.repository import reservation_repository

quotation_router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/quotations",
    tags=["Sales Quotation"],
)

sales_order_router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/sales-orders",
    tags=["Sales Order"],
)

availability_router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/inventory/availability",
    tags=["Inventory Availability"],
)


def get_quotation_svc() -> QuotationService:
    return quotation_service


def get_order_svc() -> SalesOrderService:
    return sales_order_service


def get_availability_svc() -> AvailabilityService:
    return availability_service


async def get_scoped_quotation_service(session: AsyncSession = Depends(get_db_session)) -> QuotationService:
    """
    Request-scoped QuotationService wired to the same AsyncSession for transaction boundary.
    """
    container = RepositoryContainer(session)
    membership_svc = BusinessMembershipService(
        repository=container.business_membership,
        user_repo=container.user,
        account_repo=container.account,
        business_repo=container.business,
    )
    return QuotationService(
        quotation_repo=container.quotation,
        sales_order_repo=container.sales_order,
        membership_service=membership_svc,
        session=session,
    )


async def get_scoped_sales_order_service(session: AsyncSession = Depends(get_db_session)) -> SalesOrderService:
    """
    Request-scoped SalesOrderService wired to the same AsyncSession for transaction boundary.
    """
    container = RepositoryContainer(session)
    membership_svc = BusinessMembershipService(
        repository=container.business_membership,
        user_repo=container.user,
        account_repo=container.account,
        business_repo=container.business,
    )
    inv_svc = InventoryService(
        balance_repo=container.stock_balance,
        movement_repo=container.stock_movement,
        cost_repo=container.inventory_cost,
    )
    return SalesOrderService(
        order_repo=container.sales_order,
        reservation_repo=container.reservation,
        availability_svc=availability_service,
        membership_service=membership_svc,
        inventory_srv=inv_svc,
        session=session,
    )


# === QUOTATION ENDPOINTS ===

@quotation_router.post("", response_model=QuotationResponse, status_code=status.HTTP_201_CREATED)
async def create_quotation(
    payload: QuotationCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: QuotationService = Depends(get_scoped_quotation_service),
) -> QuotationResponse:
    return await service.create_quotation(business_id, current_user.id, payload)


@quotation_router.get("", response_model=QuotationListResponse)
async def list_quotations(
    business_id: str = Path(...),
    status: Optional[QuotationStatus] = Query(None),
    customer_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: QuotationService = Depends(get_scoped_quotation_service),
) -> QuotationListResponse:
    return await service.list_quotations(
        business_id=business_id, user_id=current_user.id,
        status=status, customer_id=customer_id, branch_id=branch_id,
        search=search, page=page, page_size=page_size,
    )


@quotation_router.get("/{quotation_id}", response_model=QuotationResponse)
async def get_quotation(
    business_id: str = Path(...),
    quotation_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: QuotationService = Depends(get_scoped_quotation_service),
) -> QuotationResponse:
    return await service.get_quotation(business_id, quotation_id, current_user.id)


@quotation_router.put("/{quotation_id}", response_model=QuotationResponse)
async def update_quotation(
    payload: QuotationUpdate,
    business_id: str = Path(...),
    quotation_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: QuotationService = Depends(get_scoped_quotation_service),
) -> QuotationResponse:
    return await service.update_quotation(business_id, quotation_id, current_user.id, payload)


@quotation_router.post("/{quotation_id}/lines", response_model=QuotationLineResponse, status_code=status.HTTP_201_CREATED)
async def add_quotation_line(
    payload: QuotationLineCreate,
    business_id: str = Path(...),
    quotation_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: QuotationService = Depends(get_scoped_quotation_service),
) -> QuotationLineResponse:
    return await service.add_line(business_id, quotation_id, current_user.id, payload)


@quotation_router.put("/{quotation_id}/lines/{line_id}", response_model=QuotationLineResponse)
async def update_quotation_line(
    payload: QuotationLineUpdate,
    business_id: str = Path(...),
    quotation_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: QuotationService = Depends(get_scoped_quotation_service),
) -> QuotationLineResponse:
    return await service.update_line(business_id, quotation_id, line_id, current_user.id, payload)


@quotation_router.delete("/{quotation_id}/lines/{line_id}")
async def delete_quotation_line(
    business_id: str = Path(...),
    quotation_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: QuotationService = Depends(get_scoped_quotation_service),
) -> dict:
    return await service.delete_line(business_id, quotation_id, line_id, current_user.id)


@quotation_router.post("/{quotation_id}/send", response_model=QuotationResponse)
async def send_quotation(
    business_id: str = Path(...),
    quotation_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: QuotationService = Depends(get_scoped_quotation_service),
) -> QuotationResponse:
    return await service.send_quotation(business_id, quotation_id, current_user.id)


@quotation_router.post("/{quotation_id}/accept", response_model=QuotationResponse)
async def accept_quotation(
    business_id: str = Path(...),
    quotation_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: QuotationService = Depends(get_scoped_quotation_service),
) -> QuotationResponse:
    return await service.accept_quotation(business_id, quotation_id, current_user.id)


@quotation_router.post("/{quotation_id}/reject", response_model=QuotationResponse)
async def reject_quotation(
    business_id: str = Path(...),
    quotation_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: QuotationService = Depends(get_scoped_quotation_service),
) -> QuotationResponse:
    return await service.reject_quotation(business_id, quotation_id, current_user.id)


@quotation_router.post("/{quotation_id}/cancel", response_model=QuotationResponse)
async def cancel_quotation(
    business_id: str = Path(...),
    quotation_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: QuotationService = Depends(get_scoped_quotation_service),
) -> QuotationResponse:
    return await service.cancel_quotation(business_id, quotation_id, current_user.id)


@quotation_router.post("/{quotation_id}/convert")
async def convert_quotation(
    payload: QuotationConvert,
    business_id: str = Path(...),
    quotation_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: QuotationService = Depends(get_scoped_quotation_service),
):
    return await service.convert_quotation(business_id, quotation_id, current_user.id, payload)


# === SALES ORDER ENDPOINTS ===

@sales_order_router.post("", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_sales_order(
    payload: SalesOrderCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesOrderService = Depends(get_scoped_sales_order_service),
) -> SalesOrderResponse:
    return await service.create_order(business_id, current_user.id, payload)


@sales_order_router.get("", response_model=SalesOrderListResponse)
async def list_sales_orders(
    business_id: str = Path(...),
    status: Optional[SalesOrderStatus] = Query(None),
    customer_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesOrderService = Depends(get_scoped_sales_order_service),
) -> SalesOrderListResponse:
    return await service.list_orders(
        business_id=business_id, user_id=current_user.id,
        status=status, customer_id=customer_id, branch_id=branch_id,
        search=search, page=page, page_size=page_size,
    )


@sales_order_router.get("/{order_id}", response_model=SalesOrderResponse)
async def get_sales_order(
    business_id: str = Path(...),
    order_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesOrderService = Depends(get_scoped_sales_order_service),
) -> SalesOrderResponse:
    return await service.get_order(business_id, order_id, current_user.id)


@sales_order_router.put("/{order_id}", response_model=SalesOrderResponse)
async def update_sales_order(
    payload: SalesOrderUpdate,
    business_id: str = Path(...),
    order_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesOrderService = Depends(get_scoped_sales_order_service),
) -> SalesOrderResponse:
    return await service.update_order(business_id, order_id, current_user.id, payload)


@sales_order_router.post("/{order_id}/lines", response_model=SalesOrderLineResponse, status_code=status.HTTP_201_CREATED)
async def add_sales_order_line(
    payload: SalesOrderLineCreate,
    business_id: str = Path(...),
    order_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesOrderService = Depends(get_scoped_sales_order_service),
) -> SalesOrderLineResponse:
    return await service.add_line(business_id, order_id, current_user.id, payload)


@sales_order_router.put("/{order_id}/lines/{line_id}", response_model=SalesOrderLineResponse)
async def update_sales_order_line(
    payload: SalesOrderLineUpdate,
    business_id: str = Path(...),
    order_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesOrderService = Depends(get_scoped_sales_order_service),
) -> SalesOrderLineResponse:
    return await service.update_line(business_id, order_id, line_id, current_user.id, payload)


@sales_order_router.delete("/{order_id}/lines/{line_id}")
async def delete_sales_order_line(
    business_id: str = Path(...),
    order_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesOrderService = Depends(get_scoped_sales_order_service),
) -> dict:
    return await service.delete_line(business_id, order_id, line_id, current_user.id)


@sales_order_router.post("/{order_id}/confirm", response_model=SalesOrderResponse)
async def confirm_sales_order(
    business_id: str = Path(...),
    order_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesOrderService = Depends(get_scoped_sales_order_service),
) -> SalesOrderResponse:
    return await service.confirm_order(business_id, order_id, current_user.id)


@sales_order_router.post("/{order_id}/cancel", response_model=SalesOrderResponse)
async def cancel_sales_order(
    business_id: str = Path(...),
    order_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesOrderService = Depends(get_scoped_sales_order_service),
) -> SalesOrderResponse:
    return await service.cancel_order(business_id, order_id, current_user.id)


@sales_order_router.post("/{order_id}/fulfill", response_model=SalesOrderResponse)
async def fulfill_sales_order(
    payload: SalesOrderFulfill,
    business_id: str = Path(...),
    order_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesOrderService = Depends(get_scoped_sales_order_service),
) -> SalesOrderResponse:
    return await service.fulfill_order(business_id, order_id, current_user.id, payload)


# === AVAILABILITY ENDPOINTS ===

@availability_router.get("/check", response_model=AvailabilityCheckResponse)
async def check_availability(
    business_id: str = Path(...),
    product_id: str = Query(...),
    variant_id: Optional[str] = Query(None),
    warehouse_id: str = Query(...),
    quantity: float = Query(..., gt=0),
    current_user: UserResponse = Depends(get_current_user),
    service: AvailabilityService = Depends(get_availability_svc),
) -> AvailabilityCheckResponse:
    from decimal import Decimal
    is_available, physical, reserved, available = await service.check_availability(
        business_id, warehouse_id, product_id, variant_id, Decimal(str(quantity)),
    )
    return AvailabilityCheckResponse(
        available=is_available,
        physical_on_hand=physical,
        active_reserved_quantity=reserved,
        available_to_sell=available,
        requested_quantity=Decimal(str(quantity)),
    )
