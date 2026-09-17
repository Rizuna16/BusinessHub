import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type {
  PaymentAnalyticsSummaryResponse,
  PaymentAnalyticsByDirectionResponse,
  PaymentAnalyticsByMethodResponse,
} from '@/types/paymentAnalytics';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

const fmt = (val: number | string) => {
  const num = typeof val === 'string' ? parseFloat(val) : val;
  return isNaN(num) ? '0' : num.toLocaleString('id-ID');
};

export const PaymentAnalytics: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();

  const [dateFrom, setDateFrom] = useState<string>(() => {
    const d = new Date();
    d.setDate(1);
    return d.toISOString().slice(0, 10);
  });
  const [dateTo, setDateTo] = useState<string>(() => new Date().toISOString().slice(0, 10));
  const [directionFilter, setDirectionFilter] = useState<string>('');
  const [methodFilter, setMethodFilter] = useState<string>('');

  const [summary, setSummary] = useState<PaymentAnalyticsSummaryResponse | null>(null);
  const [directionData, setDirectionData] = useState<PaymentAnalyticsByDirectionResponse | null>(null);
  const [methodData, setMethodData] = useState<PaymentAnalyticsByMethodResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');

  const fetchData = useCallback(async () => {
    if (!businessId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const params = {
        date_from: `${dateFrom}T00:00:00Z`,
        date_to: `${dateTo}T23:59:59Z`,
        ...(directionFilter ? { direction: directionFilter } : {}),
        ...(methodFilter ? { payment_method: methodFilter } : {}),
      };

      const [sumData, dirData, methData] = await Promise.all([
        apiClient.getPaymentAnalyticsSummary(businessId, params),
        apiClient.getPaymentAnalyticsByDirection(businessId, params),
        apiClient.getPaymentAnalyticsByMethod(businessId, params),
      ]);
      setSummary(sumData);
      setDirectionData(dirData);
      setMethodData(methData);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal memuat data analitik pembayaran.';
      setServerError(msg);
      setSummary(null);
      setDirectionData(null);
      setMethodData(null);
    } finally {
      setIsLoading(false);
    }
  }, [businessId, dateFrom, dateTo, directionFilter, methodFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-6">
          <nav className="flex text-sm text-slate-500 dark:text-slate-400 mb-1">
            <Link to={`/businesses/${businessId}`} className="hover:underline">Business</Link>
            <span className="mx-2">/</span>
            <Link to={`/businesses/${businessId}/payments`} className="hover:underline">Payments</Link>
            <span className="mx-2">/</span>
            <span className="text-slate-900 dark:text-slate-100 font-medium">Analytics</span>
          </nav>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Payment Analytics</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Analisis pembayaran berdasarkan periode, arah, dan metode.</p>
        </header>

        {/* Filters */}
        <Card className="mb-6">
          <div className="flex flex-col sm:flex-row flex-wrap gap-3">
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
            <div className="w-full sm:w-48">
              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Arah</label>
              <select value={directionFilter} onChange={(e) => setDirectionFilter(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm">
                <option value="">Semua Arah</option>
                <option value="CUSTOMER_IN">Customer In (Pemasukan)</option>
                <option value="SUPPLIER_OUT">Supplier Out (Pengeluaran)</option>
              </select>
            </div>
            <div className="w-full sm:w-48">
              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1">Metode</label>
              <select value={methodFilter} onChange={(e) => setMethodFilter(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm">
                <option value="">Semua Metode</option>
                <option value="CASH">Tunai</option>
                <option value="BANK_TRANSFER">Transfer Bank</option>
                <option value="DEBIT_CARD">Kartu Debit</option>
                <option value="CREDIT_CARD">Kartu Kredit</option>
                <option value="QRIS">QRIS</option>
                <option value="E_WALLET">E-Wallet</option>
                <option value="OTHER">Lainnya</option>
              </select>
            </div>
          </div>
        </Card>

        {serverError && <ErrorState message={serverError} onRetry={fetchData} />}

        {isLoading ? (
          <Card><div className="py-12 flex justify-center"><Loading text="Memuat analitik pembayaran..." /></div></Card>
        ) : summary && directionData && methodData ? (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <Card><div className="p-4">
                <span className="text-xs text-slate-500 block mb-1 uppercase">Rekam Pembayaran</span>
                <div className="text-xl font-bold text-emerald-600">Rp {fmt(summary.gross_recorded)}</div>
              </div></Card>
              <Card><div className="p-4">
                <span className="text-xs text-slate-500 block mb-1 uppercase">Pemasukan</span>
                <div className="text-xl font-bold text-emerald-600">Rp {fmt(summary.customer_in_total)}</div>
              </div></Card>
              <Card><div className="p-4">
                <span className="text-xs text-slate-500 block mb-1 uppercase">Pengeluaran</span>
                <div className="text-xl font-bold text-rose-600">Rp {fmt(summary.supplier_out_total)}</div>
              </div></Card>
              <Card><div className="p-4">
                <span className="text-xs text-slate-500 block mb-1 uppercase">Aliran Bersih</span>
                <div className="text-xl font-bold text-slate-900 dark:text-slate-100">Rp {fmt(summary.net_payment_flow)}</div>
              </div></Card>
              <Card><div className="p-4">
                <span className="text-xs text-slate-500 block mb-1 uppercase">Jumlah Transaksi</span>
                <div className="text-xl font-bold text-slate-900 dark:text-slate-100">{summary.payment_count}</div>
              </div></Card>
              <Card><div className="p-4">
                <span className="text-xs text-slate-500 block mb-1 uppercase">Rata-rata</span>
                <div className="text-xl font-bold text-indigo-600">Rp {fmt(summary.average_payment_value)}</div>
              </div></Card>
            </div>

            {/* Direction Breakdown */}
            <Card title="Breakdown Arah">
              {directionData.directions.length === 0 ? (
                <EmptyState title="Tidak ada data" description="Tidak ada pembayaran pada periode ini." />
              ) : (
                <div className="hidden md:block overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                        <th className="pb-3 pr-4 font-medium">Arah</th>
                        <th className="pb-3 pr-4 font-medium text-right">Jumlah Transaksi</th>
                        <th className="pb-3 font-medium text-right">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {directionData.directions.map((d) => (
                        <tr key={d.direction} className="border-b border-slate-100 dark:border-slate-800">
                          <td className="py-3 pr-4 font-medium text-slate-900 dark:text-slate-100">{d.direction === 'CUSTOMER_IN' ? 'Pemasukan (Customer In)' : 'Pengeluaran (Supplier Out)'}</td>
                          <td className="py-3 pr-4 text-right text-slate-600 dark:text-slate-300">{d.payment_count}</td>
                          <td className="py-3 text-right font-medium text-slate-900 dark:text-slate-100">Rp {fmt(d.amount)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            {/* Method Breakdown */}
            <Card title="Breakdown Metode Pembayaran">
              {methodData.methods.length === 0 ? (
                <EmptyState title="Tidak ada data" description="Tidak ada pembayaran pada periode ini." />
              ) : (
                <div className="hidden md:block overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                        <th className="pb-3 pr-4 font-medium">Metode</th>
                        <th className="pb-3 pr-4 font-medium text-right">Jumlah Transaksi</th>
                        <th className="pb-3 font-medium text-right">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {methodData.methods.map((m) => (
                        <tr key={m.payment_method} className="border-b border-slate-100 dark:border-slate-800">
                          <td className="py-3 pr-4 font-medium text-slate-900 dark:text-slate-100">{m.payment_method}</td>
                          <td className="py-3 pr-4 text-right text-slate-600 dark:text-slate-300">{m.payment_count}</td>
                          <td className="py-3 text-right font-medium text-slate-900 dark:text-slate-100">Rp {fmt(m.amount)}</td>
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

export default PaymentAnalytics;
