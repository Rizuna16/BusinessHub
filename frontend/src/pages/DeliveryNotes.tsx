import React, { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { DeliveryNote } from '@/types/deliveryNote';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';

const STATUS_COLORS: Record<string, string> = {
  DRAFT: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800',
  READY: 'bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-950/40 dark:text-blue-400 dark:border-blue-800',
  DELIVERED: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
  CANCELLED: 'bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800',
};

export const DeliveryNotes: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();

  const [deliveryNotes, setDeliveryNotes] = useState<DeliveryNote[]>([]);
  const [page] = useState<number>(1);
  const [pageSize] = useState<number>(20);
  const [statusFilter] = useState<string>('');
  const [soFilter] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');

  const fetchDeliveryNotes = useCallback(async () => {
    if (!businessId) return;
    try {
      setIsLoading(true);
      setServerError('');
      const res = await apiClient.listDeliveryNotes(businessId, {
        status: statusFilter || undefined,
        sales_order_id: soFilter || undefined,
        page,
        page_size: pageSize,
      });
      setDeliveryNotes(res.items || []);
    } catch (err: any) {
      const msg = err?.message || 'Gagal memuat delivery note.';
      if (msg.toLowerCase().includes('unauthorized')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [businessId, statusFilter, soFilter, page, pageSize, navigate]);

  useEffect(() => {
    fetchDeliveryNotes();
  }, [fetchDeliveryNotes]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Delivery Notes (Surat Jalan)</h2>
        <Link
          to={`/businesses/${businessId}/delivery-notes/new`}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
        >
          + Buat Delivery Note
        </Link>
      </div>

      <Card>
        {isLoading && (
          <div className="h-64 flex items-center justify-center text-slate-500">
            Memuat data...
          </div>
        )}

        {serverError && (
          <div className="p-4 bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 rounded-lg text-sm">
            {serverError}
          </div>
        )}

        {!isLoading && deliveryNotes.length === 0 && (
          <EmptyState
            title="Tidak ada Delivery Note"
            description="Buat Delivery Note pertama untuk melacak surat jalan pengiriman."
          />
        )}

        {!isLoading && deliveryNotes.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  <th className="p-4">No</th>
                  <th className="p-4">Nomor</th>
                  <th className="p-4">Sales Order</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Tanggal</th>
                  <th className="p-4 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {deliveryNotes.map((dn, index) => (
                  <tr key={dn.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="p-4 text-sm text-slate-600 dark:text-slate-400">{(page - 1) * pageSize + index + 1}</td>
                    <td className="p-4 text-sm font-medium text-slate-900 dark:text-slate-100">{dn.delivery_number}</td>
                    <td className="p-4 text-sm">
                      <Link to={`/businesses/${businessId}/sales-orders/${dn.sales_order_id}`} className="text-indigo-600 hover:underline">
                        {dn.sales_order_id}
                      </Link>
                    </td>
                    <td className="p-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[dn.status] || 'bg-slate-100 text-slate-800'}`}>
                        {dn.status}
                      </span>
                    </td>
                    <td className="p-4 text-sm text-slate-600 dark:text-slate-400">
                      {new Date(dn.delivery_date).toLocaleDateString()}
                    </td>
                    <td className="p-4 text-right">
                      <Link
                        to={`/businesses/${businessId}/delivery-notes/${dn.id}`}
                        className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
                      >
                        Detail
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};
