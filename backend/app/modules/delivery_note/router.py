from typing import Optional
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.modules.business_membership.service import BusinessMembershipService
from app.modules.delivery_note.schemas import (
    DeliveryNoteResponse,
    DeliveryNoteListResponse,
    DeliveryNoteCreate,
    DeliveryNoteUpdate,
    DeliveryNoteStatus,
    DeliveryNoteLineCreate,
    DeliveryNoteLineResponse,
)
from app.modules.delivery_note.service import DeliveryNoteService, delivery_note_service

delivery_note_router = APIRouter(
    prefix=settings.api_v1_prefix + "/businesses/{business_id}/delivery-notes",
    tags=["Delivery Note"],
)


def get_delivery_note_svc() -> DeliveryNoteService:
    return delivery_note_service


async def get_scoped_delivery_note_service(session: AsyncSession = Depends(get_db_session)) -> DeliveryNoteService:
    from app.core.container import RepositoryContainer

    container = RepositoryContainer(session)
    membership_svc = BusinessMembershipService(
        repository=container.business_membership,
        user_repo=container.user,
        account_repo=container.account,
        business_repo=container.business,
    )
    return DeliveryNoteService(
        delivery_note_repo=container.delivery_note,
        sales_order_repo=container.sales_order,
        membership_service=membership_svc,
        session=session,
    )


@delivery_note_router.post("", response_model=DeliveryNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery_note(
    payload: DeliveryNoteCreate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: DeliveryNoteService = Depends(get_scoped_delivery_note_service),
) -> DeliveryNoteResponse:
    return await service.create_delivery_note(business_id, current_user.id, payload)


@delivery_note_router.get("", response_model=DeliveryNoteListResponse)
async def list_delivery_notes(
    business_id: str = Path(...),
    status: Optional[DeliveryNoteStatus] = Query(None),
    sales_order_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    service: DeliveryNoteService = Depends(get_scoped_delivery_note_service),
) -> DeliveryNoteListResponse:
    return await service.list_delivery_notes(
        business_id=business_id, user_id=current_user.id,
        status=status, sales_order_id=sales_order_id,
        search=search, page=page, page_size=page_size,
    )


@delivery_note_router.get("/{delivery_note_id}", response_model=DeliveryNoteResponse)
async def get_delivery_note(
    business_id: str = Path(...),
    delivery_note_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: DeliveryNoteService = Depends(get_scoped_delivery_note_service),
) -> DeliveryNoteResponse:
    return await service.get_delivery_note(business_id, delivery_note_id, current_user.id)


@delivery_note_router.put("/{delivery_note_id}", response_model=DeliveryNoteResponse)
async def update_delivery_note(
    payload: DeliveryNoteUpdate,
    business_id: str = Path(...),
    delivery_note_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: DeliveryNoteService = Depends(get_scoped_delivery_note_service),
) -> DeliveryNoteResponse:
    return await service.update_delivery_note(business_id, delivery_note_id, current_user.id, payload)


@delivery_note_router.post("/{delivery_note_id}/lines", response_model=DeliveryNoteLineResponse, status_code=status.HTTP_201_CREATED)
async def add_delivery_note_line(
    payload: DeliveryNoteLineCreate,
    business_id: str = Path(...),
    delivery_note_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: DeliveryNoteService = Depends(get_scoped_delivery_note_service),
) -> DeliveryNoteLineResponse:
    return await service.add_line(business_id, delivery_note_id, current_user.id, payload)


@delivery_note_router.put("/{delivery_note_id}/lines/{line_id}", response_model=DeliveryNoteLineResponse)
async def update_delivery_note_line(
    business_id: str = Path(...),
    delivery_note_id: str = Path(...),
    line_id: str = Path(...),
    delivery_quantity: float = Query(..., gt=0),
    notes: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    service: DeliveryNoteService = Depends(get_scoped_delivery_note_service),
) -> DeliveryNoteLineResponse:
    from decimal import Decimal
    return await service.update_line(business_id, delivery_note_id, line_id, current_user.id, Decimal(str(delivery_quantity)), notes)


@delivery_note_router.delete("/{delivery_note_id}/lines/{line_id}")
async def delete_delivery_note_line(
    business_id: str = Path(...),
    delivery_note_id: str = Path(...),
    line_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: DeliveryNoteService = Depends(get_scoped_delivery_note_service),
) -> dict:
    return await service.delete_line(business_id, delivery_note_id, line_id, current_user.id)


@delivery_note_router.post("/{delivery_note_id}/ready", response_model=DeliveryNoteResponse)
async def ready_delivery_note(
    business_id: str = Path(...),
    delivery_note_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: DeliveryNoteService = Depends(get_scoped_delivery_note_service),
) -> DeliveryNoteResponse:
    return await service.ready_delivery_note(business_id, delivery_note_id, current_user.id)


@delivery_note_router.post("/{delivery_note_id}/deliver", response_model=DeliveryNoteResponse)
async def deliver_delivery_note(
    business_id: str = Path(...),
    delivery_note_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: DeliveryNoteService = Depends(get_scoped_delivery_note_service),
) -> DeliveryNoteResponse:
    return await service.deliver_delivery_note(business_id, delivery_note_id, current_user.id)


@delivery_note_router.post("/{delivery_note_id}/cancel", response_model=DeliveryNoteResponse)
async def cancel_delivery_note(
    business_id: str = Path(...),
    delivery_note_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    service: DeliveryNoteService = Depends(get_scoped_delivery_note_service),
) -> DeliveryNoteResponse:
    return await service.cancel_delivery_note(business_id, delivery_note_id, current_user.id)
