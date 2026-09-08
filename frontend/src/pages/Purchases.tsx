import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { BusinessMembership } from '@/types/businessMembership';
import type { Supplier } from '@/types/supplier';
import type { Branch } from '@/types/branch';
import type {
  PurchaseResponse,
  PurchaseCreateInput,
} from '@/types/purchase';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';

const STATUS_COLORS: Record<string, string> = {
  DRAFT: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800',
  FINALIZED: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
  CANCELLED: 'bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800',
};

const RECEIVING_STATUS_COLORS: Record<string, string> = {
  NOT_RECEIVED: 'bg-slate-50 text-slate-700 border border-slate-200 dark:bg-slate-900/40 dark:text-slate-400 dark:border-slate-800',
  PARTIALLY_RECEIVED: 'bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-950/40 dark:text-blue-400 dark:border-blue-800',
  FULLY_RECEIVED: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
};

export const Purchases: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [purchases, setPurchases] = useState<PurchaseResponse[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(20);

  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [supplierFilter, setSupplierFilter] = useState<string>('');
  const [branchFilter, setBranchFilter] = useState<string>('');
  const [receivingStatusFilter, setReceivingStatusFilter] = useState<string>('');

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string>('');

  const [createForm, setCreateForm] = useState<PurchaseCreateInput>({
    supplier_id: '',
    branch_id: '',
    purchase_date: new Date().toISOString().slice(0, 10),
    notes: '',
  });

  const canManage = myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN';

  const fetchPurchases = useCallback(async () => {
    if (!businessId) return;
    try {
      setIsLoading(true);
      setServerError('');
      const res = await apiClient.listPurchases(businessId, {
        search: searchQuery || undefined,
        status: statusFilter || undefined,
        supplier_id: supplierFilter || undefined,
        branch_id: branchFilter || undefined,
        receiving_status: receivingStatusFilter || undefined,
        page,
        page_size: pageSize,
      });
      setPurchases(res.items);
      setTotal(res.total);
    } catch (err: any) {
      const msg = err?.message || 'Gagal memuat pembelian.';
      if (msg.toLowerCase().includes('unauthorized')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [businessId, searchQuery, statusFilter, supplierFilter, branchFilter, receivingStatusFilter, page, pageSize, navigate]);

  const fetchMeta = useCallback(async () => {
    if (!businessId) return;
    try {
      const [supData, brData, membersData] = await Promise.all([
        apiClient.listSuppliers(businessId, { status: 'ACTIVE' }),
        apiClient.listBranches(businessId),
        apiClient.listBusinessMembers(businessId).catch(() => []),
      ]);
      setSuppliers(supData.items || []);
      setBranches(brData || []);
      if (user) {
        const mine = membersData.find((m: any) => m.user_id === user.id);
        setMyMembership(mine || null);
      }
    } catch { /* ignore */ }
  }, [businessId, user]);

  useEffect(() => { fetchMeta(); }, [fetchMeta]);
  useEffect(() => { fetchPurchases(); }, [fetchPurchases]);

  const handleCreatePurchase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      const payload: PurchaseCreateInput = {
        supplier_id: createForm.supplier_id,
        branch_id: createForm.branch_id,
        purchase_date: createForm.purchase_date,
        notes: createForm.notes?.trim() || undefined,
      };
      const created = await apiClient.createPurchase(businessId, payload);
      setIsCreateModalOpen(false);
      setSuccessMsg(`Pembelian ${created.purchase_number} berhasil dibuat.`);
      setTimeout(() => setSuccessMsg(''), 4000);
      navigate(`/businesses/${businessId}/purchases/${created.id}`);
    } catch (err: any) {
      setFormError(err?.message || 'Gagal membuat pembelian.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getSupplierName = (id: string) => suppliers.find(s => s.id === id)?.name || id;
  const getBranchName = (id: string) => branches.find(b => b.id === id)?.name || id;

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return num.toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  };

  if (isLoading && purchases.length === 0) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-900">
        <Loading size="lg" text="Memuat pembelian..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <Link
              to={`/businesses/${businessId}`}
              className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            >
              &larr; Kembali ke Bisnis
            </Link>
            <h1 className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-100">Pembelian</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">{total} transaksi</p>
          </div>
          {canManage && (
            <Button onClick={() => { setIsCreateModalOpen(true); setFormError(''); }}>
              + Pembelian Baru
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
                placeholder="Cari nomor / supplier..."
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
                value={supplierFilter}
                onChange={(e) => { setSupplierFilter(e.target.value); setPage(1); }}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Semua Supplier</option>
                {suppliers.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
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
            <div className="w-full sm:w-44">
              <select
                value={receivingStatusFilter}
                onChange={(e) => { setReceivingStatusFilter(e.target.value); setPage(1); }}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Semua Receiving</option>
                <option value="NOT_RECEIVED">Belum Diterima</option>
                <option value="PARTIALLY_RECEIVED">Sebagian Diterima</option>
                <option value="FULLY_RECEIVED">Sudah Diterima</option>
              </select>
            </div>
          </div>
        </Card>

        {purchases.length === 0 && !isLoading ? (
          <EmptyState
            title="Belum ada pembelian"
            description="Buat pembelian pertama Anda untuk mulai mencatat transaksi."
            action={canManage ? <Button onClick={() => setIsCreateModalOpen(true)}>+ Pembelian Baru</Button> : undefined}
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
                    <th className="pb-3 pr-4 font-medium">Supplier</th>
                    <th className="pb-3 pr-4 font-medium">Branch</th>
                    <th className="pb-3 pr-4 font-medium text-right">Grand Total</th>
                    <th className="pb-3 pr-4 font-medium">Status</th>
                    <th className="pb-3 font-medium">Receiving</th>
                  </tr>
                </thead>
                <tbody>
                  {purchases.map(p => (
                    <tr
                      key={p.id}
                      className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900/50 cursor-pointer"
                      onClick={() => navigate(`/businesses/${businessId}/purchases/${p.id}`)}
                    >
                      <td className="py-3 pr-4 font-medium text-indigo-600 dark:text-indigo-400">{p.purchase_number}</td>
                      <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{new Date(p.purchase_date).toLocaleDateString('id-ID')}</td>
                      <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{getSupplierName(p.supplier_id)}</td>
                      <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{getBranchName(p.branch_id)}</td>
                      <td className="py-3 pr-4 text-right font-medium text-slate-900 dark:text-slate-100">{formatCurrency(p.grand_total)}</td>
                      <td className="py-3 pr-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[p.status] || ''}`}>
                          {p.status}
                        </span>
                      </td>
                      <td className="py-3">
                        {p.receiving_summary && (
                          <div className="flex flex-col">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${RECEIVING_STATUS_COLORS[p.receiving_summary.status] || ''}`}>
                              {p.receiving_summary.status.replace('_', ' ')}
                            </span>
                            <span className="text-xs text-slate-400 mt-1">
                              {p.receiving_summary.total_received}/{p.receiving_summary.total_ordered}
                            </span>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="md:hidden space-y-3">
              {purchases.map(p => (
                <div
                  key={p.id}
                  className="cursor-pointer"
                  onClick={() => navigate(`/businesses/${businessId}/purchases/${p.id}`)}
                >
                  <Card className="hover:ring-2 hover:ring-indigo-500">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-medium text-indigo-600 dark:text-indigo-400">{p.purchase_number}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">{new Date(p.purchase_date).toLocaleDateString('id-ID')}</p>
                      </div>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[p.status] || ''}`}>
                        {p.status}
                      </span>
                    </div>
                    <div className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                      <p>{getSupplierName(p.supplier_id)} / {getBranchName(p.branch_id)}</p>
                      <p className="font-medium text-slate-900 dark:text-slate-100 mt-1">Rp {formatCurrency(p.grand_total)}</p>
                    </div>
                  </Card>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {total > pageSize && (
              <div className="mt-4 flex items-center justify-between text-sm">
                <span className="text-slate-500 dark:text-slate-400">
                  Menampilkan {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, total)} dari {total}
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage(p => p - 1)}
                  >
                    Sebelumnya
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page * pageSize >= total}
                    onClick={() => setPage(p => p + 1)}
                  >
                    Berikutnya
                  </Button>
                </div>
              </div>
            )}
          </>
        )}

        {/* Create Purchase Modal */}
        {isCreateModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4">
            <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-900 shadow-xl p-6 max-h-[90vh] overflow-y-auto">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Pembelian Baru</h2>
              {formError && <p className="mb-3 text-sm text-rose-600 dark:text-rose-400">{formError}</p>}
              <form onSubmit={handleCreatePurchase} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Supplier *</label>
                  <select
                    required
                    value={createForm.supplier_id}
                    onChange={(e) => setCreateForm(f => ({ ...f, supplier_id: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Pilih Supplier</option>
                    {suppliers.filter(s => s.status === 'ACTIVE').map(s => (
                      <option key={s.id} value={s.id}>{s.name}</option>
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
                <Input
                  id="purchase_date"
                  label="Tanggal Pembelian *"
                  type="date"
                  value={createForm.purchase_date}
                  onChange={(e) => setCreateForm(f => ({ ...f, purchase_date: e.target.value }))}
                />
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Catatan</label>
                  <textarea
                    rows={3}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500 resize-y"
                    value={createForm.notes || ''}
                    onChange={(e) => setCreateForm(f => ({ ...f, notes: e.target.value }))}
                  />
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="outline" type="button" onClick={() => setIsCreateModalOpen(false)} disabled={isSubmitting}>Batal</Button>
                  <Button type="submit" isLoading={isSubmitting} disabled={isSubmitting}>Buat</Button>
                </div>
              </form>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default Purchases;
