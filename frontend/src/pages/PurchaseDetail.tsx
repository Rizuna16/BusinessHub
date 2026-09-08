import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { BusinessMembership } from '@/types/businessMembership';
import type { Supplier } from '@/types/supplier';
import type { Branch } from '@/types/branch';
import type { Product } from '@/types/product';
import type { ProductVariant } from '@/types/product';
import type {
  PurchaseResponse,
  PurchaseLineResponse,
  PurchaseUpdateInput,
  PurchaseLineCreateInput,
  PurchaseLineUpdateInput,
} from '@/types/purchase';
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

const RECEIVING_STATUS_COLORS: Record<string, string> = {
  NOT_RECEIVED: 'bg-slate-50 text-slate-700 border border-slate-200 dark:bg-slate-900/40 dark:text-slate-400 dark:border-slate-800',
  PARTIALLY_RECEIVED: 'bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-950/40 dark:text-blue-400 dark:border-blue-800',
  FULLY_RECEIVED: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
};

export const PurchaseDetail: React.FC = () => {
  const { businessId, purchaseId } = useParams<{ businessId: string; purchaseId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [purchase, setPurchase] = useState<PurchaseResponse | null>(null);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [productVariants, setProductVariants] = useState<Record<string, ProductVariant[]>>({});
  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');
  const [actionError, setActionError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const [isEditHeaderOpen, setIsEditHeaderOpen] = useState<boolean>(false);
  const [isAddLineOpen, setIsAddLineOpen] = useState<boolean>(false);
  const [editingLine, setEditingLine] = useState<PurchaseLineResponse | null>(null);
  const [confirmAction, setConfirmAction] = useState<'finalize' | 'cancel' | 'delete' | 'deleteLine' | null>(null);
  const [lineToDelete, setLineToDelete] = useState<string | null>(null);
  const [formError, setFormError] = useState<string>('');

  const [editForm, setEditForm] = useState<PurchaseUpdateInput>({});
  const [lineForm, setLineForm] = useState<PurchaseLineCreateInput>({
    product_id: '',
    variant_id: null,
    description: '',
    quantity: 1,
    unit_price: 0,
    discount_amount: 0,
    tax_amount: 0,
  });

  const isDraft = purchase?.status === 'DRAFT';
  const canManage = (myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN') && isDraft;

  const loadVariants = useCallback(async (productId: string) => {
    if (!businessId || !productId) return;
    try {
      const res = await apiClient.listProductVariants(businessId, productId);
      const variants = Array.isArray(res) ? res : (res as any).items || [];
      setProductVariants(prev => ({ ...prev, [productId]: variants }));
    } catch {
      setProductVariants(prev => ({ ...prev, [productId]: [] }));
    }
  }, [businessId]);

  const fetchDetail = useCallback(async () => {
    if (!businessId || !purchaseId) return;
    try {
      setIsLoading(true);
      setServerError('');
      const [purData, supData, brData, prodData, membersData] = await Promise.all([
        apiClient.getPurchase(businessId, purchaseId),
        apiClient.listSuppliers(businessId).catch(() => ({ items: [] })),
        apiClient.listBranches(businessId).catch(() => []),
        apiClient.listProducts(businessId, { status: 'ACTIVE', product_type: 'GOODS' }).catch(() => ({ items: [] })),
        apiClient.listBusinessMembers(businessId).catch(() => []),
      ]);
      setPurchase(purData);
      setSuppliers(supData.items || []);
      setBranches(brData || []);
      setProducts(prodData.items || []);
      if (user) {
        const mine = membersData.find((m: any) => m.user_id === user.id);
        setMyMembership(mine || null);
      }
      setEditForm({
        supplier_id: purData.supplier_id,
        branch_id: purData.branch_id,
        purchase_date: purData.purchase_date,
        notes: purData.notes || undefined,
      });
    } catch (err: any) {
      const msg = err?.message || 'Gagal memuat pembelian.';
      if (msg.toLowerCase().includes('unauthorized')) navigate('/login');
      else setServerError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [businessId, purchaseId, user, navigate]);

  useEffect(() => { fetchDetail(); }, [fetchDetail]);

  const showSuccess = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(''), 4000);
  };

  const handleEditHeader = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !purchaseId) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      const payload: PurchaseUpdateInput = {
        supplier_id: editForm.supplier_id,
        branch_id: editForm.branch_id,
        purchase_date: editForm.purchase_date,
        notes: editForm.notes?.trim() || undefined,
      };
      const updated = await apiClient.updatePurchase(businessId, purchaseId, payload);
      setPurchase(updated);
      setIsEditHeaderOpen(false);
      showSuccess('Data pembelian diperbarui.');
    } catch (err: any) {
      setFormError(err?.message || 'Gagal memperbarui pembelian.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddLine = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !purchaseId) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      const payload: PurchaseLineCreateInput = {
        product_id: lineForm.product_id,
        variant_id: lineForm.variant_id || undefined,
        description: lineForm.description?.trim() || undefined,
        quantity: lineForm.quantity,
        unit_price: lineForm.unit_price,
        discount_amount: lineForm.discount_amount || 0,
        tax_amount: lineForm.tax_amount || 0,
      };
      await apiClient.addPurchaseLine(businessId, purchaseId, payload);
      setIsAddLineOpen(false);
      setLineForm({ product_id: '', variant_id: null, description: '', quantity: 1, unit_price: 0, discount_amount: 0, tax_amount: 0 });
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
    if (!businessId || !purchaseId || !editingLine) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      const payload: PurchaseLineUpdateInput = {
        product_id: lineForm.product_id || undefined,
        variant_id: lineForm.variant_id || null,
        description: lineForm.description?.trim() || undefined,
        quantity: lineForm.quantity,
        unit_price: lineForm.unit_price,
        discount_amount: lineForm.discount_amount ?? 0,
        tax_amount: lineForm.tax_amount ?? 0,
      };
      await apiClient.updatePurchaseLine(businessId, purchaseId, editingLine.id, payload);
      setEditingLine(null);
      setLineForm({ product_id: '', variant_id: null, description: '', quantity: 1, unit_price: 0, discount_amount: 0, tax_amount: 0 });
      await fetchDetail();
      showSuccess('Item berhasil diperbarui.');
    } catch (err: any) {
      setFormError(err?.message || 'Gagal memperbarui item.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteLine = async () => {
    if (!businessId || !purchaseId || !lineToDelete) return;
    setIsSubmitting(true);
    try {
      await apiClient.deletePurchaseLine(businessId, purchaseId, lineToDelete);
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
    if (!businessId || !purchaseId) return;
    setIsSubmitting(true);
    try {
      const updated = await apiClient.finalizePurchase(businessId, purchaseId);
      setPurchase(updated);
      setConfirmAction(null);
      showSuccess('Pembelian berhasil difinalisasi.');
    } catch (err: any) {
      setActionError(err?.message || 'Gagal memfinalisasi pembelian.');
      setConfirmAction(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async () => {
    if (!businessId || !purchaseId) return;
    setIsSubmitting(true);
    try {
      const updated = await apiClient.cancelPurchase(businessId, purchaseId);
      setPurchase(updated);
      setConfirmAction(null);
      showSuccess('Pembelian dibatalkan.');
    } catch (err: any) {
      setActionError(err?.message || 'Gagal membatalkan pembelian.');
      setConfirmAction(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteDraft = async () => {
    if (!businessId || !purchaseId) return;
    setIsSubmitting(true);
    try {
      await apiClient.deletePurchase(businessId, purchaseId);
      navigate(`/businesses/${businessId}/purchases`);
    } catch (err: any) {
      setActionError(err?.message || 'Gagal menghapus pembelian.');
      setConfirmAction(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getSupplierName = (id: string) => suppliers.find(s => s.id === id)?.name || id;
  const getBranchName = (id: string) => branches.find(b => b.id === id)?.name || id;
  const getProductName = (id: string) => products.find(p => p.id === id)?.name || id;

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return num.toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  };

  const openEditLine = (line: PurchaseLineResponse) => {
    setEditingLine(line);
    setLineForm({
      product_id: line.product_id,
      variant_id: line.variant_id || null,
      description: line.description || '',
      quantity: parseFloat(String(line.quantity)),
      unit_price: parseFloat(String(line.unit_price)),
      discount_amount: parseFloat(String(line.discount_amount)) || 0,
      tax_amount: parseFloat(String(line.tax_amount)) || 0,
    });
    if (line.product_id) loadVariants(line.product_id);
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-900">
        <Loading size="lg" text="Memuat pembelian..." />
      </div>
    );
  }

  if (serverError && !purchase) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-950">
        <ErrorState message={serverError} onRetry={fetchDetail} />
      </div>
    );
  }

  if (!purchase) return null;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-6">
          <Link
            to={`/businesses/${businessId}/purchases`}
            className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
          >
            &larr; Daftar Pembelian
          </Link>
          <div className="mt-2 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{purchase.purchase_number}</h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {new Date(purchase.purchase_date).toLocaleString('id-ID')}
              </p>
            </div>
            <span className={`inline-flex self-start items-center px-3 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[purchase.status] || ''}`}>
              {purchase.status}
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
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">Informasi Pembelian</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Supplier</dt><dd className="font-medium text-slate-900 dark:text-slate-100">{getSupplierName(purchase.supplier_id)}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Branch</dt><dd className="font-medium text-slate-900 dark:text-slate-100">{getBranchName(purchase.branch_id)}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Tanggal</dt><dd className="text-slate-600 dark:text-slate-300">{new Date(purchase.purchase_date).toLocaleDateString('id-ID')}</dd></div>
              {purchase.notes && (
                <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                  <dt className="text-slate-500 dark:text-slate-400 text-xs">Catatan</dt>
                  <dd className="text-slate-700 dark:text-slate-200 mt-1">{purchase.notes}</dd>
                </div>
              )}
            </dl>
          </Card>

          <Card>
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">Ringkasan Biaya</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Subtotal</dt><dd className="text-slate-900 dark:text-slate-100">Rp {formatCurrency(purchase.subtotal)}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Diskon</dt><dd className="text-rose-600 dark:text-rose-400">- Rp {formatCurrency(purchase.discount_total)}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Pajak</dt><dd className="text-emerald-600 dark:text-emerald-400">+ Rp {formatCurrency(purchase.tax_total)}</dd></div>
              <div className="flex justify-between border-t border-slate-200 dark:border-slate-700 pt-2 font-bold">
                <dt className="text-slate-900 dark:text-slate-100">Grand Total</dt>
                <dd className="text-slate-900 dark:text-slate-100">Rp {formatCurrency(purchase.grand_total)}</dd>
              </div>
            </dl>
          </Card>
        </div>

        {/* Receiving Summary Card */}
        {purchase.receiving_summary && (
          <div className="mb-6">
            <Card>
              <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">Ringkasan Penerimaan</h3>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Total Dipesan</dt><dd className="font-medium text-slate-900 dark:text-slate-100">{purchase.receiving_summary.total_ordered}</dd></div>
                <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Total Diterima</dt><dd className="font-medium text-blue-600 dark:text-blue-400">{purchase.receiving_summary.total_received}</dd></div>
                <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Total Tersisa</dt><dd className="font-medium text-amber-600 dark:text-amber-400">{purchase.receiving_summary.total_remaining}</dd></div>
                <div className="flex justify-between border-t border-slate-200 dark:border-slate-700 pt-2">
                  <dt className="text-slate-500 dark:text-slate-400">Status Penerimaan</dt>
                  <dd>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${RECEIVING_STATUS_COLORS[purchase.receiving_summary.status] || ''}`}>
                      {purchase.receiving_summary.status.replace('_', ' ')}
                    </span>
                  </dd>
                </div>
              </dl>
            </Card>
          </div>
        )}

        {canManage && (
          <div className="mb-6 flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => setIsEditHeaderOpen(true)}>Edit</Button>
            <Button size="sm" onClick={() => { setIsAddLineOpen(true); setFormError(''); }}>Tambah Item</Button>
            <Button size="sm" onClick={() => setConfirmAction('finalize')} className="bg-emerald-600 hover:bg-emerald-700 text-white">Finalisasi</Button>
            <Button variant="outline" size="sm" onClick={() => setConfirmAction('cancel')} className="border-rose-300 text-rose-600 dark:border-rose-800 dark:text-rose-400">Batalkan</Button>
            <Button variant="danger" size="sm" onClick={() => setConfirmAction('delete')}>Hapus Draft</Button>
          </div>
        )}

        <Card>
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-4">Items ({purchase.lines.length})</h3>

          {purchase.lines.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-8">Belum ada item. Tambahkan produk untuk memulai.</p>
          ) : (
            <>
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                      <th className="pb-2 pr-4 font-medium">Produk</th>
                      <th className="pb-2 pr-4 font-medium">Varian</th>
                      <th className="pb-2 pr-4 font-medium text-right">Dipesan</th>
                      <th className="pb-2 pr-4 font-medium text-right">Diterima</th>
                      <th className="pb-2 pr-4 font-medium text-right">Tersisa</th>
                      <th className="pb-2 pr-4 font-medium text-right">Harga</th>
                      <th className="pb-2 pr-4 font-medium text-right">Total</th>
                      {isDraft && <th className="pb-2 font-medium">Aksi</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {purchase.lines.map(line => (
                      <tr key={line.id} className="border-b border-slate-100 dark:border-slate-800">
                        <td className="py-3 pr-4 text-slate-900 dark:text-slate-100">{getProductName(line.product_id)}</td>
                        <td className="py-3 pr-4 text-slate-500 dark:text-slate-400">{line.variant_id ? 'Varian' : '-'}</td>
                        <td className="py-3 pr-4 text-right">{line.ordered_quantity ?? line.quantity}</td>
                        <td className="py-3 pr-4 text-right text-blue-600 dark:text-blue-400">{line.received_quantity ?? '0'}</td>
                        <td className="py-3 pr-4 text-right text-amber-600 dark:text-amber-400">{line.remaining_quantity ?? '0'}</td>
                        <td className="py-3 pr-4 text-right">
                          Rp {formatCurrency(line.unit_price)}
                          {line.suggested_supplier_price && (
                            <div className="text-xs text-green-600 dark:text-green-400 mt-1">
                              Suggestion: Rp {formatCurrency(line.suggested_supplier_price)}
                            </div>
                          )}
                        </td>
                        <td className="py-3 pr-4 text-right font-medium">Rp {formatCurrency(line.line_total)}</td>
                        {isDraft && (
                          <td className="py-3 flex gap-1">
                            <Button variant="outline" size="sm" onClick={() => openEditLine(line)}>Edit</Button>
                            <Button variant="danger" size="sm" onClick={() => { setLineToDelete(line.id); setConfirmAction('deleteLine'); }}>Hapus</Button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="md:hidden space-y-3">
                {purchase.lines.map(line => (
                  <div key={line.id} className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 bg-slate-50 dark:bg-slate-900">
                    <p className="font-medium text-slate-900 dark:text-slate-100">{getProductName(line.product_id)}</p>
                    <div className="mt-1 text-xs text-slate-500 dark:text-slate-400 grid grid-cols-2 gap-1">
                      <span>Dipesan: {line.ordered_quantity ?? line.quantity}</span>
                      <span>Diterima: {line.received_quantity ?? '0'}</span>
                      <span>Tersisa: {line.remaining_quantity ?? '0'}</span>
                      <span>Harga: Rp {formatCurrency(line.unit_price)}</span>
                      <span>Subtotal: Rp {formatCurrency(line.line_subtotal)}</span>
                      <span className="font-medium text-slate-900 dark:text-slate-100">Total: Rp {formatCurrency(line.line_total)}</span>
                    </div>
                    {line.suggested_supplier_price && (
                      <p className="text-xs text-green-600 dark:text-green-400 mt-1">Suggested supplier price: Rp {formatCurrency(line.suggested_supplier_price)}</p>
                    )}
                    {isDraft && (
                      <div className="mt-2 flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => openEditLine(line)}>Edit</Button>
                        <Button variant="danger" size="sm" onClick={() => { setLineToDelete(line.id); setConfirmAction('deleteLine'); }}>Hapus</Button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>

        {/* Edit Header Modal */}
        {isEditHeaderOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4">
            <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-900 shadow-xl p-6 max-h-[90vh] overflow-y-auto">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Edit Pembelian</h2>
              {formError && <p className="mb-3 text-sm text-rose-600 dark:text-rose-400">{formError}</p>}
              <form onSubmit={handleEditHeader} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Supplier *</label>
                  <select
                    required
                    value={editForm.supplier_id || ''}
                    onChange={(e) => setEditForm(f => ({ ...f, supplier_id: e.target.value }))}
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
                    value={editForm.branch_id || ''}
                    onChange={(e) => setEditForm(f => ({ ...f, branch_id: e.target.value }))}
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
                  label="Tanggal *"
                  type="date"
                  value={editForm.purchase_date?.slice(0, 10) || ''}
                  onChange={(e) => setEditForm(f => ({ ...f, purchase_date: new Date(e.target.value).toISOString() }))}
                />
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Catatan</label>
                  <textarea
                    rows={3}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500 resize-y"
                    value={editForm.notes || ''}
                    onChange={(e) => setEditForm(f => ({ ...f, notes: e.target.value }))}
                  />
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="outline" type="button" onClick={() => setIsEditHeaderOpen(false)} disabled={isSubmitting}>Batal</Button>
                  <Button type="submit" isLoading={isSubmitting} disabled={isSubmitting}>Simpan</Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Add Line Modal */}
        {isAddLineOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4">
            <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-900 shadow-xl p-6 max-h-[90vh] overflow-y-auto">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Tambah Item</h2>
              {formError && <p className="mb-3 text-sm text-rose-600 dark:text-rose-400">{formError}</p>}
              <form onSubmit={handleAddLine} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Produk *</label>
                  <select
                    required
                    value={lineForm.product_id}
                    onChange={(e) => {
                      const pid = e.target.value;
                      setLineForm(f => ({ ...f, product_id: pid, variant_id: null }));
                      if (pid) loadVariants(pid);
                    }}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Pilih Produk</option>
                    {products.map(p => (
                      <option key={p.id} value={p.id}>{p.name} ({p.code})</option>
                    ))}
                  </select>
                </div>
                {lineForm.product_id && (productVariants[lineForm.product_id]?.length || 0) > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Varian</label>
                    <select
                      value={lineForm.variant_id || ''}
                      onChange={(e) => setLineForm(f => ({ ...f, variant_id: e.target.value || null }))}
                      className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="">Tanpa Varian</option>
                      {(productVariants[lineForm.product_id] || []).filter(v => v.status === 'ACTIVE').map(v => (
                        <option key={v.id} value={v.id}>{v.name} ({v.code})</option>
                      ))}
                    </select>
                  </div>
                )}
                <Input
                  id="add_quantity"
                  label="Jumlah *"
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
                  value={String(lineForm.unit_price)}
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
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Edit Item</h2>
              {formError && <p className="mb-3 text-sm text-rose-600 dark:text-rose-400">{formError}</p>}
              <form onSubmit={handleUpdateLine} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Produk *</label>
                  <select
                    required
                    value={lineForm.product_id}
                    onChange={(e) => {
                      const pid = e.target.value;
                      setLineForm(f => ({ ...f, product_id: pid, variant_id: null }));
                      if (pid) loadVariants(pid);
                    }}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Pilih Produk</option>
                    {products.map(p => (
                      <option key={p.id} value={p.id}>{p.name} ({p.code})</option>
                    ))}
                  </select>
                </div>
                {lineForm.product_id && (productVariants[lineForm.product_id]?.length || 0) > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Varian</label>
                    <select
                      value={lineForm.variant_id || ''}
                      onChange={(e) => setLineForm(f => ({ ...f, variant_id: e.target.value || null }))}
                      className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="">Tanpa Varian</option>
                      {(productVariants[lineForm.product_id] || []).filter(v => v.status === 'ACTIVE').map(v => (
                        <option key={v.id} value={v.id}>{v.name} ({v.code})</option>
                      ))}
                    </select>
                  </div>
                )}
                <Input
                  id="edit_quantity"
                  label="Jumlah *"
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
                  value={String(lineForm.unit_price)}
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
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Finalisasi Pembelian</h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Apakah Anda yakin ingin memfinalisasi pembelian {purchase.purchase_number}? Tindakan ini tidak dapat dibatalkan.</p>
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
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Batalkan Pembelian</h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Apakah Anda yakin ingin membatalkan pembelian ini?</p>
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
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Apakah Anda yakin ingin menghapus draft pembelian ini?</p>
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
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Apakah Anda yakin ingin menghapus item ini?</p>
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

export default PurchaseDetail;
