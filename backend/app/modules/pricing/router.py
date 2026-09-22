from typing import Optional
from fastapi import APIRouter, Depends, Path, Query, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.pricing.schemas import (
    PriceEntryCreate,
    PriceEntryListResponse,
    PriceEntryResponse,
    PriceEntryUpdate,
    PriceListCreate,
    PriceListListResponse,
    PriceListResponse,
    PriceListUpdate,
    DiscountRuleCreate,
    DiscountRuleUpdate,
)
from app.modules.pricing.service import PricingService, pricing_service

router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/price-lists",
    tags=["Pricing"],
)


def get_pricing_service() -> PricingService:
    return pricing_service


# Price List Endpoints


@router.post("", response_model=PriceListResponse, status_code=status.HTTP_201_CREATED)
async def create_price_list(
    payload: PriceListCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
) -> PriceListResponse:
    return await service.create_price_list(business_id, current_user.id, payload)


@router.get("", response_model=PriceListListResponse)
async def list_price_lists(
    business_id: str = Path(...),
    include_archived: bool = Query(False),
    current_user: UserResponse = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
) -> PriceListListResponse:
    return await service.list_price_lists(
        business_id, current_user.id, include_archived=include_archived
    )


@router.get("/{price_list_id}", response_model=PriceListResponse)
async def get_price_list(
    business_id: str = Path(...),
    price_list_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
) -> PriceListResponse:
    return await service.get_price_list(business_id, current_user.id, price_list_id)


@router.patch("/{price_list_id}", response_model=PriceListResponse)
async def update_price_list(
    payload: PriceListUpdate,
    business_id: str = Path(...),
    price_list_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
) -> PriceListResponse:
    return await service.update_price_list(
        business_id, current_user.id, price_list_id, payload
    )


@router.delete("/{price_list_id}", response_model=PriceListResponse)
async def archive_price_list(
    business_id: str = Path(...),
    price_list_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
) -> PriceListResponse:
    return await service.archive_price_list(business_id, current_user.id, price_list_id)


# Price Entry Endpoints


@router.post(
    "/{price_list_id}/prices",
    response_model=PriceEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_price_entry(
    payload: PriceEntryCreate,
    business_id: str = Path(...),
    price_list_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
) -> PriceEntryResponse:
    return await service.create_price_entry(
        business_id, price_list_id, current_user.id, payload
    )


@router.get("/{price_list_id}/prices", response_model=PriceEntryListResponse)
async def list_price_entries(
    business_id: str = Path(...),
    price_list_id: str = Path(...),
    include_archived: bool = Query(False),
    current_user: UserResponse = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
) -> PriceEntryListResponse:
    return await service.list_price_entries(
        business_id, price_list_id, current_user.id, include_archived=include_archived
    )


@router.get("/{price_list_id}/prices/{price_id}", response_model=PriceEntryResponse)
async def get_price_entry(
    business_id: str = Path(...),
    price_list_id: str = Path(...),
    price_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
) -> PriceEntryResponse:
    return await service.get_price_entry(
        business_id, price_list_id, price_id, current_user.id
    )


@router.patch("/{price_list_id}/prices/{price_id}", response_model=PriceEntryResponse)
async def update_price_entry(
    payload: PriceEntryUpdate,
    business_id: str = Path(...),
    price_list_id: str = Path(...),
    price_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
) -> PriceEntryResponse:
    return await service.update_price_entry(
        business_id, price_list_id, price_id, current_user.id, payload
    )


@router.delete("/{price_list_id}/prices/{price_id}", response_model=PriceEntryResponse)
async def archive_price_entry(
    business_id: str = Path(...),
    price_list_id: str = Path(...),
    price_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
) -> PriceEntryResponse:
    return await service.archive_price_entry(
        business_id, price_list_id, price_id, current_user.id
    )


# Discount Rule Endpoints


@router.get("/discount-rules")
async def list_discount_rules(
    business_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
    include_archived: bool = Query(False),
):
    return await service.discount_rule_list(business_id, current_user.id, include_archived)


@router.post("/discount-rules", status_code=status.HTTP_201_CREATED)
async def create_discount_rule(
    business_id: str,
    data: DiscountRuleCreate,
    current_user: UserResponse = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
):
    return await service.discount_rule_create(business_id, current_user.id, data)


@router.get("/discount-rules/{rule_id}")
async def get_discount_rule(
    business_id: str,
    rule_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
):
    return await service.discount_rule_get(business_id, current_user.id, rule_id)


@router.put("/discount-rules/{rule_id}")
async def update_discount_rule(
    business_id: str,
    rule_id: str,
    data: DiscountRuleUpdate,
    current_user: UserResponse = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
):
    return await service.discount_rule_update(business_id, current_user.id, rule_id, data)


@router.delete("/discount-rules/{rule_id}")
async def archive_discount_rule(
    business_id: str,
    rule_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
):
    return await service.discount_rule_archive(business_id, current_user.id, rule_id)


@router.post("/discount-rules/{rule_id}/activate")
async def activate_discount_rule(
    business_id: str,
    rule_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
):
    return await service.discount_rule_activate(business_id, current_user.id, rule_id)


@router.post("/discount-rules/{rule_id}/deactivate")
async def deactivate_discount_rule(
    business_id: str,
    rule_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
):
    return await service.discount_rule_deactivate(business_id, current_user.id, rule_id)
