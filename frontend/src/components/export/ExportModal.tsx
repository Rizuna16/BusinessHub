import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { exportApiClient, type ExportFormat, type ExportTableParams, type ExportReportParams } from '@/services/exportApiClient';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  businessId: string;
  resourceKey: string;
  type?: 'table' | 'report';
  filters?: Record<string, string | undefined>;
  title?: string;
}

export const ExportModal: React.FC<ExportModalProps> = ({
  isOpen,
  onClose,
  businessId,
  resourceKey,
  type = 'table',
  filters = {},
  title = 'Export Data',
}) => {
  const [format, setFormat] = useState<ExportFormat>('csv');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleExport = async () => {
    setIsLoading(true);
    setError(null);
    setSuccess(false);
    try {
      if (type === 'report') {
        const params: ExportReportParams = { format, ...filters };
        await exportApiClient.exportReport(businessId, resourceKey, params);
      } else {
        const params: ExportTableParams = { format, export_mode: 'all_matching', ...filters };
        await exportApiClient.exportTable(businessId, resourceKey, params);
      }
      setSuccess(true);
      setTimeout(() => {
        onClose();
        setSuccess(false);
      }, 1500);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Export failed';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 dark:bg-black/70 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
            <button
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              onClick={onClose}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div className="px-6 py-5">
          <div className="mb-4">
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              Export Format
            </label>
            <div className="flex gap-3">
              <button
                className={`flex-1 px-4 py-3 rounded-lg border-2 transition-colors ${
                  format === 'csv'
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300'
                    : 'border-slate-200 dark:border-slate-600 hover:border-slate-300 dark:hover:border-slate-500 text-slate-700 dark:text-slate-300'
                }`}
                onClick={() => setFormat('csv')}
              >
                <div className="font-medium">CSV</div>
                <div className="text-xs mt-0.5 opacity-70">Comma-separated values</div>
              </button>
              <button
                className={`flex-1 px-4 py-3 rounded-lg border-2 transition-colors ${
                  format === 'xlsx'
                    ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300'
                    : 'border-slate-200 dark:border-slate-600 hover:border-slate-300 dark:hover:border-slate-500 text-slate-700 dark:text-slate-300'
                }`}
                onClick={() => setFormat('xlsx')}
              >
                <div className="font-medium">Excel</div>
                <div className="text-xs mt-0.5 opacity-70">.xlsx spreadsheet</div>
              </button>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-rose-50 dark:bg-rose-900/30 border border-rose-200 dark:border-rose-700 text-rose-700 dark:text-rose-300 text-sm rounded-lg">
              {error}
            </div>
          )}

          {success && (
            <div className="mb-4 p-3 bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-700 text-emerald-700 dark:text-emerald-300 text-sm rounded-lg">
              Export downloaded successfully!
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-3">
          <Button variant="outline" size="sm" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            isLoading={isLoading}
            disabled={isLoading || success}
            onClick={handleExport}
          >
            {success ? 'Downloaded' : 'Download'}
          </Button>
        </div>
      </div>
    </div>
  );
};
