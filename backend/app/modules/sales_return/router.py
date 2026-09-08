from fastapi import APIRouter, Depends, Path, Query, status
from typing import Optional

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.sales_return.schemas import (
    SalesReturnResponse,
    SalesReturnListResponse,
    SalesReturnCreate,
    SalesReturnUpdate,
    SalesReturnLineResponse,
    SalesReturnLineCreate,
    SalesReturnLineUpdate,
    SalesReturnStatus,
)
from app.modules.sales_return.service import (
    SalesReturnService,
    sales_return_service,
)

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/sales-returns",
    tags=["Sales Returns"],
)


def get_sales_return_service() -> SalesReturnService:
    return sales_return_service


@router.post("", response_model=SalesReturnResponse, status_code=status.HTTP_201_CREATED)
async def create_sales_return(
    payload: SalesReturnCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesReturnService = Depends(get_sales_return_service),
):
    return await service.create_return(business_id, current_user.id, payload)


@router.get("", response_model=SalesReturnListResponse, status_code=status.HTTP_200_OK)
async def list_sales_returns(
    business_id: str = Path(...),
    status: Optional[SalesReturnStatus] = Query(None),
    sales_id: Optional[str] = Query(None),
    inventory_location_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesReturnService = Depends(get_sales_return_service),
):
    return await service.list_returns(
        business_id=business_id,
        user_id=current_user.id,
        status_filter=status,
        sales_id=sales_id,
        inventory_location_id=inventory_location_id,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/{return_id}", response_model=SalesReturnResponse, status_code=status.HTTP_200_OK)
async def get_sales_return(
    business_id: str = Path(...),
    return_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesReturnService = Depends(get_sales_return_service),
):
    return await service.get_return(business_id, return_id, current_user.id)


@router.patch("/{return_id}", response_model=SalesReturnResponse, status_code=status.HTTP_200_OK)
async def update_sales_return(
    payload: SalesReturnUpdate,
    business_id: str = Path(...),
    return_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesReturnService = Depends(get_sales_return_service),
):
    return await service.update_return(business_id, return_id, current_user.id, payload)


@router.post("/{return_id}/lines", response_model=SalesReturnLineResponse, status_code=status.HTTP_201_CREATED)
async def add_sales_return_line(
    payload: SalesReturnLineCreate,
    business_id: str = Path(...),
    return_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesReturnService = Depends(get_sales_return_service),
):
    return await service.add_line(business_id, return_id, current_user.id, payload)


@router.patch("/{return_id}/lines/{line_id}", response_model=SalesReturnLineResponse, status_code=status.HTTP_200_OK)
async def update_sales_return_line(
    payload: SalesReturnLineUpdate,
    business_id: str = Path(...),
    return_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesReturnService = Depends(get_sales_return_service),
):
    return await service.update_line(business_id, return_id, line_id, current_user.id, payload)


@router.delete("/{return_id}/lines/{line_id}", status_code=status.HTTP_200_OK)
async def delete_sales_return_line(
    business_id: str = Path(...),
    return_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesReturnService = Depends(get_sales_return_service),
):
    return await service.delete_line(business_id, return_id, line_id, current_user.id)


@router.post("/{return_id}/finalize", response_model=SalesReturnResponse, status_code=status.HTTP_200_OK)
async def finalize_sales_return(
    business_id: str = Path(...),
    return_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesReturnService = Depends(get_sales_return_service),
):
    return await service.finalize_return(business_id, return_id, current_user.id)


@router.post("/{return_id}/cancel", response_model=SalesReturnResponse, status_code=status.HTTP_200_OK)
async def cancel_sales_return(
    business_id: str = Path(...),
    return_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: SalesReturnService = Depends(get_sales_return_service),
):
    return await service.cancel_return(business_id, return_id, current_user.id)
