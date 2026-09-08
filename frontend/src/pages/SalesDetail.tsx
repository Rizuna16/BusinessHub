import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { BusinessMembership } from '@/types/businessMembership';
import type { Customer } from '@/types/customer';
import type { Branch } from '@/types/branch';
import type { Product, ProductVariant } from '@/types/product';
import type {
  SalesResponse,
  SalesLineResponse,
  SalesUpdateInput,
  SalesLineCreateInput,
  SalesLineUpdateInput,
  SalesPayment,
  SalesPaymentSummary,
  CreateSalesPaymentRequest,
  PaymentMethod,
} from '@/types/sales';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { Badge } from '@/components/ui/Badge';
import { useAuth } from '@/context/AuthContext';
import type { Warehouse, InventoryLocation } from '@/types/warehouse';

const STATUS_COLORS: Record<string, string> = {
  DRAFT: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800',
  FINALIZED: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
  CANCELLED: 'bg-rose-50 text-rose-700 border border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800',
};

export const SalesDetail: React.FC = () => {
  const { businessId, salesId } = useParams<{ businessId: string; salesId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [sales, setSales] = useState<SalesResponse | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
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
  const [editingLine, setEditingLine] = useState<SalesLineResponse | null>(null);
  const [confirmAction, setConfirmAction] = useState<'finalize' | 'cancel' | 'delete' | 'deleteLine' | 'cancelPayment' | 'addPayment' | null>(null);
  const [lineToDelete, setLineToDelete] = useState<string | null>(null);
  const [formError, setFormError] = useState<string>('');
  const [payments, setPayments] = useState<SalesPayment[]>([]);
  const [paymentSummary, setPaymentSummary] = useState<SalesPaymentSummary | null>(null);
  const [isPaymentLoading, setIsPaymentLoading] = useState<boolean>(false);
  const [selectedLocation, setSelectedLocation] = useState<string>('');
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [locations, setLocations] = useState<Record<string, InventoryLocation[]>>({});
  const [paymentForm, setPaymentForm] = useState<CreateSalesPaymentRequest>({
    payment_method: 'CASH',
    amount: '',
    reference_number: '',
    notes: '',
  });

  const [targetType, setTargetType] = useState<'product' | 'variant'>('product');
  const [editForm, setEditForm] = useState<SalesUpdateInput>({});
  const [lineForm, setLineForm] = useState<SalesLineCreateInput>({
    product_id: '',
    variant_id: null,
    description: '',
    quantity: 1,
    unit_price: 0,
    discount_amount: 0,
    tax_amount: 0,
  });

  const isDraft = sales?.status === 'DRAFT';
  const isFinalized = sales?.status === 'FINALIZED';
  const canManage = (myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN') && isDraft;
  const canManagePayments = (myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN') && isFinalized;

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
    if (!businessId || !salesId) return;
    try {
      setIsLoading(true);
      setServerError('');
      const [salesData, custList, brList, prodList, membersData, whList] = await Promise.all([
        apiClient.getSales(businessId, salesId),
        apiClient.listCustomers(businessId).catch(() => ({ items: [] })),
        apiClient.listBranches(businessId).catch(() => []),
        apiClient.listProducts(businessId).catch(() => ({ items: [] })),
        apiClient.listBusinessMembers(businessId).catch(() => []),
        apiClient.listWarehouses(businessId).catch(() => []),
      ]);

      setSales(salesData);
      setCustomers(custList.items || []);
      setBranches(brList || []);
      setProducts(prodList.items || []);
      setWarehouses(whList || []);

      // Load locations for active warehouses
      for (const w of (whList || [])) {
        if (w.status === 'ACTIVE') {
          apiClient.listWareLocations(businessId, w.id).then(locs => {
            setLocations(prev => ({ ...prev, [w.id]: locs || [] }));
          }).catch(() => {});
        }
      }

      if (user) {
        const mine = membersData.find((m: any) => m.user_id === user.id);
        setMyMembership(mine || null);
      }

      setEditForm({
        customer_id: salesData.customer_id || undefined,
        branch_id: salesData.branch_id,
        sales_date: salesData.sales_date,
        notes: salesData.notes || undefined,
      });

      // Load variants for all lines in the sales
      for (const line of salesData.lines) {
        if (line.product_id) {
          loadVariants(line.product_id);
        }
      }
    } catch (err: any) {
      const msg = err?.message || 'Gagal memuat detail penjualan.';
      if (msg.toLowerCase().includes('unauthorized')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [businessId, salesId, user, navigate, loadVariants]);

  useEffect(() => { fetchDetail(); }, [fetchDetail]);

  const fetchPayments = useCallback(async () => {
    if (!businessId || !salesId) return;
    try {
      const res = await apiClient.listSalesPayments(businessId, salesId);
      setPayments(res.items || []);
      setPaymentSummary(res.summary || null);
    } catch (err: any) {
      console.error(err);
      setPayments([]);
      setPaymentSummary(null);
    }
  }, [businessId, salesId]);

  useEffect(() => {
    if (sales?.status === 'FINALIZED') {
      fetchPayments();
    }
  }, [sales, fetchPayments]);

  const handleUpdateHeader = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !salesId) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      const payload: SalesUpdateInput = {
        customer_id: editForm.customer_id || undefined,
        branch_id: editForm.branch_id,
        sales_date: editForm.sales_date,
        notes: editForm.notes?.trim() || undefined,
      };
      const updated = await apiClient.updateSales(businessId, salesId, payload);
      setSales(updated);
      setIsEditHeaderOpen(false);
      setSuccessMsg('Informasi penjualan berhasil diperbarui.');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err: any) {
      setFormError(err?.message || 'Gagal memperbarui header penjualan.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddLine = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !salesId) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      const payload: SalesLineCreateInput = {
        product_id: targetType === 'product' ? lineForm.product_id : undefined,
        variant_id: targetType === 'variant' ? lineForm.variant_id : undefined,
        description: lineForm.description?.trim() || undefined,
        quantity: Number(lineForm.quantity),
        unit_price: Number(lineForm.unit_price),
        discount_amount: Number(lineForm.discount_amount || 0),
        tax_amount: Number(lineForm.tax_amount || 0),
      };
      await apiClient.addSalesLine(businessId, salesId, payload);
      setIsAddLineOpen(false);
      setLineForm({ product_id: '', variant_id: null, description: '', quantity: 1, unit_price: 0, discount_amount: 0, tax_amount: 0 });
      fetchDetail();
      setSuccessMsg('Item berhasil ditambahkan.');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err: any) {
      setFormError(err?.message || 'Gagal menambahkan item.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateLine = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !salesId || !editingLine) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      const payload: SalesLineUpdateInput = {
        product_id: targetType === 'product' ? lineForm.product_id : undefined,
        variant_id: targetType === 'variant' ? lineForm.variant_id : undefined,
        description: lineForm.description?.trim() || undefined,
        quantity: Number(lineForm.quantity),
        unit_price: Number(lineForm.unit_price),
        discount_amount: Number(lineForm.discount_amount || 0),
        tax_amount: Number(lineForm.tax_amount || 0),
      };
      await apiClient.updateSalesLine(businessId, salesId, editingLine.id, payload);
      setEditingLine(null);
      fetchDetail();
      setSuccessMsg('Item berhasil diperbarui.');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err: any) {
      setFormError(err?.message || 'Gagal memperbarui item.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteLine = async () => {
    if (!businessId || !salesId || !lineToDelete) return;
    try {
      await apiClient.deleteSalesLine(businessId, salesId, lineToDelete);
      setLineToDelete(null);
      setConfirmAction(null);
      fetchDetail();
      setSuccessMsg('Item berhasil dihapus.');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err: any) {
      setActionError(err?.message || 'Gagal menghapus item.');
      setTimeout(() => setActionError(''), 4000);
    }
  };

  const handleFinalize = async (locationId?: string) => {
    if (!businessId || !salesId) return;
    try {
      const updated = await apiClient.finalizeSales(businessId, salesId, locationId ? { inventory_location_id: locationId } : undefined);
      setSales(updated);
      setConfirmAction(null);
      setSelectedLocation('');
      fetchPayments();
      setSuccessMsg('Transaksi penjualan berhasil difinalisasi.');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err: any) {
      setActionError(err?.message || 'Gagal memfinalisasi penjualan.');
      setTimeout(() => setActionError(''), 4000);
    }
  };

  const handleCancel = async () => {
    if (!businessId || !salesId) return;
    try {
      const updated = await apiClient.cancelSales(businessId, salesId);
      setSales(updated);
      setConfirmAction(null);
      setSuccessMsg('Transaksi penjualan berhasil dibatalkan.');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err: any) {
      setActionError(err?.message || 'Gagal membatalkan penjualan.');
      setTimeout(() => setActionError(''), 4000);
    }
  };

  const handleDeleteDraft = async () => {
    if (!businessId || !salesId) return;
    try {
      await apiClient.deleteSalesDraft(businessId, salesId);
      navigate(`/businesses/${businessId}/sales`);
    } catch (err: any) {
      setActionError(err?.message || 'Gagal menghapus draft penjualan.');
      setTimeout(() => setActionError(''), 4000);
    }
  };

  const handleAddPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !salesId) return;
    setFormError('');
    setIsPaymentLoading(true);
    try {
      const amount = Number(paymentForm.amount);
      if (amount <= 0) {
        throw new Error('Jumlah pembayaran harus lebih dari 0.');
      }
      await apiClient.createSalesPayment(businessId, salesId, {
        payment_method: paymentForm.payment_method,
        amount: paymentForm.amount,
        reference_number: paymentForm.reference_number?.trim() || undefined,
        notes: paymentForm.notes?.trim() || undefined,
      });
      setPaymentForm({ payment_method: 'CASH', amount: '', reference_number: '', notes: '' });
      fetchPayments();
      fetchDetail();
      setSuccessMsg('Pembayaran berhasil dicatat.');
      setTimeout(() => setSuccessMsg(''), 3000);
      setConfirmAction(null);
    } catch (err: any) {
      setActionError(err?.message || 'Gagal mencatat pembayaran.');
      setTimeout(() => setActionError(''), 4000);
    } finally {
      setIsPaymentLoading(false);
    }
  };

  const handleCancelPayment = async (paymentId: string) => {
    if (!businessId || !salesId) return;
    setActionError('');
    try {
      await apiClient.cancelSalesPayment(businessId, salesId, paymentId);
      fetchPayments();
      setSuccessMsg('Pembayaran berhasil dibatalkan.');
      setTimeout(() => setSuccessMsg(''), 3000);
      setConfirmAction(null);
    } catch (err: any) {
      setActionError(err?.message || 'Gagal membatalkan pembayaran.');
      setTimeout(() => setActionError(''), 4000);
    }
  };

  const getCustomerName = (id?: string | null) => {
    if (!id) return 'Walk-in / Umum';
    return customers.find(c => c.id === id)?.name || id;
  };

  const getBranchName = (id: string) => branches.find(b => b.id === id)?.name || id;
  const getProductName = (id: string) => products.find(p => p.id === id)?.name || id;

  const openEditLine = (line: SalesLineResponse) => {
    setEditingLine(line);
    setTargetType(line.variant_id ? 'variant' : 'product');
    setLineForm({
      product_id: line.product_id,
      variant_id: line.variant_id || null,
      description: line.description || '',
      quantity: Number(line.quantity),
      unit_price: Number(line.unit_price),
      discount_amount: Number(line.discount_amount),
      tax_amount: Number(line.tax_amount),
    });
    if (line.product_id) loadVariants(line.product_id);
    setFormError('');
  };

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '0' : num.toLocaleString('id-ID');
  };

  if (isLoading && !sales) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-950">
        <Loading text="Memuat detail penjualan..." />
      </div>
    );
  }

  if (serverError && !sales) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 px-4 py-8">
        <div className="mx-auto max-w-4xl">
          <ErrorState message={serverError} onRetry={fetchDetail} />
        </div>
      </div>
    );
  }

  if (!sales) return null;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-6">
          <Link
            to={`/businesses/${businessId}/sales`}
            className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
          >
            &larr; Daftar Penjualan
          </Link>
          <div className="mt-2 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{sales.sales_number}</h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {new Date(sales.sales_date).toLocaleString('id-ID')}
              </p>
            </div>
            <span className={`inline-flex self-start items-center px-3 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[sales.status] || ''}`}>
              {sales.status}
            </span>
            <div className="flex gap-2">
              <Link to={`/businesses/${businessId}/sales-returns?sales_id=${sales.id}`}>
                <Button variant="secondary">View Returns</Button>
              </Link>
              {isFinalized && (
                <Link to={`/businesses/${businessId}/receivables/${sales.id}`}>
                  <Button variant="secondary">View Receivable</Button>
                </Link>
              )}
              {(myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN') && isFinalized && (
                <Button 
                  onClick={async () => {
                    try {
                      const res = await apiClient.createSalesReturn(businessId!, { sales_id: sales.id });
                      navigate(`/businesses/${businessId}/sales-returns/${res.id}`);
                    } catch (err: any) {
                      setActionError(err.message || 'Failed to create sales return');
                    }
                  }}
                  variant="secondary"
                >
                  Create Return
                </Button>
              )}
            </div>
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
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">Informasi Penjualan</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Customer</dt><dd className="font-medium text-slate-900 dark:text-slate-100">{getCustomerName(sales.customer_id)}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Branch</dt><dd className="font-medium text-slate-900 dark:text-slate-100">{getBranchName(sales.branch_id)}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Tanggal</dt><dd className="text-slate-600 dark:text-slate-300">{new Date(sales.sales_date).toLocaleDateString('id-ID')}</dd></div>
              {sales.notes && (
                <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                  <dt className="text-slate-500 dark:text-slate-400 text-xs">Catatan</dt>
                  <dd className="text-slate-700 dark:text-slate-200 mt-1">{sales.notes}</dd>
                </div>
              )}
            </dl>
          </Card>

          <Card>
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">Ringkasan Biaya</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Subtotal</dt><dd className="text-slate-900 dark:text-slate-100">Rp {formatCurrency(sales.subtotal)}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Diskon</dt><dd className="text-rose-600 dark:text-rose-400">- Rp {formatCurrency(sales.discount_total)}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Pajak</dt><dd className="text-emerald-600 dark:text-emerald-400">+ Rp {formatCurrency(sales.tax_total)}</dd></div>
              <div className="flex justify-between border-t border-slate-200 dark:border-slate-700 pt-2 font-bold">
                <dt className="text-slate-900 dark:text-slate-100">Grand Total</dt>
                <dd className="text-slate-900 dark:text-slate-100">Rp {formatCurrency(sales.grand_total)}</dd>
              </div>
            </dl>
          </Card>
        </div>

        {isFinalized && paymentSummary && (
          <Card className="mb-6">
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-3">Ringkasan Pembayaran</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Total Penjualan</dt><dd className="text-slate-900 dark:text-slate-100">Rp {formatCurrency(paymentSummary.grand_total)}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500 dark:text-slate-400">Total Dibayar</dt><dd className="text-emerald-600 dark:text-emerald-400 font-medium">Rp {formatCurrency(paymentSummary.total_paid)}</dd></div>
              <div className="flex justify-between border-t border-slate-200 dark:border-slate-700 pt-2 font-bold">
                <dt className="text-slate-900 dark:text-slate-100">Sisa Tagihan</dt>
                <dd className={Number(paymentSummary.remaining_amount) > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}>Rp {formatCurrency(paymentSummary.remaining_amount)}</dd>
              </div>
            </dl>
          </Card>
        )}

        {isFinalized && (
          <Card className="mb-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-slate-900 dark:text-slate-100">Riwayat Pembayaran ({payments.length})</h3>
              {canManagePayments && paymentSummary && Number(paymentSummary.remaining_amount) > 0 && (
                <Button size="sm" onClick={() => setConfirmAction('addPayment')} aria-label="Tambah Pembayaran">Tambah Pembayaran</Button>
              )}
            </div>
            {payments.length === 0 ? (
              <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-8">Belum ada pembayaran.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                      <th className="pb-2 pr-4 font-medium">Nomor Bayar</th>
                      <th className="pb-2 pr-4 font-medium">Tanggal</th>
                      <th className="pb-2 pr-4 font-medium">Metode</th>
                      <th className="pb-2 pr-4 font-medium text-right">Jumlah</th>
                      <th className="pb-2 pr-4 font-medium">Referensi</th>
                      <th className="pb-2 pr-4 font-medium">Status</th>
                      {canManagePayments && <th className="pb-2 font-medium">Aksi</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {payments.map(p => (
                      <tr key={p.id} className="border-b border-slate-100 dark:border-slate-800">
                        <td className="py-3 pr-4 text-slate-900 dark:text-slate-100">{p.payment_number}</td>
                        <td className="py-3 pr-4 text-slate-600 dark:text-slate-300">{new Date(p.payment_date).toLocaleDateString('id-ID')}</td>
                        <td className="py-3 pr-4">{p.payment_method}</td>
                        <td className="py-3 pr-4 text-right font-medium">Rp {formatCurrency(p.amount)}</td>
                        <td className="py-3 pr-4 text-slate-500 dark:text-slate-400">{p.reference_number || '-'}</td>
                        <td className="py-3 pr-4">
                          <Badge variant={p.status === 'RECORDED' ? 'success' : 'error'} size="sm">{p.status}</Badge>
                        </td>
                        {canManagePayments && (
                          <td className="py-3">
                            {p.status === 'RECORDED' && (
                              <Button variant="danger" size="sm" onClick={() => { setLineToDelete(p.id); setConfirmAction('cancelPayment'); }} aria-label={`Batalkan ${p.payment_number}`}>Batalkan</Button>
                            )}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
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
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-4">Items ({sales.lines.length})</h3>

          {sales.lines.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-8">Belum ada item. Tambahkan produk untuk memulai.</p>
          ) : (
            <>
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                      <th className="pb-2 pr-4 font-medium">Produk / Varian</th>
                      <th className="pb-2 pr-4 font-medium text-right">Jumlah</th>
                      <th className="pb-2 pr-4 font-medium text-right">Harga</th>
                      <th className="pb-2 pr-4 font-medium text-right">Diskon</th>
                      <th className="pb-2 pr-4 font-medium text-right">Pajak</th>
                      <th className="pb-2 pr-4 font-medium text-right">Total</th>
                      {isDraft && <th className="pb-2 font-medium">Aksi</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {sales.lines.map(line => (
                      <tr key={line.id} className="border-b border-slate-100 dark:border-slate-800">
                        <td className="py-3 pr-4 text-slate-900 dark:text-slate-100">
                          {getProductName(line.product_id || '')}
                          {line.variant_id && (
                            <span className="ml-1 text-xs text-slate-400 block">Varian ID: {line.variant_id}</span>
                          )}
                        </td>
                        <td className="py-3 pr-4 text-right">{line.quantity}</td>
                        <td className="py-3 pr-4 text-right">
                          Rp {formatCurrency(line.unit_price)}
                          {line.suggested_selling_price && (
                            <div className="text-xs text-green-600 dark:text-green-400 mt-0.5">
                              Saran Harga: Rp {formatCurrency(line.suggested_selling_price)}
                            </div>
                          )}
                        </td>
                        <td className="py-3 pr-4 text-right text-rose-600 dark:text-rose-400">- Rp {formatCurrency(line.discount_amount)}</td>
                        <td className="py-3 pr-4 text-right text-emerald-600 dark:text-emerald-400">+ Rp {formatCurrency(line.tax_amount)}</td>
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
                {sales.lines.map(line => (
                  <div key={line.id} className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 bg-slate-50 dark:bg-slate-900">
                    <p className="font-medium text-slate-900 dark:text-slate-100">{getProductName(line.product_id || '')}</p>
                    <div className="mt-1 text-xs text-slate-500 dark:text-slate-400 grid grid-cols-2 gap-1">
                      <span>Jumlah: {line.quantity}</span>
                      <span>Harga: Rp {formatCurrency(line.unit_price)}</span>
                      <span>Diskon: Rp {formatCurrency(line.discount_amount)}</span>
                      <span>Pajak: Rp {formatCurrency(line.tax_amount)}</span>
                      <span className="col-span-2 font-medium text-slate-900 dark:text-slate-100 mt-1 pt-1 border-t border-slate-200 dark:border-slate-800">
                        Total: Rp {formatCurrency(line.line_total)}
                      </span>
                    </div>
                    {line.suggested_selling_price && (
                      <p className="text-xs text-green-600 dark:text-green-400 mt-1">Saran Harga: Rp {formatCurrency(line.suggested_selling_price)}</p>
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

        {/* Modal Edit Header */}
        {isEditHeaderOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4">
            <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-900 shadow-xl p-6">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Edit Informasi Penjualan</h2>
              {formError && <p className="mb-3 text-sm text-rose-600 dark:text-rose-400">{formError}</p>}
              <form onSubmit={handleUpdateHeader} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Customer (Opsional / Walk-in)</label>
                  <select
                    value={editForm.customer_id || ''}
                    onChange={(e) => setEditForm(f => ({ ...f, customer_id: e.target.value || undefined }))}
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

                <div>
                  <label htmlFor="edit_sales_date" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Tanggal *</label>
                  <input
                    type="date"
                    id="edit_sales_date"
                    value={editForm.sales_date?.slice(0, 10) || ''}
                    onChange={(e) => setEditForm(f => ({ ...f, sales_date: new Date(e.target.value).toISOString() }))}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label htmlFor="edit_notes" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Catatan</label>
                  <textarea
                    id="edit_notes"
                    rows={3}
                    value={editForm.notes || ''}
                    onChange={(e) => setEditForm(f => ({ ...f, notes: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
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

        {/* Modal Tambah Item */}
        {isAddLineOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4">
            <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-900 shadow-xl p-6 max-h-[90vh] overflow-y-auto">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Tambah Item Penjualan</h2>
              {formError && <p className="mb-3 text-sm text-rose-600 dark:text-rose-400">{formError}</p>}
              <form onSubmit={handleAddLine} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Target Item</label>
                  <div className="flex gap-4 mb-2">
                    <label className="flex items-center gap-1.5 text-sm">
                      <input
                        type="radio"
                        name="targetType"
                        value="product"
                        checked={targetType === 'product'}
                        onChange={() => setTargetType('product')}
                      />
                      Produk Standar
                    </label>
                    <label className="flex items-center gap-1.5 text-sm">
                      <input
                        type="radio"
                        name="targetType"
                        value="variant"
                        checked={targetType === 'variant'}
                        onChange={() => setTargetType('variant')}
                      />
                      Varian Produk
                    </label>
                  </div>
                </div>

                {targetType === 'product' ? (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Produk (Barang / Jasa) *</label>
                    <select
                      required
                      value={lineForm.product_id || ''}
                      onChange={(e) => setLineForm(f => ({ ...f, product_id: e.target.value, variant_id: null }))}
                      className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="">Pilih Produk</option>
                      {products.filter(p => p.status === 'ACTIVE').map(p => (
                        <option key={p.id} value={p.id}>{p.name} ({p.code}) [{p.product_type}]</option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Pilih Produk Induk Dulu</label>
                    <select
                      value={lineForm.product_id || ''}
                      onChange={(e) => {
                        const pid = e.target.value;
                        setLineForm(f => ({ ...f, product_id: pid, variant_id: null }));
                        if (pid) loadVariants(pid);
                      }}
                      className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500 mb-2"
                    >
                      <option value="">Pilih Produk Induk</option>
                      {products.filter(p => p.status === 'ACTIVE' && p.product_type === 'GOODS').map(p => (
                        <option key={p.id} value={p.id}>{p.name} ({p.code})</option>
                      ))}
                    </select>

                    {lineForm.product_id && (
                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Varian *</label>
                        <select
                          required
                          value={lineForm.variant_id || ''}
                          onChange={(e) => setLineForm(f => ({ ...f, variant_id: e.target.value || null }))}
                          className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                        >
                          <option value="">Pilih Varian</option>
                          {(productVariants[lineForm.product_id] || []).filter(v => v.status === 'ACTIVE').map(v => (
                            <option key={v.id} value={v.id}>{v.name} ({v.code})</option>
                          ))}
                        </select>
                      </div>
                    )}
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
                  label="Diskon (Rp)"
                  type="number"
                  min="0"
                  step="any"
                  value={String(lineForm.discount_amount || 0)}
                  onChange={(e) => setLineForm(f => ({ ...f, discount_amount: parseFloat(e.target.value) || 0 }))}
                />
                <Input
                  id="add_tax"
                  label="Pajak (Rp)"
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

        {/* Modal Edit Item */}
        {editingLine && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4">
            <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-900 shadow-xl p-6 max-h-[90vh] overflow-y-auto">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Edit Item Penjualan</h2>
              {formError && <p className="mb-3 text-sm text-rose-600 dark:text-rose-400">{formError}</p>}
              <form onSubmit={handleUpdateLine} className="space-y-4">
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
                  label="Diskon (Rp)"
                  type="number"
                  min="0"
                  step="any"
                  value={String(lineForm.discount_amount || 0)}
                  onChange={(e) => setLineForm(f => ({ ...f, discount_amount: parseFloat(e.target.value) || 0 }))}
                />
                <Input
                  id="edit_tax"
                  label="Pajak (Rp)"
                  type="number"
                  min="0"
                  step="any"
                  value={String(lineForm.tax_amount || 0)}
                  onChange={(e) => setLineForm(f => ({ ...f, tax_amount: parseFloat(e.target.value) || 0 }))}
                />
                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="outline" type="button" onClick={() => setEditingLine(null)} disabled={isSubmitting}>Batal</Button>
                  <Button type="submit" isLoading={isSubmitting} disabled={isSubmitting}>Simpan Perubahan</Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal Tambah Pembayaran */}
        {confirmAction === 'addPayment' && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4">
            <div className="w-full max-w-md rounded-xl bg-white dark:bg-slate-900 shadow-xl p-6">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Catat Pembayaran Baru</h2>
              <form onSubmit={handleAddPayment} className="space-y-4">
                <div>
                  <label htmlFor="payment_method" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Metode Pembayaran *</label>
                  <select
                    id="payment_method"
                    value={paymentForm.payment_method}
                    onChange={(e) => setPaymentForm(f => ({ ...f, payment_method: e.target.value as PaymentMethod }))}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="CASH">CASH</option>
                    <option value="BANK_TRANSFER">BANK TRANSFER</option>
                    <option value="DEBIT_CARD">DEBIT CARD</option>
                    <option value="CREDIT_CARD">CREDIT CARD</option>
                    <option value="QRIS">QRIS</option>
                    <option value="E_WALLET">E-WALLET</option>
                    <option value="OTHER">OTHER</option>
                  </select>
                </div>

                <Input
                  id="payment_amount"
                  label={`Jumlah (Sisa Tagihan: Rp ${paymentSummary ? formatCurrency(paymentSummary.remaining_amount) : '0'}) *`}
                  type="number"
                  min="0.01"
                  step="any"
                  value={String(paymentForm.amount)}
                  onChange={(e) => setPaymentForm(f => ({ ...f, amount: e.target.value }))}
                  required
                />

                <Input
                  id="payment_reference"
                  label="Nomor Referensi (Opsional)"
                  value={paymentForm.reference_number || ''}
                  onChange={(e) => setPaymentForm(f => ({ ...f, reference_number: e.target.value }))}
                />

                <div>
                  <label htmlFor="payment_notes" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Catatan (Opsional)</label>
                  <textarea
                    id="payment_notes"
                    rows={2}
                    value={paymentForm.notes || ''}
                    onChange={(e) => setPaymentForm(f => ({ ...f, notes: e.target.value }))}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="outline" type="button" onClick={() => setConfirmAction(null)} disabled={isPaymentLoading}>Batal</Button>
                  <Button type="submit" isLoading={isPaymentLoading} disabled={isPaymentLoading}>Simpan Pembayaran</Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal Konfirmasi */}
        {confirmAction && confirmAction !== 'addPayment' && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70 p-4">
            <div className="w-full max-w-md rounded-xl bg-white dark:bg-slate-900 shadow-xl p-6">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                {confirmAction === 'finalize' && 'Finalisasi Penjualan'}
                {confirmAction === 'cancel' && 'Batalkan Penjualan'}
                {confirmAction === 'delete' && 'Hapus Draft Penjualan'}
                {confirmAction === 'deleteLine' && 'Hapus Item'}
                {confirmAction === 'cancelPayment' && 'Batalkan Pembayaran'}
              </h2>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                {confirmAction === 'finalize' && `Apakah Anda yakin ingin memfinalisasi penjualan ${sales.sales_number}? Tindakan ini tidak dapat dibatalkan.`}
                {confirmAction === 'cancel' && `Apakah Anda yakin ingin membatalkan penjualan ${sales.sales_number}? Tindakan ini bersifat permanen.`}
                {confirmAction === 'delete' && `Apakah Anda yakin ingin menghapus draft penjualan ${sales.sales_number}?`}
                {confirmAction === 'deleteLine' && 'Apakah Anda yakin ingin menghapus item ini dari penjualan?'}
                {confirmAction === 'cancelPayment' && 'Apakah Anda yakin ingin membatalkan pembayaran ini? Pembayaran yang dibatalkan tidak dapat diaktifkan kembali.'}
              </p>

              {confirmAction === 'finalize' && (
                <div className="mt-4">
                  <label htmlFor="inventory_location" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Lokasi Inventaris (Opsional / Default)
                  </label>
                  <select
                    id="inventory_location"
                    value={selectedLocation}
                    onChange={(e) => setSelectedLocation(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Default Gudang & Lokasi</option>
                    {warehouses.filter(w => w.status === 'ACTIVE').flatMap(w => (
                      (locations[w.id] || []).filter(l => l.status === 'ACTIVE').map(l => (
                        <option key={l.id} value={l.id}>
                          {w.name} - {l.name} ({l.code})
                        </option>
                      ))
                    ))}
                  </select>
                </div>
              )}

              <div className="mt-6 flex justify-end gap-2">
                <Button variant="outline" onClick={() => { setConfirmAction(null); setLineToDelete(null); setSelectedLocation(''); }}>Batal</Button>
                {confirmAction === 'finalize' && (
                  <Button onClick={() => handleFinalize(selectedLocation || undefined)} className="bg-emerald-600 hover:bg-emerald-700 text-white">Finalisasi</Button>
                )}
                {confirmAction === 'cancel' && (
                  <Button variant="danger" onClick={handleCancel}>Batalkan Penjualan</Button>
                )}
                {confirmAction === 'delete' && (
                  <Button variant="danger" onClick={handleDeleteDraft}>Hapus Draft</Button>
                )}
                {confirmAction === 'deleteLine' && (
                  <Button variant="danger" onClick={handleDeleteLine}>Hapus Item</Button>
                )}
                {confirmAction === 'cancelPayment' && lineToDelete && (
                  <Button variant="danger" onClick={() => handleCancelPayment(lineToDelete)}>Batalkan Pembayaran</Button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
