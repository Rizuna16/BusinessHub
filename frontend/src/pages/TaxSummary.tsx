import React, { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';

interface TaxSummaryData {
  year: number;
  month: number;
  output_vat: number | string;
  input_vat: number | string;
  net_vat: number | string;
  taxable_sales_count: number;
  taxable_purchase_count: number;
}

export const TaxSummary: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();

  const [summary, setSummary] = useState<TaxSummaryData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);

  const months = [
    'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
    'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
  ];

  const fetchSummary = useCallback(async () => {
    if (!businessId) return;
    setIsLoading(true);
    setError('');
    try {
      const data = await apiClient.getTaxSummary(businessId, selectedYear, selectedMonth);
      setSummary(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal memuat ringkasan pajak.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [businessId, selectedYear, selectedMonth]);

  useEffect(() => { fetchSummary(); }, [fetchSummary]);

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? 'Rp 0' : `Rp ${num.toLocaleString('id-ID')}`;
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">
            <span onClick={() => navigate(-1)} className="hover:underline cursor-pointer">Kembali</span> / Laporan Pajak
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Ringkasan PPN</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Ringkasan PPN bulanan berdasarkan jurnal akuntansi yang sudah diposting.
          </p>
        </div>
      </div>

      {/* Period Selector */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-4 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex-1">
            <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Tahun</label>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
              className="mt-1 block w-full px-3 py-2 text-sm bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {[2024, 2025, 2026, 2027].map(y => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Bulan</label>
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(Number(e.target.value))}
              className="mt-1 block w-full px-3 py-2 text-sm bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {months.map((m, i) => (
                <option key={i + 1} value={i + 1}>{m} ({i + 1})</option>
              ))}
            </select>
          </div>
          <div className="flex-shrink-0 self-end">
            <button
              onClick={fetchSummary}
              disabled={isLoading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Memuat...' : 'Tampilkan'}
            </button>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-lg p-4 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-12 flex items-center justify-center">
          <div className="text-slate-500 dark:text-slate-400">Memuat ringkasan pajak...</div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && summary && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Output VAT */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-4 shadow-sm">
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">PPN Keluaran (Output VAT)</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2 font-mono">{formatCurrency(summary.output_vat)}</p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">Penjualan Kena Pajak: {summary.taxable_sales_count}</p>
            </div>

            {/* Input VAT */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-4 shadow-sm">
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">PPN Masukan (Input VAT)</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2 font-mono">{formatCurrency(summary.input_vat)}</p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">Pembelian Kena Pajak: {summary.taxable_purchase_count}</p>
            </div>

            {/* Net VAT */}
            <div className={`rounded-lg p-4 shadow-sm border ${parseFloat(String(summary.net_vat)) >= 0 ? 'bg-slate-900 border-blue-800' : 'bg-rose-950/40 border-rose-800'}`}>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">PPN Net (Hutang/Ditagih)</p>
              <p className={`text-2xl font-bold mt-2 font-mono ${parseFloat(String(summary.net_vat)) >= 0 ? 'text-blue-400' : 'text-rose-400'}`}>
                {formatCurrency(summary.net_vat)}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                {parseFloat(String(summary.net_vat)) >= 0 ? 'Masih harus dibayar' : 'Kelebihan kredit'}
              </p>
            </div>

            {/* Summary Info */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-4 shadow-sm">
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Ringkasan Bulanan</p>
              <p className="text-sm text-slate-900 dark:text-slate-100 mt-2">
                {months[selectedMonth - 1]} {selectedYear}
              </p>
              <div className="space-y-1 mt-3">
                <p className="text-xs text-slate-400">Transaksi Penjualan: {summary.taxable_sales_count}</p>
                <p className="text-xs text-slate-400">Transaksi Pembelian: {summary.taxable_purchase_count}</p>
              </div>
            </div>
          </div>

          {/* Detail Table */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-sm overflow-hidden">
            <div className="p-4 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Detail Ringkasan PPN</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 dark:bg-slate-800/50 text-xs text-slate-500 dark:text-slate-400 uppercase">
                  <tr>
                    <th className="text-left px-4 py-3 font-semibold">Deskripsi</th>
                    <th className="text-right px-4 py-3 font-semibold">Jumlah</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  <tr>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">PPN Keluaran</td>
                    <td className="px-4 py-3 text-right font-mono text-blue-600 dark:text-blue-400">{formatCurrency(summary.output_vat)}</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">PPN Masukan</td>
                    <td className="px-4 py-3 text-right font-mono text-rose-600 dark:text-rose-400">{formatCurrency(summary.input_vat)}</td>
                  </tr>
                  <tr className="border-t border-slate-200 dark:border-slate-700">
                    <td className="px-4 py-3 text-sm font-semibold text-slate-900 dark:text-slate-100">PPN Net (Hutang/Ditagih)</td>
                    <td className={`px-4 py-3 text-right font-mono font-bold ${parseFloat(String(summary.net_vat)) >= 0 ? 'text-blue-600 dark:text-blue-400' : 'text-rose-600 dark:text-rose-400'}`}>
                      {formatCurrency(summary.net_vat)}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Empty State */}
      {!isLoading && summary && summary.taxable_sales_count === 0 && summary.taxable_purchase_count === 0 && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-8 text-center">
          <p className="text-slate-500 dark:text-slate-400">Belum ada transaksi kena pajak pada periode ini.</p>
          <Link
            to={`/businesses/${businessId}/accounting/journals`}
            className="mt-2 inline-block text-sm text-blue-600 hover:underline"
          >
            Lihat Jurnal Akuntansi
          </Link>
        </div>
      )}
    </div>
  );
};
