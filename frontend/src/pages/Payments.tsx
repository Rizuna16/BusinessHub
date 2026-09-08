import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { Payment } from '@/types/payment';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

const STATUS_COLORS: Record<string, string> = {
  RECORDED: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
  VOIDED: 'bg-gray-100 text-gray-500 border border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700 line-through',
};

export const Payments: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();

  const [payments, setPayments] = useState<Payment[]>([]);
  const [directionFilter, setDirectionFilter] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');

  const fetchData = useCallback(async () => {
    if (!businessId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const data = await apiClient.listPayments(businessId, {
        page_size: 100,
        direction: directionFilter || undefined,
      });
      setPayments(data.items || []);
    } catch (err: any) {
      setServerError(err.message || 'Gagal memuat data pembayaran.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, directionFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '0' : num.toLocaleString('id-ID');
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Payments (Transaksi Pembayaran)</h1>
        <Link to={`/businesses/${businessId}/dashboard`}>
          <Button variant="secondary">Back to Dashboard</Button>
        </Link>
      </div>

      <Card>
        <div className="p-4 flex flex-col md:flex-row gap-4 justify-between items-center border-b">
          <div className="flex gap-2 w-full md:w-auto">
            <select
              value={directionFilter}
              onChange={(e) => setDirectionFilter(e.target.value)}
              className="px-3 py-1.5 border rounded-md text-sm"
            >
              <option value="">Semua Arah</option>
              <option value="CUSTOMER_IN">Customer Payment (IN)</option>
              <option value="SUPPLIER_OUT">Supplier Payment (OUT)</option>
            </select>
          </div>
        </div>

        {isLoading ? (
          <Loading />
        ) : serverError ? (
          <ErrorState message={serverError} onRetry={fetchData} />
        ) : payments.length === 0 ? (
          <EmptyState title="Tidak ada transaksi" description="Belum ada data pembayaran." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase font-medium">
                <tr>
                  <th className="p-3">No. Pembayaran</th>
                  <th className="p-3">Tanggal</th>
                  <th className="p-3">Tipe</th>
                  <th className="p-3">Metode</th>
                  <th className="p-3 text-right">Nominal</th>
                  <th className="p-3 text-center">Status</th>
                  <th className="p-3 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {payments.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                    <td className="p-3 font-mono font-medium">{p.payment_number}</td>
                    <td className="p-3">{new Date(p.payment_date).toLocaleDateString('id-ID')}</td>
                    <td className="p-3">{p.direction === 'CUSTOMER_IN' ? 'Penerimaan Pelanggan' : 'Pembayaran Supplier'}</td>
                    <td className="p-3">{p.payment_method.replace('_', ' ')}</td>
                    <td className={`p-3 text-right font-bold ${p.direction === 'CUSTOMER_IN' ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {p.direction === 'CUSTOMER_IN' ? '+' : '-'} Rp {formatCurrency(p.amount)}
                    </td>
                    <td className="p-3 text-center">
                      <span className={`px-2 py-1 text-xs rounded-full font-semibold ${STATUS_COLORS[p.status] || ''}`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      <Link to={`/businesses/${businessId}/payments/${p.id}`}>
                        <Button size="sm" variant="secondary">Detail</Button>
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
