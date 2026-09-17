from fastapi import APIRouter, Depends, Path, Query, status
from typing import Optional

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.cashier_shift.schemas import (
    CashierShiftResponse,
    CashierShiftListResponse,
    CashierShiftCreate,
    CashierShiftClose,
    CashierShiftForceClose,
    ShiftStatus,
)
from app.modules.cashier_shift.service import (
    CashierShiftService,
    cashier_shift_service,
)
from app.modules.cash_account.schemas import CashMovementListResponse


router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/shifts",
    tags=["Cashier Shifts"],
)


def get_cashier_shift_service() -> CashierShiftService:
    return cashier_shift_service


@router.post("", response_model=CashierShiftResponse, status_code=status.HTTP_201_CREATED)
async def open_shift(
    payload: CashierShiftCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CashierShiftService = Depends(get_cashier_shift_service),
):
    return await service.open_shift(business_id, current_user.id, payload)


@router.get("", response_model=CashierShiftListResponse, status_code=status.HTTP_200_OK)
async def list_shifts(
    business_id: str = Path(...),
    status_filter: Optional[ShiftStatus] = Query(None, alias="status"),
    branch_id: Optional[str] = Query(None),
    cashier_user_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: CashierShiftService = Depends(get_cashier_shift_service),
):
    return await service.list_shifts(
        business_id=business_id,
        user_id=current_user.id,
        status_filter=status_filter,
        branch_id=branch_id,
        cashier_user_id=cashier_user_id,
        page=page,
        page_size=page_size,
    )


@router.get("/{shift_id}", response_model=CashierShiftResponse, status_code=status.HTTP_200_OK)
async def get_shift(
    business_id: str = Path(...),
    shift_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CashierShiftService = Depends(get_cashier_shift_service),
):
    return await service.get_shift(business_id, shift_id, current_user.id)


@router.get("/{shift_id}/transactions", response_model=CashMovementListResponse, status_code=status.HTTP_200_OK)
async def get_shift_transactions(
    business_id: str = Path(...),
    shift_id: str = Path(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: CashierShiftService = Depends(get_cashier_shift_service),
):
    return await service.get_shift_transactions(
        business_id=business_id,
        shift_id=shift_id,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )


@router.patch("/{shift_id}/close", response_model=CashierShiftResponse, status_code=status.HTTP_200_OK)
async def close_shift(
    payload: CashierShiftClose,
    business_id: str = Path(...),
    shift_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CashierShiftService = Depends(get_cashier_shift_service),
):
    return await service.close_shift(business_id, shift_id, current_user.id, payload)


@router.patch("/{shift_id}/force-close", response_model=CashierShiftResponse, status_code=status.HTTP_200_OK)
async def force_close_shift(
    payload: CashierShiftForceClose,
    business_id: str = Path(...),
    shift_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CashierShiftService = Depends(get_cashier_shift_service),
):
    return await service.force_close_shift(business_id, shift_id, current_user.id, payload)
