from fastapi import APIRouter, Depends, Path, status
from typing import List

from app.core.config import settings
from app.modules.business_template.schemas import (
    TemplateResponse,
    BusinessConfigurationResponse,
    BusinessConfigurationUpdate,
)
from app.modules.business_template.service import (
    TemplateService,
    template_service,
    BusinessConfigurationService,
    business_configuration_service,
)
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse

router = APIRouter(prefix=settings.api_v1_prefix, tags=["Business Template & Configuration"])


def get_template_service() -> TemplateService:
    return template_service


def get_business_config_service() -> BusinessConfigurationService:
    return business_configuration_service


@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    t_service: TemplateService = Depends(get_template_service),
) -> List[TemplateResponse]:
    """List all active system business templates (read-only for customers)."""
    return await t_service.list_active_templates()


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str = Path(...),
    t_service: TemplateService = Depends(get_template_service),
) -> TemplateResponse:
    """Get a specific system business template by ID (read-only)."""
    return await t_service.get_template(template_id)


@router.get("/businesses/{business_id}/configuration", response_model=BusinessConfigurationResponse)
async def get_business_configuration(
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    c_service: BusinessConfigurationService = Depends(get_business_config_service),
) -> BusinessConfigurationResponse:
    """Get effective configuration snapshot for a business. Allowed for OWNER, ADMIN, MEMBER."""
    return await c_service.get_configuration(business_id, current_user.id)


@router.patch("/businesses/{business_id}/configuration", response_model=BusinessConfigurationResponse)
async def update_business_configuration(
    payload: BusinessConfigurationUpdate,
    business_id: str = Path(...),
    current_user: UserResponse = Depends(get_current_user),
    c_service: BusinessConfigurationService = Depends(get_business_config_service),
) -> BusinessConfigurationResponse:
    """Update configuration overrides for a business. Allowed only for OWNER and ADMIN."""
    return await c_service.update_configuration(business_id, current_user.id, payload)
