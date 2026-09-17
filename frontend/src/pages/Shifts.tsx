import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { Branch } from '@/types/branch';
import type { CashAccountResponse } from '@/types/cashAccount';
import type { CashierShift } from '@/types/shift';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { Loading } from '@/components/ui/Loading';

const STATUS_COLORS: Record<string, string> = {
  OPEN: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
  CLOSED: 'bg-slate-100 text-slate-500 border border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700',
};

export const Shifts: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();

  const [shifts, setShifts] = useState<CashierShift[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const pageSize = 20;

  const [branches, setBranches] = useState<Branch[]>([]);
  const [cashAccounts, setCashAccounts] = useState<CashAccountResponse[]>([]);

  const [statusFilter, setStatusFilter] = useState<string>('');

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');

  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string>('');

  const [createForm, setCreateForm] = useState({
    branch_id: '',
    cash_account_id: '',
    opening_balance: '',
    notes: '',
  });

  const fetchShifts = useCallback(async () => {
    if (!businessId) return;
    try {
      setIsLoading(true);
      setServerError('');
      const res = await apiClient.listShifts(businessId, {
        status: statusFilter || undefined,
        page,
        page_size: pageSize,
      });
      setShifts(res.items);
      setTotal(res.total);
    } catch (err: any) {
      const msg = err?.message || 'Failed to load shifts.';
      if (msg.toLowerCase().includes('unauthorized')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [businessId, statusFilter, page, navigate]);

  const fetchMeta = useCallback(async () => {
    if (!businessId) return;
    try {
      const [brData, caData] = await Promise.all([
        apiClient.listBranches(businessId),
        apiClient.listCashAccounts(businessId, { account_type: 'CASH', status: 'ACTIVE' }),
      ]);
      setBranches(brData || []);
      setCashAccounts(caData.items || []);
    } catch { /* ignore */ }
  }, [businessId]);

  useEffect(() => { fetchMeta(); }, [fetchMeta]);
  useEffect(() => { fetchShifts(); }, [fetchShifts]);

  const handleOpenShift = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      await apiClient.openShift(businessId, {
        branch_id: createForm.branch_id,
        cash_account_id: createForm.cash_account_id,
        opening_balance: parseFloat(createForm.opening_balance) || 0,
        notes: createForm.notes || undefined,
      });
      setIsModalOpen(false);
      setCreateForm({ branch_id: '', cash_account_id: '', opening_balance: '', notes: '' });
      setSuccessMsg('Shift opened successfully.');
      fetchShifts();
    } catch (err: any) {
      setFormError(err?.message || 'Failed to open shift.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? 'Rp 0' : `Rp ${num.toLocaleString('id-ID')}`;
  };

  const formatDate = (val: string | null) => {
    if (!val) return '-';
    return new Date(val).toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' });
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <nav className="flex text-sm text-slate-500 dark:text-slate-400 mb-1">
              <Link to={`/businesses/${businessId}`} className="hover:underline">
                Business Detail
              </Link>
              <span className="mx-2">/</span>
              <span className="text-slate-900 dark:text-slate-100 font-medium">Shifts</span>
            </nav>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Cashier Shifts</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Manage cashier shift sessions and cash drawer reconciliation.
            </p>
          </div>
          <Button onClick={() => { setIsModalOpen(true); setFormError(''); }}>
            Open New Shift
          </Button>
        </header>

        {successMsg && (
          <div className="mb-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900/50 p-3 text-emerald-800 dark:text-emerald-200 text-sm">
            {successMsg}
          </div>
        )}
        {serverError && (
          <div className="mb-4 rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 p-3 text-rose-800 dark:text-rose-200 text-sm">
            {serverError}
          </div>
        )}

        <Card className="mb-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="w-full sm:w-40">
              <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Status</label>
              <select
                value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Status</option>
                <option value="OPEN">Open</option>
                <option value="CLOSED">Closed</option>
              </select>
            </div>
          </div>
        </Card>

        {isLoading ? (
          <Card>
            <div className="py-12 flex justify-center">
              <Loading text="Loading shifts..." />
            </div>
          </Card>
        ) : shifts.length === 0 ? (
          <EmptyState
            title="No shifts found"
            description="Open a new shift to start tracking cash drawer movements."
          />
        ) : (
          <>
            <div className="space-y-3">
              {shifts.map((shift) => (
                <Link
                  key={shift.id}
                  to={`/businesses/${businessId}/shifts/${shift.id}`}
                  className="block"
                >
                  <Card className="hover:border-indigo-400 dark:hover:border-indigo-500 transition-colors">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[shift.status] || ''}`}>
                            {shift.status}
                          </span>
                          <span className="text-sm text-slate-500 dark:text-slate-400">
                            {shift.branch_name || shift.branch_id}
                          </span>
                        </div>
                        <div className="text-sm text-slate-700 dark:text-slate-300">
                          Cash Account: <span className="font-medium">{shift.cash_account_name || shift.cash_account_id}</span>
                          {shift.cashier_user_id && (
                            <span className="ml-3 text-slate-500 dark:text-slate-400">
                              Cashier: {shift.cashier_name || shift.cashier_user_id}
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                          Opened: {formatDate(shift.opened_at)}
                          {shift.closed_at && <> | Closed: {formatDate(shift.closed_at)}</>}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
                          Opening: {formatCurrency(shift.opening_balance)}
                        </div>
                        {shift.actual_cash_count != null && (
                          <div className="text-sm text-slate-600 dark:text-slate-400">
                            Actual: {formatCurrency(shift.actual_cash_count)}
                          </div>
                        )}
                        {shift.expected_cash != null && (
                          <div className="text-xs text-slate-500 dark:text-slate-400">
                            Expected: {formatCurrency(shift.expected_cash)}
                          </div>
                        )}
                        {shift.discrepancy != null && (
                          <div className={`text-xs font-medium ${parseFloat(String(shift.discrepancy)) === 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                            Discrepancy: {formatCurrency(shift.discrepancy)}
                          </div>
                        )}
                      </div>
                    </div>
                  </Card>
                </Link>
              ))}
            </div>

            <div className="mt-4 flex justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
              >
                Previous
              </Button>
              <span className="text-sm text-slate-500 dark:text-slate-400 px-3 py-1">
                Page {page} of {Math.ceil(total / pageSize)}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(page + 1)}
                disabled={page * pageSize >= total}
              >
                Next
              </Button>
            </div>
          </>
        )}

        {isModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Open New Shift</h2>
              {formError && (
                <div className="p-3 text-xs bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 rounded-lg border border-rose-200 dark:border-rose-900">
                  {formError}
                </div>
              )}
              <form onSubmit={handleOpenShift} className="space-y-4">
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="shift-branch" className="text-sm font-medium text-slate-700 dark:text-slate-300">Branch *</label>
                  <select
                    id="shift-branch"
                    required
                    value={createForm.branch_id}
                    onChange={(e) => setCreateForm({ ...createForm, branch_id: e.target.value })}
                    className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Select Branch</option>
                    {branches.map((b) => (
                      <option key={b.id} value={b.id}>{b.name}</option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="shift-cash-account" className="text-sm font-medium text-slate-700 dark:text-slate-300">Cash Account *</label>
                  <select
                    id="shift-cash-account"
                    required
                    value={createForm.cash_account_id}
                    onChange={(e) => setCreateForm({ ...createForm, cash_account_id: e.target.value })}
                    className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Select Cash Account</option>
                    {cashAccounts.map((a) => (
                      <option key={a.id} value={a.id}>{a.name} ({a.code})</option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="shift-opening-balance" className="text-sm font-medium text-slate-700 dark:text-slate-300">Opening Balance</label>
                  <input
                    id="shift-opening-balance"
                    type="number"
                    min="0"
                    step="0.01"
                    value={createForm.opening_balance}
                    onChange={(e) => setCreateForm({ ...createForm, opening_balance: e.target.value })}
                    placeholder="0"
                    className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="shift-notes" className="text-sm font-medium text-slate-700 dark:text-slate-300">Notes</label>
                  <textarea
                    id="shift-notes"
                    rows={3}
                    value={createForm.notes}
                    onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })}
                    className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Optional notes..."
                  />
                </div>
                <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-700">
                  <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" variant="primary" isLoading={isSubmitting}>
                    Open Shift
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Shifts;
