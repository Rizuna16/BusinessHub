from typing import Optional
from fastapi import APIRouter, Depends, Path, Query, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.business_membership.service import BusinessMembershipService, business_membership_service
from app.modules.business_membership.schemas import BusinessMembershipInDB
from app.modules.customer.schemas import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListResponse,
    CustomerStatus,
    CustomerType,
)
from app.modules.customer.service import CustomerService, customer_service

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/customers",
    tags=["Customer"],
)


def get_customer_service() -> CustomerService:
    return customer_service


def get_membership_service() -> BusinessMembershipService:
    return business_membership_service


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(
    payload: CustomerCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    return await service.create_customer(business_id, current_user.id, payload)


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    business_id: str = Path(...),
    search: Optional[str] = Query(None),
    status: Optional[CustomerStatus] = Query(None),
    customer_type: Optional[CustomerType] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
) -> CustomerListResponse:
    return await service.list_customers(
        business_id=business_id,
        user_id=current_user.id,
        search=search,
        status_filter=status,
        customer_type=customer_type,
        page=page,
        page_size=page_size,
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    business_id: str = Path(...),
    customer_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    return await service.get_customer(business_id, current_user.id, customer_id)


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    payload: CustomerUpdate,
    business_id: str = Path(...),
    customer_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    return await service.update_customer(business_id, current_user.id, customer_id, payload)


@router.delete("/{customer_id}", response_model=CustomerResponse)
async def archive_customer(
    business_id: str = Path(...),
    customer_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    return await service.archive_customer(business_id, current_user.id, customer_id)


@router.post("/{customer_id}/activate", response_model=CustomerResponse)
async def activate_customer(
    business_id: str = Path(...),
    customer_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    return await service.activate_customer(business_id, current_user.id, customer_id)


@router.post("/{customer_id}/deactivate", response_model=CustomerResponse)
async def deactivate_customer(
    business_id: str = Path(...),
    customer_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    return await service.deactivate_customer(business_id, current_user.id, customer_id)
