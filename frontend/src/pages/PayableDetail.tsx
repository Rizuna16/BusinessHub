import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { PurchasePayableResponse } from '@/types/payable';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';

const STATUS_COLORS: Record<string, string> = {
  UNPAID: 'bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800',
  PARTIALLY_PAID: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800',
  PAID: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
};

export const PayableDetail: React.FC = () => {
  const { businessId, purchaseId } = useParams<{ businessId: string; purchaseId: string }>();

  const [payable, setPayable] = useState<PurchasePayableResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');

  const fetchDetail = useCallback(async () => {
    if (!businessId || !purchaseId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const data = await apiClient.getPayableByPurchaseId(businessId, purchaseId);
      setPayable(data);
    } catch (err: any) {
      setServerError(err.message || 'Gagal memuat detail hutang.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, purchaseId]);

  useEffect(() => { fetchDetail(); }, [fetchDetail]);

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '0' : num.toLocaleString('id-ID');
  };

  if (isLoading) return <div className="p-6"><Loading /></div>;
  if (serverError || !payable) return <div className="p-6"><ErrorState message={serverError || 'Payable not found'} onRetry={fetchDetail} /></div>;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-3">
            Hutang: {payable.purchase_number}
            <span className={`px-2.5 py-0.5 text-xs rounded-full font-semibold ${STATUS_COLORS[payable.status] || ''}`}>
              {payable.status}
            </span>
          </h1>
          <p className="text-sm text-gray-500">
            Tanggal Pembelian: {new Date(payable.purchase_date).toLocaleDateString('id-ID')}
          </p>
        </div>
        <div className="flex gap-2">
          <Link to={`/businesses/${businessId}/purchases/${payable.purchase_id}`}>
            <Button variant="secondary">Lihat Purchase</Button>
          </Link>
          <Link to={`/businesses/${businessId}/purchases/payables`}>
            <Button variant="secondary">Kembali</Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <h3 className="font-semibold text-sm mb-3">Informasi Supplier & Cabang</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Supplier:</span>
              <span className="font-medium">{payable.supplier_name || '-'} ({payable.supplier_code || '-'})</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Cabang:</span>
              <span className="font-medium">{payable.branch_name || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Mata Uang:</span>
              <span className="font-medium">{payable.currency}</span>
            </div>
          </div>
        </Card>

        <Card>
          <h3 className="font-semibold text-sm mb-3">Rincian Finansial</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Gross Payable:</span>
              <span className="font-medium">Rp {formatCurrency(payable.gross_payable)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Penyesuaian Retur:</span>
              <span className="font-medium text-amber-600">(Rp {formatCurrency(payable.return_adjustment)})</span>
            </div>
            <div className="flex justify-between font-semibold border-t pt-2">
              <span>Net Payable:</span>
              <span>Rp {formatCurrency(payable.net_payable)}</span>
            </div>
            <div className="flex justify-between text-emerald-600">
              <span>Paid Amount:</span>
              <span>Rp {formatCurrency(payable.paid_amount)}</span>
            </div>
            <div className="flex justify-between font-bold text-rose-600 border-t pt-2 text-base">
              <span>Outstanding:</span>
              <span>Rp {formatCurrency(payable.outstanding_amount)}</span>
            </div>
          </div>
        </Card>
      </div>

      {payable.returns && payable.returns.length > 0 && (
        <Card>
          <h3 className="font-semibold text-sm mb-3">Daftar Retur Pembelian</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase font-medium">
                <tr>
                  <th className="p-3">No. Retur</th>
                  <th className="p-3">Tanggal</th>
                  <th className="p-3 text-right">Nilai Retur</th>
                  <th className="p-3 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {payable.returns.map((r) => (
                  <tr key={r.id}>
                    <td className="p-3 font-mono font-medium">{r.return_number}</td>
                    <td className="p-3">{new Date(r.return_date).toLocaleDateString('id-ID')}</td>
                    <td className="p-3 text-right font-medium text-amber-600">Rp {formatCurrency(r.grand_total)}</td>
                    <td className="p-3 text-center">
                      <span className="px-2 py-0.5 text-xs rounded-full font-medium bg-gray-100 dark:bg-gray-700">
                        {r.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
};
