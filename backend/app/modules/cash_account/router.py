from fastapi import APIRouter, Depends, Path, Query, status
from typing import Optional, List
from datetime import datetime

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.cash_account.schemas import (
    CashAccountResponse,
    CashAccountListResponse,
    CashAccountCreate,
    CashAccountUpdate,
    CashMovementResponse,
    CashMovementListResponse,
    CashMovementCreate,
    CashTransferInput,
    CashSummaryResponse,
    CashAccountType,
    CashAccountStatus,
    CashMovementType,
)
from app.modules.cash_account.service import (
    CashAccountService,
    cash_account_service,
)

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/cash-accounts",
    tags=["Cash Accounts"],
)


def get_cash_account_service() -> CashAccountService:
    return cash_account_service


@router.post("", response_model=CashAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: CashAccountCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CashAccountService = Depends(get_cash_account_service),
):
    return await service.create_account(business_id, current_user.id, payload)


@router.get("", response_model=CashAccountListResponse, status_code=status.HTTP_200_OK)
async def list_accounts(
    business_id: str = Path(...),
    account_type: Optional[CashAccountType] = Query(None),
    status: Optional[CashAccountStatus] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: CashAccountService = Depends(get_cash_account_service),
):
    return await service.list_accounts(
        business_id=business_id,
        user_id=current_user.id,
        account_type=account_type,
        status_filter=status,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=CashSummaryResponse, status_code=status.HTTP_200_OK)
async def get_cash_summary(
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CashAccountService = Depends(get_cash_account_service),
):
    return await service.get_summary(business_id=business_id, user_id=current_user.id)


@router.post("/transfers", response_model=List[CashMovementResponse], status_code=status.HTTP_201_CREATED)
async def create_transfer(
    payload: CashTransferInput,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CashAccountService = Depends(get_cash_account_service),
):
    return await service.create_transfer(business_id, current_user.id, payload)


@router.get("/{account_id}", response_model=CashAccountResponse, status_code=status.HTTP_200_OK)
async def get_account(
    business_id: str = Path(...),
    account_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CashAccountService = Depends(get_cash_account_service),
):
    return await service.get_account(business_id, account_id, current_user.id)


@router.patch("/{account_id}", response_model=CashAccountResponse, status_code=status.HTTP_200_OK)
async def update_account(
    payload: CashAccountUpdate,
    business_id: str = Path(...),
    account_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CashAccountService = Depends(get_cash_account_service),
):
    return await service.update_account(business_id, account_id, current_user.id, payload)


@router.post("/{account_id}/activate", response_model=CashAccountResponse, status_code=status.HTTP_200_OK)
async def activate_account(
    business_id: str = Path(...),
    account_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CashAccountService = Depends(get_cash_account_service),
):
    return await service.activate_account(business_id, account_id, current_user.id)


@router.post("/{account_id}/deactivate", response_model=CashAccountResponse, status_code=status.HTTP_200_OK)
async def deactivate_account(
    business_id: str = Path(...),
    account_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CashAccountService = Depends(get_cash_account_service),
):
    return await service.deactivate_account(business_id, account_id, current_user.id)


@router.post("/{account_id}/movements", response_model=CashMovementResponse, status_code=status.HTTP_201_CREATED)
async def create_cash_movement(
    payload: CashMovementCreate,
    business_id: str = Path(...),
    account_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CashAccountService = Depends(get_cash_account_service),
):
    return await service.create_cash_movement(business_id, account_id, current_user.id, payload)


@router.get("/{account_id}/movements", response_model=CashMovementListResponse, status_code=status.HTTP_200_OK)
async def list_movements(
    business_id: str = Path(...),
    account_id: str = Path(...),
    movement_type: Optional[CashMovementType] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: CashAccountService = Depends(get_cash_account_service),
):
    return await service.list_movements(
        business_id=business_id,
        account_id=account_id,
        user_id=current_user.id,
        movement_type=movement_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
