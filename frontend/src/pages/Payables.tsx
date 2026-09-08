import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { PurchasePayableResponse, PurchasePayableSummaryResponse, SupplierPayableSummaryItem } from '@/types/payable';
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

export const Payables: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();

  const [payables, setPayables] = useState<PurchasePayableResponse[]>([]);
  const [summary, setSummary] = useState<PurchasePayableSummaryResponse | null>(null);
  const [supplierSummaries, setSupplierSummaries] = useState<SupplierPayableSummaryItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [search, setSearch] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'payables' | 'suppliers'>('payables');

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');

  const fetchData = useCallback(async () => {
    if (!businessId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const [listData, sumData, supSumData] = await Promise.all([
        apiClient.listPayables(businessId, {
          page_size: 100,
          status: statusFilter || undefined,
          search: search || undefined,
        }),
        apiClient.getPayableSummary(businessId),
        apiClient.getSupplierPayableSummary(businessId),
      ]);
      setPayables(listData.items || []);
      setSummary(sumData);
      setSupplierSummaries(supSumData.items || []);
    } catch (err: any) {
      setServerError(err.message || 'Gagal memuat data hutang.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, statusFilter, search]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '0' : num.toLocaleString('id-ID');
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Purchase Payables (Hutang Usaha)</h1>
        <Link to={`/businesses/${businessId}/purchases`}>
          <Button variant="secondary">Back to Purchases</Button>
        </Link>
      </div>

      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <div className="space-y-1">
              <span className="text-xs text-gray-500 font-medium uppercase">Gross Payable</span>
              <div className="text-2xl font-bold">Rp {formatCurrency(summary.total_gross_payable)}</div>
            </div>
          </Card>
          <Card>
            <div className="space-y-1">
              <span className="text-xs text-gray-500 font-medium uppercase">Return Adjustment</span>
              <div className="text-2xl font-bold text-amber-600">Rp {formatCurrency(summary.total_return_adjustment)}</div>
            </div>
          </Card>
          <Card>
            <div className="space-y-1">
              <span className="text-xs text-gray-500 font-medium uppercase">Net Payable</span>
              <div className="text-2xl font-bold text-blue-600">Rp {formatCurrency(summary.total_net_payable)}</div>
            </div>
          </Card>
          <Card>
            <div className="space-y-1">
              <span className="text-xs text-gray-500 font-medium uppercase">Total Outstanding</span>
              <div className="text-2xl font-bold text-rose-600">Rp {formatCurrency(summary.total_outstanding_amount)}</div>
            </div>
          </Card>
        </div>
      )}

      <div className="flex gap-2 border-b">
        <button
          className={`pb-2 px-4 font-medium ${activeTab === 'payables' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'}`}
          onClick={() => setActiveTab('payables')}
        >
          Payable List
        </button>
        <button
          className={`pb-2 px-4 font-medium ${activeTab === 'suppliers' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'}`}
          onClick={() => setActiveTab('suppliers')}
        >
          Supplier Summary
        </button>
      </div>

      {activeTab === 'payables' ? (
        <Card>
          <div className="p-4 flex flex-col md:flex-row gap-4 justify-between items-center border-b">
            <div className="flex gap-2 w-full md:w-auto">
              <input
                type="text"
                placeholder="Cari no. purchase / supplier..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="px-3 py-1.5 border rounded-md text-sm w-full md:w-64"
              />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-1.5 border rounded-md text-sm"
              >
                <option value="">Semua Status</option>
                <option value="UNPAID">UNPAID</option>
                <option value="PARTIALLY_PAID">PARTIALLY_PAID</option>
                <option value="PAID">PAID</option>
              </select>
            </div>
          </div>

          {isLoading ? (
            <Loading />
          ) : serverError ? (
            <ErrorState message={serverError} onRetry={fetchData} />
          ) : payables.length === 0 ? (
            <EmptyState title="Tidak ada data hutang" description="Tidak ditemukan record hutang yang sesuai filter." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase font-medium">
                  <tr>
                    <th className="p-3">No. Purchase</th>
                    <th className="p-3">Tanggal</th>
                    <th className="p-3">Supplier</th>
                    <th className="p-3 text-right">Gross Total</th>
                    <th className="p-3 text-right">Retur</th>
                    <th className="p-3 text-right">Net Payable</th>
                    <th className="p-3 text-right">Paid</th>
                    <th className="p-3 text-right">Outstanding</th>
                    <th className="p-3 text-center">Status</th>
                    <th className="p-3 text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {payables.map((item) => (
                    <tr key={item.purchase_id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                      <td className="p-3 font-mono font-medium">{item.purchase_number}</td>
                      <td className="p-3">{new Date(item.purchase_date).toLocaleDateString('id-ID')}</td>
                      <td className="p-3">{item.supplier_name || '-'}</td>
                      <td className="p-3 text-right">Rp {formatCurrency(item.gross_payable)}</td>
                      <td className="p-3 text-right text-amber-600 font-medium">
                        {parseFloat(String(item.return_adjustment)) > 0 ? `(Rp ${formatCurrency(item.return_adjustment)})` : 'Rp 0'}
                      </td>
                      <td className="p-3 text-right font-medium">Rp {formatCurrency(item.net_payable)}</td>
                      <td className="p-3 text-right text-emerald-600 font-medium">Rp {formatCurrency(item.paid_amount)}</td>
                      <td className="p-3 text-right font-bold text-rose-600">Rp {formatCurrency(item.outstanding_amount)}</td>
                      <td className="p-3 text-center">
                        <span className={`px-2 py-1 text-xs rounded-full font-semibold ${STATUS_COLORS[item.status] || ''}`}>
                          {item.status}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        <Link to={`/businesses/${businessId}/purchases/payables/${item.purchase_id}`}>
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
      ) : (
        <Card>
          {isLoading ? (
            <Loading />
          ) : supplierSummaries.length === 0 ? (
            <EmptyState title="Tidak ada ringkasan supplier" description="Belum ada data hutang per supplier." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase font-medium">
                  <tr>
                    <th className="p-3">Supplier</th>
                    <th className="p-3 text-center">Jumlah Purchase</th>
                    <th className="p-3 text-right">Gross Total</th>
                    <th className="p-3 text-right">Retur</th>
                    <th className="p-3 text-right">Net Payable</th>
                    <th className="p-3 text-right">Paid</th>
                    <th className="p-3 text-right">Outstanding</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {supplierSummaries.map((s) => (
                    <tr key={s.supplier_id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                      <td className="p-3 font-medium">{s.supplier_name || 'Tanpa Supplier'}</td>
                      <td className="p-3 text-center">{s.purchase_count}</td>
                      <td className="p-3 text-right">Rp {formatCurrency(s.total_gross_payable)}</td>
                      <td className="p-3 text-right text-amber-600">Rp {formatCurrency(s.total_return_adjustment)}</td>
                      <td className="p-3 text-right font-medium">Rp {formatCurrency(s.total_net_payable)}</td>
                      <td className="p-3 text-right text-emerald-600 font-medium">Rp {formatCurrency(s.total_paid_amount)}</td>
                      <td className="p-3 text-right font-bold text-rose-600">Rp {formatCurrency(s.total_outstanding_amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  );
};
