import React, { useState, useCallback, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { Business } from '@/types/business';
import type { BusinessMembership } from '@/types/businessMembership';
import type { InventoryLocation } from '@/types/warehouse';
import type { Product, ProductVariant } from '@/types/product';
import type {
  StockOpname,
  StockOpnameCreatePayload,
  StockOpnameLineCreatePayload,
} from '@/types/stockOpname';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';

export const StockOpnamePage: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const { user } = useAuth();

  const [business, setBusiness] = useState<Business | null>(null);
  const [opnames, setOpnames] = useState<StockOpname[]>([]);
  const [selectedOpname, setSelectedOpname] = useState<StockOpname | null>(null);
  const [allLocations, setAllLocations] = useState<InventoryLocation[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [variants, setVariants] = useState<ProductVariant[]>([]);
  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');
  const [actionError, setActionError] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  // Modals & form state
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [isAddLineModalOpen, setIsAddLineModalOpen] = useState<boolean>(false);
  const [isFinalizeModalOpen, setIsFinalizeModalOpen] = useState<boolean>(false);
  const [editingLineId, setEditingLineId] = useState<string | null>(null);
  const [countInput, setCountInput] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string>('');

  const [createForm, setCreateForm] = useState<StockOpnameCreatePayload>({
    inventory_location_id: '',
    notes: '',
  });

  const [lineForm, setLineForm] = useState<StockOpnameLineCreatePayload>({
    product_id: '',
    variant_id: null,
  });

  const canManage = myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN';

  const loadVariants = useCallback(async (productId: string) => {
    if (!businessId || !productId) { setVariants([]); return; }
    try {
      const res = await apiClient.listProductVariants(businessId, productId);
      setVariants(Array.isArray(res) ? res : (res as any).items || []);
    } catch { setVariants([]); }
  }, [businessId]);

  const fetchData = useCallback(async () => {
    if (!businessId) return;
    try {
      setIsLoading(true);
      setServerError('');

      const [bizData, whData, prodData, membersData, opnamesData] = await Promise.all([
        apiClient.getBusiness(businessId),
        apiClient.listWarehouses(businessId),
        apiClient.listProducts(businessId, { status: 'ACTIVE', product_type: 'GOODS' }).catch(() => ({ items: [] })),
        apiClient.listBusinessMembers(businessId).catch(() => []),
        apiClient.listStockOpnames(businessId).catch(() => []),
      ]);

      setBusiness(bizData);
      setProducts(prodData.items || []);
      setOpnames(opnamesData);

      if (user) {
        const mine = membersData.find((m: any) => m.user_id === user.id);
        setMyMembership(mine || null);
      }

      // Load all active locations
      const locPromises = whData.filter((w: any) => w.status === 'ACTIVE').map((w: any) =>
        apiClient.listWareLocations(businessId, w.id).catch(() => [])
      );
      const locResults = await Promise.all(locPromises);
      const flatLocs = locResults.flat().filter((l: any) => l.status === 'ACTIVE');
      setAllLocations(flatLocs);

      // Refresh selected opname detail if open
      if (selectedOpname) {
        const freshDetail = await apiClient.getStockOpname(businessId, selectedOpname.id).catch(() => null);
        if (freshDetail) setSelectedOpname(freshDetail);
      }
    } catch (err: any) {
      const msg = err?.message || 'Failed to load stock opname data.';
      if (msg.toLowerCase().includes('unauthorized') || msg.includes('401')) {
        return;
      }
      setServerError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [businessId, user, selectedOpname?.id]);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    if (isAddLineModalOpen && lineForm.product_id) {
      loadVariants(lineForm.product_id);
    }
  }, [isAddLineModalOpen, lineForm.product_id, loadVariants]);

  const getLocName = (id: string) => allLocations.find((l) => l.id === id)?.name || id.slice(0, 8);
  const getProductName = (id: string) => products.find((p) => p.id === id)?.name || id.slice(0, 8);
  const getVariantName = (id: string | null) => {
    if (!id) return '-';
    return variants.find((v) => v.id === id)?.name || id.slice(0, 8);
  };

  const handleSelectOpname = async (op: StockOpname) => {
    if (!businessId) return;
    try {
      const detail = await apiClient.getStockOpname(businessId, op.id);
      setSelectedOpname(detail);
      setActionError('');
    } catch (err: any) {
      setActionError(err?.message || 'Gagal memuat detail opname.');
    }
  };

  const handleCreateOpname = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    if (!createForm.inventory_location_id) {
      setFormError('Lokasi wajib dipilih.');
      return;
    }
    setIsSubmitting(true);
    setFormError('');
    try {
      const newOp = await apiClient.createStockOpname(businessId, createForm);
      setSuccessMsg('Sesi stock opname berhasil dibuat.');
      setIsCreateModalOpen(false);
      setCreateForm({ inventory_location_id: '', notes: '' });
      setSelectedOpname(newOp);
      setTimeout(() => setSuccessMsg(''), 4000);
      fetchData();
    } catch (err: any) {
      setFormError(err?.message || 'Gagal membuat sesi opname.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddLine = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !selectedOpname) return;
    if (!lineForm.product_id) {
      setFormError('Produk wajib dipilih.');
      return;
    }
    setIsSubmitting(true);
    setFormError('');
    try {
      await apiClient.addStockOpnameLine(businessId, selectedOpname.id, lineForm);
      setSuccessMsg('Item berhasil ditambahkan ke opname.');
      setIsAddLineModalOpen(false);
      setLineForm({ product_id: '', variant_id: null });
      setTimeout(() => setSuccessMsg(''), 4000);
      handleSelectOpname(selectedOpname);
    } catch (err: any) {
      setFormError(err?.message || 'Gagal menambahkan item opname.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveCount = async (lineId: string) => {
    if (!businessId || !selectedOpname) return;
    const cnt = parseFloat(countInput);
    if (isNaN(cnt) || cnt < 0 || !isFinite(cnt)) {
      setActionError('Jumlah fisik harus berupa angka >= 0.');
      return;
    }
    setIsSubmitting(true);
    setActionError('');
    try {
      await apiClient.updateStockOpnameLineCount(businessId, selectedOpname.id, lineId, {
        counted_quantity: countInput,
      });
      setEditingLineId(null);
      setCountInput('');
      handleSelectOpname(selectedOpname);
    } catch (err: any) {
      setActionError(err?.message || 'Gagal mengupdate jumlah fisik.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteLine = async (lineId: string) => {
    if (!businessId || !selectedOpname) return;
    try {
      await apiClient.deleteStockOpnameLine(businessId, selectedOpname.id, lineId);
      handleSelectOpname(selectedOpname);
    } catch (err: any) {
      setActionError(err?.message || 'Gagal menghapus item opname.');
    }
  };

  const handleFinalize = async () => {
    if (!businessId || !selectedOpname) return;
    setIsSubmitting(true);
    setActionError('');
    try {
      const finalized = await apiClient.finalizeStockOpname(businessId, selectedOpname.id);
      setSelectedOpname(finalized);
      setIsFinalizeModalOpen(false);
      setSuccessMsg('Stock opname berhasil difinalisasi dan movement adjustment telah dibuat.');
      setTimeout(() => setSuccessMsg(''), 5000);
      fetchData();
    } catch (err: any) {
      const msg = err?.message || 'Gagal memfinalisasi stock opname.';
      setIsFinalizeModalOpen(false);
      setActionError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredOpnames = opnames.filter((op) => {
    if (statusFilter === 'ALL') return true;
    return op.status === statusFilter;
  });

  if (isLoading) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-950">
        <Loading size="lg" text="Memuat stock opname..." />
      </div>
    );
  }

  if (serverError && !business) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-950">
        <ErrorState message={serverError} onRetry={fetchData} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 mb-1">
              <Link to={`/businesses/${businessId}`} className="hover:text-slate-700 dark:hover:text-slate-200">
                &larr; {business?.name || 'Bisnis'}
              </Link>
              <span>/</span>
              <Link to={`/businesses/${businessId}/inventory`} className="hover:text-slate-700 dark:hover:text-slate-200">
                Inventaris
              </Link>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              Stock Opname
            </h1>
            {business && (
              <p className="text-sm text-slate-500 dark:text-slate-400">{business.name}</p>
            )}
          </div>
          {canManage && (
            <Button size="sm" onClick={() => { setFormError(''); setIsCreateModalOpen(true); }}>
              + Buat Opname Baru
            </Button>
          )}
        </div>

        {/* Notifications */}
        {successMsg && (
          <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/30 dark:text-emerald-200" role="status">
            <span className="flex items-center gap-2">
              <svg className="h-4 w-4 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 001.414 0z" clipRule="evenodd" />
              </svg>
              {successMsg}
            </span>
          </div>
        )}

        {actionError && (
          <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-200" role="alert">
            <span className="flex items-center gap-2">
              <svg className="h-4 w-4 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              {actionError}
            </span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Opname Sessions List */}
          <div className="lg:col-span-1 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Daftar Sesi</h2>
              <select
                className="text-xs bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md px-2 py-1"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="ALL">Semua Status</option>
                <option value="DRAFT">DRAFT</option>
                <option value="FINALIZED">FINALIZED</option>
              </select>
            </div>

            {filteredOpnames.length === 0 ? (
              <Card className="p-6 text-center">
                <EmptyState title="Belum Ada Opname" description="Klik button diatas untuk membuat sesi opname baru." />
              </Card>
            ) : (
              filteredOpnames.map((op) => (
                <div
                  key={op.id}
                  className={`cursor-pointer p-4 transition-all rounded-xl border bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 shadow-xs hover:border-indigo-500 ${
                    selectedOpname?.id === op.id ? 'border-2 border-indigo-500 bg-indigo-50/20 dark:bg-indigo-950/20' : ''
                  }`}
                  onClick={() => handleSelectOpname(op)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-slate-500">{op.id.slice(0, 8)}...</span>
                    <Badge variant={op.status === 'FINALIZED' ? 'success' : 'warning'}>
                      {op.status}
                    </Badge>
                  </div>
                  <div className="font-semibold text-sm mb-1">{getLocName(op.inventory_location_id)}</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-2">
                    Item: {op.lines?.length || 0} line(s)
                  </div>
                  <div className="text-[11px] text-slate-400 flex justify-between">
                    <span>{new Date(op.created_at).toLocaleDateString('id-ID', { day: '2-digit', month: 'short' })}</span>
                    {op.finalized_at && <span>Final: {new Date(op.finalized_at).toLocaleDateString('id-ID', { day: '2-digit', month: 'short' })}</span>}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Selected Opname Detail */}
          <div className="lg:col-span-2">
            {!selectedOpname ? (
              <Card className="p-12 text-center text-slate-500 dark:text-slate-400">
                Pilih sesi stock opname di sebelah kiri untuk melihat detail.
              </Card>
            ) : (
              <Card className="p-6">
                {/* Header Detail */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 border-b border-slate-200 dark:border-slate-800 pb-4">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
                        {getLocName(selectedOpname.inventory_location_id)}
                      </h2>
                      <Badge variant={selectedOpname.status === 'FINALIZED' ? 'success' : 'warning'}>
                        {selectedOpname.status}
                      </Badge>
                    </div>
                    {selectedOpname.notes && (
                      <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{selectedOpname.notes}</p>
                    )}
                    <p className="text-xs text-slate-400 mt-1">
                      ID: {selectedOpname.id}
                    </p>
                  </div>

                  {canManage && selectedOpname.status === 'DRAFT' && (
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" variant="outline" onClick={() => { setFormError(''); setIsAddLineModalOpen(true); }}>
                        + Tambah Item
                      </Button>
                      <Button size="sm" onClick={() => setIsFinalizeModalOpen(true)}>
                        Finalisasi Opname
                      </Button>
                    </div>
                  )}
                </div>

                {/* Lines Table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
                    <thead className="border-b border-slate-200 bg-slate-100/70 text-xs font-semibold uppercase text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                      <tr>
                        <th scope="col" className="px-4 py-3">Produk</th>
                        <th scope="col" className="px-4 py-3">Varian</th>
                        <th scope="col" className="px-4 py-3 text-right">Stok Sistem</th>
                        <th scope="col" className="px-4 py-3 text-right">Hasil Hitung</th>
                        <th scope="col" className="px-4 py-3 text-right">Variance</th>
                        {canManage && selectedOpname.status === 'DRAFT' && (
                          <th scope="col" className="px-4 py-3 text-center">Aksi</th>
                        )}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                      {selectedOpname.lines.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="px-4 py-6 text-center text-slate-500 dark:text-slate-400">
                            Belum ada item dalam sesi opname ini.
                          </td>
                        </tr>
                      ) : (
                        selectedOpname.lines.map((line) => {
                          const isEditing = editingLineId === line.id;
                          const varNum = line.variance !== null ? parseFloat(line.variance) : null;
                          return (
                            <tr key={line.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition-colors">
                              <td className="px-4 py-3 font-medium text-xs">{getProductName(line.product_id)}</td>
                              <td className="px-4 py-3 text-xs text-slate-500">{getVariantName(line.variant_id)}</td>
                              <td className="px-4 py-3 text-right font-mono text-xs">
                                {parseFloat(line.system_quantity).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 4 })}
                              </td>
                              <td className="px-4 py-3 text-right font-mono text-xs">
                                {isEditing ? (
                                  <div className="flex items-center justify-end gap-1">
                                    <input
                                      type="number"
                                      step="any"
                                      min="0"
                                      className="w-20 px-2 py-1 text-xs border border-indigo-500 rounded bg-white dark:bg-slate-900 text-right"
                                      value={countInput}
                                      onChange={(e) => setCountInput(e.target.value)}
                                      autoFocus
                                    />
                                    <Button size="sm" className="px-2 py-1 text-xs" onClick={() => handleSaveCount(line.id)} isLoading={isSubmitting}>
                                      Simpan
                                    </Button>
                                    <Button size="sm" variant="outline" className="px-2 py-1 text-xs" onClick={() => setEditingLineId(null)}>
                                      Batal
                                    </Button>
                                  </div>
                                ) : (
                                  line.counted_quantity !== null ? (
                                    parseFloat(line.counted_quantity).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 4 })
                                  ) : (
                                    <span className="text-amber-500 italic">Belum dihitung</span>
                                  )
                                )}
                              </td>
                              <td className="px-4 py-3 text-right font-mono text-xs font-semibold">
                                {varNum === null ? '-' : (
                                  <span className={varNum > 0 ? 'text-emerald-600 dark:text-emerald-400' : varNum < 0 ? 'text-rose-600 dark:text-rose-400' : 'text-slate-500'}>
                                    {varNum > 0 ? `+${varNum}` : varNum}
                                  </span>
                                )}
                              </td>
                              {canManage && selectedOpname.status === 'DRAFT' && (
                                <td className="px-4 py-3 text-center">
                                  {!isEditing && (
                                    <div className="flex items-center justify-center gap-1">
                                      <button
                                        className="text-xs text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 font-medium px-2 py-1 rounded"
                                        onClick={() => {
                                          setEditingLineId(line.id);
                                          setCountInput(line.counted_quantity || line.system_quantity);
                                        }}
                                      >
                                        Hitung
                                      </button>
                                      <button
                                        className="text-xs text-rose-600 hover:text-rose-800 dark:text-rose-400 font-medium px-2 py-1 rounded"
                                        onClick={() => handleDeleteLine(line.id)}
                                      >
                                        Hapus
                                      </button>
                                    </div>
                                  )}
                                </td>
                              )}
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}
          </div>
        </div>

        {/* Modal Create Opname */}
        {isCreateModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="Buat Stock Opname Baru">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Buat Stock Opname Baru</h2>
              {formError && (
                <div className="mb-4 rounded-lg bg-rose-50 dark:bg-rose-950/40 p-3 text-xs text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900" role="alert">{formError}</div>
              )}
              <form onSubmit={handleCreateOpname} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Lokasi Inventory *</label>
                  <select className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={createForm.inventory_location_id} onChange={(e) => setCreateForm((p) => ({ ...p, inventory_location_id: e.target.value }))} required>
                    <option value="">-- Pilih Lokasi --</option>
                    {allLocations.map((loc) => (<option key={loc.id} value={loc.id}>{loc.name} ({loc.code})</option>))}
                  </select>
                </div>
                <Input id="opNotes" label="Catatan (Opsional)" placeholder="Contoh: Opname fisik bulanan" value={createForm.notes || ''} onChange={(e) => setCreateForm((p) => ({ ...p, notes: e.target.value }))} />
                <div className="mt-6 flex justify-end gap-3">
                  <Button type="button" variant="outline" size="sm" onClick={() => setIsCreateModalOpen(false)} disabled={isSubmitting}>Batal</Button>
                  <Button type="submit" size="sm" isLoading={isSubmitting}>Buat Opname</Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal Add Line */}
        {isAddLineModalOpen && selectedOpname && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="Tambah Item Opname">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Tambah Item Opname</h2>
              {formError && (
                <div className="mb-4 rounded-lg bg-rose-50 dark:bg-rose-950/40 p-3 text-xs text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900" role="alert">{formError}</div>
              )}
              <form onSubmit={handleAddLine} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Produk (GOODS) *</label>
                  <select className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={lineForm.product_id} onChange={(e) => setLineForm({ product_id: e.target.value, variant_id: null })} required>
                    <option value="">-- Pilih Produk --</option>
                    {products.map((p) => (<option key={p.id} value={p.id}>{p.name} ({p.code})</option>))}
                  </select>
                </div>
                {variants.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Varian (Opsional)</label>
                    <select className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={lineForm.variant_id || ''} onChange={(e) => setLineForm((p) => ({ ...p, variant_id: e.target.value || null }))}>
                      <option value="">-- Tanpa Varian --</option>
                      {variants.map((v) => (<option key={v.id} value={v.id}>{v.name} ({v.code})</option>))}
                    </select>
                  </div>
                )}
                <div className="mt-6 flex justify-end gap-3">
                  <Button type="button" variant="outline" size="sm" onClick={() => setIsAddLineModalOpen(false)} disabled={isSubmitting}>Batal</Button>
                  <Button type="submit" size="sm" isLoading={isSubmitting}>Tambah Item</Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal Finalize Warning Confirmation */}
        {isFinalizeModalOpen && selectedOpname && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="Konfirmasi Finalisasi Opname">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-2">Konfirmasi Finalisasi Opname</h2>
              <div className="mb-4 rounded-lg bg-amber-50 dark:bg-amber-950/40 p-4 text-xs text-amber-800 dark:text-amber-200 border border-amber-200 dark:border-amber-900/50">
                <p className="font-semibold mb-1">Peringatan:</p>
                <p>Setelah difinalisasi, opname tidak dapat diubah dan variance akan mempengaruhi stok.</p>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-6">
                Sistem akan secara otomatis membuat movement adjustment untuk menyesuaikan stok balance dengan hasil perhitungan fisik.
              </p>
              <div className="flex justify-end gap-3">
                <Button type="button" variant="outline" size="sm" onClick={() => setIsFinalizeModalOpen(false)} disabled={isSubmitting}>Batal</Button>
                <Button type="button" size="sm" onClick={handleFinalize} isLoading={isSubmitting}>Ya, Finalisasi Sesi Opname</Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default StockOpnamePage;
