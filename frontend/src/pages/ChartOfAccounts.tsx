import React, { useState, useCallback, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { Account } from '@/types/accounting';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

export const ChartOfAccounts: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [newAccount, setNewAccount] = useState({ code: '', name: '', account_type: 'ASSET' });

  const fetchAccounts = useCallback(async () => {
    if (!businessId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const data = await apiClient.listAccounts(businessId);
      setAccounts(data.items || []);
    } catch (err: any) {
      setServerError(err.message || 'Gagal memuat chart of accounts.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId]);

  useEffect(() => { fetchAccounts(); }, [fetchAccounts]);

  const handleCreate = async () => {
    if (!businessId || !newAccount.code || !newAccount.name) return;
    setIsCreating(true);
    try {
      await apiClient.createAccount(businessId, newAccount);
      setNewAccount({ code: '', name: '', account_type: 'ASSET' });
      fetchAccounts();
    } catch (err: any) {
      alert('Gagal membuat akun: ' + (err.message || 'Unknown error'));
    } finally {
      setIsCreating(false);
    }
  };

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '0' : num.toLocaleString('id-ID');
  };

  if (isLoading) return <div className="p-6"><Loading /></div>;
  if (serverError) return <div className="p-6"><ErrorState message={serverError} onRetry={fetchAccounts} /></div>;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Chart of Accounts</h1>
        <Button onClick={() => fetchAccounts()} variant="secondary">Refresh</Button>
      </div>

      <Card>
        <div className="p-4 border-b flex justify-between items-center">
          <h2 className="font-semibold">Tambah Akun Baru</h2>
        </div>
        <div className="p-4 grid grid-cols-1 md:grid-cols-4 gap-4">
          <input
            type="text"
            placeholder="Kode Akun"
            value={newAccount.code}
            onChange={(e) => setNewAccount({ ...newAccount, code: e.target.value })}
            className="border p-2 rounded text-sm"
          />
          <input
            type="text"
            placeholder="Nama Akun"
            value={newAccount.name}
            onChange={(e) => setNewAccount({ ...newAccount, name: e.target.value })}
            className="border p-2 rounded text-sm"
          />
          <select
            value={newAccount.account_type}
            onChange={(e) => setNewAccount({ ...newAccount, account_type: e.target.value })}
            className="border p-2 rounded text-sm"
          >
            <option value="ASSET">Asset</option>
            <option value="LIABILITY">Liability</option>
            <option value="EQUITY">Equity</option>
            <option value="REVENUE">Revenue</option>
            <option value="EXPENSE">Expense</option>
          </select>
          <Button onClick={handleCreate} disabled={isCreating}>
            {isCreating ? 'Membuat...' : 'Simpan Akun'}
          </Button>
        </div>
      </Card>

      <Card>
        {accounts.length === 0 ? (
          <EmptyState title="Tidak ada akun" description="Belum ada data akun." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase font-medium">
                <tr>
                  <th className="p-3">Kode</th>
                  <th className="p-3">Nama</th>
                  <th className="p-3">Tipe</th>
                  <th className="p-3">Saldo Normal</th>
                  <th className="p-3 text-right">Saldo</th>
                  <th className="p-3">System</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {accounts.map((acc) => (
                  <tr key={acc.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                    <td className="p-3 font-mono font-medium">{acc.code}</td>
                    <td className="p-3">{acc.name}</td>
                    <td className="p-3">{acc.account_type}</td>
                    <td className="p-3">{acc.normal_balance}</td>
                    <td className={`p-3 text-right font-bold ${parseFloat(String(acc.current_balance)) >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                      Rp {formatCurrency(acc.current_balance)}
                    </td>
                    <td className="p-3">
                      {acc.is_system ? (
                        <span className="px-2 py-0.5 bg-indigo-100 text-indigo-800 text-xs rounded">System</span>
                      ) : ''}
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
