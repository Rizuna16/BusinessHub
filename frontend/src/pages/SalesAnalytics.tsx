import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { ExpenseCategoryResponse } from '@/types/expense';
import type { Customer } from '@/types/customer';
import type { Branch } from '@/types/branch';
import type {
  SalesAnalyticsSummaryResponse,
  SalesAnalyticsByCategoryResponse,
  SalesAnalyticsByCustomerResponse,
} from '@/types/salesAnalytics';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

const formatDateLocal = (d: Date) => d.toISOString().slice(0, 10);

export const SalesAnalytics: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();

  const [dateFrom, setDateFrom] = useState<string>(() => {
    const d = new Date();
    d.setDate(1);
    return formatDateLocal(d);
  });
  const [dateTo, setDateTo] = useState<string>(() => formatDateLocal(new Date()));
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [customerFilter, setCustomerFilter] = useState<string>('');
  const [branchFilter, setBranchFilter] = useState<string>('');

  const [categories, setCategories] = useState<ExpenseCategoryResponse[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [summary, setSummary] = useState<SalesAnalyticsSummaryResponse | null>(null);
  const [categoryAnalytics, setCategoryAnalytics] = useState<SalesAnalyticsByCategoryResponse | null>(null);
  const [customerAnalytics, setCustomerAnalytics] = useState<SalesAnalyticsByCustomerResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');

  const fetchFilters = useCallback(async () => {
    if (!businessId) return;
    try {
      const [catData, custData, brData] = await Promise.all([
        apiClient.listExpenseCategories(businessId, { status: 'ACTIVE' }).catch(() => ({ items: [] } as any)),
        apiClient.listCustomers(businessId, { status: 'ACTIVE' }).catch(() => ({ items: [] } as any)),
        apiClient.listBranches(businessId).catch(() => []),
      ]);
      setCategories(catData.items || []);
      setCustomers(custData.items || []);
      setBranches(brData || []);
    } catch {
      // Non-critical
    }
  }, [businessId]);

  useEffect(() => { fetchFilters(); }, [fetchFilters]);

  const fetchData = useCallback(async () => {
    if (!businessId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const params = {
        date_from: `${dateFrom}T00:00:00Z`,
        date_to: `${dateTo}T23:59:59Z`,
        ...(categoryFilter ? { category_id: categoryFilter } : {}),
        ...(customerFilter ? { customer_id: customerFilter } : {}),
        ...(branchFilter ? { branch_id: branchFilter } : {}),
      };

      const [sumData, catData, custData] = await Promise.all([
        apiClient.getSalesAnalyticsSummary(businessId, params),
        apiClient.getSalesAnalyticsByCategory(businessId, params),
        apiClient.getSalesAnalyticsByCustomer(businessId, params),
      ]);
      setSummary(sumData);
      setCategoryAnalytics(catData);
      setCustomerAnalytics(custData);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal memuat data analitik penjualan.';
      setServerError(msg);
      setSummary(null);
      setCategoryAnalytics(null);
      setCustomerAnalytics(null);
    } finally {
      setIsLoading(false);
    }
  }, [businessId, dateFrom, dateTo, categoryFilter, customerFilter, branchFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const fmt = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '0' : num.toLocaleString('id-ID');
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-6">
          <nav className="flex text-sm text-slate-500 dark:text-slate-400 mb-1">
            <Link to={`/businesses/${businessId}`} className="hover:underline">Business</Link>
            <span className="mx-2">/</span>
            <Link to={`/businesses/${businessId}/sales`} className="hover:underline">Sales</Link>
            <span className="mx-2">/</span>
            <span className="text-slate-900 dark:text-slate-100 font-medium">Analytics</span>
          </nav>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Sales Analytics</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Ringkasan penjualan berdasarkan periode, kategori, dan customer.</p>
        </header>

        {/* Filters */}
        <Card className="mb-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end flex-wrap">
            <div className="flex-1 min-w-[150px]">
              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Dari Tanggal</label>
              <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm" />
            </div>
            <div className="flex-1 min-w-[150px]">
              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Sampai Tanggal</label>
              <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm" />
            </div>
            <div className="w-full sm:w-44">
              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Kategori</label>
              <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm">
                <option value="">Semua Kategori</option>
                {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="w-full sm:w-44">
              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Customer</label>
              <select value={customerFilter} onChange={(e) => setCustomerFilter(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm">
                <option value="">Semua Customer</option>
                {customers.map(cu => <option key={cu.id} value={cu.id}>{cu.name}</option>)}
              </select>
            </div>
            <div className="w-full sm:w-44">
              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Branch</label>
              <select value={branchFilter} onChange={(e) => setBranchFilter(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm">
                <option value="">Semua Branch</option>
                {branches.map(br => <option key={br.id} value={br.id}>{br.name}</option>)}
              </select>
            </div>
          </div>
        </Card>

        {serverError && <ErrorState message={serverError} onRetry={fetchData} />}

        {isLoading ? (
          <Card><div className="py-12 flex justify-center"><Loading text="Memuat analitik penjualan..." /></div></Card>
        ) : summary && categoryAnalytics && customerAnalytics ? (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <Card><div className="p-4">
                <span className="text-xs text-slate-500 block mb-1 uppercase">Gross Sales</span>
                <div className="text-xl font-bold text-emerald-600">Rp {fmt(summary.gross_sales)}</div>
              </div></Card>
              <Card><div className="p-4">
                <span className="text-xs text-slate-500 block mb-1 uppercase">Sales Returns</span>
                <div className="text-xl font-bold text-rose-600">Rp {fmt(summary.sales_returns)}</div>
              </div></Card>
              <Card><div className="p-4">
                <span className="text-xs text-slate-500 block mb-1 uppercase">Net Sales</span>
                <div className="text-xl font-bold text-slate-900 dark:text-slate-100">Rp {fmt(summary.net_sales)}</div>
              </div></Card>
              <Card><div className="p-4">
                <span className="text-xs text-slate-500 block mb-1 uppercase">Transactions</span>
                <div className="text-xl font-bold text-slate-900 dark:text-slate-100">{summary.transaction_count}</div>
              </div></Card>
              <Card><div className="p-4">
                <span className="text-xs text-slate-500 block mb-1 uppercase">Avg Transaction</span>
                <div className="text-xl font-bold text-indigo-600">Rp {fmt(summary.average_transaction_value)}</div>
              </div></Card>
            </div>

            {/* Category Breakdown */}
            <Card title="Breakdown Kategori">
              {categoryAnalytics.categories.length === 0 ? (
                <EmptyState title="Tidak ada data" description="Tidak ada penjualan finalized pada periode ini." />
              ) : (
                <div className="hidden md:block overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                        <th className="pb-3 pr-4 font-medium">Kategori</th>
                        <th className="pb-3 pr-4 font-medium">Kode</th>
                        <th className="pb-3 pr-4 font-medium text-right">Transaksi</th>
                        <th className="pb-3 pr-4 font-medium text-right">Gross Sales</th>
                        <th className="pb-3 pr-4 font-medium text-right">Returns</th>
                        <th className="pb-3 font-medium text-right">Net Sales</th>
                      </tr>
                    </thead>
                    <tbody>
                      {categoryAnalytics.categories.map((cat) => (
                        <tr key={cat.category_id || 'uncat'} className="border-b border-slate-100 dark:border-slate-800">
                          <td className="py-3 pr-4 font-medium text-slate-900 dark:text-slate-100">{cat.category_name}</td>
                          <td className="py-3 pr-4 text-slate-500 dark:text-slate-400 font-mono text-xs">{cat.category_code}</td>
                          <td className="py-3 pr-4 text-right text-slate-600 dark:text-slate-300">{cat.transaction_count}</td>
                          <td className="py-3 pr-4 text-right font-medium text-emerald-600">Rp {fmt(cat.gross_sales)}</td>
                          <td className="py-3 pr-4 text-right text-rose-600">Rp {fmt(cat.sales_returns)}</td>
                          <td className="py-3 text-right font-medium text-slate-900 dark:text-slate-100">Rp {fmt(cat.net_sales)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            {/* Customer Breakdown */}
            <Card title="Breakdown Customer">
              {customerAnalytics.customers.length === 0 ? (
                <EmptyState title="Tidak ada data" description="Tidak ada penjualan finalized pada periode ini." />
              ) : (
                <div className="hidden md:block overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                        <th className="pb-3 pr-4 font-medium">Customer</th>
                        <th className="pb-3 pr-4 font-medium text-right">Transaksi</th>
                        <th className="pb-3 pr-4 font-medium text-right">Gross Sales</th>
                        <th className="pb-3 pr-4 font-medium text-right">Returns</th>
                        <th className="pb-3 font-medium text-right">Net Sales</th>
                      </tr>
                    </thead>
                    <tbody>
                      {customerAnalytics.customers.map((cu) => (
                        <tr key={cu.customer_id || 'walkin'} className="border-b border-slate-100 dark:border-slate-800">
                          <td className="py-3 pr-4 font-medium text-slate-900 dark:text-slate-100">{cu.customer_name}</td>
                          <td className="py-3 pr-4 text-right text-slate-600 dark:text-slate-300">{cu.transaction_count}</td>
                          <td className="py-3 pr-4 text-right font-medium text-emerald-600">Rp {fmt(cu.gross_sales)}</td>
                          <td className="py-3 pr-4 text-right text-rose-600">Rp {fmt(cu.sales_returns)}</td>
                          <td className="py-3 text-right font-medium text-slate-900 dark:text-slate-100">Rp {fmt(cu.net_sales)}</td>
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
    </div>
  );
};

export default SalesAnalytics;
