from fastapi import APIRouter, Depends, Query, status
from typing import List, Optional
from datetime import datetime

from app.modules.authentication.schemas import UserInDB
from app.modules.authentication.router import get_current_user
from app.modules.business.schemas import BusinessStatus
from app.modules.subscription.schemas import SubscriptionResponse, SubscriptionOverrideInput
from app.modules.platform_admin.schemas import (
    PlatformDashboardResponse, PlatformBusinessDetailResponse, PlatformUserResponse,
    PlatformAuditLogResponse, BusinessActionInput
)
from app.modules.platform_admin.service import PlatformAdminService, platform_admin_service
from app.shared.utils import create_api_response


router = APIRouter(prefix="/api/v1/platform", tags=["Platform Administration"])


async def get_super_admin(
    current_user: UserInDB = Depends(get_current_user),
    service: PlatformAdminService = Depends(lambda: platform_admin_service),
) -> UserInDB:
    return await service.require_superadmin(current_user.id)


@router.get("/dashboard")
async def get_platform_dashboard(
    superadmin: UserInDB = Depends(get_super_admin),
    service: PlatformAdminService = Depends(lambda: platform_admin_service),
):
    dashboard = await service.get_dashboard(superadmin)
    return create_api_response(success=True, data=dashboard, message="Platform dashboard retrieved successfully.")


@router.get("/businesses")
async def list_platform_businesses(
    status: Optional[BusinessStatus] = None,
    search: Optional[str] = None,
    superadmin: UserInDB = Depends(get_super_admin),
    service: PlatformAdminService = Depends(lambda: platform_admin_service),
):
    businesses = await service.list_businesses(superadmin, status_filter=status, search=search)
    return create_api_response(success=True, data=businesses, message="Businesses retrieved successfully.")


@router.get("/businesses/{business_id}")
async def get_platform_business_detail(
    business_id: str,
    superadmin: UserInDB = Depends(get_super_admin),
    service: PlatformAdminService = Depends(lambda: platform_admin_service),
):
    detail = await service.get_business_detail(superadmin, business_id)
    return create_api_response(success=True, data=detail, message="Business detail retrieved successfully.")


@router.post("/businesses/{business_id}/suspend")
async def suspend_business(
    business_id: str,
    action_input: BusinessActionInput,
    superadmin: UserInDB = Depends(get_super_admin),
    service: PlatformAdminService = Depends(lambda: platform_admin_service),
):
    detail = await service.suspend_business(superadmin, business_id, action_input)
    return create_api_response(success=True, data=detail, message="Business suspended successfully.")


@router.post("/businesses/{business_id}/activate")
async def activate_business(
    business_id: str,
    action_input: BusinessActionInput,
    superadmin: UserInDB = Depends(get_super_admin),
    service: PlatformAdminService = Depends(lambda: platform_admin_service),
):
    detail = await service.activate_business(superadmin, business_id, action_input)
    return create_api_response(success=True, data=detail, message="Business activated successfully.")


@router.post("/businesses/{business_id}/archive")
async def archive_business(
    business_id: str,
    action_input: BusinessActionInput,
    superadmin: UserInDB = Depends(get_super_admin),
    service: PlatformAdminService = Depends(lambda: platform_admin_service),
):
    detail = await service.archive_business(superadmin, business_id, action_input)
    return create_api_response(success=True, data=detail, message="Business archived successfully.")


@router.get("/businesses/{business_id}/members")
async def list_business_members_for_platform(
    business_id: str,
    superadmin: UserInDB = Depends(get_super_admin),
    service: PlatformAdminService = Depends(lambda: platform_admin_service),
):
    members = await service.list_business_members(superadmin, business_id)
    return create_api_response(success=True, data=members, message="Business members retrieved successfully.")


@router.get("/users")
async def list_platform_users(
    search: Optional[str] = None,
    superadmin: UserInDB = Depends(get_super_admin),
    service: PlatformAdminService = Depends(lambda: platform_admin_service),
):
    users = await service.list_users(superadmin, search=search)
    return create_api_response(success=True, data=users, message="Global users retrieved successfully.")


@router.get("/audit-logs")
async def list_platform_audit_logs(
    actor_id: Optional[str] = None,
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    superadmin: UserInDB = Depends(get_super_admin),
    service: PlatformAdminService = Depends(lambda: platform_admin_service),
):
    logs = await service.list_audit_logs(
        superadmin,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        from_date=from_date,
        to_date=to_date,
    )
    return create_api_response(success=True, data=logs, message="Audit logs retrieved successfully.")


@router.post("/subscriptions/{subscription_id}/override")
async def override_subscription(
    subscription_id: str,
    override: SubscriptionOverrideInput,
    superadmin: UserInDB = Depends(get_super_admin),
    service: PlatformAdminService = Depends(lambda: platform_admin_service),
):
    result = await service.override_subscription(superadmin, subscription_id, override)
    return create_api_response(success=True, data=result.model_dump())
