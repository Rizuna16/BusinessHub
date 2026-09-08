import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { BalanceSheetResponse, AccountingPeriod } from '@/types/accounting';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

export const AccountingBalanceSheet: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();

  const [periods, setPeriods] = useState<AccountingPeriod[]>([]);
  const [selectedPeriodId, setSelectedPeriodId] = useState<string>('');
  const [report, setReport] = useState<BalanceSheetResponse | null>(null);
  const [isLoadingPeriods, setIsLoadingPeriods] = useState<boolean>(true);
  const [isLoadingReport, setIsLoadingReport] = useState<boolean>(false);
  const [serverError, setServerError] = useState<string>('');

  const fetchPeriods = useCallback(async () => {
    if (!businessId) return;
    setIsLoadingPeriods(true);
    setServerError('');
    try {
      const data = await apiClient.listPeriods(businessId);
      const items = data.items || [];
      setPeriods(items);
      if (items.length > 0) {
        setSelectedPeriodId(items[0].id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal memuat periode akuntansi.';
      setServerError(msg);
    } finally {
      setIsLoadingPeriods(false);
    }
  }, [businessId]);

  useEffect(() => {
    fetchPeriods();
  }, [fetchPeriods]);

  const fetchReport = useCallback(async () => {
    if (!businessId || !selectedPeriodId) return;
    setIsLoadingReport(true);
    setServerError('');
    try {
      const data = await apiClient.getBalanceSheet(businessId, selectedPeriodId);
      setReport(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal memuat Neraca Saldo (Balance Sheet).';
      setServerError(msg);
    } finally {
      setIsLoadingReport(false);
    }
  }, [businessId, selectedPeriodId]);

  useEffect(() => {
    if (selectedPeriodId) {
      fetchReport();
    }
  }, [selectedPeriodId, fetchReport]);

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '0' : num.toLocaleString('id-ID');
  };

  if (isLoadingPeriods) {
    return (
      <div className="p-6 max-w-5xl mx-auto flex justify-center">
        <Loading text="Memuat periode akuntansi..." />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
            <Link to={`/businesses/${businessId}`} className="hover:text-blue-500">
              Bisnis
            </Link>
            <span>/</span>
            <span>Akuntansi</span>
            <span>/</span>
            <span className="text-slate-900 dark:text-slate-100 font-medium">Neraca</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Laporan Neraca (Balance Sheet)
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Posisi Aset, Kewajiban, dan Ekuitas kumulatif s/d tanggal penutupan periode.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link to={`/businesses/${businessId}/accounting/reports/profit-and-loss`}>
            <Button variant="outline" size="sm">
              Laba Rugi (P&L)
            </Button>
          </Link>
          <Link to={`/businesses/${businessId}/accounting/periods`}>
            <Button variant="outline" size="sm">
              Periode Fiskal
            </Button>
          </Link>
        </div>
      </div>

      {/* Period Selector */}
      {periods.length > 0 && (
        <Card className="p-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <label htmlFor="period-select" className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Pilih Periode:
              </label>
              <select
                id="period-select"
                value={selectedPeriodId}
                onChange={(e) => setSelectedPeriodId(e.target.value)}
                className="px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {periods.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.period_name} (s/d {p.end_date}) [{p.status}]
                  </option>
                ))}
              </select>
            </div>

            {report && (
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
                  Per Tanggal: {report.as_of_date}
                </span>
                <Badge
                  variant={report.is_balanced ? 'success' : 'error'}
                  size="sm"
                >
                  {report.is_balanced ? 'BALANCED' : 'UNBALANCED'}
                </Badge>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Error state */}
      {serverError && (
        <ErrorState message={serverError} onRetry={fetchReport} />
      )}

      {/* Loading Report state */}
      {isLoadingReport ? (
        <Card>
          <div className="py-12 flex justify-center">
            <Loading text="Memuat laporan neraca..." />
          </div>
        </Card>
      ) : periods.length === 0 ? (
        <EmptyState
          title="Belum ada periode akuntansi"
          description="Buat periode akuntansi terlebih dahulu untuk melihat laporan neraca."
          action={
            <Link to={`/businesses/${businessId}/accounting/periods`}>
              <Button>Buat Periode Akuntansi</Button>
            </Link>
          }
        />
      ) : report ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column: Assets */}
          <div className="space-y-6">
            <Card title="ASET (Assets)">
              {report.asset_items.length === 0 ? (
                <p className="text-xs text-slate-400 italic py-2">Tidak ada saldo aset.</p>
              ) : (
                <div className="divide-y divide-slate-100 dark:divide-slate-800">
                  {report.asset_items.map((item) => (
                    <div key={item.account_id} className="py-2.5 flex justify-between items-center text-sm">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-slate-400">{item.account_code}</span>
                        <span className="font-medium text-slate-900 dark:text-slate-100">{item.account_name}</span>
                      </div>
                      <span className="font-mono font-medium text-emerald-600 dark:text-emerald-400">
                        Rp {formatCurrency(item.balance)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
              <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700 flex justify-between items-center font-bold text-sm">
                <span className="text-slate-700 dark:text-slate-300">TOTAL ASET</span>
                <span className="font-mono text-emerald-600 dark:text-emerald-400 text-base">
                  Rp {formatCurrency(report.total_assets)}
                </span>
              </div>
            </Card>
          </div>

          {/* Right Column: Liabilities & Equity */}
          <div className="space-y-6">
            <Card title="KEWAJIBAN (Liabilities)">
              {report.liability_items.length === 0 ? (
                <p className="text-xs text-slate-400 italic py-2">Tidak ada saldo kewajiban.</p>
              ) : (
                <div className="divide-y divide-slate-100 dark:divide-slate-800">
                  {report.liability_items.map((item) => (
                    <div key={item.account_id} className="py-2.5 flex justify-between items-center text-sm">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-slate-400">{item.account_code}</span>
                        <span className="font-medium text-slate-900 dark:text-slate-100">{item.account_name}</span>
                      </div>
                      <span className="font-mono font-medium text-amber-600 dark:text-amber-400">
                        Rp {formatCurrency(item.balance)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
              <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700 flex justify-between items-center font-bold text-sm">
                <span className="text-slate-700 dark:text-slate-300">Total Kewajiban</span>
                <span className="font-mono text-amber-600 dark:text-amber-400">
                  Rp {formatCurrency(report.total_liabilities)}
                </span>
              </div>
            </Card>

            <Card title="EKUITAS (Equity)">
              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {report.equity_items.map((item) => (
                  <div key={item.account_id} className="py-2.5 flex justify-between items-center text-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-slate-400">{item.account_code}</span>
                      <span className="font-medium text-slate-900 dark:text-slate-100">{item.account_name}</span>
                    </div>
                    <span className="font-mono font-medium text-indigo-600 dark:text-indigo-400">
                      Rp {formatCurrency(item.balance)}
                    </span>
                  </div>
                ))}

                {/* Current Period Profit line */}
                <div className="py-2.5 flex justify-between items-center text-sm bg-blue-50/50 dark:bg-blue-950/20 px-2 rounded-lg my-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-blue-500 font-bold">★</span>
                    <span className="font-semibold text-blue-700 dark:text-blue-300">Laba Bersih (Periode Berjalan)</span>
                  </div>
                  <span className={`font-mono font-bold ${parseFloat(String(report.net_profit_current_period)) >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                    Rp {formatCurrency(report.net_profit_current_period)}
                  </span>
                </div>
              </div>

              <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700 flex justify-between items-center font-bold text-sm">
                <span className="text-slate-700 dark:text-slate-300">Total Ekuitas (+ Laba Berjalan)</span>
                <span className="font-mono text-indigo-600 dark:text-indigo-400">
                  Rp {formatCurrency(parseFloat(String(report.total_equity)) + parseFloat(String(report.net_profit_current_period)))}
                </span>
              </div>
            </Card>

            {/* Total Liabilities + Equity Summary */}
            <Card className="bg-slate-900 text-white dark:bg-slate-900 border-slate-800">
              <div className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold">TOTAL KEWAJIBAN + EKUITAS</span>
                  <p className="text-xs text-slate-400 mt-0.5">Harus seimbang dengan Total Aset ({report.is_balanced ? 'Balanced' : 'Unbalanced'})</p>
                </div>
                <div className="text-right">
                  <span className={`text-xl font-extrabold font-mono ${report.is_balanced ? 'text-emerald-400' : 'text-rose-400'}`}>
                    Rp {formatCurrency(report.total_liabilities_and_equity)}
                  </span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default AccountingBalanceSheet;
