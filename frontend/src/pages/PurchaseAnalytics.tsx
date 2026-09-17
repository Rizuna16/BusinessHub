import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

const fmt = (val: number | string) => {
  const num = typeof val === 'string' ? parseFloat(val) : val;
  return isNaN(num) ? '0' : num.toLocaleString('id-ID');
};

export const PurchaseAnalytics: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();

  const [dateFrom, setDateFrom] = useState<string>(() => {
    const d = new Date();
    d.setDate(1);
    return d.toISOString().slice(0, 10);
  });
  const [dateTo, setDateTo] = useState<string>(() => {
    const d = new Date();
    return d.toISOString().slice(0, 10);
  });
  const [supplierFilter, setSupplierFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');

  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [summary, setSummary] = useState<any | null>(null);
  const [supplierAnalytics, setSupplierAnalytics] = useState<any | null>(null);
  const [categoryAnalytics, setCategoryAnalytics] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');

  const fetchFilters = useCallback(async () => {
    if (!businessId) return;
    try {
      const [supData, catData] = await Promise.all([
        apiClient.listSuppliers(businessId, { status: 'ACTIVE' }).catch(() => ({ items: [] })),
        apiClient.listExpenseCategories(businessId, { status: 'ACTIVE' }).catch(() => ({ items: [] })),
      ]);
      setSuppliers(supData.items || []);
      setCategories(catData.items || []);
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
        ...(supplierFilter ? { supplier_id: supplierFilter } : {}),
        ...(categoryFilter ? { category_id: categoryFilter } : {}),
      };

      const [sumData, supData, catData] = await Promise.all([
        apiClient.getPurchaseAnalyticsSummary(businessId, params),
        apiClient.getPurchaseAnalyticsBySupplier(businessId, params),
        apiClient.getPurchaseAnalyticsByCategory(businessId, params),
      ]);
      setSummary(sumData);
      setSupplierAnalytics(supData);
      setCategoryAnalytics(catData);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal memuat data analitik pembelian.';
      setServerError(msg);
      setSummary(null);
      setSupplierAnalytics(null);
      setCategoryAnalytics(null);
    } finally {
      setIsLoading(false);
    }
  }, [businessId, dateFrom, dateTo, supplierFilter, categoryFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-6">
          <nav className="flex text-sm text-slate-500 dark:text-slate-400 mb-1">
            <Link to={`/businesses/${businessId}/purchases`} className="hover:underline">Purchases</Link>
            <span className="mx-2">/</span>
            <span className="text-slate-900 dark:text-slate-100 font-medium">Analytics</span>
          </nav>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Purchase Analytics</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Analisis pembelian berdasarkan periode, supplier, dan kategori.</p>
        </header>

        {/* Filters */}
        <Card className="mb-6">
          <div className="flex flex-col sm:flex-row flex-wrap gap-2">
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
            <div className="flex-1">
              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Supplier</label>
              <select value={supplierFilter} onChange={(e) => setSupplierFilter(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm">
                <option value="">Semua Supplier</option>
                {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div className="flex-1">
              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Kategori</label>
              <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm">
                <option value="">Semua Kategori</option>
                {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
          </div>
        </Card>

        {serverError && <ErrorState message={serverError} onRetry={fetchData} />}

        {isLoading ? (
          <Card><div className="py-12 flex justify-center"><Loading text="Memuat analitik pembelian..." /></div></Card>
        ) : summary && supplierAnalytics && categoryAnalytics ? (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <Card><div className="p-4">
                <span className="text-xs text-slate-500 block mb-1 uppercase">Pembelian Kasar</span>
                <div className="text-xl font-bold text-emerald-600">Rp {fmt(summary.gross_purchases)}</div>
              </div></Card>
              <Card><div className="p-4">
                <span className="text-xs text-slate-500 block mb-1 uppercase">Pembalian</span>
                <div className="text-xl font-bold text-rose-600">Rp {fmt(summary.purchase_returns)}</div>
              </div></Card>
              <Card><div className="p-4">
                <span className="text-xs text-slate-500 block mb-1 uppercase">Beli Bersih</span>
                <div className="text-xl font-bold text-slate-900 dark:text-slate-100">Rp {fmt(summary.net_purchases)}</div>
              </div></Card>
              <Card><div className="p-4">
                <span className="text-xs text-slate-500 block mb-1 uppercase">Pembelian</span>
                <div className="text-xl font-bold text-slate-900 dark:text-slate-100">{summary.purchase_count}</div>
              </div></Card>
              <Card><div className="p-4">
                <span className="text-xs text-slate-500 block mb-1 rata-atas">Rata-rata</span>
                <div className="text-xl font-bold text-indigo-600">Rp {fmt(summary.average_purchase_value)}</div>
              </div></Card>
            </div>

            {/* Supplier Breakdown */}
            <Card title="Breakdown Supplier">
              {supplierAnalytics.suppliers.length === 0 ? (
                <EmptyState title="Tidak ada data" description="Tidak ada pembelian finalized pada periode ini." />
              ) : (
                <div className="hidden md:block overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                        <th className="pb-3 pr-4 font-medium">Supplier</th>
                        <th className="pb-3 pr-4 font-medium text-right">Transaksi</th>
                        <th className="pb-3 pr-4 font-medium text-right">Beli Kasar</th>
                        <th className="pb-3 pr-4 font-medium text-right">Kembali</th>
                        <th className="pb-3 font-medium text-right">Beli Bersih</th>
                      </tr>
                    </thead>
                    <tbody>
                      {supplierAnalytics.suppliers.map((s: any) => (
                        <tr key={s.supplier_id} className="border-b border-slate-100 dark:border-slate-800">
                          <td className="py-3 pr-4 font-medium text-slate-900 dark:text-slate-100">{s.supplier_name}</td>
                          <td className="py-3 pr-4 text-right text-slate-600 dark:text-slate-300">{s.purchase_count}</td>
                          <td className="py-3 pr-4 text-right font-medium text-emerald-600">Rp {fmt(s.gross_purchases)}</td>
                          <td className="py-3 pr-4 text-right text-rose-600">Rp {fmt(s.purchase_returns)}</td>
                          <td className="py-3 text-right font-medium text-slate-900 dark:text-slate-100">Rp {fmt(s.net_purchases)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            {/* Category Breakdown */}
            <Card title="Breakdown Kategori">
              {categoryAnalytics.categories.length === 0 ? (
                <EmptyState title="Tidak ada data" description="Tidak ada pembelian finalized pada periode ini." />
              ) : (
                <div className="hidden md:block overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                        <th className="pb-3 pr-4 font-medium">Kategori</th>
                        <th className="pb-3 pr-4 font-medium">Kode</th>
                        <th className="pb-3 pr-4 font-medium text-right">Transaksi</th>
                        <th className="pb-3 pr-4 font-medium text-right">Beli Kasar</th>
                        <th className="pb-3 pr-4 font-medium text-right">Kembali</th>
                        <th className="pb-3 font-medium text-right">Beli Bersih</th>
                      </tr>
                    </thead>
                    <tbody>
                      {categoryAnalytics.categories.map((c: any) => (
                        <tr key={c.category_id || 'uncat'} className="border-b border-slate-100 dark:border-slate-800">
                          <td className="py-3 pr-4 font-medium text-slate-900 dark:text-slate-100">{c.category_name}</td>
                          <td className="py-3 pr-4 text-slate-500 dark:text-slate-400 font-mono text-xs">{c.category_code}</td>
                          <td className="py-3 pr-4 text-right text-slate-600 dark:text-slate-300">{c.purchase_count}</td>
                          <td className="py-3 pr-4 text-right font-medium text-emerald-600">Rp {fmt(c.gross_purchases)}</td>
                          <td className="py-3 pr-4 text-right text-rose-600">Rp {fmt(c.purchase_returns)}</td>
                          <td className="py-3 text-right font-medium text-slate-900 dark:text-slate-100">Rp {fmt(c.net_purchases)}</td>
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

export default PurchaseAnalytics;