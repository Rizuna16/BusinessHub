from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from app.modules.authentication.schemas import UserInDB
from app.modules.authentication.router import get_current_user
from app.modules.notification.schemas import (
    NotificationResponse,
    UnreadCountResponse,
    NotificationScope,
)
from app.modules.notification.service import NotificationService, notification_service
from app.modules.platform_admin.service import PlatformAdminService, platform_admin_service
from app.shared.utils import create_api_response


router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


async def get_tenant_user(
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    return current_user


async def get_platform_super_admin(
    current_user: UserInDB = Depends(get_current_user),
    service: PlatformAdminService = Depends(lambda: platform_admin_service),
) -> UserInDB:
    return await service.require_superadmin(current_user.id)


@router.get("")
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    user: UserInDB = Depends(get_tenant_user),
):
    notifications = await notification_service.list_notifications(
        recipient_id=user.id,
        scope=NotificationScope.TENANT,
        business_id=None,
        unread_only=unread_only,
        limit=limit,
    )
    return create_api_response(success=True, data=[n.model_dump() for n in notifications])


@router.get("/platform")
async def list_platform_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    user: UserInDB = Depends(get_platform_super_admin),
):
    notifications = await notification_service.list_notifications(
        recipient_id=user.id,
        scope=NotificationScope.PLATFORM,
        business_id=None,
        unread_only=unread_only,
        limit=limit,
    )
    return create_api_response(success=True, data=[n.model_dump() for n in notifications])


@router.get("/unread-count")
async def get_unread_count(
    user: UserInDB = Depends(get_tenant_user),
):
    count = await notification_service.get_unread_count(
        recipient_id=user.id,
        scope=NotificationScope.TENANT,
        business_id=None,
    )
    return create_api_response(success=True, data=UnreadCountResponse(count=count).model_dump())


@router.get("/platform/unread-count")
async def get_platform_unread_count(
    user: UserInDB = Depends(get_platform_super_admin),
):
    count = await notification_service.get_unread_count(
        recipient_id=user.id,
        scope=NotificationScope.PLATFORM,
        business_id=None,
    )
    return create_api_response(success=True, data=UnreadCountResponse(count=count).model_dump())


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    user: UserInDB = Depends(get_tenant_user),
):
    result = await notification_service.mark_as_read(notification_id, user.id)
    return create_api_response(success=True, data=result.model_dump())


@router.post("/platform/{notification_id}/read")
async def mark_platform_as_read(
    notification_id: str,
    user: UserInDB = Depends(get_platform_super_admin),
):
    result = await notification_service.mark_as_read(notification_id, user.id)
    return create_api_response(success=True, data=result.model_dump())


@router.post("/read-all")
async def mark_all_read(
    user: UserInDB = Depends(get_tenant_user),
):
    count = await notification_service.mark_all_as_read(
        recipient_id=user.id,
        scope=NotificationScope.TENANT,
        business_id=None,
    )
    return create_api_response(success=True, data={"marked_read": count})


@router.post("/platform/read-all")
async def mark_platform_all_read(
    user: UserInDB = Depends(get_platform_super_admin),
):
    count = await notification_service.mark_all_as_read(
        recipient_id=user.id,
        scope=NotificationScope.PLATFORM,
        business_id=None,
    )
    return create_api_response(success=True, data={"marked_read": count})


notification_router = router