from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Path, Query, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.profitability.schemas import ProductProfitabilityResponse
from app.modules.profitability.service import ProfitabilityService, profitability_service


router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/reports",
    tags=["Product Profitability Analytics"],
)


def get_profitability_service() -> ProfitabilityService:
    return profitability_service


@router.get("/product-profitability", response_model=ProductProfitabilityResponse, status_code=status.HTTP_200_OK)
async def get_product_profitability_report(
    business_id: str = Path(...),
    period_id: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    group_by: str = Query("product"),
    branch_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    variant_id: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: ProfitabilityService = Depends(get_profitability_service),
):
    return await service.get_profitability_report(
        business_id=business_id,
        user_id=current_user.id,
        period_id=period_id,
        date_from=date_from,
        date_to=date_to,
        group_by=group_by,
        branch_id=branch_id,
        product_id=product_id,
        variant_id=variant_id,
        category_id=category_id,
        customer_id=customer_id,
    )
