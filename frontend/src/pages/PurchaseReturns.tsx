import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { BusinessMembership } from '@/types/businessMembership';
import type { PurchaseResponse } from '@/types/purchase';
import type { InventoryLocation } from '@/types/warehouse';
import type {
  PurchaseReturnResponse,
  PurchaseReturnCreateInput,
} from '@/types/purchaseReturn';
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

export const PurchaseReturns: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [returns, setReturns] = useState<PurchaseReturnResponse[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(20);

  const [finalizedPurchases, setFinalizedPurchases] = useState<PurchaseResponse[]>([]);
  const [locations, setLocations] = useState<InventoryLocation[]>([]);
  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [purchaseFilter, setPurchaseFilter] = useState<string>('');
  const [locationFilter, setLocationFilter] = useState<string>('');

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');

  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string>('');

  const [createForm, setCreateForm] = useState<PurchaseReturnCreateInput>({
    purchase_id: '',
    inventory_location_id: '',
    notes: '',
  });

  const canManage = myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN';

  const fetchReturns = useCallback(async () => {
    if (!businessId) return;
    try {
      setIsLoading(true);
      setServerError('');
      const res = await apiClient.listPurchaseReturns(businessId, {
        search: searchQuery || undefined,
        status: statusFilter || undefined,
        purchase_id: purchaseFilter || undefined,
        inventory_location_id: locationFilter || undefined,
        page,
        page_size: pageSize,
      });
      setReturns(res.items);
      setTotal(res.total);
    } catch (err: any) {
      const msg = err?.message || 'Gagal memuat retur pembelian.';
      if (msg.toLowerCase().includes('unauthorized')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [businessId, searchQuery, statusFilter, purchaseFilter, locationFilter, page, pageSize, navigate]);

  const fetchMeta = useCallback(async () => {
    if (!businessId) return;
    try {
      const [purData, whData, membersData] = await Promise.all([
        apiClient.listPurchases(businessId, { status: 'FINALIZED' }),
        apiClient.listWarehouses(businessId).catch(() => []),
        apiClient.listBusinessMembers(businessId).catch(() => []),
      ]);
      setFinalizedPurchases(purData.items || []);
      if (user) {
        const mine = membersData.find((m: any) => m.user_id === user.id);
        setMyMembership(mine || null);
      }

      // Fetch active locations
      const locPromises = (whData || []).filter((w: any) => w.status === 'ACTIVE').map((w: any) =>
        apiClient.listWareLocations(businessId, w.id).catch(() => [])
      );
      const locResults = await Promise.all(locPromises);
      setLocations(locResults.flat().filter((l: any) => l.status === 'ACTIVE'));
    } catch { /* ignore */ }
  }, [businessId, user]);

  useEffect(() => { fetchMeta(); }, [fetchMeta]);
  useEffect(() => { fetchReturns(); }, [fetchReturns]);

  const handleCreateReturn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      const payload: PurchaseReturnCreateInput = {
        purchase_id: createForm.purchase_id,
        inventory_location_id: createForm.inventory_location_id,
        notes: createForm.notes?.trim() || undefined,
      };
      const created = await apiClient.createPurchaseReturn(businessId, payload);
      setIsCreateModalOpen(false);
      setSuccessMsg(`Retur ${created.return_number} berhasil dibuat.`);
      setTimeout(() => setSuccessMsg(''), 4000);
      navigate(`/businesses/${businessId}/purchase-returns/${created.id}`);
    } catch (err: any) {
      setFormError(err?.message || 'Gagal membuat retur pembelian.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getPurchaseNumber = (id: string) => {
    const p = finalizedPurchases.find(p => p.id === id);
    return p ? p.purchase_number : id;
  };
  const getLocationName = (id: string) => locations.find(l => l.id === id)?.name || id;

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return num.toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  };

  if (isLoading && returns.length === 0) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-900">
        <Loading size="lg" text="Memuat retur pembelian..." />
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
            <h1 className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-100">Retur Pembelian</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">{total} retur</p>
          </div>
          {canManage && (
            <Button onClick={() => { setIsCreateModalOpen(true); setFormError(''); }}>
              + Retur Baru
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
                placeholder="Cari nomor retur..."
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
                value={purchaseFilter}
                onChange={(e) => { setPurchaseFilter(e.target.value); setPage(1); }}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Semua Pembelian</option>
                {finalizedPurchases.map(p => (
                  <option key={p.id} value={p.id}>{p.purchase_number}</option>
                ))}
              </select>
            </div>
            <div className="w-full sm:w-48">
              <select
                value={locationFilter}
                onChange={(e) => { setLocationFilter(e.target.value); setPage(1); }}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Semua Lokasi</option>
                {locations.map(l => (
                  <option key={l.id} value={l.id}>{l.name}</option>
                ))}
              </select>
            </div>
          </div>
        </Card>

        {returns.length === 0 && !isLoading ? (
          <EmptyState
            title="Belum ada retur pembelian"
            description="Buat retur pembelian pertama dari Pembelian yang sudah memiliki Penerimaan Barang."
            action={canManage ? <Button onClick={() => setIsCreateModalOpen(true)}>+ Retur Baru</Button> : undefined}
          />
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                    <th className="pb-3 pr-4 font-medium">Nomor</th>
                    <th className="pb-3 pr-4 font-medium">Pembelian</th>
                    <th className="pb-3 pr-4 font-medium">Lokasi Asal</th>
                    <th className="pb-3 pr-4 font-medium text-right">Grand Total</th>
                    <th className="pb-3 pr-4 font-medium">Tanggal Dibuat</th>
                    <th className="pb-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {returns.map(r => (
                    <tr
                      key={r.id}
                      className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900/50 cursor-pointer"
                      onClick={() => navigate(`/businesses/${businessId}/purchase-returns/${r.id}`)}
                    >
                      <td className="py-3 pr-4 font-medium text-indigo-600 dark:text-indigo-400">{r.return_number}</td>
                      <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{getPurchaseNumber(r.purchase_id)}</td>
                      <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{getLocationName(r.inventory_location_id)}</td>
                      <td className="py-3 pr-4 text-right font-medium text-slate-900 dark:text-slate-100">Rp {formatCurrency(r.grand_total)}</td>
                      <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{new Date(r.created_at).toLocaleDateString('id-ID')}</td>
                      <td className="py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[r.status] || ''}`}>
                          {r.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="md:hidden space-y-3">
              {returns.map(r => (
                <div
                  key={r.id}
                  className="cursor-pointer"
                  onClick={() => navigate(`/businesses/${businessId}/purchase-returns/${r.id}`)}
                >
                  <Card className="hover:ring-2 hover:ring-indigo-500">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-medium text-indigo-600 dark:text-indigo-400">{r.return_number}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">{new Date(r.created_at).toLocaleDateString('id-ID')}</p>
                      </div>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[r.status] || ''}`}>
                        {r.status}
                      </span>
                    </div>
                    <div className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                      <p>PO: {getPurchaseNumber(r.purchase_id)}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Lokasi: {getLocationName(r.inventory_location_id)}</p>
                      <p className="font-medium text-slate-900 dark:text-slate-100 mt-1">Rp {formatCurrency(r.grand_total)}</p>
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

        {/* Create Return Modal */}
        {isCreateModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4">
            <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-900 shadow-xl p-6 max-h-[90vh] overflow-y-auto">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Retur Pembelian Baru</h2>
              {formError && <p className="mb-3 text-sm text-rose-600 dark:text-rose-400">{formError}</p>}
              <form onSubmit={handleCreateReturn} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Pembelian (PO) *</label>
                  <select
                    required
                    value={createForm.purchase_id}
                    onChange={(e) => setCreateForm(f => ({ ...f, purchase_id: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Pilih Pembelian Final</option>
                    {finalizedPurchases.map(p => (
                      <option key={p.id} value={p.id}>{p.purchase_number} - {new Date(p.purchase_date).toLocaleDateString('id-ID')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Lokasi Asal Retur *</label>
                  <select
                    required
                    value={createForm.inventory_location_id}
                    onChange={(e) => setCreateForm(f => ({ ...f, inventory_location_id: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Pilih Lokasi</option>
                    {locations.map(l => (
                      <option key={l.id} value={l.id}>{l.name} ({l.location_type})</option>
                    ))}
                  </select>
                </div>
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

export default PurchaseReturns;
