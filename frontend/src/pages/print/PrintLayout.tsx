import React from 'react';
import { PrintButton } from '@/components/export/PrintButton';

interface PrintLayoutProps {
  title: string;
  subtitle?: string;
  businessName?: string;
  branchName?: string;
  generatedAt?: string;
  filterInfo?: string;
  children: React.ReactNode;
}

export const PrintLayout: React.FC<PrintLayoutProps> = ({
  title,
  subtitle,
  businessName,
  branchName,
  generatedAt,
  filterInfo,
  children,
}) => {
  return (
    <>
      <style>{`
        @media print {
          body * { visibility: hidden; }
          .print-area, .print-area * { visibility: visible; }
          .print-area { position: absolute; left: 0; top: 0; width: 100%; padding: 20px; }
          .no-print { display: none !important; }
          @page { margin: 15mm; size: A4; }
        }
        @media screen {
          .print-area { max-width: 800px; margin: 0 auto; padding: 40px; background: white; min-height: 100vh; }
        }
      `}</style>

      <div className="no-print fixed top-4 right-4 z-50">
        <PrintButton />
      </div>

      <div className="print-area">
        <div className="text-center mb-6 border-b border-slate-300 pb-4">
          {businessName && (
            <h1 className="text-xl font-bold text-slate-900">{businessName}</h1>
          )}
          {branchName && (
            <p className="text-sm text-slate-600">{branchName}</p>
          )}
          <h2 className="text-lg font-semibold text-slate-800 mt-3">{title}</h2>
          {subtitle && <p className="text-sm text-slate-600 mt-1">{subtitle}</p>}
          {filterInfo && (
            <p className="text-xs text-slate-500 mt-2 italic">{filterInfo}</p>
          )}
        </div>

        <div className="mb-4">
          {children}
        </div>

        <div className="text-center text-xs text-slate-400 mt-6 pt-4 border-t border-slate-200">
          <p>Generated at: {generatedAt || new Date().toLocaleString()}</p>
          <p className="mt-1">BusinessHub — Data Export</p>
        </div>
      </div>
    </>
  );
};
