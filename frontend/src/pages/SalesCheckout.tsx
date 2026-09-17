import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { Product } from '@/types/product';
import type { Branch } from '@/types/branch';
import type { InventoryLocation } from '@/types/warehouse';
import type { CashAccountResponse } from '@/types/cashAccount';
import type { Customer } from '@/types/customer';
import type { SalesResponse, PaymentMethod } from '@/types/sales';
import type { CashierShift } from '@/types/shift';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import {
  ShoppingCart,
  Search,
  Barcode,
  Trash2,
  Plus,
  Minus,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
  Printer,
  User,
  MapPin,
  Wallet,
  Building,
} from 'lucide-react';

interface CartItem {
  product: Product;
  quantity: number;
  unitPrice: number;
  suggestedPrice?: number;
}

type CheckoutState =
  | 'IDLE'
  | 'CREATING_SALE'
  | 'ADDING_LINES'
  | 'FINALIZING_SALE'
  | 'SALE_FINALIZED'
  | 'RECORDING_PAYMENT'
  | 'COMPLETED'
  | 'PAYMENT_FAILED'
  | 'ERROR';

export const SalesCheckout: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();

  // Operational Context
  const [branches, setBranches] = useState<Branch[]>([]);
  const [selectedBranchId, setSelectedBranchId] = useState<string>('');
  const [locations, setLocations] = useState<InventoryLocation[]>([]);
  const [selectedLocationId, setSelectedLocationId] = useState<string>('');
  const [cashAccounts, setCashAccounts] = useState<CashAccountResponse[]>([]);
  const [selectedCashAccountId, setSelectedCashAccountId] = useState<string>('');
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState<string>('');

  // Catalog & Search
  const [products, setProducts] = useState<Product[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [barcodeInput, setBarcodeInput] = useState<string>('');
  const barcodeInputRef = useRef<HTMLInputElement>(null);

  // Cart State
  const [cart, setCart] = useState<CartItem[]>([]);

  // Payment State
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('CASH');
  const [cashTendered, setCashTendered] = useState<string>('');

  // Checkout & Recovery State
  const [checkoutState, setCheckoutState] = useState<CheckoutState>('IDLE');
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [completedSale, setCompletedSale] = useState<SalesResponse | null>(null);
  const [failedSalesId, setFailedSalesId] = useState<string | null>(null);
  const [failedSalesNumber, setFailedSalesNumber] = useState<string | null>(null);
  const [failedGrandTotal, setFailedGrandTotal] = useState<number>(0);

  // Shift context
  const [activeShift, setActiveShift] = useState<CashierShift | null>(null);

  const [isLoadingMeta, setIsLoadingMeta] = useState<boolean>(true);

  // Load operational metadata
  const loadMetadata = useCallback(async () => {
    if (!businessId) return;
    try {
      setIsLoadingMeta(true);
      setErrorMessage('');
      const [brData, whData, caData, custData, prodData] = await Promise.all([
        apiClient.listBranches(businessId),
        apiClient.listWarehouses(businessId),
        apiClient.listCashAccounts(businessId, { status: 'ACTIVE' }),
        apiClient.listCustomers(businessId, { status: 'ACTIVE' }),
        apiClient.listProducts(businessId, { status: 'ACTIVE', page: 1, page_size: 100 }),
      ]);

      setBranches(brData || []);
      if (brData && brData.length > 0) {
        const defaultBranch = brData.find((b) => b.is_default) || brData[0];
        setSelectedBranchId(defaultBranch.id);
      }

      // Load locations for all warehouses using listWareLocations
      const allLocs: InventoryLocation[] = [];
      for (const wh of whData || []) {
        try {
          const locs = await apiClient.listWareLocations(businessId, wh.id);
          allLocs.push(...(locs || []));
        } catch {
          // ignore location fetch errors per warehouse
        }
      }
      setLocations(allLocs);
      if (allLocs.length > 0) {
        const defLoc = allLocs.find((l) => l.is_default) || allLocs[0];
        setSelectedLocationId(defLoc.id);
      }

      setCashAccounts(caData.items || []);
      if (caData.items && caData.items.length > 0) {
        const defCa = caData.items.find((a) => a.is_default) || caData.items[0];
        setSelectedCashAccountId(defCa.id);
      }

      setCustomers(custData.items || []);
      setProducts(prodData.items || []);

      // Load active shift for selected cash account
      try {
        const shiftRes = await apiClient.listShifts(businessId, { status: 'OPEN' });
        const cashAccount = caData.items?.[0];
        const matchedShift = shiftRes.items?.find(
          (s) => s.status === 'OPEN' && (!cashAccount || s.cash_account_id === (selectedCashAccountId || cashAccount.id))
        );
        setActiveShift(matchedShift || null);
      } catch {
        setActiveShift(null);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal memuat data operasional sales checkout.';
      setErrorMessage(msg);
    } finally {
      setIsLoadingMeta(false);
    }
  }, [businessId]);

  useEffect(() => {
    loadMetadata();
  }, [loadMetadata]);

  // Filter products by search query
  const filteredProducts = products.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Add item to cart
  const addToCart = async (product: Product) => {
    let unitPrice = 0;
    try {
      const lists = await apiClient.listPriceLists(businessId!);
      const defaultList = lists.items.find((l) => l.is_default) || lists.items[0];
      if (defaultList) {
        const entries = await apiClient.listPriceEntries(businessId!, defaultList.id);
        const entry = entries.items.find((e) => e.product_id === product.id);
        if (entry) {
          unitPrice = parseFloat(entry.amount);
        }
      }
    } catch {
      // fallback to 0 if pricing lookup fails
    }

    setCart((prev) => {
      const existing = prev.find((item) => item.product.id === product.id);
      if (existing) {
        return prev.map((item) =>
          item.product.id === product.id ? { ...item, quantity: item.quantity + 1 } : item
        );
      }
      return [...prev, { product, quantity: 1, unitPrice, suggestedPrice: unitPrice }];
    });
  };

  // Handle barcode scanning (Enter key)
  const handleBarcodeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!barcodeInput.trim() || !businessId) return;
    const code = barcodeInput.trim().toUpperCase();
    setBarcodeInput('');

    try {
      // 1. Try barcode lookup via listBarcodes
      const barcodeRes = await apiClient.listBarcodes(businessId, { product_id: undefined }).catch(() => null);
      if (barcodeRes && barcodeRes.items && barcodeRes.items.length > 0) {
        const matchedBarcode = barcodeRes.items.find((b) => b.code.toUpperCase() === code);
        if (matchedBarcode && matchedBarcode.product_id) {
          const prod = products.find((p) => p.id === matchedBarcode.product_id);
          if (prod) {
            addToCart(prod);
            return;
          }
        }
      }

      // 2. Try product code match
      const matchedProd = products.find((p) => p.code.toUpperCase() === code);
      if (matchedProd) {
        addToCart(matchedProd);
        return;
      }

      setErrorMessage(`Produk dengan barcode/kode "${code}" tidak ditemukan.`);
    } catch {
      setErrorMessage(`Gagal mencari barcode "${code}".`);
    }
  };

  // Update cart quantity
  const updateQuantity = (productId: string, delta: number) => {
    setCart((prev) =>
      prev
        .map((item) => {
          if (item.product.id === productId) {
            const newQty = item.quantity + delta;
            return newQty > 0 ? { ...item, quantity: newQty } : null;
          }
          return item;
        })
        .filter(Boolean) as CartItem[]
    );
  };

  // Remove cart item
  const removeFromCart = (productId: string) => {
    setCart((prev) => prev.filter((item) => item.product.id !== productId));
  };

  // Cart Financial Totals
  const subtotal = cart.reduce((sum, item) => sum + item.quantity * item.unitPrice, 0);
  const taxTotal = 0;
  const grandTotal = subtotal;

  const numericTendered = parseFloat(cashTendered) || 0;
  const changeDue = paymentMethod === 'CASH' ? Math.max(0, numericTendered - grandTotal) : 0;

  // --- CHECKOUT ORCHESTRATION ---
  const handleCheckout = async () => {
    if (!businessId || cart.length === 0) return;
    if (!selectedBranchId) {
      setErrorMessage('Pilih cabang operasional terlebih dahulu.');
      return;
    }
    if (!selectedLocationId) {
      setErrorMessage('Pilih lokasi / gudang inventaris untuk pemotongan stok.');
      return;
    }
    if (!selectedCashAccountId) {
      setErrorMessage('Pilih akun kas untuk penerimaan pembayaran.');
      return;
    }
    if (paymentMethod === 'CASH' && numericTendered < grandTotal) {
      setErrorMessage('Jumlah uang tunai yang diterima kurang dari total tagihan.');
      return;
    }
    if (paymentMethod === 'CASH' && !activeShift) {
      setErrorMessage('Tidak ada shift aktif untuk pembayaran tunai. Buka shift terlebih dahulu.');
      return;
    }

    setErrorMessage('');
    setCheckoutState('CREATING_SALE');
    setStatusMessage('Membuat draft penjualan...');

    let createdSalesId: string | null = null;

    try {
      const salesPayload = {
        branch_id: selectedBranchId,
        customer_id: selectedCustomerId ? selectedCustomerId : undefined,
        sales_date: new Date().toISOString(),
        notes: 'Sales Checkout Transaction',
      };
      const saleRes = await apiClient.createSales(businessId, salesPayload);
      createdSalesId = saleRes.id;
      setFailedSalesId(createdSalesId);
      setFailedSalesNumber(saleRes.sales_number);

      setCheckoutState('ADDING_LINES');
      setStatusMessage('Menambahkan item ke transaksi...');
      for (const item of cart) {
        await apiClient.addSalesLine(businessId, createdSalesId, {
          product_id: item.product.id,
          quantity: item.quantity,
          unit_price: item.unitPrice,
          discount_amount: 0,
          tax_amount: 0,
        });
      }

      setCheckoutState('FINALIZING_SALE');
      setStatusMessage('Memproses inventaris & akuntansi...');
      const finalizedRes = await apiClient.finalizeSales(businessId, createdSalesId, {
        inventory_location_id: selectedLocationId,
      });
      setFailedGrandTotal(parseFloat(String(finalizedRes.grand_total)));
      setCheckoutState('SALE_FINALIZED');

      setCheckoutState('RECORDING_PAYMENT');
      setStatusMessage('Mencatat pembayaran kasir...');
      await apiClient.createPayment(businessId, {
        direction: 'CUSTOMER_IN',
        target_type: 'SALES',
        target_id: createdSalesId,
        amount: finalizedRes.grand_total,
        currency: 'IDR',
        payment_method: paymentMethod,
        cash_account_id: selectedCashAccountId,
        notes: `Sales Checkout Payment via ${paymentMethod}`,
        shift_id: paymentMethod === 'CASH' && activeShift ? activeShift.id : undefined,
      });

      setCompletedSale(finalizedRes);
      setCheckoutState('COMPLETED');
      setStatusMessage('Transaksi berhasil diselesaikan!');
      setCart([]);
      setCashTendered('');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Terjadi kesalahan saat memproses transaksi.';
      setErrorMessage(msg);

      if (checkoutState === 'RECORDING_PAYMENT' || checkoutState === 'FINALIZING_SALE') {
        if (createdSalesId) {
          setCheckoutState('PAYMENT_FAILED');
          return;
        }
      }
      setCheckoutState('ERROR');
    }
  };

  const handleRetryPayment = async () => {
    if (!businessId || !failedSalesId) return;
    setErrorMessage('');
    setCheckoutState('RECORDING_PAYMENT');
    setStatusMessage('Mencoba ulang pencatatan pembayaran...');

    try {
      await apiClient.createPayment(businessId, {
        direction: 'CUSTOMER_IN',
        target_type: 'SALES',
        target_id: failedSalesId,
        amount: failedGrandTotal,
        currency: 'IDR',
        payment_method: paymentMethod,
        cash_account_id: selectedCashAccountId,
        notes: `Sales Checkout Retry Payment via ${paymentMethod}`,
        shift_id: paymentMethod === 'CASH' && activeShift ? activeShift.id : undefined,
      });

      const saleDetails = await apiClient.getSales(businessId, failedSalesId);
      setCompletedSale(saleDetails);
      setCheckoutState('COMPLETED');
      setStatusMessage('Pembayaran berhasil dicatat!');
      setCart([]);
      setCashTendered('');
      setFailedSalesId(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal mencoba ulang pembayaran.';
      setErrorMessage(msg);
      setCheckoutState('PAYMENT_FAILED');
    }
  };

  const handleNewSale = () => {
    setCheckoutState('IDLE');
    setCompletedSale(null);
    setFailedSalesId(null);
    setCart([]);
    setCashTendered('');
    setErrorMessage('');
    if (barcodeInputRef.current) {
      barcodeInputRef.current.focus();
    }
  };

  const formatCurrency = (val: number) => {
    return `Rp ${val.toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
  };

  if (isLoadingMeta) {
    return (
      <div className="flex h-96 w-full items-center justify-center">
        <Loading size="lg" text="Memuat terminal sales checkout..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <nav className="flex text-xs text-slate-500 dark:text-slate-400 mb-1">
            <Link to={`/businesses/${businessId}`} className="hover:underline">
              Detail Bisnis
            </Link>
            <span className="mx-2">/</span>
            <span className="text-slate-900 dark:text-slate-100 font-medium">Sales Checkout</span>
          </nav>
          <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <ShoppingCart className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
            Sales Checkout
          </h1>
        </div>

        {/* Operational Selectors Bar */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs bg-slate-100 dark:bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700">
            <Building className="h-3.5 w-3.5 text-slate-400" />
            <select
              value={selectedBranchId}
              onChange={(e) => setSelectedBranchId(e.target.value)}
              className="bg-transparent font-medium focus:outline-none text-slate-800 dark:text-slate-200"
              aria-label="Pilih Cabang"
            >
              {branches.map((b) => (
                <option key={b.id} value={b.id} className="dark:bg-slate-900">
                  Cabang: {b.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-xs bg-slate-100 dark:bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700">
            <MapPin className="h-3.5 w-3.5 text-slate-400" />
            <select
              value={selectedLocationId}
              onChange={(e) => setSelectedLocationId(e.target.value)}
              className="bg-transparent font-medium focus:outline-none text-slate-800 dark:text-slate-200"
              aria-label="Pilih Lokasi Stok"
            >
              {locations.map((l) => (
                <option key={l.id} value={l.id} className="dark:bg-slate-900">
                  Lokasi: {l.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-xs bg-slate-100 dark:bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700">
            <Wallet className="h-3.5 w-3.5 text-slate-400" />
            <select
              value={selectedCashAccountId}
              onChange={(e) => setSelectedCashAccountId(e.target.value)}
              className="bg-transparent font-medium focus:outline-none text-slate-800 dark:text-slate-200"
              aria-label="Pilih Akun Kas"
            >
              {cashAccounts.map((a) => (
                <option key={a.id} value={a.id} className="dark:bg-slate-900">
                  Kas: {a.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Active Shift Info Bar */}
      {activeShift && (
        <div className="flex flex-wrap items-center gap-4 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 px-4 py-2 rounded-lg text-xs">
          <span className="font-semibold text-emerald-800 dark:text-emerald-300">Active Shift:</span>
          <span className="text-emerald-700 dark:text-emerald-400">
            {activeShift.branch_name || activeShift.branch_id} | {activeShift.cash_account_name || activeShift.cash_account_id}
          </span>
          <span className="text-emerald-700 dark:text-emerald-400">
            Opening: {formatCurrency(parseFloat(String(activeShift.opening_balance)))}
          </span>
          <Link
            to={`/businesses/${businessId}/shifts/${activeShift.id}`}
            className="text-emerald-600 dark:text-emerald-400 hover:underline font-medium"
          >
            View Shift
          </Link>
        </div>
      )}
      {!activeShift && paymentMethod === 'CASH' && (
        <div className="flex items-center gap-2 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 px-4 py-2 rounded-lg text-xs">
          <AlertCircle className="h-4 w-4 text-amber-500 flex-shrink-0" />
          <span className="text-amber-800 dark:text-amber-300">
            No active shift for CASH payments.
            <Link to={`/businesses/${businessId}/shifts`} className="ml-1 font-medium underline">
              Open a shift first
            </Link>
          </span>
        </div>
      )}

      {/* Error / Status Messages */}
      {errorMessage && (
        <div className="rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 p-4 text-rose-800 dark:text-rose-200 text-sm flex items-center justify-between gap-3 shadow-sm">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 flex-shrink-0 text-rose-500" />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage('')}
            className="text-xs font-semibold hover:underline px-2 py-1"
          >
            Tutup
          </button>
        </div>
      )}

      {/* COMPLETED SUCCESS RECEIPT VIEW */}
      {checkoutState === 'COMPLETED' && completedSale && (
        <Card className="max-w-2xl mx-auto p-6 space-y-6">
          <div className="text-center space-y-2">
            <CheckCircle2 className="h-16 w-16 text-emerald-500 mx-auto" />
            <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              Transaksi Berhasil!
            </h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Penjualan <span className="font-semibold">{completedSale.sales_number}</span> telah difinalisasi dan pembayaran tercatat.
            </p>
          </div>

          <div className="border-t border-b border-slate-200 dark:border-slate-800 py-4 space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-500">Tanggal:</span>
              <span className="font-medium text-slate-800 dark:text-slate-200">
                {new Date(completedSale.sales_date).toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Pelanggan:</span>
              <span className="font-medium text-slate-800 dark:text-slate-200">
                {completedSale.customer_id
                  ? customers.find((c) => c.id === completedSale.customer_id)?.name || completedSale.customer_id
                  : 'Walk-in / Umum'}
              </span>
            </div>

            <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
              <p className="text-xs font-semibold text-slate-400 uppercase mb-2">Item Pembelian:</p>
              <div className="space-y-1.5">
                {completedSale.lines.map((l) => (
                  <div key={l.id} className="flex justify-between text-xs">
                    <span className="text-slate-700 dark:text-slate-300">
                      {l.description || l.product_id} × {l.quantity}
                    </span>
                    <span className="font-medium text-slate-900 dark:text-slate-100">
                      {formatCurrency(parseFloat(String(l.line_total)))}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex justify-between font-bold text-base">
              <span>Grand Total:</span>
              <span className="text-indigo-600 dark:text-indigo-400">
                {formatCurrency(parseFloat(String(completedSale.grand_total)))}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <Button variant="outline" onClick={() => window.print()} className="flex items-center gap-1.5">
              <Printer className="h-4 w-4" /> Cetak Struk
            </Button>
            <Button variant="primary" onClick={handleNewSale} className="flex items-center gap-1.5">
              <RotateCcw className="h-4 w-4" /> Transaksi Baru
            </Button>
          </div>
        </Card>
      )}

      {/* PAYMENT FAILED RECOVERY VIEW */}
      {checkoutState === 'PAYMENT_FAILED' && (
        <Card className="max-w-xl mx-auto p-6 space-y-4 border-amber-200 dark:border-amber-900/60 bg-amber-50/50 dark:bg-amber-950/20">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-8 w-8 text-amber-600 dark:text-amber-400 flex-shrink-0" />
            <div>
              <h3 className="text-lg font-bold text-amber-900 dark:text-amber-100">
                Penjualan Sukses, Pembayaran Gagal
              </h3>
              <p className="text-xs text-amber-700 dark:text-amber-300">
                Draft penjualan <span className="font-semibold">{failedSalesNumber}</span> telah sukses difinalisasi dan stok telah dipotong, namun pencatatan pembayaran menemui kendala.
              </p>
            </div>
          </div>

          <div className="p-3 bg-white dark:bg-slate-900 rounded-lg border border-amber-200 dark:border-amber-800 text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-500">Nomor Sales:</span>
              <span className="font-mono font-medium">{failedSalesNumber}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Total Tagihan:</span>
              <span className="font-bold text-indigo-600 dark:text-indigo-400">{formatCurrency(failedGrandTotal)}</span>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <Button variant="outline" onClick={handleNewSale}>
              Batal / Transaksi Baru
            </Button>
            <Button variant="primary" onClick={handleRetryPayment}>
              Coba Ulang Pembayaran Saja
            </Button>
          </div>
        </Card>
      )}

      {/* MAIN SALES CHECKOUT SPLIT-SCREEN WORKFLOW */}
      {checkoutState !== 'COMPLETED' && checkoutState !== 'PAYMENT_FAILED' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Product Search & Grid */}
          <div className="lg:col-span-7 space-y-4">
            <Card title="Katalog Produk & Pencarian">
              <div className="space-y-4">
                {/* Barcode & Search inputs */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <form onSubmit={handleBarcodeSubmit} className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <Barcode className="h-4 w-4" />
                    </div>
                    <input
                      ref={barcodeInputRef}
                      type="text"
                      placeholder="Scan barcode / SKU..."
                      value={barcodeInput}
                      onChange={(e) => setBarcodeInput(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-150 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </form>

                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                      <Search className="h-4 w-4" />
                    </div>
                    <Input
                      placeholder="Cari nama produk..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-9"
                    />
                  </div>
                </div>

                {/* Product List / Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[550px] overflow-y-auto pr-1">
                  {filteredProducts.length === 0 ? (
                    <div className="col-span-2 py-12 text-center text-sm text-slate-400">
                      Tidak ada produk yang cocok dengan pencarian.
                    </div>
                  ) : (
                    filteredProducts.map((p) => (
                      <div
                        key={p.id}
                        onClick={() => addToCart(p)}
                        className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-indigo-500 dark:hover:border-indigo-500 cursor-pointer transition-all shadow-2xs hover:shadow-md flex flex-col justify-between gap-2 group"
                      >
                        <div>
                          <div className="flex items-start justify-between gap-2">
                            <h4 className="font-semibold text-sm text-slate-900 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                              {p.name}
                            </h4>
                            <Badge variant="neutral" size="sm">
                              {p.code}
                            </Badge>
                          </div>
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-1">
                            {p.description || 'Barang siap jual'}
                          </p>
                        </div>
                        <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
                          <span className="font-bold text-indigo-600 dark:text-indigo-400">
                            {p.product_type}
                          </span>
                          <span className="text-slate-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 font-medium flex items-center gap-1">
                            + Tambah <Plus className="h-3 w-3" />
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </Card>
          </div>

          {/* Right Column: Cart, Customer & Checkout */}
          <div className="lg:col-span-5 space-y-4">
            <Card title="Keranjang Belanja (Cart)">
              <div className="space-y-4">
                {/* Customer Selector */}
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4 text-slate-400 flex-shrink-0" />
                  <select
                    value={selectedCustomerId}
                    onChange={(e) => setSelectedCustomerId(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                    aria-label="Pilih Pelanggan"
                  >
                    <option value="">Walk-in Customer (Umum)</option>
                    {customers.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.code})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Cart Items List */}
                <div className="divide-y divide-slate-100 dark:divide-slate-800 max-h-[260px] overflow-y-auto pr-1">
                  {cart.length === 0 ? (
                    <div className="py-12 text-center text-sm text-slate-400">
                      Keranjang kosong. Pilih produk dari katalog atau scan barcode.
                    </div>
                  ) : (
                    cart.map((item) => (
                      <div key={item.product.id} className="py-2.5 flex items-center justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <h5 className="font-medium text-xs text-slate-900 dark:text-slate-100 truncate">
                            {item.product.name}
                          </h5>
                          <p className="text-[11px] text-slate-500">
                            {formatCurrency(item.unitPrice)} / unit
                          </p>
                        </div>

                        {/* Quantity Controls */}
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          <button
                            type="button"
                            onClick={() => updateQuantity(item.product.id, -1)}
                            className="w-6 h-6 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 flex items-center justify-center text-slate-700 dark:text-slate-300"
                            aria-label="Kurangi kuantitas"
                          >
                            <Minus className="h-3 w-3" />
                          </button>
                          <span className="w-6 text-center text-xs font-semibold">{item.quantity}</span>
                          <button
                            type="button"
                            onClick={() => updateQuantity(item.product.id, 1)}
                            className="w-6 h-6 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 flex items-center justify-center text-slate-700 dark:text-slate-300"
                            aria-label="Tambah kuantitas"
                          >
                            <Plus className="h-3 w-3" />
                          </button>
                        </div>

                        <div className="text-right flex-shrink-0">
                          <span className="font-semibold text-xs text-slate-900 dark:text-slate-100 block">
                            {formatCurrency(item.quantity * item.unitPrice)}
                          </span>
                          <button
                            type="button"
                            onClick={() => removeFromCart(item.product.id)}
                            className="text-[10px] text-rose-500 hover:underline inline-flex items-center gap-0.5 mt-0.5"
                          >
                            <Trash2 className="h-3 w-3" /> Hapus
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {/* Financial Totals */}
                <div className="pt-3 border-t border-slate-200 dark:border-slate-800 space-y-1.5 text-xs">
                  <div className="flex justify-between text-slate-600 dark:text-slate-400">
                    <span>Subtotal:</span>
                    <span>{formatCurrency(subtotal)}</span>
                  </div>
                  <div className="flex justify-between text-slate-600 dark:text-slate-400">
                    <span>Pajak (Tax):</span>
                    <span>{formatCurrency(taxTotal)}</span>
                  </div>
                  <div className="flex justify-between font-bold text-base text-slate-900 dark:text-slate-100 pt-1.5 border-t border-slate-100 dark:border-slate-800">
                    <span>Grand Total:</span>
                    <span className="text-indigo-600 dark:text-indigo-400">{formatCurrency(grandTotal)}</span>
                  </div>
                </div>

                {/* Payment Options */}
                <div className="space-y-3 pt-2">
                  <div className="flex flex-col gap-1.5">
                    <label htmlFor="payment-method-select" className="text-xs font-medium text-slate-700 dark:text-slate-300">
                      Metode Pembayaran
                    </label>
                    <select
                      id="payment-method-select"
                      value={paymentMethod}
                      onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod)}
                      className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-indigo-500"
                      aria-label="Metode Pembayaran"
                    >
                      <option value="CASH">Tunai (Cash)</option>
                      <option value="QRIS">QRIS</option>
                      <option value="BANK_TRANSFER">Transfer Bank</option>
                      <option value="DEBIT_CARD">Kartu Debit</option>
                      <option value="CREDIT_CARD">Kartu Kredit</option>
                      <option value="E_WALLET">E-Wallet</option>
                      <option value="OTHER">Lainnya</option>
                    </select>
                  </div>

                  {paymentMethod === 'CASH' && (
                    <div className="space-y-1">
                      <Input
                        label="Uang Tunai Diterima (Cash Tendered)"
                        type="number"
                        placeholder="Contoh: 150000"
                        value={cashTendered}
                        onChange={(e) => setCashTendered(e.target.value)}
                      />
                      {numericTendered > 0 && (
                        <div className="flex justify-between text-xs px-1 pt-1">
                          <span className="text-slate-500">Kembalian (Change):</span>
                          <span className={`font-bold ${changeDue >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500'}`}>
                            {formatCurrency(changeDue)}
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Submit / Checkout Button */}
                  <Button
                    variant="primary"
                    className="w-full py-3 text-sm font-bold shadow-md"
                    isLoading={checkoutState !== 'IDLE' && checkoutState !== 'ERROR'}
                    disabled={cart.length === 0}
                    onClick={handleCheckout}
                  >
                    {checkoutState === 'CREATING_SALE' && 'Membuat Transaksi...'}
                    {checkoutState === 'ADDING_LINES' && 'Menambahkan Item...'}
                    {checkoutState === 'FINALIZING_SALE' && 'Memproses Stok & Akuntansi...'}
                    {checkoutState === 'RECORDING_PAYMENT' && 'Mencatat Pembayaran...'}
                    {checkoutState === 'IDLE' && `Bayar & Selesaikan (${formatCurrency(grandTotal)})`}
                    {checkoutState === 'ERROR' && `Coba Ulang (${formatCurrency(grandTotal)})`}
                  </Button>
                  {statusMessage && checkoutState !== 'IDLE' && checkoutState !== 'ERROR' && (
                    <p className="text-[11px] text-center text-indigo-600 dark:text-indigo-400 animate-pulse font-medium">
                      {statusMessage}
                    </p>
                  )}
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
};

export default SalesCheckout;
