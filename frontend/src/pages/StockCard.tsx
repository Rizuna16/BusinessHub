import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { StockCardResponse } from '@/services/apiClient';
import type { Business } from '@/types/business';
import type { InventoryLocation } from '@/types/warehouse';
import type { Product, ProductVariant } from '@/types/product';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';

export const StockCard: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();

  const [business, setBusiness] = useState<Business | null>(null);
  const [locations, setLocations] = useState<InventoryLocation[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [variants, setVariants] = useState<ProductVariant[]>([]);

  const [selectedLocationId, setSelectedLocationId] = useState<string>('');
  const [selectedProductId, setSelectedProductId] = useState<string>('');
  const [selectedVariantId, setSelectedVariantId] = useState<string>('');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [page, setPage] = useState<number>(1);

  const [stockCardData, setStockCardData] = useState<StockCardResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isFetchingReport, setIsFetchingReport] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');

  const fetchInitialData = useCallback(async () => {
    if (!businessId) return;
    setIsLoading(true);
    setErrorMsg('');
    try {
      const bizRes = await apiClient.getBusiness(businessId);
      setBusiness(bizRes);

      const locRes = await apiClient.listWarehouses(businessId);
      const locs: InventoryLocation[] = [];
      for (const wh of locRes) {
        const whLocs = await apiClient.listWareLocations(businessId, wh.id);
        locs.push(...whLocs);
      }
      setLocations(locs);
      if (locs.length > 0) {
        setSelectedLocationId(locs[0].id);
      }

      const prodRes = await apiClient.listProducts(businessId, { page_size: 200 });
      setProducts(prodRes.items || []);
      if (prodRes.items && prodRes.items.length > 0) {
        setSelectedProductId(prodRes.items[0].id);
      }
    } catch (err: unknown) {
      const error = err as { message?: string };
      setErrorMsg(error?.message || 'Failed to load initial master data.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId]);

  useEffect(() => {
    fetchInitialData();
  }, [fetchInitialData]);

  useEffect(() => {
    if (!businessId || !selectedProductId) {
      setVariants([]);
      setSelectedVariantId('');
      return;
    }
    apiClient.listProductVariants(businessId, selectedProductId)
      .then((res) => {
        const itemVariants = res.items || [];
        setVariants(itemVariants);
        if (itemVariants.length > 0) {
          setSelectedVariantId(itemVariants[0].id);
        } else {
          setSelectedVariantId('');
        }
      })
      .catch(() => {
        setVariants([]);
        setSelectedVariantId('');
      });
  }, [businessId, selectedProductId]);

  const fetchStockCard = useCallback(async () => {
    if (!businessId || !selectedLocationId || !selectedProductId) return;
    setIsFetchingReport(true);
    setErrorMsg('');
    try {
      const res = await apiClient.getStockCard(businessId, {
        location_id: selectedLocationId,
        product_id: selectedProductId,
        variant_id: selectedVariantId || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        page,
        page_size: 50,
      });
      setStockCardData(res);
    } catch (err: unknown) {
      const error = err as { message?: string };
      setErrorMsg(error?.message || 'Failed to generate Stock Card report.');
    } finally {
      setIsFetchingReport(false);
    }
  }, [businessId, selectedLocationId, selectedProductId, selectedVariantId, dateFrom, dateTo, page]);

  useEffect(() => {
    if (selectedLocationId && selectedProductId) {
      fetchStockCard();
    }
  }, [fetchStockCard, selectedLocationId, selectedProductId]);

  if (isLoading) {
    return <Loading text="Loading Stock Card Master Data..." />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <nav className="text-sm text-gray-500 mb-1">
            <Link to={`/businesses/${businessId}`} className="hover:underline">
              {business?.name || 'Business'}
            </Link>
            {' / '}
            <Link to={`/businesses/${businessId}/inventory`} className="hover:underline">
              Inventory
            </Link>
            {' / '}
            <span className="text-gray-900 font-medium">Kartu Stok</span>
          </nav>
          <h1 className="text-2xl font-bold text-gray-900">Kartu Stok / Inventory Movement Ledger</h1>
          <p className="text-sm text-gray-500">
            Chronological stock & valuation movement audit trail per location and SKU.
          </p>
        </div>
      </div>

      {errorMsg && <ErrorState message={errorMsg} />}

      {/* Filter Card */}
      <Card className="p-4 bg-white shadow-sm border border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Location *</label>
            <select
              className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:border-indigo-500"
              value={selectedLocationId}
              onChange={(e) => { setSelectedLocationId(e.target.value); setPage(1); }}
            >
              {locations.map((loc) => (
                <option key={loc.id} value={loc.id}>{loc.name} ({loc.code})</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Product *</label>
            <select
              className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:border-indigo-500"
              value={selectedProductId}
              onChange={(e) => { setSelectedProductId(e.target.value); setPage(1); }}
            >
              {products.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.code})</option>
              ))}
            </select>
          </div>

          {variants.length > 0 && (
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Variant SKU *</label>
              <select
                className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:border-indigo-500"
                value={selectedVariantId}
                onChange={(e) => { setSelectedVariantId(e.target.value); setPage(1); }}
              >
                {variants.map((v) => (
                  <option key={v.id} value={v.id}>{v.name} ({v.code})</option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Date From</label>
            <Input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1); }} />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Date To</label>
            <Input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1); }} />
          </div>
        </div>
      </Card>

      {/* Summary KPI Cards */}
      {stockCardData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="p-4 bg-slate-50 border border-slate-200">
            <div className="text-xs text-slate-500 font-medium">Opening Balance</div>
            <div className="text-lg font-bold text-slate-800">
              {Number(stockCardData.opening_quantity).toLocaleString('en-US')} {stockCardData.unit_code || 'pcs'}
            </div>
            <div className="text-xs text-slate-500">
              Valuation: IDR {Number(stockCardData.opening_valuation).toLocaleString('en-US')}
            </div>
          </Card>

          <Card className="p-4 bg-emerald-50 border border-emerald-200">
            <div className="text-xs text-emerald-600 font-medium">Total Inbound (Masuk)</div>
            <div className="text-lg font-bold text-emerald-800">
              +{Number(stockCardData.total_qty_in).toLocaleString('en-US')} {stockCardData.unit_code || 'pcs'}
            </div>
            <div className="text-xs text-emerald-600">
              Value: IDR {Number(stockCardData.total_in_value).toLocaleString('en-US')}
            </div>
          </Card>

          <Card className="p-4 bg-amber-50 border border-amber-200">
            <div className="text-xs text-amber-600 font-medium">Total Outbound (Keluar)</div>
            <div className="text-lg font-bold text-amber-800">
              -{Number(stockCardData.total_qty_out).toLocaleString('en-US')} {stockCardData.unit_code || 'pcs'}
            </div>
            <div className="text-xs text-amber-600">
              Value: IDR {Number(stockCardData.total_out_value).toLocaleString('en-US')}
            </div>
          </Card>

          <Card className="p-4 bg-indigo-50 border border-indigo-200">
            <div className="text-xs text-indigo-600 font-medium">Closing Balance</div>
            <div className="text-lg font-bold text-indigo-900">
              {Number(stockCardData.closing_quantity).toLocaleString('en-US')} {stockCardData.unit_code || 'pcs'}
            </div>
            <div className="text-xs text-indigo-600">
              Valuation: IDR {Number(stockCardData.closing_valuation).toLocaleString('en-US')}
            </div>
          </Card>
        </div>
      )}

      {/* Stock Card Table */}
      <Card className="p-0 overflow-hidden bg-white shadow-sm border border-gray-200">
        {isFetchingReport ? (
          <div className="p-8">
            <Loading text="Computing Stock Card movements..." />
          </div>
        ) : !stockCardData || stockCardData.lines.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No movements found for the selected location, SKU, and date range.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-600">
              <thead className="bg-gray-50 text-xs uppercase text-gray-500 font-semibold border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Ref Number</th>
                  <th className="px-4 py-3 text-right">Qty In</th>
                  <th className="px-4 py-3 text-right">Qty Out</th>
                  <th className="px-4 py-3 text-right">Unit Cost (IDR)</th>
                  <th className="px-4 py-3 text-right">Value (IDR)</th>
                  <th className="px-4 py-3 text-right font-bold text-gray-900">Running Qty</th>
                  <th className="px-4 py-3 text-right font-bold text-gray-900">Running Valuation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {stockCardData.lines.map((line, idx) => {
                  const isIn = Number(line.qty_in) > 0;
                  return (
                    <tr key={idx} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 text-xs text-gray-700 whitespace-nowrap">
                        {new Date(line.transaction_date).toLocaleString('en-US')}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${isIn ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                          {line.movement_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs font-mono text-gray-800 whitespace-nowrap">
                        {line.reference_number || line.reference_id}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-emerald-700">
                        {Number(line.qty_in) > 0 ? `+${Number(line.qty_in).toLocaleString('en-US')}` : '-'}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-amber-700">
                        {Number(line.qty_out) > 0 ? `-${Number(line.qty_out).toLocaleString('en-US')}` : '-'}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-gray-700">
                        {Number(line.unit_cost).toLocaleString('en-US')}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-gray-700">
                        {Number(line.movement_value).toLocaleString('en-US')}
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-bold text-gray-900">
                        {Number(line.running_quantity).toLocaleString('en-US')}
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-bold text-gray-900">
                        {Number(line.running_valuation).toLocaleString('en-US')}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Controls */}
        {stockCardData && stockCardData.total_items > stockCardData.page_size && (
          <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-600">
            <div>
              Showing page {stockCardData.page} of {Math.ceil(stockCardData.total_items / stockCardData.page_size)} (Total {stockCardData.total_items} items)
            </div>
            <div className="flex space-x-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page * stockCardData.page_size >= stockCardData.total_items}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};
