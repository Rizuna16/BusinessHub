import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { APAgingResponse, AgingBucket, APInvoiceAgingItem, APSupplierAgingSummaryItem } from '@/types/aging';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

const BUCKET_LABELS: Record<AgingBucket, string> = {
  CURRENT: 'Current',
  '1_30': '1–30 days',
  '31_60': '31–60 days',
  '61_90': '61–90 days',
  '91_120': '91–120 days',
  OVER_120: '>120 days',
};

const BUCKET_KEYS: AgingBucket[] = ['CURRENT', '1_30', '31_60', '61_90', '91_120', 'OVER_120'];

const BUCKET_COLORS: Record<AgingBucket, string> = {
  CURRENT: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  '1_30': 'bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400',
  '31_60': 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  '61_90': 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  '91_120': 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400',
  OVER_120: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

type Tab = 'summary' | 'purchases';

export const APAging: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const [asOfDate, setAsOfDate] = useState<string>(() => {
    const d = new Date();
    return d.toISOString().slice(0, 10);
  });
  const [bucketFilter, setBucketFilter] = useState<string>('');
  const [activeTab, setActiveTab] = useState<Tab>('summary');
  const [data, setData] = useState<APAgingResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');

  const fetchData = useCallback(async () => {
    if (!businessId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const result = await apiClient.getAPAging(businessId, {
        as_of_date: asOfDate ? `${asOfDate}T23:59:59` : undefined,
        bucket: bucketFilter || undefined,
      });
      setData(result);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Gagal memuat data aging hutang.';
      setServerError(message);
    } finally {
      setIsLoading(false);
    }
  }, [businessId, asOfDate, bucketFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '0' : num.toLocaleString('id-ID');
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">AP Aging Report (Hutang Aging)</h1>
        <Link to={`/businesses/${businessId}/purchases/payables`}>
          <Button variant="secondary">Back to Payables</Button>
        </Link>
      </div>

      <Card>
        <div className="p-4 flex flex-col md:flex-row gap-4 items-center">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-500 uppercase">As of Date</label>
            <input
              type="date"
              value={asOfDate}
              onChange={(e) => setAsOfDate(e.target.value)}
              className="border rounded px-3 py-1.5 text-sm dark:bg-gray-800 dark:border-gray-700"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-gray-500 uppercase">Aging Bucket</label>
            <select
              value={bucketFilter}
              onChange={(e) => setBucketFilter(e.target.value)}
              className="border rounded px-3 py-1.5 text-sm dark:bg-gray-800 dark:border-gray-700"
            >
              <option value="">All Buckets</option>
              {BUCKET_KEYS.map((k) => (
                <option key={k} value={k}>{BUCKET_LABELS[k]}</option>
              ))}
            </select>
          </div>
          <Button onClick={fetchData} className="mt-4 md:mt-5">Refresh</Button>
        </div>
      </Card>

      {isLoading ? (
        <Loading />
      ) : serverError ? (
        <ErrorState message={serverError} />
      ) : !data || (data.summary.total_outstanding === 0 || data.summary.total_outstanding === '0') ? (
        <EmptyState title="No outstanding AP" description="No outstanding payables for the selected period." />
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {BUCKET_KEYS.map((k) => {
              const val = data.summary[k === 'CURRENT' ? 'current' : `bucket_${k}` as keyof typeof data.summary];
              return (
                <Card key={k}>
                  <div className="space-y-1">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded ${BUCKET_COLORS[k]}`}>
                      {BUCKET_LABELS[k]}
                    </span>
                    <div className="text-lg font-bold">Rp {formatCurrency(val)}</div>
                  </div>
                </Card>
              );
            })}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <Card>
              <div className="space-y-1">
                <span className="text-xs text-gray-500 font-medium uppercase">Total Outstanding</span>
                <div className="text-2xl font-bold text-rose-600">Rp {formatCurrency(data.summary.total_outstanding)}</div>
              </div>
            </Card>
            <Card>
              <div className="space-y-1">
                <span className="text-xs text-gray-500 font-medium uppercase">Total Gross Payable</span>
                <div className="text-2xl font-bold">Rp {formatCurrency(data.summary.total_gross)}</div>
              </div>
            </Card>
            <Card>
              <div className="space-y-1">
                <span className="text-xs text-gray-500 font-medium uppercase">Total Paid</span>
                <div className="text-2xl font-bold text-emerald-600">Rp {formatCurrency(data.summary.total_paid)}</div>
              </div>
            </Card>
          </div>

          <div className="flex gap-2 border-b">
            <button
              className={`pb-2 px-4 font-medium ${activeTab === 'summary' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'}`}
              onClick={() => setActiveTab('summary')}
            >
              By Supplier
            </button>
            <button
              className={`pb-2 px-4 font-medium ${activeTab === 'purchases' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'}`}
              onClick={() => setActiveTab('purchases')}
            >
              Purchase Detail
            </button>
          </div>

          {activeTab === 'summary' ? (
            <Card>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase font-medium">
                    <tr>
                      <th className="p-3">Supplier</th>
                      <th className="p-3 text-center">Purchases</th>
                      <th className="p-3 text-right">Outstanding</th>
                      <th className="p-3 text-right">Current</th>
                      <th className="p-3 text-right">1–30</th>
                      <th className="p-3 text-right">31–60</th>
                      <th className="p-3 text-right">61–90</th>
                      <th className="p-3 text-right">91–120</th>
                      <th className="p-3 text-right">&gt;120</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {data.suppliers.map((s: APSupplierAgingSummaryItem) => (
                      <tr key={s.supplier_id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                        <td className="p-3 font-medium">{s.supplier_name || 'Tanpa Supplier'}</td>
                        <td className="p-3 text-center">{s.purchase_count}</td>
                        <td className="p-3 text-right font-bold text-rose-600">Rp {formatCurrency(s.total_outstanding)}</td>
                        <td className="p-3 text-right">Rp {formatCurrency(s.current)}</td>
                        <td className="p-3 text-right">Rp {formatCurrency(s.bucket_1_30)}</td>
                        <td className="p-3 text-right">Rp {formatCurrency(s.bucket_31_60)}</td>
                        <td className="p-3 text-right">Rp {formatCurrency(s.bucket_61_90)}</td>
                        <td className="p-3 text-right">Rp {formatCurrency(s.bucket_91_120)}</td>
                        <td className="p-3 text-right">Rp {formatCurrency(s.bucket_over_120)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          ) : (
            <Card>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase font-medium">
                    <tr>
                      <th className="p-3">No. Purchase</th>
                      <th className="p-3">Date</th>
                      <th className="p-3">Supplier</th>
                      <th className="p-3 text-right">Gross Total</th>
                      <th className="p-3 text-right">Return Adj</th>
                      <th className="p-3 text-right">Paid</th>
                      <th className="p-3 text-right">Outstanding</th>
                      <th className="p-3 text-center">Days</th>
                      <th className="p-3 text-center">Bucket</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {data.purchases.map((pur: APInvoiceAgingItem) => (
                      <tr key={pur.purchase_id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                        <td className="p-3 font-mono font-medium">{pur.purchase_number}</td>
                        <td className="p-3">{new Date(pur.purchase_date).toLocaleDateString('id-ID')}</td>
                        <td className="p-3">{pur.supplier_name || '-'}</td>
                        <td className="p-3 text-right">Rp {formatCurrency(pur.gross_payable)}</td>
                        <td className="p-3 text-right text-amber-600">
                          {parseFloat(String(pur.return_adjustment)) > 0 ? `Rp ${formatCurrency(pur.return_adjustment)}` : '-'}
                        </td>
                        <td className="p-3 text-right text-emerald-600 font-medium">Rp {formatCurrency(pur.paid_amount)}</td>
                        <td className="p-3 text-right font-bold text-rose-600">Rp {formatCurrency(pur.outstanding_amount)}</td>
                        <td className="p-3 text-center font-mono">{pur.aging_days}</td>
                        <td className="p-3 text-center">
                          <span className={`px-2 py-1 text-xs rounded-full font-semibold ${BUCKET_COLORS[pur.aging_bucket]}`}>
                            {BUCKET_LABELS[pur.aging_bucket]}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
};
