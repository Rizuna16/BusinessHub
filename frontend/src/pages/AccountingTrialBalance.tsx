import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { TrialBalanceResponse } from '@/types/accounting';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

export const AccountingTrialBalance: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();

  const [trialBalance, setTrialBalance] = useState<TrialBalanceResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');

  const fetchData = useCallback(async () => {
    if (!businessId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const data = await apiClient.getTrialBalance(businessId);
      setTrialBalance(data);
    } catch (err: any) {
      setServerError(err.message || 'Gagal memuat trial balance.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '0' : num.toLocaleString('id-ID');
  };

  if (isLoading) return <div className="p-6"><Loading /></div>;
  if (serverError || !trialBalance) return <div className="p-6"><ErrorState message={serverError || 'Data not found'} onRetry={fetchData} /></div>;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Trial Balance (Neraca Saldo)</h1>
        <Link to={`/businesses/${businessId}/accounting/journals`}>
          <Button variant="secondary">Kembali ke Jurnal</Button>
        </Link>
      </div>

      <Card>
        <div className="p-4 flex justify-between items-center border-b">
          <div className="flex gap-2">
            <span className="font-semibold">Total Debit: <span className="text-emerald-600">Rp {formatCurrency(trialBalance.total_debit)}</span></span>
            <span className="mx-2">|</span>
            <span className="font-semibold">Total Kredit: <span className="text-rose-600">Rp {formatCurrency(trialBalance.total_credit)}</span></span>
          </div>
          <div>
            {trialBalance.is_balanced ? (
              <span className="px-3 py-1 bg-emerald-100 text-emerald-800 rounded-full font-semibold">BALANCED</span>
            ) : (
              <span className="px-3 py-1 bg-rose-100 text-rose-800 rounded-full font-semibold">UNBALANCED</span>
            )}
          </div>
        </div>

        {trialBalance.items.length === 0 ? (
          <EmptyState title="Tidak ada data" description="Belum ada posting akuntansi." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase font-medium">
                <tr>
                  <th className="p-3">Kode</th>
                  <th className="p-3">Nama Akun</th>
                  <th className="p-3">Tipe</th>
                  <th className="p-3 text-right">Saldo Debit</th>
                  <th className="p-3 text-right">Saldo Kredit</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {trialBalance.items.map((item) => (
                  <tr key={item.account_id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                    <td className="p-3 font-mono font-medium">{item.account_code}</td>
                    <td className="p-3">{item.account_name}</td>
                    <td className="p-3">{item.account_type}</td>
                    <td className="p-3 text-right font-medium text-emerald-600">
                      {parseFloat(String(item.debit_balance)) > 0 ? `Rp ${formatCurrency(item.debit_balance)}` : '-'}
                    </td>
                    <td className="p-3 text-right font-medium text-rose-600">
                      {parseFloat(String(item.credit_balance)) > 0 ? `Rp ${formatCurrency(item.credit_balance)}` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};
