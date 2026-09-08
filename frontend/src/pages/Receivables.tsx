import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { SalesReceivableResponse, SalesReceivableSummaryResponse } from '@/types/receivable';
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

export const Receivables: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();

  const [receivables, setReceivables] = useState<SalesReceivableResponse[]>([]);
  const [summary, setSummary] = useState<SalesReceivableSummaryResponse | null>(null);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [search, setSearch] = useState<string>('');

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');

  const fetchData = useCallback(async () => {
    if (!businessId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const [listData, sumData] = await Promise.all([
        apiClient.listReceivables(businessId, {
          page,
          page_size: 20,
          status: statusFilter || undefined,
          search: search || undefined,
        }),
        apiClient.getReceivableSummary(businessId),
      ]);
      setReceivables(listData.items || []);
      setTotal(listData.total || 0);
      setSummary(sumData);
    } catch (err: any) {
      setServerError(err.message || 'Gagal memuat data piutang.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, page, statusFilter, search]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '0' : num.toLocaleString('id-ID');
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Sales Receivables (Piutang)</h1>
        <Link to={`/businesses/${businessId}/sales`}>
          <Button variant="secondary">Back to Sales</Button>
        </Link>
      </div>

      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <div className="space-y-1">
              <span className="text-xs text-gray-500 font-medium uppercase">Total Sales</span>
              <div className="text-2xl font-bold">Rp {formatCurrency(summary.total_sales_amount)}</div>
            </div>
          </Card>
          <Card>
            <div className="space-y-1">
              <span className="text-xs text-gray-500 font-medium uppercase">Total Paid</span>
              <div className="text-2xl font-bold text-emerald-600">Rp {formatCurrency(summary.total_paid_amount)}</div>
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

      <Card>
        <div className="p-4 flex flex-col md:flex-row gap-4 justify-between items-center border-b">
          <div className="flex gap-2 w-full md:w-auto">
            <input
              type="text"
              placeholder="Cari no. sales / customer..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="border rounded px-3 py-1.5 text-sm w-full md:w-64 dark:bg-gray-800 dark:border-gray-700"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="border rounded px-3 py-1.5 text-sm dark:bg-gray-800 dark:border-gray-700"
            >
              <option value="">Semua Status</option>
              <option value="UNPAID">Unpaid</option>
              <option value="PARTIALLY_PAID">Partially Paid</option>
              <option value="PAID">Paid</option>
            </select>
          </div>
        </div>

        {isLoading ? (
          <Loading />
        ) : serverError ? (
          <ErrorState message={serverError} />
        ) : receivables.length === 0 ? (
          <EmptyState title="Tidak ada piutang" description="Tidak ada data piutang yang ditemukan." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 border-b">
                <tr>
                  <th className="px-6 py-3">Sales Number</th>
                  <th className="px-6 py-3">Customer</th>
                  <th className="px-6 py-3">Date</th>
                  <th className="px-6 py-3 text-right">Grand Total</th>
                  <th className="px-6 py-3 text-right">Paid</th>
                  <th className="px-6 py-3 text-right">Outstanding</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Action</th>
                </tr>
              </thead>
              <tbody>
                {receivables.map((rec) => (
                  <tr key={rec.sales_id} className="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-6 py-4 font-medium">{rec.sales_number}</td>
                    <td className="px-6 py-4">{rec.customer_name || 'Walk-in'}</td>
                    <td className="px-6 py-4">{new Date(rec.sales_date).toLocaleDateString()}</td>
                    <td className="px-6 py-4 text-right">Rp {formatCurrency(rec.sales_total)}</td>
                    <td className="px-6 py-4 text-right text-emerald-600 font-medium">Rp {formatCurrency(rec.paid_amount)}</td>
                    <td className="px-6 py-4 text-right text-rose-600 font-bold">Rp {formatCurrency(rec.outstanding_amount)}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-md text-xs font-medium ${STATUS_COLORS[rec.status]}`}>
                        {rec.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <Link to={`/businesses/${businessId}/receivables/${rec.sales_id}`}>
                        <Button size="sm" variant="ghost">Detail</Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <div className="p-4 flex justify-between items-center text-sm text-gray-500">
        <span>Total: {total}</span>
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>Prev</Button>
          <span>Page {page}</span>
          <Button size="sm" variant="secondary" disabled={receivables.length < 20} onClick={() => setPage(p => p + 1)}>Next</Button>
        </div>
      </div>
    </div>
  );
};
