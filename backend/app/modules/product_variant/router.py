from typing import List
from fastapi import APIRouter, Depends, Path, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.product_variant.schemas import (
    ProductVariantCreate,
    ProductVariantUpdate,
    ProductVariantResponse,
    ProductVariantListResponse,
)
from app.modules.product_variant.service import (
    product_variant_service,
    ProductVariantService,
)

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/products/{product_id}/variants",
    tags=["Product Variant"],
)


def get_product_variant_service() -> ProductVariantService:
    return product_variant_service


@router.post("", response_model=ProductVariantResponse, status_code=status.HTTP_201_CREATED)
async def create_variant(
    business_id: str = Path(...),
    product_id: str = Path(...),
    data: ProductVariantCreate = ...,
    current_user: UserResponse = Depends(get_current_user),
    service: ProductVariantService = Depends(get_product_variant_service),
):
    return await service.create_variant(business_id, product_id, current_user.id, data)


@router.get("", response_model=ProductVariantListResponse)
async def list_variants(
    business_id: str = Path(...),
    product_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ProductVariantService = Depends(get_product_variant_service),
):
    return await service.list_variants(business_id, current_user.id, product_id)


@router.get("/{variant_id}", response_model=ProductVariantResponse)
async def get_variant(
    business_id: str = Path(...),
    product_id: str = Path(...),
    variant_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ProductVariantService = Depends(get_product_variant_service),
):
    return await service.get_variant(business_id, current_user.id, product_id, variant_id)


@router.patch("/{variant_id}", response_model=ProductVariantResponse)
async def update_variant(
    business_id: str = Path(...),
    product_id: str = Path(...),
    variant_id: str = Path(...),
    data: ProductVariantUpdate = ...,
    current_user: UserResponse = Depends(get_current_user),
    service: ProductVariantService = Depends(get_product_variant_service),
):
    return await service.update_variant(
        business_id, current_user.id, product_id, variant_id, data
    )


@router.delete("/{variant_id}", response_model=ProductVariantResponse)
async def archive_variant(
    business_id: str = Path(...),
    product_id: str = Path(...),
    variant_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ProductVariantService = Depends(get_product_variant_service),
):
    return await service.archive_variant(
        business_id, current_user.id, product_id, variant_id
    )
