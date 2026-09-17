from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import Response
from typing import Optional

from app.core.config import settings
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse, PlatformRole
from app.modules.business_membership.service import business_membership_service
from app.modules.export.registry import (
    get_export_definition,
    validate_resource,
    validate_format,
    validate_role,
    ExportResourceType,
)
from app.modules.export.service import export_service


router = APIRouter(
    tags=["Data Export"],
)


async def _resolve_user_role(business_id: str, user_id: str) -> str:
    membership = await business_membership_service.get_active_membership(business_id, user_id)
    if not membership or not hasattr(membership, "role"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not have an active membership in this business.",
        )
    return membership.role.value if hasattr(membership.role, "value") else str(membership.role)


async def _resolve_business_slug(business_id: str) -> str:
    try:
        from app.modules.business.repository import business_repository
        biz = await business_repository.get_by_id(business_id)
        if biz and hasattr(biz, "slug") and biz.slug:
            return biz.slug
        if biz and hasattr(biz, "name") and biz.name:
            return biz.name
    except Exception:
        pass
    return "business"


@router.get(
    settings.api_v1_prefix + "/businesses/{business_id}/export/table/{resource_key}",
)
async def export_table(
    business_id: str = Path(...),
    resource_key: str = Path(...),
    format: str = Query("csv", alias="format"),
    export_mode: str = Query("all_matching", alias="export_mode"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("desc"),
    search: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    warehouse_id: Optional[str] = Query(None),
    location_id: Optional[str] = Query(None),
    supplier_id: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    as_of_date: Optional[str] = Query(None),
    unit_type: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
):
    defn = validate_resource(resource_key)
    if defn.resource_type != ExportResourceType.TABLE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"'{resource_key}' is not a table export resource.",
        )

    user_role = await _resolve_user_role(business_id, current_user.id)
    business_slug = await _resolve_business_slug(business_id)

    filters = {}
    if search:
        filters["search"] = search
    if category_id:
        filters["category_id"] = category_id
    if product_id:
        filters["product_id"] = product_id
    if warehouse_id:
        filters["warehouse_id"] = warehouse_id
    if location_id:
        filters["location_id"] = location_id
    if supplier_id:
        filters["supplier_id"] = supplier_id
    if customer_id:
        filters["customer_id"] = customer_id
    if branch_id:
        filters["branch_id"] = branch_id
    if status:
        filters["status"] = status
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    if as_of_date:
        filters["as_of_date"] = as_of_date
    if unit_type:
        filters["unit_type"] = unit_type

    content, content_type, filename = await export_service.export_table(
        resource_key=resource_key,
        business_id=business_id,
        user_id=current_user.id,
        user_role=user_role,
        fmt=format,
        export_mode=export_mode,
        page=page,
        page_size=page_size,
        filters=filters,
        business_slug=business_slug,
    )

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get(
    settings.api_v1_prefix + "/businesses/{business_id}/export/report/{resource_key}",
)
async def export_report(
    business_id: str = Path(...),
    resource_key: str = Path(...),
    format: str = Query("csv", alias="format"),
    period_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
):
    defn = validate_resource(resource_key)
    if defn.resource_type != ExportResourceType.REPORT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"'{resource_key}' is not a report export resource.",
        )

    user_role = await _resolve_user_role(business_id, current_user.id)
    business_slug = await _resolve_business_slug(business_id)

    filters = {}
    if period_id:
        filters["period_id"] = period_id
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    if year:
        filters["year"] = year
    if month:
        filters["month"] = month

    content, content_type, filename = await export_service.export_report(
        resource_key=resource_key,
        business_id=business_id,
        user_id=current_user.id,
        user_role=user_role,
        fmt=format,
        filters=filters,
        business_slug=business_slug,
    )

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get(
    settings.api_v1_prefix + "/platform/export/{resource_key}",
)
async def export_platform(
    resource_key: str = Path(...),
    format: str = Query("csv", alias="format"),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: UserResponse = Depends(get_current_user),
):
    defn = validate_resource(resource_key)
    if defn.resource_type != ExportResourceType.PLATFORM:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"'{resource_key}' is not a platform export resource.",
        )

    if not hasattr(current_user, "platform_role") or current_user.platform_role != PlatformRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform Super Admin authority required.",
        )

    filters = {}
    if search:
        filters["search"] = search
    if status_filter:
        filters["status"] = status_filter

    content, content_type, filename = await export_service.export_platform(
        resource_key=resource_key,
        user_id=current_user.id,
        user_role="SUPER_ADMIN",
        fmt=format,
        filters=filters,
    )

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
