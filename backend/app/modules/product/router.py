from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.product.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductStatus,
    ProductType,
    ProductResponse,
    ProductListResponse,
)
from app.modules.product.service import product_service, ProductService

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/products",
    tags=["Product"],
)


def get_product_service() -> ProductService:
    return product_service


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    business_id: str = Path(...),
    data: ProductCreate = ...,
    current_user: UserResponse = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.create_product(business_id, current_user.id, data)


@router.get("", response_model=ProductListResponse)
async def list_products(
    business_id: str = Path(...),
    status: Optional[ProductStatus] = Query(None),
    product_type: Optional[ProductType] = Query(None),
    category_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.list_products(
        business_id=business_id,
        user_id=current_user.id,
        status=status,
        product_type=product_type,
        category_id=category_id,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    business_id: str = Path(...),
    product_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.get_product(business_id, current_user.id, product_id)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    business_id: str = Path(...),
    product_id: str = Path(...),
    data: ProductUpdate = ...,
    current_user: UserResponse = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.update_product(business_id, current_user.id, product_id, data)


@router.delete("/{product_id}", response_model=ProductResponse)
async def archive_product(
    business_id: str = Path(...),
    product_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    return await service.archive_product(business_id, current_user.id, product_id)
