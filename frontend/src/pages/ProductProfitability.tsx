import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { ProductProfitabilityResponse } from '@/types/profitability';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

export const ProductProfitability: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();

  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [groupBy, setGroupBy] = useState<string>('product');
  const [branchId, setBranchId] = useState<string>('');
  const [categoryId, setCategoryId] = useState<string>('');
  const [productId, setProductId] = useState<string>('');
  const [customerId, setCustomerId] = useState<string>('');

  const [report, setReport] = useState<ProductProfitabilityResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [serverError, setServerError] = useState<string>('');

  const fetchReport = useCallback(async () => {
    if (!businessId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const data = await apiClient.getProductProfitability(businessId, {
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        group_by: groupBy,
        branch_id: branchId || undefined,
        category_id: categoryId || undefined,
        product_id: productId || undefined,
        customer_id: customerId || undefined,
      });
      setReport(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal memuat laporan profitabilitas.';
      setServerError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [businessId, dateFrom, dateTo, groupBy, branchId, categoryId, productId, customerId]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const formatCurrency = (val: number | string | null | undefined) => {
    if (val == null) return '0';
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '0' : num.toLocaleString('id-ID');
  };

  const formatNumber = (val: number | string | null | undefined) => {
    if (val == null) return '-';
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '-' : num.toLocaleString('id-ID');
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
            <Link to={`/businesses/${businessId}`} className="hover:text-blue-500">
              Bisnis
            </Link>
            <span>/</span>
            <span className="text-slate-900 dark:text-slate-100 font-medium">
              Profitabilitas & Gross Margin
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Product Profitability & Gross Margin Analytics
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Analisis Net Revenue, HPP (COGS), Laba Kotor, dan Gross Margin % berdasarkan data penjualan aktual dan HPP aktual.
          </p>
        </div>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              Group By (Dimensi)
            </label>
            <select
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value)}
              className="w-full px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="product">Product</option>
              <option value="variant">Product Variant</option>
              <option value="category">Category</option>
              <option value="customer">Customer</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              Dari Tanggal (date_from)
            </label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              Sampai Tanggal (date_to)
            </label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              Branch ID
            </label>
            <input
              type="text"
              value={branchId}
              onChange={(e) => setBranchId(e.target.value)}
              placeholder="Filter branch..."
              className="w-full px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              Category ID
            </label>
            <input
              type="text"
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              placeholder="Filter category..."
              className="w-full px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              Product ID
            </label>
            <input
              type="text"
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              placeholder="Filter product..."
              className="w-full px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              Customer ID / "walk-in"
            </label>
            <input
              type="text"
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              placeholder="Customer ID or walk-in..."
              className="w-full px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-end">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setDateFrom('');
                setDateTo('');
                setGroupBy('product');
                setBranchId('');
                setCategoryId('');
                setProductId('');
                setCustomerId('');
              }}
            >
              Reset Filter
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
            <Loading text="Memuat laporan profitabilitas..." />
          </div>
        </Card>
      ) : report ? (
        <div className="space-y-6">
          {/* Summary */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Total Net Revenue
              </span>
              <p className="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400 mt-1">
                Rp {formatCurrency(report.summary.total_net_revenue)}
              </p>
              <div className="text-xs text-slate-500 mt-1">
                Sales: {report.summary.total_sales_count} | Returns: {report.summary.total_return_count}
              </div>
            </Card>
            <Card className="p-4">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Total COGS (HPP)
              </span>
              <p className="text-xl font-bold font-mono text-rose-600 dark:text-rose-400 mt-1">
                Rp {formatCurrency(report.summary.total_cogs)}
              </p>
              <div className="text-xs text-slate-500 mt-1">
                Units Sold: {formatNumber(report.summary.total_units_sold)} | Returned: {formatNumber(report.summary.total_units_returned)}
              </div>
            </Card>
            <Card className="p-4">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Total Gross Profit
              </span>
              <p
                className={`text-xl font-bold font-mono mt-1 ${
                  parseFloat(String(report.summary.total_gross_profit)) >= 0
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-rose-600 dark:text-rose-400'
                }`}
              >
                Rp {formatCurrency(report.summary.total_gross_profit)}
              </p>
            </Card>
            <Card className="p-4">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Overall Gross Margin %
              </span>
              <p className="text-xl font-bold font-mono text-blue-600 dark:text-blue-400 mt-1">
                {formatNumber(report.summary.overall_gross_margin_percentage)}%
              </p>
            </Card>
          </div>

          {/* Table */}
          <Card title={`Hasil Analisis (Group by: ${groupBy})`}>
            {report.items.length === 0 ? (
              <EmptyState
                title="Tidak ada data"
                description="Tidak ada data profitabilitas yang ditemukan untuk parameter yang dipilih."
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700">
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Nama / Group
                      </th>
                      <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Kategori / Atribut
                      </th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Units Sold
                      </th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Units Ret.
                      </th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Net Revenue
                      </th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        COGS
                      </th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Gross Profit
                      </th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Margin %
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {report.items.map((item) => (
                      <tr key={item.group_id} className="hover:bg-slate-50 dark:hover:bg-slate-900/50">
                        <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">
                          <div>{item.group_name}</div>
                          {item.group_code && (
                            <div className="font-mono text-xs text-slate-500">{item.group_code}</div>
                          )}
                        </td>
                        <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                          {item.category_name || item.customer_name || item.branch_name || '-'}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-xs text-slate-700 dark:text-slate-200">
                          {formatNumber(item.units_sold)}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-xs text-rose-500 dark:text-rose-400">
                          {formatNumber(item.units_returned)}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-xs text-emerald-600 dark:text-emerald-400">
                          Rp {formatCurrency(item.net_revenue)}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-xs text-rose-600 dark:text-rose-400">
                          Rp {formatCurrency(item.cogs)}
                        </td>
                        <td
                          className={`px-4 py-3 text-right font-mono text-xs font-medium ${
                            parseFloat(String(item.gross_profit)) >= 0
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-rose-600 dark:text-rose-400'
                          }`}
                        >
                          Rp {formatCurrency(item.gross_profit)}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-xs font-medium text-blue-600 dark:text-blue-400">
                          {item.gross_margin_percentage != null ? `${formatNumber(item.gross_margin_percentage)}%` : '-'}
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
};

export default ProductProfitability;
