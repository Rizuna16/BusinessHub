export interface BusinessConfiguration {
  id: string;
  business_id: string;
  template_id: string;
  template_code: string;
  template_version: string;
  preset_code: string;
  configuration: Record<string, any>;
  module_overrides: Record<string, boolean>;
  feature_overrides: Record<string, boolean>;
  menu_overrides: Record<string, any>[];
  widget_overrides: Record<string, any>[];
  effective_configuration: Record<string, any>;
  effective_modules: Record<string, any>[];
  effective_features: Record<string, any>[];
  effective_menus: Record<string, any>[];
  effective_widgets: Record<string, any>[];
  created_at: string;
  updated_at: string;
}

export interface BusinessConfigurationUpdate {
  configuration?: Record<string, any>;
  module_overrides?: Record<string, boolean>;
  feature_overrides?: Record<string, boolean>;
  menu_overrides?: Record<string, any>[];
  widget_overrides?: Record<string, any>[];
}
