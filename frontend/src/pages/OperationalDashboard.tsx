import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { OperationalDashboardResponse } from '@/types/dashboard';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

const activityTypeLabels: Record<string, string> = {
  SALE: 'Penjualan',
  SALES_RETURN: 'Retur Penjualan',
  EXPENSE: 'Belanja',
};

function getDefaultDateRange(): { from: string; to: string } {
  const today = new Date();
  const firstOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
  const to = today.toISOString().split('T')[0];
  const from = firstOfMonth.toISOString().split('T')[0];
  return { from, to };
}

export default function OperationalDashboard() {
  const { businessId } = useParams<{ businessId: string }>();

  const defaults = getDefaultDateRange();
  const [dateFrom, setDateFrom] = useState<string>(defaults.from);
  const [dateTo, setDateTo] = useState<string>(defaults.to);
  const [branchId, setBranchId] = useState<string>('');

  const [report, setReport] = useState<OperationalDashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [serverError, setServerError] = useState<string>('');

  const fetchReport = useCallback(async () => {
    if (!businessId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const data = await apiClient.getOperationalDashboard(businessId, {
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        branch_id: branchId || undefined,
      });
      setReport(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal memuat dashboard.';
      setServerError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [businessId, dateFrom, dateTo, branchId]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const formatCurrency = (val: string | null | undefined) => {
    if (val == null) return 'Rp 0';
    const num = parseFloat(val);
    return isNaN(num) ? 'Rp 0' : `Rp ${num.toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
  };


  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Dashboard Operasional
          </h1>
          <p className="text-sm text-gray-500">
            Ringkasan operasional berdasarkan data penjualan, belanja, dan kas.
          </p>
        </div>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
              Dari Tanggal
            </label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
              Sampai Tanggal
            </label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
              Branch (opsional)
            </label>
            <input
              type="text"
              value={branchId}
              onChange={(e) => setBranchId(e.target.value)}
              placeholder="Filter branch..."
              className="w-full px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-end">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const d = getDefaultDateRange();
                setDateFrom(d.from);
                setDateTo(d.to);
                setBranchId('');
              }}
            >
              Reset
            </Button>
          </div>
        </div>
      </Card>

      {/* Error state */}
      {serverError && <ErrorState message={serverError} onRetry={fetchReport} />}

      {/* Loading state */}
      {isLoading ? (
        <Card>
          <div className="py-12 flex justify-center">
            <Loading text="Memuat dashboard..." />
          </div>
        </Card>
      ) : report ? (
        <div className="space-y-6">
          {/* KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Pendapatan Bersih
              </span>
              <p className="text-2xl font-bold font-mono text-emerald-600 mt-1">
                {formatCurrency(report?.revenue?.net)}
              </p>
              <div className="text-xs text-gray-400 mt-1">
                {report?.revenue?.sales_count} penjualan | {report?.revenue?.return_count} retur
              </div>
            </Card>
            <Card className="p-4">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Total Belanja
              </span>
              <p className="text-2xl font-bold font-mono text-rose-600 mt-1">
                {formatCurrency(report?.expenses?.total)}
              </p>
              <div className="text-xs text-gray-400 mt-1">
                {report?.expenses?.expense_count} catatan
              </div>
            </Card>
            <Card className="p-4">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Hasil Operasional
              </span>
              <p
                className={`text-2xl font-bold font-mono mt-1 ${
                  parseFloat(String(report?.net_operating_result)) >= 0
                    ? 'text-emerald-600'
                    : 'text-rose-600'
                }`}
              >
                {formatCurrency(report?.net_operating_result)}
              </p>
              <div className="text-xs text-gray-400 mt-1">
                (Pendapatan Bersih - Belanja)
              </div>
            </Card>
            <Card className="p-4">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Saldo Kas
              </span>
              <p className="text-2xl font-bold font-mono text-blue-600 mt-1">
                {formatCurrency(report?.cash_position?.total_balance)}
              </p>
              <div className="text-xs text-gray-400 mt-1">
                {report?.cash_position?.account_count} akun aktif
              </div>
            </Card>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card className="p-4">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Piutang (Customer)
              </span>
              <p className="text-2xl font-bold font-mono text-rose-600 mt-1">
                {formatCurrency(report?.receivables?.total_outstanding)}
              </p>
              <div className="text-xs text-gray-400 mt-1">
                {report?.receivables?.unpaid_count} belum lunas | {report?.receivables?.partially_paid_count} sebagian lunas
              </div>
            </Card>
            <Card className="p-4">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Hutang (Vendor)
              </span>
              <p className="text-2xl font-bold font-mono text-blue-600 mt-1">
                {formatCurrency(report?.payables?.total_outstanding)}
              </p>
              <div className="text-xs text-gray-400 mt-1">
                {report?.payables?.unpaid_count} belum lunas | {report?.payables?.partially_paid_count} sebagian lunas
              </div>
            </Card>
            <Card className="p-4">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Nilai Inventori
              </span>
              <p className="text-2xl font-bold font-mono text-emerald-600 mt-1">
                {formatCurrency(report?.inventory?.total_valuation)}
              </p>
              <div className="text-xs text-gray-400 mt-1">
                {report?.inventory?.total_items} item produk
              </div>
            </Card>
          </div>

          {/* Recent Activity */}
          <Card title="Aktivitas Terakhir">
            {report?.recent_activity.length === 0 ? (
              <EmptyState
                title="Tidak ada aktivitas"
                description="Tidak ada aktivitas tercatat dalam periode yang dipilih."
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700">
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Tanggal
                      </th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Jenis
                      </th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Referensi
                      </th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Jumlah
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {report?.recent_activity.map((item) => (
                      <tr key={`${item.type}-${item.reference}`} className="hover:bg-slate-50 dark:hover:bg-slate-900/50">
                        <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-300">
                          {item.date}
                        </td>
                        <td className="px-4 py-3 text-slate-500 dark:text-slate-300">
                          {activityTypeLabels[item.type as string] || item.type}
                        </td>
                        <td className="px-4 py-3 text-slate-500 dark:text-slate-300">
                          {item.reference}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-xs text-slate-700 dark:text-slate-200">
                          {formatCurrency(item.amount)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      ) : null}
    </div>
  );
}

