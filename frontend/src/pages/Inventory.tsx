import React, { useState, useCallback, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { Business } from '@/types/business';
import type { BusinessMembership } from '@/types/businessMembership';
import type { InventoryLocation } from '@/types/warehouse';
import type { Product, ProductVariant } from '@/types/product';
import type {
  StockBalance,
  StockMovement,
  OpeningBalancePayload,
  AdjustmentPayload,
  TransferPayload,
  ValuationSummaryResponse,
} from '@/types/inventory';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';

type ActiveTab = 'stock' | 'movements';
type ModalType = 'opening' | 'adjustIn' | 'adjustOut' | 'transfer' | null;

const movementTypeLabel: Record<string, string> = {
  OPENING_BALANCE: 'Opening Balance',
  ADJUSTMENT_IN: 'Adjustment (+)',
  ADJUSTMENT_OUT: 'Adjustment (-)',
  TRANSFER_IN: 'Transfer Masuk',
  TRANSFER_OUT: 'Transfer Keluar',
};

const movementTypeBadge: Record<string, string> = {
  OPENING_BALANCE: 'info',
  ADJUSTMENT_IN: 'success',
  ADJUSTMENT_OUT: 'warning',
  TRANSFER_IN: 'success',
  TRANSFER_OUT: 'warning',
};

export const Inventory: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const { user } = useAuth();

  const [business, setBusiness] = useState<Business | null>(null);
  const [stockBalances, setStockBalances] = useState<StockBalance[]>([]);
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [valuationSummary, setValuationSummary] = useState<ValuationSummaryResponse | null>(null);
  const [allLocations, setAllLocations] = useState<InventoryLocation[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [variants, setVariants] = useState<ProductVariant[]>([]);
  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');
  const [actionError, setActionError] = useState<string>('');
  const [activeTab, setActiveTab] = useState<ActiveTab>('stock');
  const [modalType, setModalType] = useState<ModalType>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string>('');

  const [openingForm, setOpeningForm] = useState<OpeningBalancePayload>({
    inventory_location_id: '',
    product_id: '',
    variant_id: null,
    quantity: '',
    unit_cost: '',
    notes: '',
  });

  const [adjForm, setAdjForm] = useState<AdjustmentPayload>({
    inventory_location_id: '',
    product_id: '',
    variant_id: null,
    quantity: '',
    notes: '',
  });

  const [transferForm, setTransferForm] = useState<TransferPayload>({
    source_inventory_location_id: '',
    destination_inventory_location_id: '',
    product_id: '',
    variant_id: null,
    quantity: '',
    notes: '',
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
      setActionError('');

      const [bizData, whData, prodData, membersData] = await Promise.all([
        apiClient.getBusiness(businessId),
        apiClient.listWarehouses(businessId),
        apiClient.listProducts(businessId, { status: 'ACTIVE', product_type: 'GOODS' }).catch(() => ({ items: [] })),
        apiClient.listBusinessMembers(businessId).catch(() => []),
      ]);

      setBusiness(bizData);
      setProducts(prodData.items || []);

      if (user) {
        const mine = membersData.find((m: any) => m.user_id === user.id);
        setMyMembership(mine || null);
      }

      // Load all locations for all active warehouses
      const locPromises = whData.filter((w: any) => w.status === 'ACTIVE').map((w: any) =>
        apiClient.listWareLocations(businessId, w.id).catch(() => [])
      );
      const locResults = await Promise.all(locPromises);
      const flatLocs = locResults.flat().filter((l: any) => l.status === 'ACTIVE');
      setAllLocations(flatLocs);

      // Load stock, movements, and valuation
      const [stockData, movData, valData] = await Promise.all([
        apiClient.listStockBalances(businessId),
        apiClient.listMovements(businessId),
        apiClient.getValuationSummary(businessId).catch(() => null),
      ]);
      setStockBalances(stockData);
      setMovements(movData);
      setValuationSummary(valData);
    } catch (err: any) {
      const msg = err?.message || 'Failed to load inventory data.';
      if (msg.toLowerCase().includes('unauthorized') || msg.includes('401')) {
        return;
      }
      setServerError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [businessId, user]);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    if (modalType === 'opening' && openingForm.product_id) {
      loadVariants(openingForm.product_id);
    } else if ((modalType === 'adjustIn' || modalType === 'adjustOut') && adjForm.product_id) {
      loadVariants(adjForm.product_id);
    } else if (modalType === 'transfer' && transferForm.product_id) {
      loadVariants(transferForm.product_id);
    }
  }, [modalType, openingForm.product_id, adjForm.product_id, transferForm.product_id, loadVariants]);

  const getLocName = (id: string) => allLocations.find((l) => l.id === id)?.name || id.slice(0, 8);
  const getProductName = (id: string) => products.find((p) => p.id === id)?.name || id.slice(0, 8);
  const getVariantName = (id: string | null) => {
    if (!id) return '-';
    return variants.find((v) => v.id === id)?.name || id.slice(0, 8);
  };

  const validateQty = (qty: string): boolean => {
    const n = parseFloat(qty);
    return !isNaN(n) && n > 0 && isFinite(n);
  };

  const handleOpeningSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    if (!openingForm.inventory_location_id || !openingForm.product_id || !validateQty(String(openingForm.quantity))) {
      setFormError('Lokasi, produk, dan jumlah (> 0) wajib diisi.');
      return;
    }
    setIsSubmitting(true);
    setFormError('');
    try {
      await apiClient.createOpeningBalance(businessId, {
        ...openingForm,
        quantity: parseFloat(String(openingForm.quantity)),
        unit_cost: openingForm.unit_cost ? parseFloat(String(openingForm.unit_cost)) : undefined,
        variant_id: openingForm.variant_id || null,
      });
      setSuccessMsg('Opening balance berhasil dibuat.');
      setModalType(null);
      setTimeout(() => setSuccessMsg(''), 4000);
      fetchData();
    } catch (err: any) {
      setFormError(err?.message || 'Gagal membuat opening balance.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAdjSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !modalType) return;
    if (!adjForm.inventory_location_id || !adjForm.product_id || !validateQty(String(adjForm.quantity))) {
      setFormError('Lokasi, produk, dan jumlah (> 0) wajib diisi.');
      return;
    }
    setIsSubmitting(true);
    setFormError('');
    try {
      const payload: AdjustmentPayload = {
        ...adjForm,
        quantity: parseFloat(String(adjForm.quantity)),
        variant_id: adjForm.variant_id || null,
      };
      if (modalType === 'adjustIn') {
        await apiClient.adjustIn(businessId, payload);
        setSuccessMsg('Adjustment IN berhasil.');
      } else {
        await apiClient.adjustOut(businessId, payload);
        setSuccessMsg('Adjustment OUT berhasil.');
      }
      setModalType(null);
      setTimeout(() => setSuccessMsg(''), 4000);
      fetchData();
    } catch (err: any) {
      setFormError(err?.message || 'Gagal melakukan adjustment.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTransferSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    if (!transferForm.source_inventory_location_id || !transferForm.destination_inventory_location_id || !transferForm.product_id || !validateQty(String(transferForm.quantity))) {
      setFormError('Lokasi sumber, lokasi tujuan, produk, dan jumlah (> 0) wajib diisi.');
      return;
    }
    if (transferForm.source_inventory_location_id === transferForm.destination_inventory_location_id) {
      setFormError('Lokasi sumber dan tujuan harus berbeda.');
      return;
    }
    setIsSubmitting(true);
    setFormError('');
    try {
      await apiClient.createTransfer(businessId, {
        ...transferForm,
        quantity: parseFloat(String(transferForm.quantity)),
        variant_id: transferForm.variant_id || null,
      });
      setSuccessMsg('Transfer berhasil.');
      setModalType(null);
      setTimeout(() => setSuccessMsg(''), 4000);
      fetchData();
    } catch (err: any) {
      setFormError(err?.message || 'Gagal melakukan transfer.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetAllForms = () => {
    setFormError('');
    setModalType(null);
    setOpeningForm({ inventory_location_id: '', product_id: '', variant_id: null, quantity: '', unit_cost: '', notes: '' });
    setAdjForm({ inventory_location_id: '', product_id: '', variant_id: null, quantity: '', notes: '' });
    setTransferForm({ source_inventory_location_id: '', destination_inventory_location_id: '', product_id: '', variant_id: null, quantity: '', notes: '' });
    setVariants([]);
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-950">
        <Loading size="lg" text="Memuat inventaris..." />
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
              <Link to={`/businesses/${businessId}/inventory/stock-opnames`} className="text-indigo-600 dark:text-indigo-400 hover:underline font-medium">
                Stock Opname &rarr;
              </Link>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              Inventaris & Stok
            </h1>
            {business && (
              <p className="text-sm text-slate-500 dark:text-slate-400">{business.name}</p>
            )}
          </div>
          {canManage && (
            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={() => { resetAllForms(); setModalType('opening'); }}>
                + Opening Balance
              </Button>
              <Button size="sm" variant="outline" onClick={() => { resetAllForms(); setModalType('adjustIn'); }}>
                Adjustment IN
              </Button>
              <Button size="sm" variant="outline" onClick={() => { resetAllForms(); setModalType('adjustOut'); }}>
                Adjustment OUT
              </Button>
              <Button size="sm" variant="outline" onClick={() => { resetAllForms(); setModalType('transfer'); }}>
                Transfer
              </Button>
            </div>
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

        {/* Valuation Summary Widget */}
        {valuationSummary && valuationSummary.items.length > 0 && (
          <div className="mb-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-900/50 dark:bg-emerald-950/30">
            <h2 className="text-sm font-semibold text-emerald-800 dark:text-emerald-200 mb-2">Total Nilai Persediaan (MAC)</h2>
            <p className="text-2xl font-bold text-emerald-700 dark:text-emerald-300">
              Rp {parseFloat(valuationSummary.total_inventory_value).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}
            </p>
            <div className="mt-3 overflow-x-auto text-xs text-emerald-700 dark:text-emerald-300">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="text-left py-1 pr-4">Produk</th>
                    <th className="text-right py-1 pr-4">Qty</th>
                    <th className="text-right py-1 pr-4">Unit Cost</th>
                    <th className="text-right py-1">Total Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {valuationSummary.items.map((item, idx) => (
                    <tr key={idx}>
                      <td className="text-left py-1 pr-4">{item.product_name || item.product_id}{item.variant_name ? ` (${item.variant_name})` : ''}</td>
                      <td className="text-right py-1 pr-4">{parseFloat(item.total_quantity).toLocaleString('id-ID', { maximumFractionDigits: 4 })}</td>
                      <td className="text-right py-1 pr-4">Rp {parseFloat(item.unit_cost).toLocaleString('id-ID', { maximumFractionDigits: 2 })}</td>
                      <td className="text-right py-1">Rp {parseFloat(item.total_cost).toLocaleString('id-ID', { maximumFractionDigits: 2 })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="mb-6 flex gap-1 border-b border-slate-200 dark:border-slate-800">
          <button
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
              activeTab === 'stock'
                ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
            onClick={() => setActiveTab('stock')}
          >
            Stok Saat Ini
          </button>
          <button
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
              activeTab === 'movements'
                ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
            onClick={() => setActiveTab('movements')}
          >
            Riwayat Pergerakan
          </button>
        </div>

        {/* Stock Table */}
        {activeTab === 'stock' && (
          <Card className="p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
                <thead className="border-b border-slate-200 bg-slate-100/70 text-xs font-semibold uppercase text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                  <tr>
                    <th scope="col" className="px-6 py-3.5">Lokasi</th>
                    <th scope="col" className="px-6 py-3.5">Produk</th>
                    <th scope="col" className="px-6 py-3.5">Varian</th>
                    <th scope="col" className="px-6 py-3.5 text-right">Jumlah</th>
                    <th scope="col" className="px-6 py-3.5 text-right">Unit Cost</th>
                    <th scope="col" className="px-6 py-3.5 text-right">Total Cost</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {stockBalances.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-8 text-center text-slate-500 dark:text-slate-400">
                        <EmptyState
                          title="Belum ada stok"
                          description="Buat opening balance untuk mulai mencatat inventaris."
                        />
                      </td>
                    </tr>
                  ) : (
                    stockBalances.map((sb) => {
                      // Find matching valuation item
                      const valItem = valuationSummary?.items.find(
                        (vi) => vi.product_id === sb.product_id && (vi.variant_id || null) === (sb.variant_id || null)
                      );
                      return (
                        <tr key={sb.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition-colors">
                          <td className="px-6 py-4 text-xs">{getLocName(sb.inventory_location_id)}</td>
                          <td className="px-6 py-4 font-medium text-xs">{getProductName(sb.product_id)}</td>
                          <td className="px-6 py-4 text-xs text-slate-500 dark:text-slate-400">{getVariantName(sb.variant_id)}</td>
                          <td className="px-6 py-4 text-right font-mono text-sm font-semibold">
                            {parseFloat(sb.quantity).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 4 })}
                          </td>
                          <td className="px-6 py-4 text-right font-mono text-xs text-slate-600 dark:text-slate-400">
                            {valItem ? `Rp ${parseFloat(valItem.unit_cost).toLocaleString('id-ID', { maximumFractionDigits: 2 })}` : '-'}
                          </td>
                          <td className="px-6 py-4 text-right font-mono text-xs text-slate-600 dark:text-slate-400">
                            {valItem ? `Rp ${parseFloat(valItem.total_cost).toLocaleString('id-ID', { maximumFractionDigits: 2 })}` : '-'}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {/* Movements Table */}
        {activeTab === 'movements' && (
          <Card className="p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
                <thead className="border-b border-slate-200 bg-slate-100/70 text-xs font-semibold uppercase text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                  <tr>
                    <th scope="col" className="px-6 py-3.5">Tanggal</th>
                    <th scope="col" className="px-6 py-3.5">Tipe</th>
                    <th scope="col" className="px-6 py-3.5">Produk</th>
                    <th scope="col" className="px-6 py-3.5">Lokasi</th>
                    <th scope="col" className="px-6 py-3.5">Arah</th>
                    <th scope="col" className="px-6 py-3.5 text-right">Jumlah</th>
                    <th scope="col" className="px-6 py-3.5">Catatan</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {movements.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-8 text-center text-slate-500 dark:text-slate-400">
                        <EmptyState
                          title="Belum ada riwayat pergerakan"
                          description="Riwayat akan muncul setelah ada aktivitas inventaris."
                        />
                      </td>
                    </tr>
                  ) : (
                    movements.map((m) =>
                      m.lines.map((line) => (
                        <tr key={`${m.id}-${line.id}`} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition-colors">
                          <td className="px-6 py-4 text-xs whitespace-nowrap">
                            {new Date(m.created_at).toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' })}
                          </td>
                          <td className="px-6 py-4">
                            <Badge variant={(movementTypeBadge[m.movement_type] as any) || 'neutral'}>
                              {movementTypeLabel[m.movement_type] || m.movement_type}
                            </Badge>
                          </td>
                          <td className="px-6 py-4 text-xs font-medium">{getProductName(line.product_id)}</td>
                          <td className="px-6 py-4 text-xs">{getLocName(line.inventory_location_id)}</td>
                          <td className="px-6 py-4">
                            <span className={`text-xs font-semibold ${line.direction === 'IN' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                              {line.direction === 'IN' ? '+' : '-'}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-right font-mono text-xs">
                            {parseFloat(line.quantity).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 4 })}
                          </td>
                          <td className="px-6 py-4 text-xs text-slate-500 dark:text-slate-400 max-w-[150px] truncate">
                            {m.notes || '-'}
                          </td>
                        </tr>
                      ))
                    )
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {/* Opening Balance Modal */}
        {modalType === 'opening' && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="Opening Balance">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800 max-h-[90vh] overflow-y-auto">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Opening Balance</h2>
              {formError && (
                <div className="mb-4 rounded-lg bg-rose-50 dark:bg-rose-950/40 p-3 text-xs text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900" role="alert">{formError}</div>
              )}
              <form onSubmit={handleOpeningSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Lokasi Inventory *</label>
                  <select className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={openingForm.inventory_location_id} onChange={(e) => setOpeningForm((p) => ({ ...p, inventory_location_id: e.target.value }))} required>
                    <option value="">-- Pilih Lokasi --</option>
                    {allLocations.map((loc) => (<option key={loc.id} value={loc.id}>{loc.name} ({loc.code})</option>))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Produk (GOODS) *</label>
                  <select className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={openingForm.product_id} onChange={(e) => { setOpeningForm((p) => ({ ...p, product_id: e.target.value, variant_id: null })); }} required>
                    <option value="">-- Pilih Produk --</option>
                    {products.map((p) => (<option key={p.id} value={p.id}>{p.name} ({p.code})</option>))}
                  </select>
                </div>
                {variants.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Varian (Opsional)</label>
                    <select className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={openingForm.variant_id || ''} onChange={(e) => setOpeningForm((p) => ({ ...p, variant_id: e.target.value || null }))}>
                      <option value="">-- Tanpa Varian --</option>
                      {variants.map((v) => (<option key={v.id} value={v.id}>{v.name} ({v.code})</option>))}
                    </select>
                  </div>
                )}
                <Input id="opQty" label="Jumlah *" type="number" min="0.0001" step="any" placeholder="Contoh: 100" value={openingForm.quantity as any} onChange={(e) => setOpeningForm((p) => ({ ...p, quantity: e.target.value }))} required />
                <Input id="opCost" label="Harga Pokok Satuan (Unit Cost) *" type="number" min="0" step="any" placeholder="Contoh: 50000 (opsional)" value={openingForm.unit_cost as any} onChange={(e) => setOpeningForm((p) => ({ ...p, unit_cost: e.target.value }))} />
                <Input id="opNotes" label="Catatan (Opsional)" placeholder="Catatan pembukaan stok" value={openingForm.notes || ''} onChange={(e) => setOpeningForm((p) => ({ ...p, notes: e.target.value }))} />
                <div className="mt-6 flex justify-end gap-3">
                  <Button type="button" variant="outline" size="sm" onClick={resetAllForms} disabled={isSubmitting}>Batal</Button>
                  <Button type="submit" size="sm" isLoading={isSubmitting}>Buat Opening Balance</Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Adjustment Modals */}
        {(modalType === 'adjustIn' || modalType === 'adjustOut') && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label={modalType === 'adjustIn' ? 'Adjustment IN' : 'Adjustment OUT'}>
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800 max-h-[90vh] overflow-y-auto">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">{modalType === 'adjustIn' ? 'Adjustment IN' : 'Adjustment OUT'}</h2>
              {formError && (
                <div className="mb-4 rounded-lg bg-rose-50 dark:bg-rose-950/40 p-3 text-xs text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900" role="alert">{formError}</div>
              )}
              <form onSubmit={handleAdjSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Lokasi Inventory *</label>
                  <select className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={adjForm.inventory_location_id} onChange={(e) => setAdjForm((p) => ({ ...p, inventory_location_id: e.target.value }))} required>
                    <option value="">-- Pilih Lokasi --</option>
                    {allLocations.map((loc) => (<option key={loc.id} value={loc.id}>{loc.name} ({loc.code})</option>))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Produk (GOODS) *</label>
                  <select className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={adjForm.product_id} onChange={(e) => { setAdjForm((p) => ({ ...p, product_id: e.target.value, variant_id: null })); }} required>
                    <option value="">-- Pilih Produk --</option>
                    {products.map((p) => (<option key={p.id} value={p.id}>{p.name} ({p.code})</option>))}
                  </select>
                </div>
                {variants.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Varian (Opsional)</label>
                    <select className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={adjForm.variant_id || ''} onChange={(e) => setAdjForm((p) => ({ ...p, variant_id: e.target.value || null }))}>
                      <option value="">-- Tanpa Varian --</option>
                      {variants.map((v) => (<option key={v.id} value={v.id}>{v.name} ({v.code})</option>))}
                    </select>
                  </div>
                )}
                <Input id="adjQty" label="Jumlah *" type="number" min="0.0001" step="any" placeholder="Contoh: 10" value={adjForm.quantity as any} onChange={(e) => setAdjForm((p) => ({ ...p, quantity: e.target.value }))} required />
                <Input id="adjNotes" label="Catatan (Opsional)" placeholder="Alasan adjustment" value={adjForm.notes || ''} onChange={(e) => setAdjForm((p) => ({ ...p, notes: e.target.value }))} />
                <div className="mt-6 flex justify-end gap-3">
                  <Button type="button" variant="outline" size="sm" onClick={resetAllForms} disabled={isSubmitting}>Batal</Button>
                  <Button type="submit" size="sm" variant={modalType === 'adjustOut' ? 'danger' : 'primary'} isLoading={isSubmitting}>
                    {modalType === 'adjustIn' ? 'Tambah Stok (IN)' : 'Kurangi Stok (OUT)'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Transfer Modal */}
        {modalType === 'transfer' && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="Transfer Stok">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800 max-h-[90vh] overflow-y-auto">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">Transfer Stok</h2>
              {formError && (
                <div className="mb-4 rounded-lg bg-rose-50 dark:bg-rose-950/40 p-3 text-xs text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900" role="alert">{formError}</div>
              )}
              <form onSubmit={handleTransferSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Lokasi Sumber *</label>
                  <select className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={transferForm.source_inventory_location_id} onChange={(e) => setTransferForm((p) => ({ ...p, source_inventory_location_id: e.target.value }))} required>
                    <option value="">-- Pilih Lokasi Sumber --</option>
                    {allLocations.map((loc) => (<option key={loc.id} value={loc.id}>{loc.name} ({loc.code})</option>))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Lokasi Tujuan *</label>
                  <select className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={transferForm.destination_inventory_location_id} onChange={(e) => setTransferForm((p) => ({ ...p, destination_inventory_location_id: e.target.value }))} required>
                    <option value="">-- Pilih Lokasi Tujuan --</option>
                    {allLocations.filter((l) => l.id !== transferForm.source_inventory_location_id).map((loc) => (<option key={loc.id} value={loc.id}>{loc.name} ({loc.code})</option>))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Produk (GOODS) *</label>
                  <select className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={transferForm.product_id} onChange={(e) => { setTransferForm((p) => ({ ...p, product_id: e.target.value, variant_id: null })); }} required>
                    <option value="">-- Pilih Produk --</option>
                    {products.map((p) => (<option key={p.id} value={p.id}>{p.name} ({p.code})</option>))}
                  </select>
                </div>
                {variants.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Varian (Opsional)</label>
                    <select className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500" value={transferForm.variant_id || ''} onChange={(e) => setTransferForm((p) => ({ ...p, variant_id: e.target.value || null }))}>
                      <option value="">-- Tanpa Varian --</option>
                      {variants.map((v) => (<option key={v.id} value={v.id}>{v.name} ({v.code})</option>))}
                    </select>
                  </div>
                )}
                <Input id="tfQty" label="Jumlah *" type="number" min="0.0001" step="any" placeholder="Contoh: 10" value={transferForm.quantity as any} onChange={(e) => setTransferForm((p) => ({ ...p, quantity: e.target.value }))} required />
                <Input id="tfNotes" label="Catatan (Opsional)" placeholder="Alasan transfer" value={transferForm.notes || ''} onChange={(e) => setTransferForm((p) => ({ ...p, notes: e.target.value }))} />
                <div className="mt-6 flex justify-end gap-3">
                  <Button type="button" variant="outline" size="sm" onClick={resetAllForms} disabled={isSubmitting}>Batal</Button>
                  <Button type="submit" size="sm" isLoading={isSubmitting}>Transfer Stok</Button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Inventory;
