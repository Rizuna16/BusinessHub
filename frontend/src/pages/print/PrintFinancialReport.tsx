import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { PrintLayout } from './PrintLayout';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

function authFetch(url: string) {
  return fetch(url, { headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` } })
    .then(r => r.ok ? r.json() : Promise.reject(new Error(`Failed: ${r.status}`)))
    .then(j => j.data ?? j);
}

const REPORT_TITLES: Record<string, string> = {
  'profit-loss': 'Profit & Loss',
  'balance-sheet': 'Balance Sheet',
  'trial-balance': 'Trial Balance',
  'cash-flow': 'Cash Flow Statement',
};

export const PrintFinancialReport: React.FC = () => {
  const { businessId, reportType } = useParams<{ businessId: string; reportType: string }>();
  const [searchParams] = useSearchParams();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const periodId = searchParams.get('period_id') || undefined;

  useEffect(() => {
    if (businessId && reportType) {
      const params = new URLSearchParams();
      if (periodId) params.set('period_id', periodId);
      const qs = params.toString() ? `?${params}` : '';
      let path = '';
      if (reportType === 'profit-loss') path = `/accounting/reports/profit-and-loss`;
      else if (reportType === 'balance-sheet') path = `/accounting/reports/balance-sheet`;
      else if (reportType === 'trial-balance') path = `/accounting/trial-balance`;
      else if (reportType === 'cash-flow') path = `/accounting/reports/cash-flow`;
      else { setError('Invalid report type.'); setLoading(false); return; }

      authFetch(`${API_BASE}/businesses/${businessId}${path}${qs}`)
        .then(setData).catch(e => setError(e.message)).finally(() => setLoading(false));
    }
  }, [businessId, reportType, periodId]);

  if (loading) return <Loading fullPage />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <ErrorState message="Financial report not found." />;

  const title = REPORT_TITLES[reportType || ''] || 'Financial Report';

  return (
    <PrintLayout title={`Financial Report: ${title}`}>
      {data.items && (
        <table className="w-full border-collapse border border-slate-300 text-sm mb-6">
          <thead>
            <tr className="bg-slate-100">
              <th className="border border-slate-300 p-2 text-left">Code</th>
              <th className="border border-slate-300 p-2 text-left">Name</th>
              <th className="border border-slate-300 p-2 text-right">Debit</th>
              <th className="border border-slate-300 p-2 text-right">Credit</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((item: any, idx: number) => (
              <tr key={idx}>
                <td className="border border-slate-300 p-2">{item.account_code}</td>
                <td className="border border-slate-300 p-2">{item.account_name}</td>
                <td className="border border-slate-300 p-2 text-right">{item.debit_balance}</td>
                <td className="border border-slate-300 p-2 text-right">{item.credit_balance}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {data.revenue_items && (
        <table className="w-full border-collapse border border-slate-300 text-sm mb-6">
          <thead><tr className="bg-slate-100"><th className="border border-slate-300 p-2 text-left">Account</th><th className="border border-slate-300 p-2 text-right">Amount</th></tr></thead>
          <tbody>
            {data.revenue_items.map((r: any, i: number) => <tr key={i}><td className="border border-slate-300 p-2">{r.account_name}</td><td className="border border-slate-300 p-2 text-right">{r.amount}</td></tr>)}
          </tbody>
        </table>
      )}
      {data.asset_items && (
        <table className="w-full border-collapse border border-slate-300 text-sm mb-6">
          <thead><tr className="bg-slate-100"><th className="border border-slate-300 p-2 text-left">Account</th><th className="border border-slate-300 p-2 text-right">Balance</th></tr></thead>
          <tbody>
            {data.asset_items.map((a: any, i: number) => <tr key={i}><td className="border border-slate-300 p-2">{a.account_name}</td><td className="border border-slate-300 p-2 text-right">{a.balance}</td></tr>)}
          </tbody>
        </table>
      )}
      {!data.items && !data.revenue_items && !data.asset_items && (
        <pre className="text-xs bg-slate-50 p-4 rounded-lg overflow-auto border border-slate-200">{JSON.stringify(data, null, 2)}</pre>
      )}
    </PrintLayout>
  );
};
