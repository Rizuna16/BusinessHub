export type TemplateStatus = 'DRAFT' | 'ACTIVE' | 'DEPRECATED';

export type ModuleStatus = 'PLANNED' | 'AVAILABLE';

export interface ModuleDefinition {
  code: string;
  name: string;
  description: string;
  status: ModuleStatus;
}

export interface FeatureDefinition {
  code: string;
  name: string;
  module_code: string;
  description: string;
  enabled_default: boolean;
}

export interface MenuDefinition {
  code: string;
  label: string;
  route: string;
  module_code: string;
  feature_code?: string | null;
  order: number;
  visibility: string[];
}

export interface DashboardWidgetDefinition {
  code: string;
  title: string;
  module_code: string;
  feature_code?: string | null;
  order: number;
  enabled_default: boolean;
}

export interface Template {
  id: string;
  code: string;
  name: string;
  business_type: string;
  preset_code: string;
  version: string;
  description?: string;
  status: TemplateStatus;
  is_system: boolean;
  modules: ModuleDefinition[];
  features: FeatureDefinition[];
  menus: MenuDefinition[];
  dashboard_widgets: DashboardWidgetDefinition[];
  default_configuration: Record<string, any>;
  created_at: string;
  updated_at: string;
}
