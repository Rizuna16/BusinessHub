from typing import Optional
from fastapi import APIRouter, Depends, Path, Query, UploadFile, File, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.product_image.service import product_image_service, ProductImageService
from app.modules.product_image.schemas import ProductImageListResponse, ProductImageResponse

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/products",
    tags=["Product Images"],
)


def get_product_image_service() -> ProductImageService:
    return product_image_service


# ── Product Images ───────────────────────────────────────────────────────

@router.get("/{product_id}/images", response_model=ProductImageListResponse)
async def list_product_images(
    business_id: str = Path(...),
    product_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ProductImageService = Depends(get_product_image_service),
):
    return await service.list_images(business_id, current_user.id, product_id)


@router.post("/{product_id}/images", response_model=ProductImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_product_image(
    business_id: str = Path(...),
    product_id: str = Path(...),
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ProductImageService = Depends(get_product_image_service),
):
    return await service.upload_image(business_id, current_user.id, product_id, None, file)


@router.get("/{product_id}/images/{image_id}", response_model=ProductImageResponse)
async def get_product_image(
    business_id: str = Path(...),
    product_id: str = Path(...),
    image_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ProductImageService = Depends(get_product_image_service),
):
    return await service.get_image(business_id, current_user.id, image_id)


@router.patch("/{product_id}/images/{image_id}", response_model=ProductImageResponse)
async def update_product_image(
    business_id: str = Path(...),
    product_id: str = Path(...),
    image_id: str = Path(...),
    sort_order: Optional[int] = Query(None),
    set_primary: Optional[bool] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: ProductImageService = Depends(get_product_image_service),
):
    if set_primary is True:
        return await service.set_primary(business_id, current_user.id, image_id)
    elif sort_order is not None:
        return await service.update_sort_order(business_id, current_user.id, image_id, sort_order)
    else:
        image = await service.get_image(business_id, current_user.id, image_id)
        return image


@router.delete("/{product_id}/images/{image_id}", response_model=ProductImageResponse)
async def archive_product_image(
    business_id: str = Path(...),
    product_id: str = Path(...),
    image_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ProductImageService = Depends(get_product_image_service),
):
    return await service.archive_image(business_id, current_user.id, image_id)


# ── Variant Images ───────────────────────────────────────────────────────

@router.get("/{product_id}/variants/{variant_id}/images", response_model=ProductImageListResponse)
async def list_variant_images(
    business_id: str = Path(...),
    product_id: str = Path(...),
    variant_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ProductImageService = Depends(get_product_image_service),
):
    return await service.list_images(business_id, current_user.id, product_id, variant_id)


@router.post("/{product_id}/variants/{variant_id}/images", response_model=ProductImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_variant_image(
    business_id: str = Path(...),
    product_id: str = Path(...),
    variant_id: str = Path(...),
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ProductImageService = Depends(get_product_image_service),
):
    return await service.upload_image(business_id, current_user.id, product_id, variant_id, file)


@router.get("/{product_id}/variants/{variant_id}/images/{image_id}", response_model=ProductImageResponse)
async def get_variant_image(
    business_id: str = Path(...),
    product_id: str = Path(...),
    variant_id: str = Path(...),
    image_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ProductImageService = Depends(get_product_image_service),
):
    return await service.get_image(business_id, current_user.id, image_id)


@router.patch("/{product_id}/variants/{variant_id}/images/{image_id}", response_model=ProductImageResponse)
async def update_variant_image(
    business_id: str = Path(...),
    product_id: str = Path(...),
    variant_id: str = Path(...),
    image_id: str = Path(...),
    sort_order: Optional[int] = Query(None),
    set_primary: Optional[bool] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: ProductImageService = Depends(get_product_image_service),
):
    if set_primary is True:
        return await service.set_primary(business_id, current_user.id, image_id)
    elif sort_order is not None:
        return await service.update_sort_order(business_id, current_user.id, image_id, sort_order)
    else:
        image = await service.get_image(business_id, current_user.id, image_id)
        return image


@router.delete("/{product_id}/variants/{variant_id}/images/{image_id}", response_model=ProductImageResponse)
async def archive_variant_image(
    business_id: str = Path(...),
    product_id: str = Path(...),
    variant_id: str = Path(...),
    image_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: ProductImageService = Depends(get_product_image_service),
):
    return await service.archive_image(business_id, current_user.id, image_id)
