from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Path, Query, HTTPException, status

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.dashboard.schemas import OperationalDashboardResponse
from app.modules.dashboard.service import operational_dashboard_service


router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/dashboard",
    tags=["Dashboard"],
)


@router.get("/operational", response_model=OperationalDashboardResponse)
async def get_operational_dashboard(
    business_id: str = Path(...),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    branch_id: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
) -> OperationalDashboardResponse:
    if date_from is None and date_to is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Both date_from and date_to must be provided.",
        )
    if date_from is None or date_to is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Both date_from and date_to must be provided.",
        )
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from must be less than or equal to date_to.",
        )
    return await operational_dashboard_service.get_dashboard(
        business_id=business_id,
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        branch_id=branch_id,
    )
