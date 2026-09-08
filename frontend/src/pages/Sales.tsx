import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { BusinessMembership } from '@/types/businessMembership';
import type { Customer } from '@/types/customer';
import type { Branch } from '@/types/branch';
import type {
  SalesResponse,
  SalesCreateInput,
} from '@/types/sales';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';

const STATUS_COLORS: Record<string, string> = {
  DRAFT: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800',
  FINALIZED: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
  CANCELLED: 'bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800',
};

export const Sales: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [salesList, setSalesList] = useState<SalesResponse[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(20);

  const [customers, setCustomers] = useState<Customer[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [customerFilter, setCustomerFilter] = useState<string>('');
  const [branchFilter, setBranchFilter] = useState<string>('');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [successMsg] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string>('');

  const [createForm, setCreateForm] = useState<SalesCreateInput>({
    customer_id: '',
    branch_id: '',
    sales_date: new Date().toISOString().slice(0, 10),
    notes: '',
  });

  const canManage = myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN';

  const fetchSales = useCallback(async () => {
    if (!businessId) return;
    try {
      setIsLoading(true);
      setServerError('');
      const res = await apiClient.listSales(businessId, {
        search: searchQuery || undefined,
        status: statusFilter || undefined,
        customer_id: customerFilter || undefined,
        branch_id: branchFilter || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        page,
        page_size: pageSize,
      });
      setSalesList(res.items);
      setTotal(res.total);
    } catch (err: any) {
      const msg = err?.message || 'Gagal memuat penjualan.';
      if (msg.toLowerCase().includes('unauthorized')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [businessId, searchQuery, statusFilter, customerFilter, branchFilter, dateFrom, dateTo, page, pageSize, navigate]);

  const fetchMeta = useCallback(async () => {
    if (!businessId) return;
    try {
      const [custData, brData, membersData] = await Promise.all([
        apiClient.listCustomers(businessId, { status: 'ACTIVE' }),
        apiClient.listBranches(businessId),
        apiClient.listBusinessMembers(businessId).catch(() => []),
      ]);
      setCustomers(custData.items || []);
      setBranches(brData || []);
      if (user) {
        const mine = membersData.find((m: any) => m.user_id === user.id);
        setMyMembership(mine || null);
      }
    } catch { /* ignore */ }
  }, [businessId, user]);

  useEffect(() => { fetchMeta(); }, [fetchMeta]);
  useEffect(() => { fetchSales(); }, [fetchSales]);

  const handleCreateSales = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      const payload: SalesCreateInput = {
        customer_id: createForm.customer_id ? createForm.customer_id : undefined,
        branch_id: createForm.branch_id,
        sales_date: createForm.sales_date,
        notes: createForm.notes?.trim() || undefined,
      };
      const created = await apiClient.createSales(businessId, payload);
      setIsCreateModalOpen(false);
      setCreateForm({
        customer_id: '',
        branch_id: '',
        sales_date: new Date().toISOString().slice(0, 10),
        notes: '',
      });
      navigate(`/businesses/${businessId}/sales/${created.id}`);
    } catch (err: any) {
      setFormError(err?.message || 'Gagal membuat draft penjualan.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getCustomerName = (id?: string | null) => {
    if (!id) return 'Walk-in / Umum';
    return customers.find(c => c.id === id)?.name || id;
  };

  const getBranchName = (id: string) => branches.find(b => b.id === id)?.name || id;

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
              <Link to={`/businesses/${businessId}`} className="hover:underline">
                Business Detail
              </Link>
              <span className="mx-2">/</span>
              <span className="text-slate-900 dark:text-slate-100 font-medium">Penjualan</span>
            </nav>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Penjualan (Sales)</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Kelola transaksi penjualan barang dan jasa.
            </p>
          </div>
          {canManage && (
            <Button onClick={() => { setIsCreateModalOpen(true); setFormError(''); }}>
              + Penjualan Baru
            </Button>
          )}
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
            <div className="flex-1">
              <Input
                id="search"
                placeholder="Cari nomor penjualan..."
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
              />
            </div>
            <div className="w-full sm:w-40">
              <select
                value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Semua Status</option>
                <option value="DRAFT">Draft</option>
                <option value="FINALIZED">Selesai</option>
                <option value="CANCELLED">Dibatalkan</option>
              </select>
            </div>
            <div className="w-full sm:w-48">
              <select
                value={customerFilter}
                onChange={(e) => { setCustomerFilter(e.target.value); setPage(1); }}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Semua Customer</option>
                {customers.map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div className="w-full sm:w-40">
              <select
                value={branchFilter}
                onChange={(e) => { setBranchFilter(e.target.value); setPage(1); }}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Semua Branch</option>
                {branches.map(b => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
            </div>
            <div className="w-full sm:w-36">
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
                placeholder="Dari Tanggal"
              />
            </div>
            <div className="w-full sm:w-36">
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
                placeholder="Sampai Tanggal"
              />
            </div>
          </div>
        </Card>

        {salesList.length === 0 && !isLoading ? (
          <EmptyState
            title="Belum ada transaksi penjualan"
            description="Buat penjualan pertama Anda untuk mulai mencatat transaksi."
            action={canManage ? <Button onClick={() => setIsCreateModalOpen(true)}>+ Penjualan Baru</Button> : undefined}
          />
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                    <th className="pb-3 pr-4 font-medium">Nomor</th>
                    <th className="pb-3 pr-4 font-medium">Tanggal</th>
                    <th className="pb-3 pr-4 font-medium">Customer</th>
                    <th className="pb-3 pr-4 font-medium">Branch</th>
                    <th className="pb-3 pr-4 font-medium text-right">Grand Total</th>
                    <th className="pb-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {salesList.map(s => (
                    <tr
                      key={s.id}
                      className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900/50 cursor-pointer"
                      onClick={() => navigate(`/businesses/${businessId}/sales/${s.id}`)}
                    >
                      <td className="py-3 pr-4 font-medium text-indigo-600 dark:text-indigo-400">{s.sales_number}</td>
                      <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{new Date(s.sales_date).toLocaleDateString('id-ID')}</td>
                      <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{getCustomerName(s.customer_id)}</td>
                      <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{getBranchName(s.branch_id)}</td>
                      <td className="py-3 pr-4 text-right font-medium text-slate-900 dark:text-slate-100">Rp {formatCurrency(s.grand_total)}</td>
                      <td className="py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[s.status] || ''}`}>
                          {s.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="md:hidden space-y-3">
              {salesList.map(s => (
                <div
                  key={s.id}
                  className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm hover:border-slate-300 cursor-pointer"
                  onClick={() => navigate(`/businesses/${businessId}/sales/${s.id}`)}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="font-semibold text-indigo-600 dark:text-indigo-400">{s.sales_number}</span>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        {new Date(s.sales_date).toLocaleDateString('id-ID')}
                      </p>
                    </div>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[s.status] || ''}`}>
                      {s.status}
                    </span>
                  </div>
                  <div className="mt-2 text-xs text-slate-600 dark:text-slate-300 space-y-1">
                    <p><span className="text-slate-400">Customer:</span> {getCustomerName(s.customer_id)}</p>
                    <p><span className="text-slate-400">Branch:</span> {getBranchName(s.branch_id)}</p>
                  </div>
                  <div className="mt-3 pt-2 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center text-sm">
                    <span className="text-slate-500">Total</span>
                    <span className="font-bold text-slate-900 dark:text-slate-100">Rp {formatCurrency(s.grand_total)}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {total > pageSize && (
              <div className="mt-6 flex items-center justify-between">
                <span className="text-sm text-slate-500 dark:text-slate-400">
                  Menampilkan {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)} dari {total}
                </span>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
                    Sebelumnya
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={page * pageSize >= total}>
                    Selanjutnya
                  </Button>
                </div>
              </div>
            )}
          </>
        )}

        {/* Modal Buat Penjualan Baru */}
        {isCreateModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4">
            <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-900 shadow-xl p-6">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Buat Draft Penjualan Baru</h2>
              {formError && (
                <div className="mb-4 rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 p-3 text-rose-800 dark:text-rose-200 text-sm">
                  {formError}
                </div>
              )}
              <form onSubmit={handleCreateSales} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Customer (Opsional / Walk-in)</label>
                  <select
                    value={createForm.customer_id || ''}
                    onChange={(e) => setCreateForm(f => ({ ...f, customer_id: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Walk-in / Umum</option>
                    {customers.filter(c => c.status === 'ACTIVE').map(c => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Branch *</label>
                  <select
                    required
                    value={createForm.branch_id}
                    onChange={(e) => setCreateForm(f => ({ ...f, branch_id: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Pilih Branch</option>
                    {branches.filter(b => b.status === 'ACTIVE').map(b => (
                      <option key={b.id} value={b.id}>{b.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="sales_date" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Tanggal Penjualan *</label>
                  <input
                    type="date"
                    id="sales_date"
                    required
                    value={createForm.sales_date.slice(0, 10)}
                    onChange={(e) => setCreateForm(f => ({ ...f, sales_date: new Date(e.target.value).toISOString() }))}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label htmlFor="notes" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Catatan</label>
                  <textarea
                    id="notes"
                    rows={3}
                    value={createForm.notes || ''}
                    onChange={(e) => setCreateForm(f => ({ ...f, notes: e.target.value }))}
                    placeholder="Catatan tambahan..."
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="outline" type="button" onClick={() => setIsCreateModalOpen(false)} disabled={isSubmitting}>
                    Batal
                  </Button>
                  <Button type="submit" isLoading={isSubmitting} disabled={isSubmitting}>
                    Simpan Draft
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
