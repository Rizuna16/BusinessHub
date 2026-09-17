from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Path, Query, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.payment.schemas import (
    PaymentCreate,
    PaymentResponse,
    PaymentListResponse,
    PaymentDirection,
    PaymentTargetType,
    PaymentMethod,
    PaymentAnalyticsSummaryResponse,
    PaymentAnalyticsByDirectionResponse,
    PaymentAnalyticsByMethodResponse,
)
from app.modules.payment.service import (
    PaymentService,
    payment_service,
)


router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/payments",
    tags=["Payments"],
)


def get_payment_service() -> PaymentService:
    return payment_service


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    business_id: str = Path(...),
    payload: PaymentCreate = ...,
    current_user: UserResponse = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
):
    return await service.create_payment(business_id=business_id, user_id=current_user.id, payload=payload)


@router.get("", response_model=PaymentListResponse, status_code=status.HTTP_200_OK)
async def list_payments(
    business_id: str = Path(...),
    direction: Optional[PaymentDirection] = Query(None),
    target_type: Optional[PaymentTargetType] = Query(None),
    target_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
):
    return await service.list_payments(
        business_id=business_id, user_id=current_user.id, direction=direction,
        target_type=target_type, target_id=target_id, page=page, page_size=page_size
    )


@router.get("/{payment_id}", response_model=PaymentResponse, status_code=status.HTTP_200_OK)
async def get_payment(
    business_id: str = Path(...),
    payment_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
):
    return await service.get_payment(business_id=business_id, payment_id=payment_id, user_id=current_user.id)


@router.post("/{payment_id}/void", response_model=PaymentResponse, status_code=status.HTTP_200_OK)
async def void_payment(
    business_id: str = Path(...),
    payment_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
):
    return await service.void_payment(business_id=business_id, payment_id=payment_id, user_id=current_user.id)


# --- Payment Analytics ---

@router.get("/analytics/summary", response_model=PaymentAnalyticsSummaryResponse, status_code=status.HTTP_200_OK)
async def get_payment_analytics_summary(
    business_id: str = Path(...),
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    branch_id: Optional[str] = Query(None),
    direction: Optional[PaymentDirection] = Query(None),
    payment_method: Optional[PaymentMethod] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
):
    return await service.get_payment_analytics_summary(
        business_id=business_id, user_id=current_user.id,
        date_from=date_from, date_to=date_to,
        branch_id=branch_id, direction=direction, payment_method=payment_method,
    )


@router.get("/analytics/by-direction", response_model=PaymentAnalyticsByDirectionResponse, status_code=status.HTTP_200_OK)
async def get_payment_analytics_by_direction(
    business_id: str = Path(...),
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    branch_id: Optional[str] = Query(None),
    direction: Optional[PaymentDirection] = Query(None),
    payment_method: Optional[PaymentMethod] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
):
    return await service.get_payment_analytics_by_direction(
        business_id=business_id, user_id=current_user.id,
        date_from=date_from, date_to=date_to,
        branch_id=branch_id, direction=direction, payment_method=payment_method,
    )


@router.get("/analytics/by-method", response_model=PaymentAnalyticsByMethodResponse, status_code=status.HTTP_200_OK)
async def get_payment_analytics_by_method(
    business_id: str = Path(...),
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    branch_id: Optional[str] = Query(None),
    direction: Optional[PaymentDirection] = Query(None),
    payment_method: Optional[PaymentMethod] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
):
    return await service.get_payment_analytics_by_method(
        business_id=business_id, user_id=current_user.id,
        date_from=date_from, date_to=date_to,
        branch_id=branch_id, direction=direction, payment_method=payment_method,
    )
