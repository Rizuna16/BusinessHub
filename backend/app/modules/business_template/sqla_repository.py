from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.business_template.models import (
    BusinessTemplateInDB as TemplateModel,
    BusinessConfigurationRecord as ConfigRecordModel,
)
from app.modules.business_template.repository import (
    AbstractBusinessTemplateRepository,
    AbstractBusinessConfigurationRepository,
    BusinessConfigurationRecord,
)
from app.modules.business_template.schemas import (
    TemplateResponse,
    TemplateStatus,
    ModuleDefinition,
    FeatureDefinition,
    MenuDefinition,
    DashboardWidgetDefinition,
)
from app.modules.sqla_base import sa_create


def _parse_list_items(raw: Optional[list], item_cls) -> list:
    if not raw:
        return []
    return [item_cls(**item) for item in raw]


def _to_template_response(obj: TemplateModel) -> TemplateResponse:
    return TemplateResponse(
        id=obj.id,
        code=obj.code,
        name=obj.name,
        business_type=obj.business_type,
        preset_code=obj.preset_code,
        version=obj.version,
        description=obj.description,
        status=TemplateStatus(obj.status),
        is_system=obj.is_system,
        modules=_parse_list_items(obj.modules, ModuleDefinition),
        features=_parse_list_items(obj.features, FeatureDefinition),
        menus=_parse_list_items(obj.menus, MenuDefinition),
        dashboard_widgets=_parse_list_items(obj.dashboard_widgets, DashboardWidgetDefinition),
        default_configuration=obj.default_configuration or {},
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_config_record(obj: ConfigRecordModel) -> BusinessConfigurationRecord:
    return BusinessConfigurationRecord(
        id=obj.id,
        business_id=obj.business_id,
        template_id=obj.template_id,
        template_code=obj.template_code,
        template_version=obj.template_version,
        preset_code=obj.preset_code,
        configuration=obj.configuration or {},
        module_overrides=obj.module_overrides or {},
        feature_overrides=obj.feature_overrides or {},
        menu_overrides=obj.menu_overrides or [],
        widget_overrides=obj.widget_overrides or [],
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class SQLAlchemyBusinessTemplateRepository(AbstractBusinessTemplateRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active(self) -> List[TemplateResponse]:
        stmt = select(TemplateModel).where(TemplateModel.status == TemplateStatus.ACTIVE.value)
        res = await self.session.execute(stmt)
        return [_to_template_response(o) for o in res.scalars().all()]

    async def get_by_id(self, template_id: str) -> Optional[TemplateResponse]:
        stmt = select(TemplateModel).where(TemplateModel.id == template_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_template_response(obj) if obj else None

    async def get_by_code_version(self, code: str, version: str) -> Optional[TemplateResponse]:
        stmt = select(TemplateModel).where(
            TemplateModel.code == code.upper(),
            TemplateModel.version == version,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_template_response(obj) if obj else None

    async def get_default_for_business_type(self, business_type: str, preset_code: Optional[str] = None) -> Optional[TemplateResponse]:
        b_type_lower = business_type.lower()
        preset_upper = (preset_code or "STANDARD").upper()

        stmt = select(TemplateModel).where(
            TemplateModel.status == TemplateStatus.ACTIVE.value,
        )
        res = await self.session.execute(stmt)
        all_templates = [_to_template_response(t) for t in res.scalars().all()]

        # Filter by business_type
        matched = [
            t for t in all_templates
            if t.business_type.lower() == b_type_lower
            and t.preset_code.upper() == preset_upper
            and t.status == TemplateStatus.ACTIVE
        ]
        if matched:
            return _latest_version(matched)

        # Fallback: business_type only
        fallback = [
            t for t in all_templates
            if t.business_type.lower() == b_type_lower and t.status == TemplateStatus.ACTIVE
        ]
        if fallback:
            return _latest_version(fallback)

        # Fallback: UMKM
        umkm = [t for t in all_templates if t.code == "UMKM_STANDARD" and t.status == TemplateStatus.ACTIVE]
        if umkm:
            return _latest_version(umkm)

        active = [t for t in all_templates if t.status == TemplateStatus.ACTIVE]
        return _latest_version(active) if active else None

    @classmethod
    def clear(cls):
        pass


def _latest_version(templates: List[TemplateResponse]) -> Optional[TemplateResponse]:
    def semver_key(t: TemplateResponse):
        parts = t.version.split(".")
        try:
            return tuple(int(p) for p in parts)
        except ValueError:
            return (0, 0, 0)
    return max(templates, key=semver_key) if templates else None


class SQLAlchemyBusinessConfigurationRepository(AbstractBusinessConfigurationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        business_id: str,
        template_id: str,
        template_code: str,
        template_version: str,
        preset_code: str,
        configuration: Dict[str, Any],
    ) -> BusinessConfigurationRecord:
        data = {
            "business_id": business_id,
            "template_id": template_id,
            "template_code": template_code,
            "template_version": template_version,
            "preset_code": preset_code,
            "configuration": configuration,
            "module_overrides": {},
            "feature_overrides": {},
            "menu_overrides": [],
            "widget_overrides": [],
        }
        obj = await sa_create(self.session, ConfigRecordModel, data)
        return _to_config_record(obj)

    async def get_by_business(self, business_id: str) -> Optional[BusinessConfigurationRecord]:
        stmt = select(ConfigRecordModel).where(ConfigRecordModel.business_id == business_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_config_record(obj) if obj else None

    async def update(
        self,
        business_id: str,
        configuration: Optional[Dict[str, Any]] = None,
        module_overrides: Optional[Dict[str, bool]] = None,
        feature_overrides: Optional[Dict[str, bool]] = None,
        menu_overrides: Optional[List[Dict[str, Any]]] = None,
        widget_overrides: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[BusinessConfigurationRecord]:
        stmt = select(ConfigRecordModel).where(ConfigRecordModel.business_id == business_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return None
        if configuration is not None:
            existing = obj.configuration or {}
            obj.configuration = {**existing, **configuration}
        if module_overrides is not None:
            existing = obj.module_overrides or {}
            obj.module_overrides = {**existing, **module_overrides}
        if feature_overrides is not None:
            existing = obj.feature_overrides or {}
            obj.feature_overrides = {**existing, **feature_overrides}
        if menu_overrides is not None:
            obj.menu_overrides = menu_overrides
        if widget_overrides is not None:
            obj.widget_overrides = widget_overrides
        await self.session.flush()
        return _to_config_record(obj)

    async def exists(self, business_id: str) -> bool:
        stmt = select(func.count()).select_from(ConfigRecordModel).where(
            ConfigRecordModel.business_id == business_id
        )
        res = await self.session.execute(stmt)
        return (res.scalar_one() or 0) > 0

    @classmethod
    def clear(cls):
        pass
