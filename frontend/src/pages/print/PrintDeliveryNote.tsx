import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { PrintLayout } from './PrintLayout';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

function authFetch(url: string) {
  return fetch(url, { headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` } })
    .then(r => r.ok ? r.json() : Promise.reject(new Error(`Failed: ${r.status}`)))
    .then(j => j.data ?? j);
}

export const PrintDeliveryNote: React.FC = () => {
  const { businessId, id } = useParams<{ businessId: string; id: string }>();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (businessId && id) {
      authFetch(`${API_BASE}/businesses/${businessId}/delivery-notes/${id}`)
        .then(setData).catch(e => setError(e.message)).finally(() => setLoading(false));
    }
  }, [businessId, id]);

  if (loading) return <Loading fullPage />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <ErrorState message="Delivery note not found." />;

  return (
    <PrintLayout title="Delivery Note (Surat Jalan)" subtitle={`Note #${data.note_number}`}>
      <div className="mb-4 text-sm">
        <div className="flex justify-between">
          <span><strong>Date:</strong> {new Date(data.delivery_date).toLocaleString()}</span>
          <span><strong>Status:</strong> {data.status}</span>
        </div>
      </div>
      <table className="w-full border-collapse border border-slate-300 text-sm mb-6">
        <thead>
          <tr className="bg-slate-100">
            <th className="border border-slate-300 p-2 text-left">Product</th>
            <th className="border border-slate-300 p-2 text-right">Delivery Quantity</th>
            <th className="border border-slate-300 p-2 text-left">Notes</th>
          </tr>
        </thead>
        <tbody>
          {data.lines?.map((line: any, idx: number) => (
            <tr key={idx}>
              <td className="border border-slate-300 p-2">{line.product_name || line.product_id}</td>
              <td className="border border-slate-300 p-2 text-right">{line.delivery_quantity}</td>
              <td className="border border-slate-300 p-2">{line.notes || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </PrintLayout>
  );
};
