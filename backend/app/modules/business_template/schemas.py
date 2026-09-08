from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class TemplateStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"


class ModuleStatus(str, Enum):
    PLANNED = "PLANNED"
    AVAILABLE = "AVAILABLE"


class ModuleDefinition(BaseModel):
    code: str
    name: str
    description: str
    status: ModuleStatus


class FeatureDefinition(BaseModel):
    code: str
    name: str
    module_code: str
    description: str
    enabled_default: bool = False


class MenuDefinition(BaseModel):
    code: str
    label: str
    route: str
    module_code: str
    feature_code: Optional[str] = None
    order: int = 0
    visibility: List[str] = ["OWNER", "ADMIN", "MEMBER"]


class DashboardWidgetDefinition(BaseModel):
    code: str
    title: str
    module_code: str
    feature_code: Optional[str] = None
    order: int = 0
    enabled_default: bool = True


class TemplateBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    business_type: str = Field(..., min_length=2, max_length=50)
    preset_code: str = Field(..., min_length=2, max_length=50)
    version: str = Field(..., min_length=5, max_length=20)  # e.g., "1.0.0"
    description: Optional[str] = Field(None, max_length=500)
    status: TemplateStatus = TemplateStatus.ACTIVE
    is_system: bool = True
    modules: List[ModuleDefinition] = Field(default_factory=list)
    features: List[FeatureDefinition] = Field(default_factory=list)
    menus: List[MenuDefinition] = Field(default_factory=list)
    dashboard_widgets: List[DashboardWidgetDefinition] = Field(default_factory=list)
    default_configuration: Dict[str, Any] = Field(default_factory=dict)


class TemplateResponse(TemplateBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TemplateListResponse(BaseModel):
    items: List[TemplateResponse]
    total: int


class BusinessConfigurationUpdate(BaseModel):
    configuration: Optional[Dict[str, Any]] = None
    module_overrides: Optional[Dict[str, bool]] = None
    feature_overrides: Optional[Dict[str, bool]] = None
    menu_overrides: Optional[List[Dict[str, Any]]] = None
    widget_overrides: Optional[List[Dict[str, Any]]] = None


class BusinessConfigurationResponse(BaseModel):
    id: str
    business_id: str
    template_id: str
    template_code: str
    template_version: str
    preset_code: str
    configuration: Dict[str, Any]
    module_overrides: Dict[str, bool]
    feature_overrides: Dict[str, bool]
    menu_overrides: List[Dict[str, Any]]
    widget_overrides: List[Dict[str, Any]]
    effective_configuration: Dict[str, Any]
    effective_modules: List[Dict[str, Any]]
    effective_features: List[Dict[str, Any]]
    effective_menus: List[Dict[str, Any]]
    effective_widgets: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
