import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { ExpenseResponse } from '@/types/expense';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/context/AuthContext';
import type { BusinessMembership } from '@/types/businessMembership';

const STATUS_COLORS: Record<string, string> = {
  DRAFT: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800',
  FINALIZED: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
  CANCELLED: 'bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800',
};

export const ExpenseDetail: React.FC = () => {
  const { businessId, expenseId } = useParams<{ businessId: string; expenseId: string }>();
  const { user } = useAuth();

  const [expense, setExpense] = useState<ExpenseResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);

  const [actionError, setActionError] = useState<string>('');
  const [confirmAction, setConfirmAction] = useState<'finalize' | 'cancel' | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const canManage = myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN';
  const isDraft = expense?.status === 'DRAFT';

  const fetchDetail = useCallback(async () => {
    if (!businessId || !expenseId) return;
    setIsLoading(true);
    try {
      const [expData, membersData] = await Promise.all([
        apiClient.getExpense(businessId, expenseId),
        apiClient.listBusinessMembers(businessId).catch(() => []),
      ]);
      setExpense(expData);
      if (user) {
        const mine = membersData.find((m: any) => m.user_id === user.id);
        setMyMembership(mine || null);
      }
    } catch (err: any) {
      setError(err?.message || 'Gagal memuat detail pengeluaran');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, expenseId, user]);

  useEffect(() => { fetchDetail(); }, [fetchDetail]);

  const handleFinalize = async () => {
    if (!businessId || !expenseId) return;
    setActionError('');
    setIsSubmitting(true);
    try {
      await apiClient.finalizeExpense(businessId, expenseId);
      fetchDetail();
      setConfirmAction(null);
    } catch (err: any) {
      setActionError(err?.message || 'Gagal finalisasi');
      setTimeout(() => setActionError(''), 5000);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async () => {
    if (!businessId || !expenseId) return;
    setActionError('');
    setIsSubmitting(true);
    try {
      await apiClient.cancelExpense(businessId, expenseId);
      fetchDetail();
      setConfirmAction(null);
    } catch (err: any) {
      setActionError(err?.message || 'Gagal membatalkan');
      setTimeout(() => setActionError(''), 5000);
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
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        <nav className="flex text-sm text-slate-500 dark:text-slate-400 mb-1">
          <Link to={`/businesses/${businessId}`} className="hover:underline">Business</Link>
          <span className="mx-2">/</span>
          <Link to={`/businesses/${businessId}/expenses`} className="hover:underline">Pengeluaran</Link>
          <span className="mx-2">/</span>
          <span className="text-slate-900 dark:text-slate-100 font-medium">Detail Pengeluaran</span>
        </nav>

        {isLoading ? (
          <div className="text-center py-10 text-slate-500">Memuat detail pengeluaran...</div>
        ) : error ? (
          <div className="rounded-lg bg-rose-50 dark:bg-rose-950/30 p-4 text-rose-800">{error}</div>
        ) : expense ? (
          <>
            <header className="mb-6 flex justify-between items-start">
              <div>
                <h1 className="text-2xl font-bold">{expense.expense_number}</h1>
                <p className="text-sm text-slate-500">{new Date(expense.expense_date).toLocaleDateString('id-ID')}</p>
              </div>
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[expense.status]}`}>{expense.status}</span>
            </header>

            {actionError && <div className="mb-4 rounded-lg bg-rose-50 border border-rose-200 p-3 text-rose-800 text-sm">{actionError}</div>}

            <Card className="mb-6">
              <div className="p-6 grid grid-cols-2 md:grid-cols-4 gap-6">
                <div><span className="text-xs text-slate-500 block mb-1">Kategori</span><span className="font-medium">{expense.category_name || '-'}</span></div>
                <div><span className="text-xs text-slate-500 block mb-1">Akun Kas</span><span className="font-medium">{expense.cash_account_name || '-'}</span></div>
                <div><span className="text-xs text-slate-500 block mb-1">Jumlah</span><span className="text-xl font-bold text-rose-600">Rp {formatCurrency(expense.amount)}</span></div>
                <div><span className="text-xs text-slate-500 block mb-1">Mata Uang</span><span className="font-medium">{expense.currency}</span></div>
              </div>
              <div className="p-6 grid grid-cols-2 md:grid-cols-4 gap-6 border-t border-slate-100 dark:border-slate-800">
                <div><span className="text-xs text-slate-500 block mb-1">Deskripsi</span><span className="font-medium">{expense.description || '-'}</span></div>
                <div><span className="text-xs text-slate-500 block mb-1">Dibuat Oleh</span><span className="font-medium text-xs">{expense.created_by_user_id}</span></div>
                <div><span className="text-xs text-slate-500 block mb-1">Finalized Pada</span><span className="font-medium text-xs">{expense.finalized_at ? new Date(expense.finalized_at).toLocaleString() : '-'}</span></div>
                <div><span className="text-xs text-slate-500 block mb-1">Dibatalkan Pada</span><span className="font-medium text-xs">{expense.cancelled_at ? new Date(expense.cancelled_at).toLocaleString() : '-'}</span></div>
              </div>
            </Card>

            <div className="flex gap-2 justify-end">
              {canManage && isDraft && <Button onClick={() => setConfirmAction('finalize')}>Finalisasi</Button>}
              {canManage && isDraft && <Button variant="outline" onClick={() => setConfirmAction('cancel')}>Batalkan</Button>}
              {canManage && expense.status === 'FINALIZED' && expense.cash_account_id && (
                <Link to={`/businesses/${businessId}/cash-accounts/${expense.cash_account_id}`}>
                  <Button variant="secondary">Lihat Akun Kas</Button>
                </Link>
              )}
            </div>

            {confirmAction === 'finalize' && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-xl shadow-xl p-6">
                  <h3 className="text-lg font-bold mb-2">Konfirmasi Finalisasi</h3>
                  <p className="text-slate-600 text-sm mb-4">Apakah Anda yakin ingin finalisasi pengeluaran ini?{expense.cash_account_id ? ' Saldo akun kas akan dikurangi.' : ''}</p>
                  {actionError && <div className="mb-3 text-rose-600 text-sm">{actionError}</div>}
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => { setConfirmAction(null); setActionError(''); }} disabled={isSubmitting}>Tidak</Button>
                    <Button onClick={handleFinalize} isLoading={isSubmitting} disabled={isSubmitting}>Ya, Finalisasi</Button>
                  </div>
                </div>
              </div>
            )}

            {confirmAction === 'cancel' && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-xl shadow-xl p-6">
                  <h3 className="text-lg font-bold mb-2">Konfirmasi Pembatalan</h3>
                  <p className="text-slate-600 text-sm mb-4">Apakah Anda yakin ingin membatalkan draft pengeluaran ini?</p>
                  {actionError && <div className="mb-3 text-rose-600 text-sm">{actionError}</div>}
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => { setConfirmAction(null); setActionError(''); }} disabled={isSubmitting}>Tidak</Button>
                    <Button variant="danger" onClick={handleCancel} isLoading={isSubmitting} disabled={isSubmitting}>Ya, Batalkan</Button>
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-10 text-slate-500">Pengeluaran tidak ditemukan.</div>
        )}
      </div>
    </div>
  );
};
