import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { CashAccountResponse, CashMovementResponse, CashMovementCreateInput } from '@/types/cashAccount';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuth } from '@/context/AuthContext';
import type { BusinessMembership } from '@/types/businessMembership';

const MOVEMENT_TYPE_LABELS: Record<string, string> = {
  OPENING_BALANCE: 'Saldo Awal',
  CASH_IN: 'Kas Masuk',
  CASH_OUT: 'Kas Keluar',
  TRANSFER_IN: 'Transfer Masuk',
  TRANSFER_OUT: 'Transfer Keluar',
  SALES_PAYMENT: 'Pembayaran Penjualan',
};

const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  CASH: 'Kas',
  BANK: 'Bank',
  E_WALLET: 'E-Wallet',
  OTHER: 'Lainnya',
};

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: 'bg-emerald-50 text-emerald-700',
  INACTIVE: 'bg-amber-50 text-amber-700',
  ARCHIVED: 'bg-gray-100 text-gray-500',
};

export const CashAccountDetail: React.FC = () => {
  const { businessId, accountId } = useParams<{ businessId: string; accountId: string }>();
  const { user } = useAuth();

  const [account, setAccount] = useState<CashAccountResponse | null>(null);
  const [movements, setMovements] = useState<CashMovementResponse[]>([]);
  const [totalMovements, setTotalMovements] = useState<number>(0);
  const [page, setPage] = useState<number>(1);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);

  const [isMovementModalOpen, setIsMovementModalOpen] = useState<boolean>(false);
  const [movementForm, setMovementForm] = useState<CashMovementCreateInput>({ movement_type: 'CASH_IN', amount: 0, direction: 'IN', description: '' });
  const [movementError, setMovementError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const canManage = myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN';

  const fetchAccount = useCallback(async () => {
    if (!businessId || !accountId) return;
    setIsLoading(true);
    try {
      const [accData, movData, membersData] = await Promise.all([
        apiClient.getCashAccount(businessId, accountId),
        apiClient.listCashMovements(businessId, accountId, { page, page_size: 20 }),
        apiClient.listBusinessMembers(businessId).catch(() => []),
      ]);
      setAccount(accData);
      setMovements(movData.items || []);
      setTotalMovements(movData.total || 0);
      if (user) {
        const mine = membersData.find((m: any) => m.user_id === user.id);
        setMyMembership(mine || null);
      }
    } catch (err: any) {
      setError(err?.message || 'Gagal memuat detail akun kas');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, accountId, page, user]);

  useEffect(() => { fetchAccount(); }, [fetchAccount]);

  const handleCreateMovement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !accountId) return;
    setMovementError('');
    setIsSubmitting(true);
    try {
      await apiClient.createCashMovement(businessId, accountId, movementForm);
      setIsMovementModalOpen(false);
      setMovementForm({ movement_type: 'CASH_IN', amount: 0, direction: 'IN', description: '' });
      fetchAccount();
    } catch (err: any) {
      setMovementError(err?.message || 'Gagal mencatat transaksi');
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
          <Link to={`/businesses/${businessId}/cash-accounts`} className="hover:underline">Kas & Akun</Link>
          <span className="mx-2">/</span>
          <span className="text-slate-900 dark:text-slate-100 font-medium">Detail Akun</span>
        </nav>

        {isLoading ? (
          <div className="text-center py-10 text-slate-500">Memuat detail akun...</div>
        ) : error ? (
          <div className="rounded-lg bg-rose-50 dark:bg-rose-950/30 p-4 text-rose-800 dark:text-rose-200">{error}</div>
        ) : account ? (
          <>
            <header className="mb-6 flex justify-between items-start">
              <div>
                <h1 className="text-2xl font-bold">{account.name} <span className="text-sm font-normal text-slate-500">({account.code})</span></h1>
                <p className="text-sm text-slate-500">{ACCOUNT_TYPE_LABELS[account.account_type]}</p>
              </div>
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[account.status]}`}>{account.status}</span>
            </header>

            <Card className="mb-6">
              <div className="p-6 grid grid-cols-2 md:grid-cols-4 gap-6">
                <div><span className="text-xs text-slate-500 block mb-1">Saldo Saat Ini</span><span className="text-xl font-bold text-indigo-600">{account.currency === 'IDR' ? 'Rp' : account.currency} {formatCurrency(account.current_balance)}</span></div>
                <div><span className="text-xs text-slate-500 block mb-1">Saldo Awal</span><span className="font-medium">{account.currency === 'IDR' ? 'Rp' : account.currency} {formatCurrency(account.opening_balance)}</span></div>
                <div><span className="text-xs text-slate-500 block mb-1">Mata Uang</span><span className="font-medium">{account.currency}</span></div>
                <div><span className="text-xs text-slate-500 block mb-1">Default?</span><span className="font-medium">{account.is_default ? 'Ya' : 'Tidak'}</span></div>
              </div>
            </Card>

            <Card>
              <div className="p-6 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
                <h2 className="font-semibold text-lg">Riwayat Transaksi</h2>
                {canManage && account.status === 'ACTIVE' && (
                  <Button onClick={() => { setIsMovementModalOpen(true); setMovementError(''); }} size="sm">+ Transaksi Baru</Button>
                )}
              </div>
              {movements.length === 0 ? (
                <div className="p-8 text-center text-slate-500">Belum ada riwayat transaksi.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-slate-500 border-b border-slate-100 dark:border-slate-800">
                        <th className="px-6 py-3 font-medium">Tanggal</th>
                        <th className="px-6 py-3 font-medium">Tipe</th>
                        <th className="px-6 py-3 font-medium">Deskripsi</th>
                        <th className="px-6 py-3 font-medium text-right">Nominal</th>
                      </tr>
                    </thead>
                    <tbody>
                      {movements.map(m => (
                        <tr key={m.id} className="border-b border-slate-50 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-900/50">
                          <td className="px-6 py-4 text-slate-600">{new Date(m.created_at).toLocaleDateString('id-ID')}</td>
                          <td className="px-6 py-4">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${m.direction === 'IN' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>
                              {MOVEMENT_TYPE_LABELS[m.movement_type] || m.movement_type}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-slate-600">{m.description || '-'}</td>
                          <td className={`px-6 py-4 text-right font-bold ${m.direction === 'IN' ? 'text-emerald-600' : 'text-rose-600'}`}>
                            {m.direction === 'IN' ? '+' : '-'} Rp {formatCurrency(m.amount)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {totalMovements > 20 && (
                <div className="p-4 flex justify-between items-center border-t border-slate-200 dark:border-slate-700">
                  <span className="text-xs text-slate-500">Total: {totalMovements} transaksi</span>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Sebelumnya</Button>
                    <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={movements.length < 20}>Selanjutnya</Button>
                  </div>
                </div>
              )}
            </Card>

            {isMovementModalOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-xl shadow-xl p-6">
                  <h3 className="text-lg font-bold mb-4">Catat Transaksi Baru</h3>
                  {movementError && <div className="mb-4 bg-rose-50 border border-rose-200 p-3 text-rose-800 text-sm rounded">{movementError}</div>}
                  <form onSubmit={handleCreateMovement} className="space-y-4">
                    <div className="flex gap-4">
                      <div className="flex-1">
                        <label className="text-sm font-medium mb-1 block">Tipe Transaksi</label>
                        <select value={movementForm.movement_type} onChange={(e) => setMovementForm(f => ({ ...f, movement_type: e.target.value as any, direction: e.target.value.includes('IN') ? 'IN' : 'OUT' }))} className="w-full rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 text-sm">
                          <option value="CASH_IN">Kas Masuk</option>
                          <option value="CASH_OUT">Kas Keluar</option>
                        </select>
                      </div>
                    </div>
                    <div><label className="text-sm font-medium mb-1 block">Nominal *</label><Input type="number" min="1" required value={movementForm.amount || ''} onChange={(e) => setMovementForm(f => ({ ...f, amount: e.target.value }))} /></div>
                    <div><label className="text-sm font-medium mb-1 block">Deskripsi</label><Input value={movementForm.description || ''} onChange={(e) => setMovementForm(f => ({ ...f, description: e.target.value }))} /></div>
                    <div className="flex justify-end gap-2 pt-2">
                      <Button variant="outline" type="button" onClick={() => setIsMovementModalOpen(false)} disabled={isSubmitting}>Batal</Button>
                      <Button type="submit" isLoading={isSubmitting} disabled={isSubmitting}>Simpan</Button>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-10 text-slate-500">Akun kas tidak ditemukan.</div>
        )}
      </div>
    </div>
  );
};
