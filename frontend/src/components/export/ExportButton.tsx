import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { exportApiClient, type ExportFormat, type ExportTableParams, type ExportReportParams } from '@/services/exportApiClient';

interface ExportButtonProps {
  businessId: string;
  resourceKey: string;
  type?: 'table' | 'report';
  filters?: Record<string, string | undefined>;
  disabled?: boolean;
  className?: string;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const ExportButton: React.FC<ExportButtonProps> = ({
  businessId,
  resourceKey,
  type = 'table',
  filters = {},
  disabled = false,
  className = '',
  label = 'Export',
  size = 'sm',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleExport = async (format: ExportFormat) => {
    setIsOpen(false);
    setIsLoading(true);
    setError(null);
    try {
      if (type === 'report') {
        const reportParams: ExportReportParams = { format, ...filters };
        await exportApiClient.exportReport(businessId, resourceKey, reportParams);
      } else {
        const tableParams: ExportTableParams = { format, export_mode: 'all_matching', ...filters };
        await exportApiClient.exportTable(businessId, resourceKey, tableParams);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Export failed';
      setError(message);
      setTimeout(() => setError(null), 5000);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={`relative inline-block ${className}`} ref={dropdownRef}>
      <Button
        variant="outline"
        size={size}
        isLoading={isLoading}
        disabled={disabled || isLoading}
        onClick={() => setIsOpen(!isOpen)}
      >
        <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        {label}
      </Button>

      {isOpen && (
        <div className="absolute right-0 mt-1 w-44 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg z-50">
          <button
            className="w-full text-left px-4 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-t-lg flex items-center gap-2"
            onClick={() => handleExport('csv')}
          >
            <span className="font-mono text-xs bg-slate-100 dark:bg-slate-600 px-1.5 py-0.5 rounded">CSV</span>
            Export as CSV
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-b-lg flex items-center gap-2"
            onClick={() => handleExport('xlsx')}
          >
            <span className="font-mono text-xs bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300 px-1.5 py-0.5 rounded">XLSX</span>
            Export as Excel
          </button>
        </div>
      )}

      {error && (
        <div className="absolute top-full mt-1 right-0 bg-rose-50 dark:bg-rose-900/30 border border-rose-200 dark:border-rose-700 text-rose-700 dark:text-rose-300 text-xs px-3 py-2 rounded-lg shadow-lg z-50 whitespace-nowrap">
          {error}
        </div>
      )}
    </div>
  );
};
