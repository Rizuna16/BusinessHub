import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { BusinessMembership } from '@/types/businessMembership';
import type { PurchaseResponse, PurchaseLineResponse } from '@/types/purchase';
import type { Product } from '@/types/product';
import type {
  ReceivingResponse,
  ReceivingLineResponse,
  ReceivingLineCreateInput,
  ReceivingLineUpdateInput,
} from '@/types/receiving';
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

export const ReceivingDetail: React.FC = () => {
  const { businessId, receivingId } = useParams<{ businessId: string; receivingId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [receiving, setReceiving] = useState<ReceivingResponse | null>(null);
  const [purchase, setPurchase] = useState<PurchaseResponse | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');
  const [actionError, setActionError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const [isAddLineOpen, setIsAddLineOpen] = useState<boolean>(false);
  const [editingLine, setEditingLine] = useState<ReceivingLineResponse | null>(null);
  const [confirmAction, setConfirmAction] = useState<'finalize' | 'cancel' | 'delete' | 'deleteLine' | null>(null);
  const [lineToDelete, setLineToDelete] = useState<string | null>(null);
  const [formError, setFormError] = useState<string>('');

  const [lineForm, setLineForm] = useState<ReceivingLineCreateInput>({
    purchase_line_id: '',
    quantity: 1,
  });

  const isDraft = receiving?.status === 'DRAFT';
  const canManage = (myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN') && isDraft;

  const fetchDetail = useCallback(async () => {
    if (!businessId || !receivingId) return;
    try {
      setIsLoading(true);
      setServerError('');
      const rcvData = await apiClient.getReceiving(businessId, receivingId);
      setReceiving(rcvData);

      const [purData, prodData, membersData] = await Promise.all([
        apiClient.getPurchase(businessId, rcvData.purchase_id).catch(() => null),
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
      const msg = err?.message || 'Gagal memuat penerimaan barang.';
      if (msg.toLowerCase().includes('unauthorized')) navigate('/login');
      else setServerError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [businessId, receivingId, user, navigate]);

  useEffect(() => { fetchDetail(); }, [fetchDetail]);

  const showSuccess = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 4000);
  };

  const handleAddLine = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !receivingId) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      const payload: ReceivingLineCreateInput = {
        purchase_line_id: lineForm.purchase_line_id,
        quantity: lineForm.quantity,
      };
      await apiClient.addReceivingLine(businessId, receivingId, payload);
      setIsAddLineOpen(false);
      setLineForm({ purchase_line_id: '', quantity: 1 });
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
    if (!businessId || !receivingId || !editingLine) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      const payload: ReceivingLineUpdateInput = {
        quantity: lineForm.quantity,
      };
      await apiClient.updateReceivingLine(businessId, receivingId, editingLine.id, payload);
      setEditingLine(null);
      setLineForm({ purchase_line_id: '', quantity: 1 });
      await fetchDetail();
      showSuccess('Item berhasil diperbarui.');
    } catch (err: any) {
      setFormError(err?.message || 'Gagal memperbarui item.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteLine = async () => {
    if (!businessId || !receivingId || !lineToDelete) return;
    setIsSubmitting(true);
    try {
      await apiClient.deleteReceivingLine(businessId, receivingId, lineToDelete);
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
    if (!businessId || !receivingId) return;
    setIsSubmitting(true);
    try {
      const updated = await apiClient.finalizeReceiving(businessId, receivingId);
      setReceiving(updated);
      setConfirmAction(null);
      showSuccess('Penerimaan barang berhasil difinalisasi.');
    } catch (err: any) {
      setActionError(err?.message || 'Gagal memfinalisasi penerimaan.');
      setConfirmAction(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async () => {
    if (!businessId || !receivingId) return;
    setIsSubmitting(true);
    try {
      const updated = await apiClient.cancelReceiving(businessId, receivingId);
      setReceiving(updated);
      setConfirmAction(null);
      showSuccess('Penerimaan barang dibatalkan.');
    } catch (err: any) {
      setActionError(err?.message || 'Gagal membatalkan penerimaan.');
      setConfirmAction(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteDraft = async () => {
    if (!businessId || !receivingId) return;
    setIsSubmitting(true);
    try {
      await apiClient.deleteReceiving(businessId, receivingId);
      navigate(`/businesses/${businessId}/receivings`);
    } catch (err: any) {
      setActionError(err?.message || 'Gagal menghapus draft penerimaan.');
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

  const openEditLine = (line: ReceivingLineResponse) => {
    setEditingLine(line);
    setLineForm({
      purchase_line_id: line.purchase_line_id,
      quantity: parseFloat(String(line.quantity)),
    });
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-900">
        <Loading size="lg" text="Memuat detail penerimaan..." />
      </div>
    );
  }

  if (serverError && !receiving) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-950">
        <ErrorState message={serverError} onRetry={fetchDetail} />
      </div>
    );
  }

  if (!receiving) return null;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-6">
          <Link
            to={`/businesses/${businessId}/receivings`}
            className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
          >
            &larr; Daftar Penerimaan Barang
          </Link>
          <div className="mt-2 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{receiving.receiving_number}</h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Dibuat pada {new Date(receiving.created_at).toLocaleString('id-ID')}
              </p>
            </div>
            <span className={`inline-flex self-start items-center px-3 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[receiving.status] || ''}`}>
              {receiving.status}
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
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">Informasi Penerimaan</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-500 dark:text-slate-400">Nomor PO</dt>
                <dd className="font-medium text-indigo-600 dark:text-indigo-400">
                  <Link to={`/businesses/${businessId}/purchases/${receiving.purchase_id}`}>
                    {purchase ? purchase.purchase_number : receiving.purchase_id}
                  </Link>
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500 dark:text-slate-400">Lokasi Tujuan</dt>
                <dd className="font-medium text-slate-900 dark:text-slate-100">{receiving.inventory_location_id}</dd>
              </div>
              {receiving.notes && (
                <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                  <dt className="text-slate-500 dark:text-slate-400 text-xs">Catatan</dt>
                  <dd className="text-slate-700 dark:text-slate-200 mt-1">{receiving.notes}</dd>
                </div>
              )}
            </dl>
          </Card>

          <Card>
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">Status Dokumen</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-500 dark:text-slate-400">Status</dt>
                <dd className="font-medium">{receiving.status}</dd>
              </div>
              {receiving.finalized_at && (
                <div className="flex justify-between">
                  <dt className="text-slate-500 dark:text-slate-400">Tanggal Finalisasi</dt>
                  <dd className="text-slate-600 dark:text-slate-300">{new Date(receiving.finalized_at).toLocaleString('id-ID')}</dd>
                </div>
              )}
              {receiving.cancelled_at && (
                <div className="flex justify-between">
                  <dt className="text-slate-500 dark:text-slate-400">Tanggal Pembatalan</dt>
                  <dd className="text-slate-600 dark:text-slate-300">{new Date(receiving.cancelled_at).toLocaleString('id-ID')}</dd>
                </div>
              )}
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
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-4">Item Diterima ({receiving.lines.length})</h3>

          {receiving.lines.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-8">Belum ada item. Tambahkan item dari PO untuk memulai.</p>
          ) : (
            <>
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                      <th className="pb-2 pr-4 font-medium">Produk</th>
                      <th className="pb-2 pr-4 font-medium">Varian</th>
                      <th className="pb-2 pr-4 font-medium text-right">Jumlah Dipesan</th>
                      <th className="pb-2 pr-4 font-medium text-right">Jumlah Diterima</th>
                      {isDraft && <th className="pb-2 font-medium">Aksi</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {receiving.lines.map(line => {
                      const pline = getPurchaseLineDetails(line.purchase_line_id);
                      return (
                        <tr key={line.id} className="border-b border-slate-100 dark:border-slate-800">
                          <td className="py-3 pr-4 text-slate-900 dark:text-slate-100">{getProductName(line.product_id)}</td>
                          <td className="py-3 pr-4 text-slate-500 dark:text-slate-400">{line.variant_id ? 'Varian' : '-'}</td>
                          <td className="py-3 pr-4 text-right text-slate-500">{pline ? String(pline.quantity) : '-'}</td>
                          <td className="py-3 pr-4 text-right font-semibold text-slate-900 dark:text-slate-100">{String(line.quantity)}</td>
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
                {receiving.lines.map(line => {
                  const pline = getPurchaseLineDetails(line.purchase_line_id);
                  return (
                    <div key={line.id} className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 bg-slate-50 dark:bg-slate-900">
                      <p className="font-medium text-slate-900 dark:text-slate-100">{getProductName(line.product_id)}</p>
                      <div className="mt-1 text-xs text-slate-500 dark:text-slate-400 grid grid-cols-2 gap-1">
                        <span>Dipesan: {pline ? String(pline.quantity) : '-'}</span>
                        <span className="font-semibold text-slate-900 dark:text-slate-100">Diterima: {String(line.quantity)}</span>
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
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Tambah Item Penerimaan</h2>
              {formError && <p className="mb-3 text-sm text-rose-600 dark:text-rose-400">{formError}</p>}
              <form onSubmit={handleAddLine} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Item PO *</label>
                  <select
                    required
                    value={lineForm.purchase_line_id}
                    onChange={(e) => setLineForm(f => ({ ...f, purchase_line_id: e.target.value }))}
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
                  label="Jumlah Diterima *"
                  type="number"
                  min="0.01"
                  step="any"
                  value={String(lineForm.quantity)}
                  onChange={(e) => setLineForm(f => ({ ...f, quantity: parseFloat(e.target.value) || 0 }))}
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
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Edit Jumlah Penerimaan</h2>
              {formError && <p className="mb-3 text-sm text-rose-600 dark:text-rose-400">{formError}</p>}
              <form onSubmit={handleUpdateLine} className="space-y-4">
                <Input
                  id="edit_quantity"
                  label="Jumlah Diterima *"
                  type="number"
                  min="0.01"
                  step="any"
                  value={String(lineForm.quantity)}
                  onChange={(e) => setLineForm(f => ({ ...f, quantity: parseFloat(e.target.value) || 0 }))}
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
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Finalisasi Penerimaan</h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Apakah Anda yakin ingin memfinalisasi penerimaan {receiving.receiving_number}? Tindakan ini tidak dapat dibatalkan.</p>
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
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Batalkan Penerimaan</h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Apakah Anda yakin ingin membatalkan penerimaan ini?</p>
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
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Hapus Draft</h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Apakah Anda yakin ingin menghapus draft penerimaan ini?</p>
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
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Apakah Anda yakin ingin menghapus item ini dari penerimaan?</p>
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

export default ReceivingDetail;
