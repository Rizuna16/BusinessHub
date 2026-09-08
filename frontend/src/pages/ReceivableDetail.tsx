import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { SalesReceivableResponse, ReceivablePaymentItem } from '@/types/receivable';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

const STATUS_COLORS: Record<string, string> = {
  UNPAID: 'bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800',
  PARTIALLY_PAID: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800',
  PAID: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
};

export const ReceivableDetail: React.FC = () => {
  const { businessId, salesId } = useParams<{ businessId: string; salesId: string }>();

  const [receivable, setReceivable] = useState<SalesReceivableResponse | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');

  const fetchDetail = useCallback(async () => {
    if (!businessId || !salesId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const recData = await apiClient.getReceivableBySalesId(businessId, salesId);
      setReceivable(recData);
    } catch (err: any) {
      setServerError(err.message || 'Gagal memuat detail piutang.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, salesId]);

  useEffect(() => { fetchDetail(); }, [fetchDetail]);

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '0' : num.toLocaleString('id-ID');
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Detail Piutang</h1>
        <Link to={`/businesses/${businessId}/receivables`}>
          <Button variant="secondary">Kembali ke Daftar Piutang</Button>
        </Link>
      </div>

      {isLoading ? (
        <Loading />
      ) : serverError ? (
        <ErrorState message={serverError} />
      ) : receivable ? (
        <div className="space-y-6">
          <Card>
            <div className="p-6 flex justify-between items-start">
              <div>
                <h2 className="text-xl font-bold">{receivable.sales_number}</h2>
                <p className="text-sm text-gray-500 mt-1">
                  {new Date(receivable.sales_date).toLocaleDateString('id-ID')}
                </p>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[receivable.status]}`}>
                {receivable.status}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-6 border-t">
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-gray-500">Customer:</span><span className="font-medium">{receivable.customer_name || 'Walk-in'}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Branch:</span><span className="font-medium">{receivable.branch_name}</span></div>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-gray-500">Sales Total:</span><span className="font-medium">Rp {formatCurrency(receivable.sales_total)}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Paid Amount:</span><span className="font-medium text-emerald-600">Rp {formatCurrency(receivable.paid_amount)}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Outstanding:</span><span className="font-bold text-rose-600 text-lg">Rp {formatCurrency(receivable.outstanding_amount)}</span></div>
              </div>
            </div>
          </Card>

          <Card>
            <div className="p-6 border-b">
              <h3 className="font-semibold text-lg">Riwayat Pembayaran ({receivable.payments.length})</h3>
            </div>
            {receivable.payments.length === 0 ? (
              <div className="p-8 text-center text-gray-500">Belum ada pembayaran.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 border-b">
                    <tr>
                      <th className="px-6 py-3">No. Pembayaran</th>
                      <th className="px-6 py-3">Tanggal</th>
                      <th className="px-6 py-3">Metode</th>
                      <th className="px-6 py-3 text-right">Jumlah</th>
                      <th className="px-6 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {receivable.payments.map((p: ReceivablePaymentItem) => (
                      <tr key={p.id} className="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
                        <td className="px-6 py-4 font-medium">{p.payment_number}</td>
                        <td className="px-6 py-4">{new Date(p.payment_date).toLocaleDateString()}</td>
                        <td className="px-6 py-4">{p.payment_method}</td>
                        <td className="px-6 py-4 text-right">Rp {formatCurrency(p.amount)}</td>
                        <td className="px-6 py-4">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${p.status === 'RECORDED' ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-800 line-through'}`}>
                            {p.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      ) : (
        <EmptyState title="Piutang Tidak Ditemukan" description="Data piutang ini mungkin belum tersedia atau sales belum difinalisasi." />
      )}
    </div>
  );
};
