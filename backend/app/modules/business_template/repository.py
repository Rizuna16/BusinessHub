from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field

from app.modules.business_template.schemas import (
    TemplateBase,
    TemplateResponse,
    TemplateStatus,
    ModuleStatus,
    ModuleDefinition,
    FeatureDefinition,
    MenuDefinition,
    DashboardWidgetDefinition,
)


class AbstractBusinessTemplateRepository(ABC):
    @abstractmethod
    async def list_active(self) -> List[TemplateResponse]:
        pass

    @abstractmethod
    async def get_by_id(self, template_id: str) -> Optional[TemplateResponse]:
        pass

    @abstractmethod
    async def get_by_code_version(self, code: str, version: str) -> Optional[TemplateResponse]:
        pass

    @abstractmethod
    async def get_default_for_business_type(self, business_type: str, preset_code: Optional[str] = None) -> Optional[TemplateResponse]:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class AbstractBusinessConfigurationRepository(ABC):
    @abstractmethod
    async def create(
        self,
        business_id: str,
        template_id: str,
        template_code: str,
        template_version: str,
        preset_code: str,
        configuration: Dict[str, Any],
    ) -> Any:
        pass

    @abstractmethod
    async def get_by_business(self, business_id: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def update(
        self,
        business_id: str,
        configuration: Optional[Dict[str, Any]] = None,
        module_overrides: Optional[Dict[str, bool]] = None,
        feature_overrides: Optional[Dict[str, bool]] = None,
        menu_overrides: Optional[List[Dict[str, Any]]] = None,
        widget_overrides: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Any]:
        pass

    @abstractmethod
    async def exists(self, business_id: str) -> bool:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


# Seed Data for System Templates
DEFAULT_MODULES = [
    ModuleDefinition(code="CORE", name="Core", description="Core business management", status=ModuleStatus.AVAILABLE),
    ModuleDefinition(code="ACCOUNT", name="Account", description="User account management", status=ModuleStatus.AVAILABLE),
    ModuleDefinition(code="BUSINESS", name="Business", description="Tenant core management", status=ModuleStatus.AVAILABLE),
    ModuleDefinition(code="MEMBERSHIP", name="Membership", description="Team members & roles", status=ModuleStatus.AVAILABLE),
    ModuleDefinition(code="BRANCH", name="Branch", description="Operational branches", status=ModuleStatus.AVAILABLE),
    ModuleDefinition(code="PRODUCT", name="Product", description="Product catalog", status=ModuleStatus.PLANNED),
    ModuleDefinition(code="CATEGORY", name="Category", description="Category management", status=ModuleStatus.PLANNED),
    ModuleDefinition(code="UNIT", name="Unit", description="Measurement units", status=ModuleStatus.PLANNED),
    ModuleDefinition(code="CUSTOMER", name="Customer", description="Customer management", status=ModuleStatus.PLANNED),
    ModuleDefinition(code="SUPPLIER", name="Supplier", description="Supplier management", status=ModuleStatus.PLANNED),
    ModuleDefinition(code="SALES", name="Sales", description="Sales transactions", status=ModuleStatus.PLANNED),
    ModuleDefinition(code="PURCHASE", name="Purchase", description="Purchase orders", status=ModuleStatus.PLANNED),
    ModuleDefinition(code="INVENTORY", name="Inventory", description="Stock control", status=ModuleStatus.PLANNED),
    ModuleDefinition(code="CASH", name="Cash", description="Cash flow management", status=ModuleStatus.PLANNED),
    ModuleDefinition(code="EXPENSE", name="Expense", description="Expense tracking", status=ModuleStatus.PLANNED),
    ModuleDefinition(code="REPORTS", name="Reports", description="Business reporting", status=ModuleStatus.PLANNED),
    ModuleDefinition(code="HOTEL", name="Hotel Operations", description="Hotel rooms & reservations", status=ModuleStatus.PLANNED),
    ModuleDefinition(code="RETAIL", name="Retail Operations", description="Retail POS & barcode", status=ModuleStatus.PLANNED),
]


class InMemoryBusinessTemplateRepository(AbstractBusinessTemplateRepository):
    _templates: Dict[str, TemplateResponse] = {}

    @classmethod
    def _seed_defaults(cls):
        if cls._templates:
            return
        now = datetime.now(timezone.utc)

        # HOTEL_STANDARD v1.0.0
        hotel_template = TemplateResponse(
            id="tmpl-hotel-std-100",
            code="HOTEL_STANDARD",
            name="Hotel Standard",
            business_type="hotel",
            preset_code="STANDARD",
            version="1.0.0",
            description="Standard template for hotels with room management and reservation baseline.",
            status=TemplateStatus.ACTIVE,
            is_system=True,
            modules=DEFAULT_MODULES,
            features=[
                FeatureDefinition(code="branch.multi_branch", name="Multi-Branch", module_code="BRANCH", description="Support multiple branches", enabled_default=True),
                FeatureDefinition(code="branch.default_branch", name="Default Branch", module_code="BRANCH", description="Default branch assignment", enabled_default=True),
                FeatureDefinition(code="hotel.room_management", name="Room Management", module_code="HOTEL", description="Hotel rooms configuration", enabled_default=True),
                FeatureDefinition(code="hotel.reservation", name="Reservation", module_code="HOTEL", description="Hotel room reservation", enabled_default=True),
            ],
            menus=[
                MenuDefinition(code="menu.dashboard", label="Dashboard", route="/dashboard", module_code="CORE", order=1),
                MenuDefinition(code="menu.businesses", label="Bisnis", route="/businesses", module_code="BUSINESS", order=2),
                MenuDefinition(code="menu.branches", label="Cabang", route="/branches", module_code="BRANCH", order=3),
                MenuDefinition(code="menu.configuration", label="Konfigurasi", route="/configuration", module_code="CORE", order=4),
            ],
            dashboard_widgets=[
                DashboardWidgetDefinition(code="widget.summary", title="Ringkasan Bisnis", module_code="CORE", order=1),
                DashboardWidgetDefinition(code="widget.branches", title="Cabang Aktif", module_code="BRANCH", order=2),
            ],
            default_configuration={
                "currency": "IDR",
                "date_format": "DD/MM/YYYY",
                "number_format": "id-ID",
                "timezone": "Asia/Jakarta",
                "check_in_time": "14:00",
                "check_out_time": "12:00",
            },
            created_at=now,
            updated_at=now,
        )

        # RETAIL_STANDARD v1.0.0
        retail_template = TemplateResponse(
            id="tmpl-retail-std-100",
            code="RETAIL_STANDARD",
            name="Retail Standard",
            business_type="retail",
            preset_code="STANDARD",
            version="1.0.0",
            description="Standard template for retail businesses with product & sales baseline.",
            status=TemplateStatus.ACTIVE,
            is_system=True,
            modules=DEFAULT_MODULES,
            features=[
                FeatureDefinition(code="branch.multi_branch", name="Multi-Branch", module_code="BRANCH", description="Support multiple branches", enabled_default=True),
                FeatureDefinition(code="branch.default_branch", name="Default Branch", module_code="BRANCH", description="Default branch assignment", enabled_default=True),
                FeatureDefinition(code="retail.barcode", name="Barcode", module_code="RETAIL", description="Barcode scanner support", enabled_default=True),
                FeatureDefinition(code="product.variant", name="Product Variant", module_code="PRODUCT", description="Product variations", enabled_default=True),
            ],
            menus=[
                MenuDefinition(code="menu.dashboard", label="Dashboard", route="/dashboard", module_code="CORE", order=1),
                MenuDefinition(code="menu.businesses", label="Bisnis", route="/businesses", module_code="BUSINESS", order=2),
                MenuDefinition(code="menu.branches", label="Cabang", route="/branches", module_code="BRANCH", order=3),
                MenuDefinition(code="menu.configuration", label="Konfigurasi", route="/configuration", module_code="CORE", order=4),
            ],
            dashboard_widgets=[
                DashboardWidgetDefinition(code="widget.summary", title="Ringkasan Bisnis", module_code="CORE", order=1),
                DashboardWidgetDefinition(code="widget.branches", title="Cabang Aktif", module_code="BRANCH", order=2),
            ],
            default_configuration={
                "currency": "IDR",
                "date_format": "DD/MM/YYYY",
                "number_format": "id-ID",
                "timezone": "Asia/Jakarta",
                "receipt_footer": "Terima kasih atas kunjungan Anda",
            },
            created_at=now,
            updated_at=now,
        )

        # UMKM_STANDARD v1.0.0
        umkm_template = TemplateResponse(
            id="tmpl-umkm-std-100",
            code="UMKM_STANDARD",
            name="UMKM Standard",
            business_type="umkm",
            preset_code="STANDARD",
            version="1.0.0",
            description="Simple standard template for MSMEs (UMKM).",
            status=TemplateStatus.ACTIVE,
            is_system=True,
            modules=DEFAULT_MODULES,
            features=[
                FeatureDefinition(code="branch.multi_branch", name="Multi-Branch", module_code="BRANCH", description="Support multiple branches", enabled_default=True),
                FeatureDefinition(code="branch.default_branch", name="Default Branch", module_code="BRANCH", description="Default branch assignment", enabled_default=True),
            ],
            menus=[
                MenuDefinition(code="menu.dashboard", label="Dashboard", route="/dashboard", module_code="CORE", order=1),
                MenuDefinition(code="menu.businesses", label="Bisnis", route="/businesses", module_code="BUSINESS", order=2),
                MenuDefinition(code="menu.branches", label="Cabang", route="/branches", module_code="BRANCH", order=3),
                MenuDefinition(code="menu.configuration", label="Konfigurasi", route="/configuration", module_code="CORE", order=4),
            ],
            dashboard_widgets=[
                DashboardWidgetDefinition(code="widget.summary", title="Ringkasan Bisnis", module_code="CORE", order=1),
                DashboardWidgetDefinition(code="widget.branches", title="Cabang Aktif", module_code="BRANCH", order=2),
            ],
            default_configuration={
                "currency": "IDR",
                "date_format": "DD/MM/YYYY",
                "number_format": "id-ID",
                "timezone": "Asia/Jakarta",
            },
            created_at=now,
            updated_at=now,
        )

        cls._templates[hotel_template.id] = hotel_template
        cls._templates[retail_template.id] = retail_template
        cls._templates[umkm_template.id] = umkm_template

    async def list_active(self) -> List[TemplateResponse]:
        self._seed_defaults()
        return [t for t in self._templates.values() if t.status == TemplateStatus.ACTIVE]

    async def get_by_id(self, template_id: str) -> Optional[TemplateResponse]:
        self._seed_defaults()
        return self._templates.get(template_id)

    async def get_by_code_version(self, code: str, version: str) -> Optional[TemplateResponse]:
        self._seed_defaults()
        for t in self._templates.values():
            if t.code.upper() == code.upper() and t.version == version:
                return t
        return None

    async def get_default_for_business_type(self, business_type: str, preset_code: Optional[str] = None) -> Optional[TemplateResponse]:
        self._seed_defaults()
        b_type_lower = business_type.lower()
        preset_upper = (preset_code or "STANDARD").upper()

        # Collect all matching templates (same business_type + preset_code), ACTIVE status
        matched = []
        for t in self._templates.values():
            if (
                t.business_type.lower() == b_type_lower
                and t.preset_code.upper() == preset_upper
                and t.status == TemplateStatus.ACTIVE
            ):
                matched.append(t)

        # Try matching business_type + preset_code first -> latest version
        if matched:
            return _latest_version(matched)

        # Fallback to any active template matching business_type (any preset)
        fallback = [
            t for t in self._templates.values()
            if t.business_type.lower() == b_type_lower and t.status == TemplateStatus.ACTIVE
        ]
        if fallback:
            return _latest_version(fallback)

        # Fallback to UMKM or CORE baseline
        umkm = [
            t for t in self._templates.values()
            if t.code == "UMKM_STANDARD" and t.status == TemplateStatus.ACTIVE
        ]
        if umkm:
            return _latest_version(umkm)

        if self._templates:
            active = [t for t in self._templates.values() if t.status == TemplateStatus.ACTIVE]
            return _latest_version(active) if active else None

        return None

    @classmethod
    def clear(cls):
        cls._templates.clear()


def _latest_version(templates: List[TemplateResponse]) -> Optional[TemplateResponse]:
    """Return the template with the highest semantic version."""
    def semver_key(t: TemplateResponse):
        parts = t.version.split(".")
        try:
            return tuple(int(p) for p in parts)
        except ValueError:
            return (0, 0, 0)

    return max(templates, key=semver_key) if templates else None


class BusinessConfigurationRecord(BaseModel):
    id: str
    business_id: str
    template_id: str
    template_code: str
    template_version: str
    preset_code: str
    configuration: Dict[str, Any] = Field(default_factory=dict)
    module_overrides: Dict[str, bool] = Field(default_factory=dict)
    feature_overrides: Dict[str, bool] = Field(default_factory=dict)
    menu_overrides: List[Dict[str, Any]] = Field(default_factory=list)
    widget_overrides: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class InMemoryBusinessConfigurationRepository(AbstractBusinessConfigurationRepository):
    _configurations: Dict[str, BusinessConfigurationRecord] = {}  # keyed by business_id

    async def create(
        self,
        business_id: str,
        template_id: str,
        template_code: str,
        template_version: str,
        preset_code: str,
        configuration: Dict[str, Any],
    ) -> BusinessConfigurationRecord:
        config_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        record = BusinessConfigurationRecord(
            id=config_id,
            business_id=business_id,
            template_id=template_id,
            template_code=template_code,
            template_version=template_version,
            preset_code=preset_code,
            configuration=configuration,
            module_overrides={},
            feature_overrides={},
            menu_overrides=[],
            widget_overrides=[],
            created_at=now,
            updated_at=now,
        )
        self._configurations[business_id] = record
        return record

    async def get_by_business(self, business_id: str) -> Optional[BusinessConfigurationRecord]:
        return self._configurations.get(business_id)

    async def update(
        self,
        business_id: str,
        configuration: Optional[Dict[str, Any]] = None,
        module_overrides: Optional[Dict[str, bool]] = None,
        feature_overrides: Optional[Dict[str, bool]] = None,
        menu_overrides: Optional[List[Dict[str, Any]]] = None,
        widget_overrides: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[BusinessConfigurationRecord]:
        record = self._configurations.get(business_id)
        if not record:
            return None

        current = record.model_dump()
        if configuration is not None:
            # Merge configuration overrides
            current["configuration"] = {**current["configuration"], **configuration}
        if module_overrides is not None:
            current["module_overrides"] = {**current["module_overrides"], **module_overrides}
        if feature_overrides is not None:
            current["feature_overrides"] = {**current["feature_overrides"], **feature_overrides}
        if menu_overrides is not None:
            current["menu_overrides"] = menu_overrides
        if widget_overrides is not None:
            current["widget_overrides"] = widget_overrides

        current["updated_at"] = datetime.now(timezone.utc)
        updated = BusinessConfigurationRecord(**current)
        self._configurations[business_id] = updated
        return updated

    async def exists(self, business_id: str) -> bool:
        return business_id in self._configurations

    @classmethod
    def clear(cls):
        cls._configurations.clear()


template_repository = InMemoryBusinessTemplateRepository()
business_configuration_repository = InMemoryBusinessConfigurationRepository()
