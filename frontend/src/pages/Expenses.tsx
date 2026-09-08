import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { ExpenseResponse, ExpenseCategoryResponse, ExpenseSummaryResponse, ExpenseCreateInput } from '@/types/expense';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';
import type { BusinessMembership } from '@/types/businessMembership';
import type { CashAccountResponse } from '@/types/cashAccount';

const STATUS_COLORS: Record<string, string> = {
  DRAFT: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800',
  FINALIZED: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
  CANCELLED: 'bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800',
};

export const Expenses: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [expenses, setExpenses] = useState<ExpenseResponse[]>([]);
  const [summary, setSummary] = useState<ExpenseSummaryResponse | null>(null);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');

  const [categories, setCategories] = useState<ExpenseCategoryResponse[]>([]);
  const [cashAccounts, setCashAccounts] = useState<CashAccountResponse[]>([]);
  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string>('');

  const [createForm, setCreateForm] = useState<ExpenseCreateInput>({
    category_id: '',
    expense_date: new Date().toISOString().slice(0, 10),
    amount: 0,
    currency: 'IDR',
    description: '',
  });

  const canManage = myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN';

  const fetchData = useCallback(async () => {
    if (!businessId) return;
    try {
      const [expData, sumData, catData, accData, membersData] = await Promise.all([
        apiClient.listExpenses(businessId, { page, page_size: 20, search: searchQuery || undefined, status: statusFilter || undefined, category_id: categoryFilter || undefined }),
        apiClient.getExpenseSummary(businessId),
        apiClient.listExpenseCategories(businessId, { status: 'ACTIVE' }).catch(() => ({ items: [] })),
        apiClient.listCashAccounts(businessId, { status: 'ACTIVE' }).catch(() => ({ items: [] })),
        apiClient.listBusinessMembers(businessId).catch(() => []),
      ]);
      setExpenses(expData.items || []);
      setTotal(expData.total || 0);
      setSummary(sumData);
      setCategories(catData.items || []);
      setCashAccounts(accData.items || []);
      if (user) {
        const mine = membersData.find((m: any) => m.user_id === user.id);
        setMyMembership(mine || null);
      }
    } catch (err: any) {
      console.error(err.message || 'Gagal memuat data pengeluaran');
    }
  }, [businessId, page, searchQuery, statusFilter, categoryFilter, user]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      const created = await apiClient.createExpense(businessId, createForm);
      setIsCreateModalOpen(false);
      navigate(`/businesses/${businessId}/expenses/${created.id}`);
    } catch (err: any) {
      setFormError(err?.message || 'Gagal membuat pengeluaran');
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
              <span className="text-slate-900 dark:text-slate-100 font-medium">Pengeluaran</span>
            </nav>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Pengeluaran (Expenses)</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Catat dan lacak semua pengeluaran operasional bisnis Anda.</p>
          </div>
          {canManage && <Button onClick={() => { setIsCreateModalOpen(true); setFormError(''); }}>+ Pengeluaran Baru</Button>}
        </header>

        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <Card><div className="p-4"><span className="text-xs text-slate-500 block mb-1 uppercase">Total Pengeluaran (IDR)</span><div className="text-xl font-bold text-rose-600">Rp {formatCurrency(summary.total_expense_amount)}</div></div></Card>
            <Card><div className="p-4"><span className="text-xs text-slate-500 block mb-1 uppercase">Total Dokumen</span><div className="text-xl font-bold text-slate-900 dark:text-slate-100">{summary.expense_count}</div></div></Card>
            <Card><div className="p-4"><span className="text-xs text-slate-500 block mb-1 uppercase">Finalized / Draft</span><div className="text-xl font-bold text-emerald-600">{summary.finalized_count} <span className="text-slate-400 text-sm">/ {summary.draft_count}</span></div></div></Card>
          </div>
        )}

        <Card className="mb-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <Input id="search" placeholder="Cari nomor atau deskripsi..." value={searchQuery} onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }} />
            </div>
            <div className="w-full sm:w-40">
              <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }} className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm">
                <option value="">Semua Status</option>
                <option value="DRAFT">Draft</option>
                <option value="FINALIZED">Finalized</option>
                <option value="CANCELLED">Dibatalkan</option>
              </select>
            </div>
            <div className="w-full sm:w-48">
              <select value={categoryFilter} onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }} className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm">
                <option value="">Semua Kategori</option>
                {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
          </div>
        </Card>

        {expenses.length === 0 ? (
          <EmptyState title="Belum ada pengeluaran" description="Mulai catat pengeluaran pertama Anda." action={canManage ? <Button onClick={() => setIsCreateModalOpen(true)}>+ Pengeluaran Baru</Button> : undefined} />
        ) : (
          <>
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                    <th className="pb-3 pr-4 font-medium">Nomor</th>
                    <th className="pb-3 pr-4 font-medium">Tanggal</th>
                    <th className="pb-3 pr-4 font-medium">Kategori</th>
                    <th className="pb-3 pr-4 font-medium text-right">Jumlah</th>
                    <th className="pb-3 pr-4 font-medium">Status</th>
                    <th className="pb-3 font-medium">Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {expenses.map(e => (
                    <tr key={e.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900/50 cursor-pointer" onClick={() => navigate(`/businesses/${businessId}/expenses/${e.id}`)}>
                      <td className="py-3 pr-4 font-medium text-indigo-600 dark:text-indigo-400">{e.expense_number}</td>
                      <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{new Date(e.expense_date).toLocaleDateString('id-ID')}</td>
                      <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{e.category_name || '-'}</td>
                      <td className="py-3 pr-4 text-right font-medium text-slate-900 dark:text-slate-100">Rp {formatCurrency(e.amount)}</td>
                      <td className="py-3 pr-4"><span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[e.status]}`}>{e.status}</span></td>
                      <td className="py-3 text-slate-500 text-right">Lihat</td>
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
                  <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={expenses.length < 20}>Selanjutnya</Button>
                </div>
              </div>
            )}
          </>
        )}

        {isCreateModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="w-full max-w-lg bg-white dark:bg-slate-900 rounded-xl shadow-xl p-6">
              <h2 className="text-lg font-bold mb-4">Buat Pengeluaran Baru</h2>
              {formError && <div className="mb-4 bg-rose-50 border border-rose-200 p-3 text-rose-800 text-sm rounded">{formError}</div>}
              <form onSubmit={handleCreate} className="space-y-4">
                <div><label className="text-sm font-medium mb-1 block">Tanggal *</label><Input type="date" required value={createForm.expense_date} onChange={(e) => setCreateForm(f => ({ ...f, expense_date: e.target.value }))} /></div>
                <div>
                  <label className="text-sm font-medium mb-1 block">Kategori *</label>
                  <select required value={createForm.category_id} onChange={(e) => setCreateForm(f => ({ ...f, category_id: e.target.value }))} className="w-full rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 text-sm">
                    <option value="">Pilih Kategori</option>
                    {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <div><label className="text-sm font-medium mb-1 block">Jumlah (IDR) *</label><Input type="number" min="1" required value={createForm.amount || ''} onChange={(e) => setCreateForm(f => ({ ...f, amount: e.target.value }))} /></div>
                <div>
                  <label className="text-sm font-medium mb-1 block">Akun Kas (Opsional)</label>
                  <select value={createForm.cash_account_id || ''} onChange={(e) => setCreateForm(f => ({ ...f, cash_account_id: e.target.value || undefined }))} className="w-full rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 text-sm">
                    <option value="">Tanpa Akun Kas (Akan Ditangguhkan)</option>
                    {cashAccounts.map(a => <option key={a.id} value={a.id}>{a.name} ({a.code}) - Rp {formatCurrency(a.current_balance)}</option>)}
                  </select>
                </div>
                <div><label className="text-sm font-medium mb-1 block">Deskripsi</label><Input value={createForm.description || ''} onChange={(e) => setCreateForm(f => ({ ...f, description: e.target.value }))} /></div>
                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="outline" type="button" onClick={() => setIsCreateModalOpen(false)} disabled={isSubmitting}>Batal</Button>
                  <Button type="submit" isLoading={isSubmitting} disabled={isSubmitting}>Simpan Pengeluaran</Button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
