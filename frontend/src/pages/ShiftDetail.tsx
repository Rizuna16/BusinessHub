import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { BusinessMembership } from '@/types/businessMembership';
import type { CashierShift } from '@/types/shift';
import type { CashMovementResponse } from '@/types/cashAccount';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { useAuth } from '@/context/AuthContext';

const STATUS_COLORS: Record<string, string> = {
  OPEN: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
  CLOSED: 'bg-slate-100 text-slate-500 border border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700',
};

const MOVEMENT_TYPE_LABELS: Record<string, string> = {
  SALES_PAYMENT: 'Sales Payment',
  EXPENSE: 'Expense',
  TRANSFER_IN: 'Transfer In',
  TRANSFER_OUT: 'Transfer Out',
  CASH_IN: 'Cash In',
  CASH_OUT: 'Cash Out',
  OPENING_BALANCE: 'Opening Balance',
};

export const ShiftDetail: React.FC = () => {
  const { businessId, shiftId } = useParams<{ businessId: string; shiftId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [shift, setShift] = useState<CashierShift | null>(null);
  const [transactions, setTransactions] = useState<CashMovementResponse[]>([]);
  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');

  // Close form state
  const [isCloseModalOpen, setIsCloseModalOpen] = useState<boolean>(false);
  const [isClosing, setIsClosing] = useState<boolean>(false);
  const [closeError, setCloseError] = useState<string>('');
  const [actualCashCount, setActualCashCount] = useState<string>('');
  const [closeNotes, setCloseNotes] = useState<string>('');

  // Force close form state
  const [isForceCloseModalOpen, setIsForceCloseModalOpen] = useState<boolean>(false);
  const [isForceClosing, setIsForceClosing] = useState<boolean>(false);
  const [forceCloseError, setForceCloseError] = useState<string>('');
  const [forceCloseNotes, setForceCloseNotes] = useState<string>('');

  const canForceClose = myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN';

  const fetchShift = useCallback(async () => {
    if (!businessId || !shiftId) return;
    try {
      setIsLoading(true);
      setServerError('');
      const data = await apiClient.getShift(businessId, shiftId);
      setShift(data);
    } catch (err: any) {
      const msg = err?.message || 'Failed to load shift.';
      if (msg.toLowerCase().includes('unauthorized')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [businessId, shiftId, navigate]);

  const fetchTransactions = useCallback(async () => {
    if (!businessId || !shiftId) return;
    try {
      const res = await apiClient.getShiftTransactions(businessId, shiftId, { page_size: 100 });
      setTransactions(res.items || []);
    } catch { /* ignore */ }
  }, [businessId, shiftId]);

  const fetchMembership = useCallback(async () => {
    if (!businessId) return;
    try {
      const members = await apiClient.listBusinessMembers(businessId).catch(() => []);
      if (user) {
        const mine = members.find((m: any) => m.user_id === user.id);
        setMyMembership(mine || null);
      }
    } catch { /* ignore */ }
  }, [businessId, user]);

  useEffect(() => { fetchShift(); fetchTransactions(); fetchMembership(); }, [fetchShift, fetchTransactions, fetchMembership]);

  const handleClose = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !shiftId) return;
    setCloseError('');
    setIsClosing(true);
    try {
      await apiClient.closeShift(businessId, shiftId, {
        actual_cash_count: parseFloat(actualCashCount),
        notes: closeNotes || undefined,
      });
      setIsCloseModalOpen(false);
      setSuccessMsg('Shift closed successfully.');
      setActualCashCount('');
      setCloseNotes('');
      fetchShift();
      fetchTransactions();
    } catch (err: any) {
      setCloseError(err?.message || 'Failed to close shift.');
    } finally {
      setIsClosing(false);
    }
  };

  const handleForceClose = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !shiftId) return;
    setForceCloseError('');
    setIsForceClosing(true);
    try {
      await apiClient.forceCloseShift(businessId, shiftId, {
        notes: forceCloseNotes,
      });
      setIsForceCloseModalOpen(false);
      setSuccessMsg('Shift force-closed successfully.');
      setForceCloseNotes('');
      fetchShift();
      fetchTransactions();
    } catch (err: any) {
      setForceCloseError(err?.message || 'Failed to force-close shift.');
    } finally {
      setIsForceClosing(false);
    }
  };

  const formatCurrency = (val: number | string | null | undefined) => {
    if (val == null) return '-';
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '-' : `Rp ${num.toLocaleString('id-ID')}`;
  };

  const formatDate = (val: string | null) => {
    if (!val) return '-';
    return new Date(val).toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center">
        <Loading text="Loading shift details..." />
      </div>
    );
  }

  if (!shift) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <p className="text-slate-500 dark:text-slate-400">Shift not found.</p>
          <Button className="mt-4" onClick={() => navigate(`/businesses/${businessId}/shifts`)}>
            Back to Shifts
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-6">
          <nav className="flex text-sm text-slate-500 dark:text-slate-400 mb-1">
            <Link to={`/businesses/${businessId}`} className="hover:underline">Business Detail</Link>
            <span className="mx-2">/</span>
            <Link to={`/businesses/${businessId}/shifts`} className="hover:underline">Shifts</Link>
            <span className="mx-2">/</span>
            <span className="text-slate-900 dark:text-slate-100 font-medium">Shift Detail</span>
          </nav>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Shift Detail</h1>
            {shift.status === 'OPEN' && (
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setIsCloseModalOpen(true)}>
                  Close Shift
                </Button>
                {canForceClose && (
                  <Button variant="danger" onClick={() => setIsForceCloseModalOpen(true)}>
                    Force Close
                  </Button>
                )}
              </div>
            )}
          </div>
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

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <Card title="Shift Information">
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Status</span>
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[shift.status] || ''}`}>
                  {shift.status}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Branch</span>
                <span className="font-medium">{shift.branch_name || shift.branch_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Cash Account</span>
                <span className="font-medium">{shift.cash_account_name || shift.cash_account_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Cashier</span>
                <span className="font-medium">{shift.cashier_name || shift.cashier_user_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Opened At</span>
                <span>{formatDate(shift.opened_at)}</span>
              </div>
              {shift.closed_at && (
                <div className="flex justify-between">
                  <span className="text-slate-500 dark:text-slate-400">Closed At</span>
                  <span>{formatDate(shift.closed_at)}</span>
                </div>
              )}
              {shift.closed_by_user_id && (
                <div className="flex justify-between">
                  <span className="text-slate-500 dark:text-slate-400">Closed By</span>
                  <span>{shift.closed_by_user_id}</span>
                </div>
              )}
              {shift.notes && (
                <div className="flex justify-between">
                  <span className="text-slate-500 dark:text-slate-400">Notes</span>
                  <span>{shift.notes}</span>
                </div>
              )}
            </div>
          </Card>

          <Card title="Reconciliation">
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Opening Balance</span>
                <span className="font-medium">{formatCurrency(shift.opening_balance)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Expected Cash</span>
                <span className="font-medium">{formatCurrency(shift.expected_cash)}</span>
              </div>
              {shift.actual_cash_count != null && (
                <div className="flex justify-between">
                  <span className="text-slate-500 dark:text-slate-400">Actual Cash Count</span>
                  <span className="font-medium">{formatCurrency(shift.actual_cash_count)}</span>
                </div>
              )}
              {shift.discrepancy != null && (
                <div className="flex justify-between">
                  <span className="text-slate-500 dark:text-slate-400">Discrepancy</span>
                  <span className={`font-medium ${parseFloat(String(shift.discrepancy)) === 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                    {formatCurrency(shift.discrepancy)}
                    {parseFloat(String(shift.discrepancy)) === 0 && ' (Balanced)'}
                    {parseFloat(String(shift.discrepancy)) > 0 && ' (Overage)'}
                    {parseFloat(String(shift.discrepancy)) < 0 && ' (Shortage)'}
                  </span>
                </div>
              )}
            </div>
          </Card>
        </div>

        <Card title="Transactions">
          {transactions.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-4">
              No transactions attributed to this shift.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    <th className="text-left py-2 px-3 text-slate-500 dark:text-slate-400 font-medium">Date</th>
                    <th className="text-left py-2 px-3 text-slate-500 dark:text-slate-400 font-medium">Type</th>
                    <th className="text-left py-2 px-3 text-slate-500 dark:text-slate-400 font-medium">Direction</th>
                    <th className="text-right py-2 px-3 text-slate-500 dark:text-slate-400 font-medium">Amount</th>
                    <th className="text-left py-2 px-3 text-slate-500 dark:text-slate-400 font-medium">Description</th>
                    <th className="text-left py-2 px-3 text-slate-500 dark:text-slate-400 font-medium">User</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((t) => (
                    <tr key={t.id} className="border-b border-slate-100 dark:border-slate-800">
                      <td className="py-2 px-3 text-slate-700 dark:text-slate-300">{formatDate(t.created_at)}</td>
                      <td className="py-2 px-3 text-slate-700 dark:text-slate-300">{MOVEMENT_TYPE_LABELS[t.movement_type] || t.movement_type}</td>
                      <td className="py-2 px-3">
                        <span className={t.direction === 'IN' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}>
                          {t.direction === 'IN' ? 'IN' : 'OUT'}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-right font-medium">{formatCurrency(t.amount)}</td>
                      <td className="py-2 px-3 text-slate-500 dark:text-slate-400 max-w-[200px] truncate">{t.description || '-'}</td>
                      <td className="py-2 px-3 text-slate-500 dark:text-slate-400">{t.performed_by_user_id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Close Shift Modal */}
        {isCloseModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Close Shift</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Enter the physical cash count from the drawer.
              </p>
              {closeError && (
                <div className="p-3 text-xs bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 rounded-lg border border-rose-200 dark:border-rose-900">
                  {closeError}
                </div>
              )}
              <div className="p-3 bg-slate-50 dark:bg-slate-900 rounded-lg text-sm">
                <span className="text-slate-500 dark:text-slate-400">Expected Cash: </span>
                <span className="font-bold">{formatCurrency(shift.expected_cash)}</span>
              </div>
              <form onSubmit={handleClose} className="space-y-4">
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="actual-cash-count" className="text-sm font-medium text-slate-700 dark:text-slate-300">Actual Cash Count *</label>
                  <input
                    id="actual-cash-count"
                    type="number"
                    min="0"
                    step="0.01"
                    required
                    value={actualCashCount}
                    onChange={(e) => setActualCashCount(e.target.value)}
                    className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Enter physical cash count"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="close-notes" className="text-sm font-medium text-slate-700 dark:text-slate-300">Notes</label>
                  <textarea
                    id="close-notes"
                    rows={3}
                    value={closeNotes}
                    onChange={(e) => setCloseNotes(e.target.value)}
                    className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Optional notes..."
                  />
                </div>
                <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-700">
                  <Button type="button" variant="outline" onClick={() => setIsCloseModalOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" variant="primary" isLoading={isClosing}>
                    Close Shift
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Force Close Modal */}
        {isForceCloseModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4">
              <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Force Close Shift</h2>
              <p className="text-sm text-rose-600 dark:text-rose-400">
                This will close the shift without recording an actual cash count.
              </p>
              {forceCloseError && (
                <div className="p-3 text-xs bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 rounded-lg border border-rose-200 dark:border-rose-900">
                  {forceCloseError}
                </div>
              )}
              <form onSubmit={handleForceClose} className="space-y-4">
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="force-close-notes" className="text-sm font-medium text-slate-700 dark:text-slate-300">Reason *</label>
                  <textarea
                    id="force-close-notes"
                    rows={3}
                    required
                    value={forceCloseNotes}
                    onChange={(e) => setForceCloseNotes(e.target.value)}
                    className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Enter reason for force close..."
                  />
                </div>
                <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-700">
                  <Button type="button" variant="outline" onClick={() => setIsForceCloseModalOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" variant="danger" isLoading={isForceClosing}>
                    Force Close
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

export default ShiftDetail;
