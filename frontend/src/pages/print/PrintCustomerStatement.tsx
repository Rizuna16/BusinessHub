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

export const PrintCustomerStatement: React.FC = () => {
  const { businessId, customerId } = useParams<{ businessId: string; customerId: string }>();
  const [searchParams] = useSearchParams();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const dateFrom = searchParams.get('date_from') || undefined;
  const dateTo = searchParams.get('date_to') || undefined;

  useEffect(() => {
    if (businessId && customerId) {
      const params = new URLSearchParams();
      if (dateFrom) params.set('date_from', dateFrom);
      if (dateTo) params.set('date_to', dateTo);
      const qs = params.toString() ? `?${params}` : '';
      authFetch(`${API_BASE}/businesses/${businessId}/receivables/statements?customer_id=${customerId}${qs ? '&' + params : ''}`)
        .then(setData).catch(e => setError(e.message)).finally(() => setLoading(false));
    }
  }, [businessId, customerId, dateFrom, dateTo]);

  if (loading) return <Loading fullPage />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <ErrorState message="Customer statement not found." />;

  return (
    <PrintLayout title="Customer Account Statement" subtitle={`Customer: ${data.customer_name || customerId}`}>
      <div className="mb-4 text-sm">
        <p><strong>Period:</strong> {dateFrom || 'Beginning'} to {dateTo || 'Present'}</p>
        <p><strong>Outstanding Balance:</strong> {data.current_balance ?? '-'}</p>
      </div>
      <table className="w-full border-collapse border border-slate-300 text-sm mb-6">
        <thead>
          <tr className="bg-slate-100">
            <th className="border border-slate-300 p-2 text-left">Date</th>
            <th className="border border-slate-300 p-2 text-left">Description</th>
            <th className="border border-slate-300 p-2 text-right">Debit</th>
            <th className="border border-slate-300 p-2 text-right">Credit</th>
            <th className="border border-slate-300 p-2 text-right">Balance</th>
          </tr>
        </thead>
        <tbody>
          {data.lines?.map((line: any, idx: number) => (
            <tr key={idx}>
              <td className="border border-slate-300 p-2">{new Date(line.date).toLocaleDateString()}</td>
              <td className="border border-slate-300 p-2">{line.description}</td>
              <td className="border border-slate-300 p-2 text-right">{line.debit}</td>
              <td className="border border-slate-300 p-2 text-right">{line.credit}</td>
              <td className="border border-slate-300 p-2 text-right">{line.running_balance}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </PrintLayout>
  );
};
