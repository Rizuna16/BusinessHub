import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { ExpenseCategoryResponse, ExpenseSummaryResponse } from '@/types/expense';
import type { ExpenseAnalyticsByCategoryResponse } from '@/types/expenseAnalytics';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

const formatDateLocal = (d: Date) => d.toISOString().slice(0, 10);

export const ExpenseAnalytics: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();

  const [dateFrom, setDateFrom] = useState<string>(() => {
    const d = new Date();
    d.setDate(1);
    return formatDateLocal(d);
  });
  const [dateTo, setDateTo] = useState<string>(() => formatDateLocal(new Date()));
  const [categoryFilter, setCategoryFilter] = useState<string>('');

  const [categories, setCategories] = useState<ExpenseCategoryResponse[]>([]);
  const [summary, setSummary] = useState<ExpenseSummaryResponse | null>(null);
  const [analytics, setAnalytics] = useState<ExpenseAnalyticsByCategoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');

  const fetchCategories = useCallback(async () => {
    if (!businessId) return;
    try {
      const data = await apiClient.listExpenseCategories(businessId, { status: 'ACTIVE' });
      setCategories(data.items || []);
    } catch {
      // Non-critical, leave categories empty
    }
  }, [businessId]);

  useEffect(() => { fetchCategories(); }, [fetchCategories]);

  const fetchAnalytics = useCallback(async () => {
    if (!businessId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const params = new URLSearchParams();
      params.set('date_from', `${dateFrom}T00:00:00Z`);
      params.set('date_to', `${dateTo}T23:59:59Z`);
      if (categoryFilter) params.set('category_id', categoryFilter);

      const [sumData, analyticsData] = await Promise.all([
        apiClient.getExpenseSummary(businessId, {
          date_from: `${dateFrom}T00:00:00Z`,
          date_to: `${dateTo}T23:59:59Z`,
          ...(categoryFilter ? { category_id: categoryFilter } : {}),
        }),
        apiClient.getExpenseAnalyticsByCategory(businessId, {
          date_from: `${dateFrom}T00:00:00Z`,
          date_to: `${dateTo}T23:59:59Z`,
          ...(categoryFilter ? { category_id: categoryFilter } : {}),
        }),
      ]);
      setSummary(sumData);
      setAnalytics(analyticsData);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal memuat data analitik.';
      setServerError(msg);
      setSummary(null);
      setAnalytics(null);
    } finally {
      setIsLoading(false);
    }
  }, [businessId, dateFrom, dateTo, categoryFilter]);

  useEffect(() => { fetchAnalytics(); }, [fetchAnalytics]);

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '0' : num.toLocaleString('id-ID');
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <header className="mb-6">
          <nav className="flex text-sm text-slate-500 dark:text-slate-400 mb-1">
            <Link to={`/businesses/${businessId}`} className="hover:underline">Business</Link>
            <span className="mx-2">/</span>
            <Link to={`/businesses/${businessId}/expenses`} className="hover:underline">Expenses</Link>
            <span className="mx-2">/</span>
            <span className="text-slate-900 dark:text-slate-100 font-medium">Analytics</span>
          </nav>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Expense Analytics</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Ringkasan pengeluaran berdasarkan periode dan kategori.</p>
        </header>

        {/* Filters */}
        <Card className="mb-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Dari Tanggal</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
              />
            </div>
            <div className="flex-1">
              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Sampai Tanggal</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
              />
            </div>
            <div className="w-full sm:w-48">
              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Kategori</label>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
              >
                <option value="">Semua Kategori</option>
                {categories.map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          </div>
        </Card>

        {/* Error */}
        {serverError && <ErrorState message={serverError} onRetry={fetchAnalytics} />}

        {/* Loading */}
        {isLoading ? (
          <Card>
            <div className="py-12 flex justify-center">
              <Loading text="Memuat analitik pengeluaran..." />
            </div>
          </Card>
        ) : summary && analytics ? (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <div className="p-4">
                  <span className="text-xs text-slate-500 block mb-1 uppercase">Total Pengeluaran</span>
                  <div className="text-2xl font-bold text-rose-600">Rp {formatCurrency(summary.total_expense_amount)}</div>
                  <span className="text-xs text-slate-400 mt-1 block">{summary.currency}</span>
                </div>
              </Card>
              <Card>
                <div className="p-4">
                  <span className="text-xs text-slate-500 block mb-1 uppercase">Jumlah Transaksi (Finalized)</span>
                  <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">{summary.finalized_count}</div>
                  <span className="text-xs text-slate-400 mt-1 block">Transaksi yang telah diselesaikan</span>
                </div>
              </Card>
            </div>

            {/* Category Breakdown */}
            <Card title="Breakdown Kategori">
              {analytics.categories.length === 0 ? (
                <EmptyState
                  title="Tidak ada data"
                  description="Tidak ada pengeluaran finalized pada periode dan filter yang dipilih."
                />
              ) : (
                <>
                  <div className="hidden md:block overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                          <th className="pb-3 pr-4 font-medium">Kategori</th>
                          <th className="pb-3 pr-4 font-medium">Kode</th>
                          <th className="pb-3 pr-4 font-medium text-right">Jumlah Transaksi</th>
                          <th className="pb-3 font-medium text-right">Total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {analytics.categories.map((cat) => (
                          <tr key={cat.category_id || 'uncat'} className="border-b border-slate-100 dark:border-slate-800">
                            <td className="py-3 pr-4 font-medium text-slate-900 dark:text-slate-100">{cat.category_name}</td>
                            <td className="py-3 pr-4 text-slate-500 dark:text-slate-400 font-mono text-xs">{cat.category_code}</td>
                            <td className="py-3 pr-4 text-right text-slate-600 dark:text-slate-300">{cat.expense_count}</td>
                            <td className="py-3 text-right font-medium text-rose-600">Rp {formatCurrency(cat.total)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Mobile cards */}
                  <div className="md:hidden divide-y divide-slate-100 dark:divide-slate-800">
                    {analytics.categories.map((cat) => (
                      <div key={cat.category_id || 'uncat'} className="py-3 flex justify-between items-center">
                        <div>
                          <span className="font-medium text-slate-900 dark:text-slate-100 text-sm">{cat.category_name}</span>
                          <span className="text-xs text-slate-400 block font-mono">{cat.category_code}</span>
                        </div>
                        <div className="text-right">
                          <span className="font-medium text-rose-600 text-sm">Rp {formatCurrency(cat.total)}</span>
                          <span className="text-xs text-slate-400 block">{cat.expense_count} transaksi</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Invariant verification line */}
                  <div className="mt-4 pt-3 border-t border-slate-200 dark:border-slate-700 flex justify-between items-center text-sm">
                    <span className="text-slate-500">Total Kategori:</span>
                    <span className="font-medium text-slate-900 dark:text-slate-100">
                      Rp {formatCurrency(analytics.total)}
                    </span>
                  </div>
                </>
              )}
            </Card>
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default ExpenseAnalytics;
