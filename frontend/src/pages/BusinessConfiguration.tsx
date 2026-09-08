import { useState, useCallback, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { BusinessConfiguration } from '@/types/businessConfiguration';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { useTheme } from '@/hooks/useTheme';

const MODULE_STATUS_LABEL: Record<string, string> = {
  AVAILABLE: 'Available',
  PLANNED: 'Planned',
};

export const BusinessConfigurationPage: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();
  const { isDark } = useTheme();
  const [config, setConfig] = useState<BusinessConfiguration | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveMessage, setSaveMessage] = useState<string>('');
  const [isEdited, setIsEdited] = useState<boolean>(false);

  const [editedConfig, setEditedConfig] = useState<Record<string, string>>({});
  const [showConfirm, setShowConfirm] = useState<boolean>(false);

  // OWNER/ADMIN can edit (enforced on backend); frontend shows edit UI.
  // Membership role is enforced at the backend via BusinessConfigurationService.
  const canEdit = true;

  const fetchConfig = useCallback(async () => {
    if (!businessId) return;
    try {
      setIsLoading(true);
      setServerError('');
      const data = await apiClient.getBusinessConfiguration(businessId);
      setConfig(data);
      setEditedConfig({});
    } catch (err: any) {
      const msg = err?.message || 'Failed to load configuration.';
      if (msg.toLowerCase().includes('unauthorized') || err?.message?.includes('401')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [businessId, navigate]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const handleConfigChange = (key: string, value: string) => {
    setEditedConfig((prev) => ({ ...prev, [key]: value }));
    setIsEdited(true);
    setSaveMessage('');
  };

  const handleSave = async (overridePayload?: Record<string, any>) => {
    if (!config || !businessId) return;
    try {
      setIsSaving(true);
      setServerError('');

      const payload: Record<string, any> = overridePayload || {};

      // If saving config overrides
      if (!overridePayload) {
        const configuration: Record<string, any> = {};
        Object.entries(editedConfig).forEach(([key, value]) => {
          configuration[key] = value;
        });
        payload.configuration = configuration;
      }

      const data = await apiClient.updateBusinessConfiguration(businessId, payload);
      setConfig(data);
      setEditedConfig({});
      setIsEdited(false);
      setSaveMessage('Configuration updated successfully.');
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (err: any) {
      setServerError(err?.message || 'Failed to save configuration.');
    } finally {
      setIsSaving(false);
      setShowConfirm(false);
    }
  };

  const effectiveConfig = config?.effective_configuration || {};
  const templateConfig = config?.configuration || {};
  const moduleOverrides = config?.module_overrides || {};
  const featureOverrides = config?.feature_overrides || {};

  return (
    <div className={`min-h-screen transition-colors duration-200 ${isDark ? 'bg-slate-900 text-slate-100' : 'bg-slate-50 text-slate-900'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Loading state */}
        {isLoading && (
          <div className="flex h-64 w-full items-center justify-center">
            <Loading size="lg" text="Loading configuration..." />
          </div>
        )}

        {/* Error state */}
        {!isLoading && serverError && (
          <ErrorState
            title="Configuration Error"
            message={serverError}
            onRetry={fetchConfig}
          />
        )}

        {/* Empty state */}
        {!isLoading && !serverError && !config && (
          <div className="text-center py-12">
            <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 ${
              isDark ? 'bg-slate-800 text-slate-500' : 'bg-slate-100 text-slate-400'
            }`}>
              <span className="text-3xl">⚙️</span>
            </div>
            <h3 className="text-lg font-medium mb-2">No configuration found</h3>
            <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
              Configuration is being initialized. Please check back in a moment.
            </p>
          </div>
        )}

        {/* Success state */}
        {!isLoading && !serverError && config && (
          <>
            {/* Header */}
            <div className="mb-6">
              <h1 className={`text-2xl font-bold ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>
                Business Configuration
              </h1>
              <p className={`text-sm mt-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                {config.template_code}
              </p>
            </div>

            {/* Save message */}
            {saveMessage && (
              <div className={`mb-4 p-3 rounded-lg text-sm ${
                isDark ? 'bg-emerald-900/30 text-emerald-300 border border-emerald-800' : 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              }`}>
                {saveMessage}
              </div>
            )}

            {/* Template Section */}
            <Card
              title="Template"
              description="System template used as the configuration baseline for this business."
              className="mb-6"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                    Template Code
                  </label>
                  <p className={`text-lg font-semibold ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>
                    {config.template_code}
                  </p>
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                    Template Version
                  </label>
                  <p className={`text-lg font-semibold ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>
                    {config.template_version}
                  </p>
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                    Preset
                  </label>
                  <p className={`text-lg font-semibold ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>
                    {config.preset_code}
                  </p>
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                    Status
                  </label>
                  <Badge variant="info">System</Badge>
                </div>
              </div>
            </Card>

            {/* Regional Configuration Section */}
            <Card
              title="Regional Settings"
              description="Configuration values for currency, date format, timezone, and locale."
              className="mb-6"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(effectiveConfig).map(([key, value]) => (
                  <div key={key}>
                    <label className={`block text-sm font-medium mb-1 capitalize ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                      {key.replace(/_/g, ' ')}
                    </label>
                    {canEdit ? (
                      <Input
                        value={editedConfig[key]?.toString() ?? value?.toString() ?? ''}
                        onChange={(e) => handleConfigChange(key, e.target.value)}
                        className="w-full"
                        aria-label={key.replace(/_/g, ' ')}
                      />
                    ) : (
                      <p className={`text-sm ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                        {String(value ?? '-')}
                      </p>
                    )}
                    {canEdit && editedConfig[key] && editedConfig[key] !== value?.toString() && (
                      <span className="text-xs text-amber-500" aria-label="modified">● Modified</span>
                    )}
                  </div>
                ))}
              </div>

              {canEdit && isEdited && (
                <div className="mt-4 pt-4 border-t">
                  <Button
                    variant="primary"
                    size="sm"
                    isLoading={isSaving}
                    onClick={() => setShowConfirm(true)}
                  >
                    Save Changes
                  </Button>
                </div>
              )}
            </Card>

            {/* Modules Section */}
            <Card
              title="Active Modules"
              description="Module definitions included in this business template."
              className="mb-6"
            >
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className={isDark ? 'border-slate-700' : 'border-slate-200'}>
                      <th className={`text-left py-2 px-3 border-b ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>Code</th>
                      <th className={`text-left py-2 px-3 border-b ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>Name</th>
                      <th className={`text-left py-2 px-3 border-b ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>Description</th>
                      <th className={`text-center py-2 px-3 border-b ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {config.effective_modules.map((mod) => {
                      return (
                        <tr key={mod.code} className={isDark ? 'border-slate-700' : 'border-slate-200'}>
                          <td className={`py-2 px-3 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>{mod.code}</td>
                          <td className={`py-2 px-3 ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>{mod.name}</td>
                          <td className={`py-2 px-3 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{mod.description}</td>
                          <td className="py-2 px-3 text-center">
                            {mod.status === 'AVAILABLE' ? (
                              <Badge variant="success">{MODULE_STATUS_LABEL['AVAILABLE']}</Badge>
                            ) : (
                              <Badge variant="neutral">{MODULE_STATUS_LABEL['PLANNED']}</Badge>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>

            {/* Features Section */}
            <Card
              title="Available Features"
              description="Feature definitions from the template. Note: enabling a feature in configuration does not implement the underlying module."
              className="mb-6"
            >
              <div className="space-y-3">
                {config.effective_features.map((feature) => {
                  const overridden = feature.code in featureOverrides;
                  const effectiveEnabled = feature.enabled ?? feature.enabled_default;
                  return (
                    <div
                      key={feature.code}
                      className={`flex items-center justify-between p-3 rounded-lg border ${
                        isDark ? 'border-slate-700 bg-slate-800/30' : 'border-slate-200 bg-slate-50'
                      }`}
                    >
                      <div className="flex-1">
                        <label className={`block text-sm font-medium ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
                          {feature.code}
                        </label>
                        <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                          {feature.description}
                        </p>
                      </div>
                      <div className="ml-4 min-w-[120px] text-right">
                        {overridden ? (
                          <Badge variant={effectiveEnabled ? 'success' : 'warning'}>
                            {effectiveEnabled ? 'Enabled (Override)' : 'Disabled (Override)'}
                          </Badge>
                        ) : (
                          <Badge variant="neutral">
                            {effectiveEnabled ? 'Default Enabled' : 'Default Disabled'}
                          </Badge>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>

            {/* Business Defaults Section */}
            <Card
              title="Business Defaults"
              description="Configuration values applied to this business. These override template defaults."
              className="mb-6"
            >
              {Object.keys(templateConfig).length === 0 && Object.keys(moduleOverrides).length === 0 && Object.keys(featureOverrides).length === 0 ? (
                <div className="text-center py-6">
                  <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                    No custom business overrides have been set.
                  </p>
                  {canEdit && (
                    <p className={`text-xs mt-1 ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
                      Modify Regional Settings above to create overrides.
                    </p>
                  )}
                </div>
              ) : (
                <div className="space-y-4">
                  {Object.keys(templateConfig).length > 0 && (
                    <div>
                      <h4 className={`text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>Configuration Overrides</h4>
                      <table className="w-full text-sm">
                        <thead>
                          <tr className={isDark ? 'border-slate-700' : 'border-slate-200'}>
                            <th className={`text-left py-1 px-2 border-b ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Key</th>
                            <th className={`text-left py-1 px-2 border-b ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Value</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(templateConfig).map(([key, value]) => (
                            <tr key={key} className={isDark ? 'border-slate-700' : 'border-slate-200'}>
                              <td className={`py-1 px-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>{key}</td>
                              <td className={`py-1 px-2 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>{String(value ?? '-')}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {Object.keys(featureOverrides).length > 0 && (
                    <div>
                      <h4 className={`text-sm font-medium mb-2 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>Feature Overrides</h4>
                      <div className="space-y-1">
                        {Object.entries(featureOverrides).map(([key, value]) => (
                          <div key={key} className="flex justify-between">
                            <span className={`text-sm ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>{key}</span>
                            <Badge variant={value ? 'success' : 'warning'}>
                              {value ? 'Enabled' : 'Disabled'}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </Card>

            {/* Confirmation Modal */}
            {showConfirm && (
              <div
                className="fixed inset-0 flex items-center justify-center z-50 bg-black/50"
                role="dialog"
                aria-modal="true"
                aria-labelledby="confirm-title"
              >
                <div className={`rounded-xl shadow-xl max-w-md w-full mx-4 p-6 ${
                  isDark ? 'bg-slate-800 border border-slate-700' : 'bg-white'
                }`}>
                  <h2 id="confirm-title" className={`text-lg font-bold mb-3 ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>
                    Confirm Configuration Update
                  </h2>
                  <p className={`text-sm mb-4 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
                    This will apply your configuration changes to this business. These changes will not affect other businesses or the global template.
                  </p>
                  <div className="flex justify-end gap-3">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setShowConfirm(false)}
                      aria-label="Cancel"
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      isLoading={isSaving}
                      onClick={() => handleSave()}
                      aria-label="Confirm save"
                    >
                      Save
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default BusinessConfigurationPage;
