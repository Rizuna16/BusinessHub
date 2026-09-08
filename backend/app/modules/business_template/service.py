from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status

from app.modules.business_template.schemas import (
    TemplateResponse,
    BusinessConfigurationResponse,
    BusinessConfigurationUpdate,
)
from app.modules.business_template.repository import (
    AbstractBusinessTemplateRepository,
    AbstractBusinessConfigurationRepository,
    template_repository,
    business_configuration_repository,
    BusinessConfigurationRecord,
)
from app.modules.business.repository import AbstractBusinessRepository, business_repository
from app.modules.business_membership.service import BusinessMembershipService, business_membership_service
from app.modules.business_membership.schemas import BusinessMembershipRole


class TemplateService:
    def __init__(self, repository: AbstractBusinessTemplateRepository = template_repository):
        self.repository = repository

    async def list_active_templates(self) -> List[TemplateResponse]:
        return await self.repository.list_active()

    async def get_template(self, template_id: str) -> TemplateResponse:
        template = await self.repository.get_by_id(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found.",
            )
        return template

    async def resolve_template(self, business_type: str, preset_code: Optional[str] = None) -> TemplateResponse:
        template = await self.repository.get_default_for_business_type(business_type, preset_code)
        if not template:
            # Safe CORE baseline fallback
            templates = await self.repository.list_active()
            if templates:
                return templates[0]
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No suitable template found for business type.",
            )
        return template


class BusinessConfigurationService:
    def __init__(
        self,
        config_repo: AbstractBusinessConfigurationRepository = business_configuration_repository,
        template_repo: AbstractBusinessTemplateRepository = template_repository,
        business_repo: AbstractBusinessRepository = business_repository,
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.config_repo = config_repo
        self.template_repo = template_repo
        self.business_repo = business_repo
        self.membership_service = membership_service

    async def initialize_configuration_for_business(self, business_id: str, business_type: str) -> BusinessConfigurationRecord:
        """Initialize configuration snapshot for a newly created business."""
        existing = await self.config_repo.get_by_business(business_id)
        if existing:
            return existing

        template = await self.template_repo.get_default_for_business_type(business_type, "STANDARD")
        if not template:
            templates = await self.template_repo.list_active()
            template = templates[0] if templates else None

        if not template:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No template available for business initialization.",
            )

        return await self.config_repo.create(
            business_id=business_id,
            template_id=template.id,
            template_code=template.code,
            template_version=template.version,
            preset_code=template.preset_code,
            configuration=template.default_configuration,
        )

    async def _build_effective_response(self, record: BusinessConfigurationRecord) -> BusinessConfigurationResponse:
        template = await self.template_repo.get_by_code_version(record.template_code, record.template_version)
        if not template:
            # Fallback to get by id or any active template matching code
            template = await self.template_repo.get_by_id(record.template_id)
            if not template:
                templates = await self.template_repo.list_active()
                template = templates[0] if templates else None

        default_config = template.default_configuration if template else {}
        effective_config = {**default_config, **record.configuration}

        # Effective modules
        modules_list = template.modules if template else []
        effective_modules = []
        for m in modules_list:
            mod_dict = m.model_dump()
            # Check override
            if m.code in record.module_overrides:
                # Configuration override for modules
                pass
            effective_modules.append(mod_dict)

        # Effective features
        features_list = template.features if template else []
        effective_features = []
        for f in features_list:
            f_dict = f.model_dump()
            enabled = f.enabled_default
            if f.code in record.feature_overrides:
                enabled = record.feature_overrides[f.code]
            f_dict["enabled"] = enabled
            effective_features.append(f_dict)

        # Effective menus
        menus_list = template.menus if template else []
        effective_menus = [m.model_dump() for m in menus_list]

        # Effective widgets
        widgets_list = template.dashboard_widgets if template else []
        effective_widgets = []
        for w in widgets_list:
            w_dict = w.model_dump()
            enabled = w.enabled_default
            # Apply widget overrides if any
            effective_widgets.append(w_dict)

        return BusinessConfigurationResponse(
            id=record.id,
            business_id=record.business_id,
            template_id=record.template_id,
            template_code=record.template_code,
            template_version=record.template_version,
            preset_code=record.preset_code,
            configuration=record.configuration,
            module_overrides=record.module_overrides,
            feature_overrides=record.feature_overrides,
            menu_overrides=record.menu_overrides,
            widget_overrides=record.widget_overrides,
            effective_configuration=effective_config,
            effective_modules=effective_modules,
            effective_features=effective_features,
            effective_menus=effective_menus,
            effective_widgets=effective_widgets,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def get_configuration(self, business_id: str, user_id: str) -> BusinessConfigurationResponse:
        # Require active membership (OWNER, ADMIN, MEMBER -> all allowed to read)
        await self.membership_service.require_active_membership(business_id, user_id)

        # Ensure business exists
        business = await self.business_repo.get_by_id(business_id)
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found.",
            )

        record = await self.config_repo.get_by_business(business_id)
        if not record:
            # Lazy initialization for existing businesses without configuration
            record = await self.initialize_configuration_for_business(business_id, business.business_type)

        return await self._build_effective_response(record)

    async def update_configuration(
        self, business_id: str, user_id: str, payload: BusinessConfigurationUpdate
    ) -> BusinessConfigurationResponse:
        membership = await self.membership_service.require_active_membership(business_id, user_id)
        if membership.role not in (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Business MEMBER role is read-only. ADMIN or OWNER role required to update configuration.",
            )

        business = await self.business_repo.get_by_id(business_id)
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found.",
            )

        record = await self.config_repo.get_by_business(business_id)
        if not record:
            record = await self.initialize_configuration_for_business(business_id, business.business_type)

        # Validate core module protection
        if payload.module_overrides:
            core_modules = ["CORE", "ACCOUNT", "BUSINESS", "MEMBERSHIP", "BRANCH"]
            for mod in core_modules:
                if mod in payload.module_overrides and not payload.module_overrides[mod]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot disable core mandatory module: {mod}.",
                    )

        updated_record = await self.config_repo.update(
            business_id=business_id,
            configuration=payload.configuration,
            module_overrides=payload.module_overrides,
            feature_overrides=payload.feature_overrides,
            menu_overrides=payload.menu_overrides,
            widget_overrides=payload.widget_overrides,
        )

        return await self._build_effective_response(updated_record)


template_service = TemplateService()
business_configuration_service = BusinessConfigurationService()
