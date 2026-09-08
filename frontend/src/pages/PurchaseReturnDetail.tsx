import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { BusinessMembership } from '@/types/businessMembership';
import type { PurchaseResponse, PurchaseLineResponse } from '@/types/purchase';
import type { Product } from '@/types/product';
import type {
  PurchaseReturnResponse,
  PurchaseReturnLineResponse,
  PurchaseReturnLineCreateInput,
  PurchaseReturnLineUpdateInput,
} from '@/types/purchaseReturn';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { useAuth } from '@/context/AuthContext';

const STATUS_COLORS: Record<string, string> = {
  DRAFT: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800',
  FINALIZED: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
  CANCELLED: 'bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800',
};

export const PurchaseReturnDetail: React.FC = () => {
  const { businessId, returnId } = useParams<{ businessId: string; returnId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [purchaseReturn, setPurchaseReturn] = useState<PurchaseReturnResponse | null>(null);
  const [purchase, setPurchase] = useState<PurchaseResponse | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');
  const [actionError, setActionError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const [isAddLineOpen, setIsAddLineOpen] = useState<boolean>(false);
  const [editingLine, setEditingLine] = useState<PurchaseReturnLineResponse | null>(null);
  const [confirmAction, setConfirmAction] = useState<'finalize' | 'cancel' | 'delete' | 'deleteLine' | null>(null);
  const [lineToDelete, setLineToDelete] = useState<string | null>(null);
  const [formError, setFormError] = useState<string>('');

  const [lineForm, setLineForm] = useState<PurchaseReturnLineCreateInput>({
    purchase_line_id: '',
    quantity: 1,
    unit_price: 0,
    discount_amount: 0,
    tax_amount: 0,
  });

  const isDraft = purchaseReturn?.status === 'DRAFT';
  const canManage = (myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN') && isDraft;

  const fetchDetail = useCallback(async () => {
    if (!businessId || !returnId) return;
    try {
      setIsLoading(true);
      setServerError('');
      const retData = await apiClient.getPurchaseReturn(businessId, returnId);
      setPurchaseReturn(retData);

      const [purData, prodData, membersData] = await Promise.all([
        apiClient.getPurchase(businessId, retData.purchase_id).catch(() => null),
        apiClient.listProducts(businessId).catch(() => ({ items: [] })),
        apiClient.listBusinessMembers(businessId).catch(() => []),
      ]);
      setPurchase(purData);
      setProducts(prodData.items || []);
      if (user) {
        const mine = membersData.find((m: any) => m.user_id === user.id);
        setMyMembership(mine || null);
      }
    } catch (err: any) {
      const msg = err?.message || 'Gagal memuat detail retur pembelian.';
      if (msg.toLowerCase().includes('unauthorized')) navigate('/login');
      else setServerError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [businessId, returnId, user, navigate]);

  useEffect(() => { fetchDetail(); }, [fetchDetail]);

  const showSuccess = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 4000);
  };

  const handleAddLine = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !returnId) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      const payload: PurchaseReturnLineCreateInput = {
        purchase_line_id: lineForm.purchase_line_id,
        quantity: lineForm.quantity,
        unit_price: lineForm.unit_price || undefined,
        discount_amount: lineForm.discount_amount || 0,
        tax_amount: lineForm.tax_amount || 0,
      };
      await apiClient.addPurchaseReturnLine(businessId, returnId, payload);
      setIsAddLineOpen(false);
      setLineForm({ purchase_line_id: '', quantity: 1, unit_price: 0, discount_amount: 0, tax_amount: 0 });
      await fetchDetail();
      showSuccess('Item berhasil ditambahkan.');
    } catch (err: any) {
      setFormError(err?.message || 'Gagal menambahkan item.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateLine = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !returnId || !editingLine) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      const payload: PurchaseReturnLineUpdateInput = {
        quantity: lineForm.quantity,
        unit_price: lineForm.unit_price,
        discount_amount: lineForm.discount_amount,
        tax_amount: lineForm.tax_amount,
      };
      await apiClient.updatePurchaseReturnLine(businessId, returnId, editingLine.id, payload);
      setEditingLine(null);
      setLineForm({ purchase_line_id: '', quantity: 1, unit_price: 0, discount_amount: 0, tax_amount: 0 });
      await fetchDetail();
      showSuccess('Item berhasil diperbarui.');
    } catch (err: any) {
      setFormError(err?.message || 'Gagal memperbarui item.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteLine = async () => {
    if (!businessId || !returnId || !lineToDelete) return;
    setIsSubmitting(true);
    try {
      await apiClient.deletePurchaseReturnLine(businessId, returnId, lineToDelete);
      setConfirmAction(null);
      setLineToDelete(null);
      await fetchDetail();
      showSuccess('Item berhasil dihapus.');
    } catch (err: any) {
      setActionError(err?.message || 'Gagal menghapus item.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFinalize = async () => {
    if (!businessId || !returnId) return;
    setIsSubmitting(true);
    try {
      const updated = await apiClient.finalizePurchaseReturn(businessId, returnId);
      setPurchaseReturn(updated);
      setConfirmAction(null);
      showSuccess('Retur pembelian berhasil difinalisasi.');
    } catch (err: any) {
      setActionError(err?.message || 'Gagal memfinalisasi retur.');
      setConfirmAction(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async () => {
    if (!businessId || !returnId) return;
    setIsSubmitting(true);
    try {
      const updated = await apiClient.cancelPurchaseReturn(businessId, returnId);
      setPurchaseReturn(updated);
      setConfirmAction(null);
      showSuccess('Retur pembelian dibatalkan.');
    } catch (err: any) {
      setActionError(err?.message || 'Gagal membatalkan retur.');
      setConfirmAction(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteDraft = async () => {
    if (!businessId || !returnId) return;
    setIsSubmitting(true);
    try {
      await apiClient.deletePurchaseReturn(businessId, returnId);
      navigate(`/businesses/${businessId}/purchase-returns`);
    } catch (err: any) {
      setActionError(err?.message || 'Gagal menghapus draft retur.');
      setConfirmAction(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getProductName = (productId: string) => {
    const p = products.find(p => p.id === productId);
    return p ? `${p.name} (${p.code})` : productId;
  };

  const getPurchaseLineDetails = (purchaseLineId: string): PurchaseLineResponse | undefined => {
    return purchase?.lines.find(l => l.id === purchaseLineId);
  };

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return num.toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  };

  const openEditLine = (line: PurchaseReturnLineResponse) => {
    setEditingLine(line);
    setLineForm({
      purchase_line_id: line.purchase_line_id,
      quantity: parseFloat(String(line.quantity)),
      unit_price: parseFloat(String(line.unit_price)),
      discount_amount: parseFloat(String(line.discount_amount)) || 0,
      tax_amount: parseFloat(String(line.tax_amount)) || 0,
    });
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-900">
        <Loading size="lg" text="Memuat detail retur pembelian..." />
      </div>
    );
  }

  if (serverError && !purchaseReturn) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-950">
        <ErrorState message={serverError} onRetry={fetchDetail} />
      </div>
    );
  }

  if (!purchaseReturn) return null;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-6">
          <Link
            to={`/businesses/${businessId}/purchase-returns`}
            className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
          >
            &larr; Daftar Retur Pembelian
          </Link>
          <div className="mt-2 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{purchaseReturn.return_number}</h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Dibuat pada {new Date(purchaseReturn.created_at).toLocaleString('id-ID')}
              </p>
            </div>
            <span className={`inline-flex self-start items-center px-3 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[purchaseReturn.status] || ''}`}>
              {purchaseReturn.status}
            </span>
          </div>
        </header>

        {successMsg && (
          <div className="mb-4 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900/50 p-3 text-emerald-800 dark:text-emerald-200 text-sm">
            {successMsg}
          </div>
        )}
        {actionError && (
          <div className="mb-4 rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 p-3 text-rose-800 dark:text-rose-200 text-sm">
            {actionError}
          </div>
        )}

        <div className="grid gap-6 md:grid-cols-2 mb-6">
          <Card>
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">Informasi Retur</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-500 dark:text-slate-400">Nomor PO</dt>
                <dd className="font-medium text-indigo-600 dark:text-indigo-400">
                  <Link to={`/businesses/${businessId}/purchases/${purchaseReturn.purchase_id}`}>
                    {purchase ? purchase.purchase_number : purchaseReturn.purchase_id}
                  </Link>
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500 dark:text-slate-400">Lokasi Asal Retur</dt>
                <dd className="font-medium text-slate-900 dark:text-slate-100">{purchaseReturn.inventory_location_id}</dd>
              </div>
              {purchaseReturn.notes && (
                <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                  <dt className="text-slate-500 dark:text-slate-400 text-xs">Catatan</dt>
                  <dd className="text-slate-700 dark:text-slate-200 mt-1">{purchaseReturn.notes}</dd>
                </div>
              )}
            </dl>
          </Card>

          <Card>
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">Ringkasan Biaya Retur</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Subtotal</dt><dd className="text-slate-900 dark:text-slate-100">Rp {formatCurrency(purchaseReturn.subtotal)}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Diskon</dt><dd className="text-rose-600 dark:text-rose-400">- Rp {formatCurrency(purchaseReturn.discount_total)}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Pajak</dt><dd className="text-emerald-600 dark:text-emerald-400">+ Rp {formatCurrency(purchaseReturn.tax_total)}</dd></div>
              <div className="flex justify-between border-t border-slate-200 dark:border-slate-700 pt-2 font-bold">
                <dt className="text-slate-900 dark:text-slate-100">Grand Total</dt>
                <dd className="text-slate-900 dark:text-slate-100">Rp {formatCurrency(purchaseReturn.grand_total)}</dd>
              </div>
            </dl>
          </Card>
        </div>

        {canManage && (
          <div className="mb-6 flex flex-wrap gap-2">
            <Button size="sm" onClick={() => { setIsAddLineOpen(true); setFormError(''); }}>Tambah Item</Button>
            <Button size="sm" onClick={() => setConfirmAction('finalize')} className="bg-emerald-600 hover:bg-emerald-700 text-white">Finalisasi</Button>
            <Button variant="outline" size="sm" onClick={() => setConfirmAction('cancel')} className="border-rose-300 text-rose-600 dark:border-rose-800 dark:text-rose-400">Batalkan</Button>
            <Button variant="danger" size="sm" onClick={() => setConfirmAction('delete')}>Hapus Draft</Button>
          </div>
        )}

        <Card>
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-4">Item Diretur ({purchaseReturn.lines.length})</h3>

          {purchaseReturn.lines.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-8">Belum ada item. Tambahkan item dari PO untuk memulai retur.</p>
          ) : (
            <>
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                      <th className="pb-2 pr-4 font-medium">Produk</th>
                      <th className="pb-2 pr-4 font-medium">Varian</th>
                      <th className="pb-2 pr-4 font-medium text-right">Dipesan</th>
                      <th className="pb-2 pr-4 font-medium text-right">Jumlah Retur</th>
                      <th className="pb-2 pr-4 font-medium text-right">Harga Satuan</th>
                      <th className="pb-2 pr-4 font-medium text-right">Total</th>
                      {isDraft && <th className="pb-2 font-medium">Aksi</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {purchaseReturn.lines.map(line => {
                      const pline = getPurchaseLineDetails(line.purchase_line_id);
                      return (
                        <tr key={line.id} className="border-b border-slate-100 dark:border-slate-800">
                          <td className="py-3 pr-4 text-slate-900 dark:text-slate-100">{getProductName(line.product_id)}</td>
                          <td className="py-3 pr-4 text-slate-500 dark:text-slate-400">{line.variant_id ? 'Varian' : '-'}</td>
                          <td className="py-3 pr-4 text-right text-slate-500">{pline ? String(pline.quantity) : '-'}</td>
                          <td className="py-3 pr-4 text-right font-semibold text-slate-900 dark:text-slate-100">{String(line.quantity)}</td>
                          <td className="py-3 pr-4 text-right">Rp {formatCurrency(line.unit_price)}</td>
                          <td className="py-3 pr-4 text-right font-medium">Rp {formatCurrency(line.line_total)}</td>
                          {isDraft && (
                            <td className="py-3 flex gap-1">
                              <Button variant="outline" size="sm" onClick={() => openEditLine(line)}>Edit</Button>
                              <Button variant="danger" size="sm" onClick={() => { setLineToDelete(line.id); setConfirmAction('deleteLine'); }}>Hapus</Button>
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div className="md:hidden space-y-3">
                {purchaseReturn.lines.map(line => {
                  const pline = getPurchaseLineDetails(line.purchase_line_id);
                  return (
                    <div key={line.id} className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 bg-slate-50 dark:bg-slate-900">
                      <p className="font-medium text-slate-900 dark:text-slate-100">{getProductName(line.product_id)}</p>
                      <div className="mt-1 text-xs text-slate-500 dark:text-slate-400 grid grid-cols-2 gap-1">
                        <span>Dipesan: {pline ? String(pline.quantity) : '-'}</span>
                        <span className="font-semibold text-slate-900 dark:text-slate-100">Retur: {String(line.quantity)}</span>
                        <span>Harga: Rp {formatCurrency(line.unit_price)}</span>
                        <span className="font-medium text-slate-900 dark:text-slate-100">Total: Rp {formatCurrency(line.line_total)}</span>
                      </div>
                      {isDraft && (
                        <div className="mt-2 flex gap-2">
                          <Button variant="outline" size="sm" onClick={() => openEditLine(line)}>Edit</Button>
                          <Button variant="danger" size="sm" onClick={() => { setLineToDelete(line.id); setConfirmAction('deleteLine'); }}>Hapus</Button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </Card>

        {/* Add Line Modal */}
        {isAddLineOpen && purchase && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4">
            <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-900 shadow-xl p-6 max-h-[90vh] overflow-y-auto">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Tambah Item Retur</h2>
              {formError && <p className="mb-3 text-sm text-rose-600 dark:text-rose-400">{formError}</p>}
              <form onSubmit={handleAddLine} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Item PO *</label>
                  <select
                    required
                    value={lineForm.purchase_line_id}
                    onChange={(e) => {
                      const plid = e.target.value;
                      const pline = purchase.lines.find(l => l.id === plid);
                      setLineForm(f => ({
                        ...f,
                        purchase_line_id: plid,
                        unit_price: pline ? parseFloat(String(pline.unit_price)) : 0,
                      }));
                    }}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Pilih Item PO</option>
                    {purchase.lines.map(pl => (
                      <option key={pl.id} value={pl.id}>
                        {getProductName(pl.product_id)} (Dipesan: {String(pl.quantity)})
                      </option>
                    ))}
                  </select>
                </div>
                <Input
                  id="add_quantity"
                  label="Jumlah Retur *"
                  type="number"
                  min="0.01"
                  step="any"
                  value={String(lineForm.quantity)}
                  onChange={(e) => setLineForm(f => ({ ...f, quantity: parseFloat(e.target.value) || 0 }))}
                />
                <Input
                  id="add_unit_price"
                  label="Harga Satuan *"
                  type="number"
                  min="0"
                  step="any"
                  value={String(lineForm.unit_price || 0)}
                  onChange={(e) => setLineForm(f => ({ ...f, unit_price: parseFloat(e.target.value) || 0 }))}
                />
                <Input
                  id="add_discount"
                  label="Diskon"
                  type="number"
                  min="0"
                  step="any"
                  value={String(lineForm.discount_amount || 0)}
                  onChange={(e) => setLineForm(f => ({ ...f, discount_amount: parseFloat(e.target.value) || 0 }))}
                />
                <Input
                  id="add_tax"
                  label="Pajak"
                  type="number"
                  min="0"
                  step="any"
                  value={String(lineForm.tax_amount || 0)}
                  onChange={(e) => setLineForm(f => ({ ...f, tax_amount: parseFloat(e.target.value) || 0 }))}
                />
                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="outline" type="button" onClick={() => setIsAddLineOpen(false)} disabled={isSubmitting}>Batal</Button>
                  <Button type="submit" isLoading={isSubmitting} disabled={isSubmitting}>Tambah</Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Edit Line Modal */}
        {editingLine && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4">
            <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-900 shadow-xl p-6 max-h-[90vh] overflow-y-auto">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Edit Item Retur</h2>
              {formError && <p className="mb-3 text-sm text-rose-600 dark:text-rose-400">{formError}</p>}
              <form onSubmit={handleUpdateLine} className="space-y-4">
                <Input
                  id="edit_quantity"
                  label="Jumlah Retur *"
                  type="number"
                  min="0.01"
                  step="any"
                  value={String(lineForm.quantity)}
                  onChange={(e) => setLineForm(f => ({ ...f, quantity: parseFloat(e.target.value) || 0 }))}
                />
                <Input
                  id="edit_unit_price"
                  label="Harga Satuan *"
                  type="number"
                  min="0"
                  step="any"
                  value={String(lineForm.unit_price || 0)}
                  onChange={(e) => setLineForm(f => ({ ...f, unit_price: parseFloat(e.target.value) || 0 }))}
                />
                <Input
                  id="edit_discount"
                  label="Diskon"
                  type="number"
                  min="0"
                  step="any"
                  value={String(lineForm.discount_amount || 0)}
                  onChange={(e) => setLineForm(f => ({ ...f, discount_amount: parseFloat(e.target.value) || 0 }))}
                />
                <Input
                  id="edit_tax"
                  label="Pajak"
                  type="number"
                  min="0"
                  step="any"
                  value={String(lineForm.tax_amount || 0)}
                  onChange={(e) => setLineForm(f => ({ ...f, tax_amount: parseFloat(e.target.value) || 0 }))}
                />
                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="outline" type="button" onClick={() => { setEditingLine(null); setFormError(''); }} disabled={isSubmitting}>Batal</Button>
                  <Button type="submit" isLoading={isSubmitting} disabled={isSubmitting}>Simpan</Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Confirmation Modals */}
        {confirmAction === 'finalize' && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4">
            <div className="w-full max-w-sm rounded-xl bg-white dark:bg-slate-900 shadow-xl p-6">
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Finalisasi Retur Pembelian</h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Apakah Anda yakin ingin memfinalisasi retur {purchaseReturn.return_number}? Tindakan ini tidak dapat dibatalkan.</p>
              <div className="mt-4 flex justify-end gap-2">
                <Button variant="outline" onClick={() => setConfirmAction(null)} disabled={isSubmitting}>Batal</Button>
                <Button onClick={handleFinalize} isLoading={isSubmitting} disabled={isSubmitting}>Finalisasi</Button>
              </div>
            </div>
          </div>
        )}

        {confirmAction === 'cancel' && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4">
            <div className="w-full max-w-sm rounded-xl bg-white dark:bg-slate-900 shadow-xl p-6">
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Batalkan Retur Pembelian</h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Apakah Anda yakin ingin membatalkan retur ini?</p>
              <div className="mt-4 flex justify-end gap-2">
                <Button variant="outline" onClick={() => setConfirmAction(null)} disabled={isSubmitting}>Tidak</Button>
                <Button variant="danger" onClick={handleCancel} isLoading={isSubmitting} disabled={isSubmitting}>Ya, Batalkan</Button>
              </div>
            </div>
          </div>
        )}

        {confirmAction === 'delete' && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4">
            <div className="w-full max-w-sm rounded-xl bg-white dark:bg-slate-900 shadow-xl p-6">
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Hapus Draft Retur</h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Apakah Anda yakin ingin menghapus draft retur ini?</p>
              <div className="mt-4 flex justify-end gap-2">
                <Button variant="outline" onClick={() => setConfirmAction(null)} disabled={isSubmitting}>Batal</Button>
                <Button variant="danger" onClick={handleDeleteDraft} isLoading={isSubmitting} disabled={isSubmitting}>Hapus</Button>
              </div>
            </div>
          </div>
        )}

        {confirmAction === 'deleteLine' && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4">
            <div className="w-full max-w-sm rounded-xl bg-white dark:bg-slate-900 shadow-xl p-6">
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Hapus Item</h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Apakah Anda yakin ingin menghapus item ini dari retur?</p>
              <div className="mt-4 flex justify-end gap-2">
                <Button variant="outline" onClick={() => { setConfirmAction(null); setLineToDelete(null); }} disabled={isSubmitting}>Batal</Button>
                <Button variant="danger" onClick={handleDeleteLine} isLoading={isSubmitting} disabled={isSubmitting}>Hapus</Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PurchaseReturnDetail;
