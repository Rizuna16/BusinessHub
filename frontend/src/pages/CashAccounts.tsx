import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { CashAccountResponse, CashAccountCreateInput, CashSummaryResponse } from '@/types/cashAccount';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';
import type { BusinessMembership } from '@/types/businessMembership';

const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  CASH: 'Kas',
  BANK: 'Bank',
  E_WALLET: 'E-Wallet',
  OTHER: 'Lainnya'
};

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
  INACTIVE: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800',
  ARCHIVED: 'bg-gray-100 text-gray-500 border border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700',
};

export const CashAccounts: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [accounts, setAccounts] = useState<CashAccountResponse[]>([]);
  const [summary, setSummary] = useState<CashSummaryResponse | null>(null);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [accountTypeFilter, setAccountTypeFilter] = useState<string>('');

  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string>('');

  const [createForm, setCreateForm] = useState<CashAccountCreateInput>({
    name: '',
    code: '',
    account_type: 'CASH',
    currency: 'IDR',
    opening_balance: 0,
    description: '',
  });

  const canManage = myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN';

  const fetchAccounts = useCallback(async () => {
    if (!businessId) return;
    try {
      const [accountsData, sumData, membersData] = await Promise.all([
        apiClient.listCashAccounts(businessId, {
          page,
          page_size: 20,
          search: searchQuery || undefined,
          account_type: accountTypeFilter || undefined,
        }),
        apiClient.getCashAccountsSummary(businessId),
        apiClient.listBusinessMembers(businessId).catch(() => []),
      ]);
      setAccounts(accountsData.items || []);
      setTotal(accountsData.total || 0);
      setSummary(sumData);
      if (user) {
        const mine = membersData.find((m: any) => m.user_id === user.id);
        setMyMembership(mine || null);
      }
    } catch (err: any) {
      console.error(err.message || 'Gagal memuat akun kas');
    }
  }, [businessId, page, searchQuery, accountTypeFilter, user]);

  useEffect(() => { fetchAccounts(); }, [fetchAccounts]);

  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      await apiClient.createCashAccount(businessId, createForm);
      setIsCreateModalOpen(false);
      setCreateForm({ name: '', code: '', account_type: 'CASH', currency: 'IDR', opening_balance: 0, description: '' });
      fetchAccounts();
    } catch (err: any) {
      setFormError(err?.message || 'Gagal membuat akun kas.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '0' : num.toLocaleString('id-ID');
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <nav className="flex text-sm text-slate-500 dark:text-slate-400 mb-1">
              <Link to={`/businesses/${businessId}`} className="hover:underline">Business Detail</Link>
              <span className="mx-2">/</span>
              <span className="text-slate-900 dark:text-slate-100 font-medium">Kas & Akun</span>
            </nav>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Kas & Akun (Cash Accounts)</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Kelola rekening operasional seperti kas, bank, dan e-wallet.
            </p>
          </div>
          {canManage && (
            <Button onClick={() => { setIsCreateModalOpen(true); setFormError(''); }}>+ Akun Baru</Button>
          )}
        </header>

        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <Card>
              <div className="p-4 space-y-1">
                <span className="text-xs text-slate-500 dark:text-slate-400 font-medium uppercase">Total Saldo (IDR)</span>
                <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">Rp {formatCurrency(summary.total_cash_balance)}</div>
              </div>
            </Card>
            <Card>
              <div className="p-4 space-y-1">
                <span className="text-xs text-slate-500 dark:text-slate-400 font-medium uppercase">Total Akun Aktif</span>
                <div className="text-2xl font-bold text-emerald-600">{summary.active_account_count}</div>
              </div>
            </Card>
            <Card>
              <div className="p-4 space-y-1">
                <span className="text-xs text-slate-500 dark:text-slate-400 font-medium uppercase">Total Akun Keseluruhan</span>
                <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">{summary.cash_account_count}</div>
              </div>
            </Card>
          </div>
        )}

        <Card className="mb-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <Input id="search" placeholder="Cari nama atau kode akun..." value={searchQuery} onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }} />
            </div>
            <div className="w-full sm:w-40">
              <select value={accountTypeFilter} onChange={(e) => { setAccountTypeFilter(e.target.value); setPage(1); }} className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm">
                <option value="">Semua Tipe</option>
                <option value="CASH">Kas</option>
                <option value="BANK">Bank</option>
                <option value="E_WALLET">E-Wallet</option>
                <option value="OTHER">Lainnya</option>
              </select>
            </div>
          </div>
        </Card>

        {accounts.length === 0 ? (
          <EmptyState title="Belum ada akun kas" description="Buat akun pertama untuk mulai mencatat transaksi kas." action={canManage ? <Button onClick={() => setIsCreateModalOpen(true)}>+ Akun Baru</Button> : undefined} />
        ) : (
          <>
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                    <th className="pb-3 pr-4 font-medium">Kode</th>
                    <th className="pb-3 pr-4 font-medium">Nama</th>
                    <th className="pb-3 pr-4 font-medium">Tipe</th>
                    <th className="pb-3 pr-4 font-medium">Mata Uang</th>
                    <th className="pb-3 pr-4 font-medium text-right">Saldo Saat Ini</th>
                    <th className="pb-3 pr-4 font-medium">Status</th>
                    <th className="pb-3 font-medium">Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {accounts.map(a => (
                    <tr key={a.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900/50 cursor-pointer" onClick={() => navigate(`/businesses/${businessId}/cash-accounts/${a.id}`)}>
                      <td className="py-3 pr-4 font-mono text-xs text-slate-500">{a.code}{a.is_default && <span className="ml-2 bg-indigo-100 text-indigo-800 px-1 py-0.5 rounded text-[10px]">DEFAULT</span>}</td>
                      <td className="py-3 pr-4 font-medium text-slate-900 dark:text-slate-100">{a.name}</td>
                      <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{ACCOUNT_TYPE_LABELS[a.account_type] || a.account_type}</td>
                      <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{a.currency}</td>
                      <td className="py-3 pr-4 text-right font-bold text-slate-900 dark:text-slate-100">
                        Rp {a.currency === 'IDR' ? formatCurrency(a.current_balance) : `${a.current_balance} ${a.currency}`}
                      </td>
                      <td className="py-3 pr-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[a.status] || ''}`}>{a.status}</span>
                      </td>
                      <td className="py-3 text-slate-500 dark:text-slate-400 text-right">
                        Lihat
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {total > 20 && (
              <div className="mt-6 flex items-center justify-between">
                <span className="text-sm text-slate-500">Total: {total}</span>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Sebelumnya</Button>
                  <span className="text-sm">Halaman {page}</span>
                  <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={accounts.length < 20}>Selanjutnya</Button>
                </div>
              </div>
            )}
          </>
        )}

        {/* Create Modal */}
        {isCreateModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4">
            <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-900 shadow-xl p-6">
              <h2 className="text-lg font-bold mb-4">Buat Akun Kas Baru</h2>
              {formError && <div className="mb-4 rounded-lg bg-rose-50 border border-rose-200 p-3 text-rose-800 text-sm">{formError}</div>}
              <form onSubmit={handleCreateAccount} className="space-y-4">
                <div><label className="block text-sm font-medium mb-1">Nama Akun *</label><Input required value={createForm.name} onChange={(e) => setCreateForm(f => ({ ...f, name: e.target.value }))} placeholder="Contoh: Kas Utama" /></div>
                <div><label className="block text-sm font-medium mb-1">Kode Akun *</label><Input required value={createForm.code} onChange={(e) => setCreateForm(f => ({ ...f, code: e.target.value }))} placeholder="Contoh: CASH-01" /></div>
                <div className="flex gap-4">
                  <div className="flex-1">
                    <label className="block text-sm font-medium mb-1">Tipe Akun *</label>
                    <select required value={createForm.account_type} onChange={(e) => setCreateForm(f => ({ ...f, account_type: e.target.value as any }))} className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm">
                      <option value="CASH">Kas</option>
                      <option value="BANK">Bank</option>
                      <option value="E_WALLET">E-Wallet</option>
                      <option value="OTHER">Lainnya</option>
                    </select>
                  </div>
                  <div className="flex-1"><label className="block text-sm font-medium mb-1">Mata Uang</label><Input value={createForm.currency || ''} onChange={(e) => setCreateForm(f => ({ ...f, currency: e.target.value.toUpperCase() }))} /></div>
                </div>
                <div><label className="block text-sm font-medium mb-1">Saldo Awal</label><Input type="number" min="0" value={createForm.opening_balance || ''} onChange={(e) => setCreateForm(f => ({ ...f, opening_balance: e.target.value }))} /></div>
                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="outline" type="button" onClick={() => setIsCreateModalOpen(false)} disabled={isSubmitting}>Batal</Button>
                  <Button type="submit" isLoading={isSubmitting} disabled={isSubmitting}>Simpan Akun</Button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
