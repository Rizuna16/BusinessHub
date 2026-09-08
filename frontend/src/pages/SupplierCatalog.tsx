import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { SupplierCatalogItem } from '@/types/supplierCatalog';
import type { Supplier } from '@/types/supplier';
import type { Product, ProductVariant } from '@/types/product';
import type { BusinessMembership } from '@/types/businessMembership';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';

export const SupplierCatalog: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [items, setItems] = useState<SupplierCatalogItem[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [variants, setVariants] = useState<ProductVariant[]>([]);
  const [role, setRole] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [archiveConfirm, setArchiveConfirm] = useState<SupplierCatalogItem | null>(null);

  // Search & Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [supplierFilter, setSupplierFilter] = useState<string>('');
  const [preferredFilter, setPreferredFilter] = useState<string>('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  // Form State
  const [targetType, setTargetType] = useState<'PRODUCT' | 'VARIANT'>('PRODUCT');
  const [formData, setFormData] = useState<{
    supplier_id: string;
    product_id: string;
    variant_id: string;
    supplier_code: string;
    supplier_product_name: string;
    purchase_price: string;
    currency: string;
    minimum_order_quantity: string;
    lead_time_days: string;
    is_preferred: boolean;
    notes: string;
  }>({
    supplier_id: '',
    product_id: '',
    variant_id: '',
    supplier_code: '',
    supplier_product_name: '',
    purchase_price: '0',
    currency: 'IDR',
    minimum_order_quantity: '',
    lead_time_days: '',
    is_preferred: false,
    notes: '',
  });

  const canManage = role === 'OWNER' || role === 'ADMIN';

  const loadData = useCallback(async () => {
    if (!businessId || !user) return;
    setIsLoading(true);
    setError(null);
    try {
      const members = await apiClient.listBusinessMembers(businessId);
      const myMembership = members.find((m: BusinessMembership) => m.user_id === user.id);
      if (myMembership) setRole(myMembership.role);

      const params: any = { page, page_size: pageSize };
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;
      if (supplierFilter) params.supplier_id = supplierFilter;
      if (preferredFilter !== '') params.is_preferred = preferredFilter === 'true';

      const res = await apiClient.listSupplierCatalogItems(businessId, params);
      setItems(res.items);
      setTotal(res.total);
    } catch (err: any) {
      setError(err.message || 'Failed to load supplier catalog.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, user, page, search, statusFilter, supplierFilter, preferredFilter]);

  const loadDropdowns = useCallback(async () => {
    if (!businessId) return;
    try {
      const supsRes = await apiClient.listSuppliers(businessId, { status: 'ACTIVE' });
      setSuppliers(supsRes.items);

      const prodsRes = await apiClient.listProducts(businessId, { status: 'ACTIVE' });
      const goodsProds = prodsRes.items.filter((p: Product) => p.product_type === 'GOODS');
      setProducts(goodsProds);

      const variantLists: ProductVariant[] = [];
      for (const p of goodsProds.slice(0, 10)) {
        try {
          const varsRes = await apiClient.listProductVariants(businessId, p.id);
          const list = (varsRes as any)?.items ?? (Array.isArray(varsRes) ? varsRes : []);
          variantLists.push(...list.filter((v: ProductVariant) => v.status === 'ACTIVE'));
        } catch {
        }
      }
      setVariants(variantLists);
    } catch (e) {
      // Ignore background fetch error
    }
  }, [businessId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    loadDropdowns();
  }, [loadDropdowns]);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;

    if (!formData.supplier_id) {
      setFormError('Please select a supplier.');
      return;
    }

    if (targetType === 'PRODUCT' && !formData.product_id) {
      setFormError('Please select a product target.');
      return;
    }
    if (targetType === 'VARIANT' && !formData.variant_id) {
      setFormError('Please select a product variant target.');
      return;
    }

    const price = parseFloat(formData.purchase_price);
    if (isNaN(price) || price < 0) {
      setFormError('Purchase price must be a valid number >= 0.');
      return;
    }

    setFormError(null);
    setIsSubmitting(true);

    try {
      await apiClient.createSupplierCatalogItem(businessId, {
        supplier_id: formData.supplier_id,
        product_id: targetType === 'PRODUCT' ? formData.product_id : null,
        variant_id: targetType === 'VARIANT' ? formData.variant_id : null,
        supplier_code: formData.supplier_code.trim() || null,
        supplier_product_name: formData.supplier_product_name.trim() || null,
        purchase_price: formData.purchase_price,
        currency: formData.currency,
        minimum_order_quantity: formData.minimum_order_quantity ? formData.minimum_order_quantity : null,
        lead_time_days: formData.lead_time_days ? parseInt(formData.lead_time_days, 10) : null,
        is_preferred: formData.is_preferred,
        notes: formData.notes.trim() || null,
      });

      setIsModalOpen(false);
      setFormData({
        supplier_id: '',
        product_id: '',
        variant_id: '',
        supplier_code: '',
        supplier_product_name: '',
        purchase_price: '0',
        currency: 'IDR',
        minimum_order_quantity: '',
        lead_time_days: '',
        is_preferred: false,
        notes: '',
      });
      loadData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to create supplier catalog item.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleArchive = async () => {
    if (!businessId || !archiveConfirm) return;
    try {
      await apiClient.archiveSupplierCatalogItem(businessId, archiveConfirm.id);
      setArchiveConfirm(null);
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to archive item.');
    }
  };

  const handleToggleStatus = async (item: SupplierCatalogItem) => {
    if (!businessId || !canManage) return;
    try {
      if (item.status === 'ACTIVE') {
        await apiClient.deactivateSupplierCatalogItem(businessId, item.id);
      } else if (item.status === 'INACTIVE') {
        await apiClient.activateSupplierCatalogItem(businessId, item.id);
      }
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to update item status.');
    }
  };

  if (isLoading && items.length === 0) {
    return <Loading text="Loading Supplier Catalog..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <nav className="flex text-sm text-gray-500 mb-1">
            <Link to={`/businesses/${businessId}`} className="hover:underline">
              Business Detail
            </Link>
            <span className="mx-2">/</span>
            <span className="text-gray-900 font-medium">Supplier Catalog</span>
          </nav>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Supplier Catalog & Pricing</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Procurement master data linking suppliers to products and pricing.
          </p>
        </div>

        {canManage && (
          <Button onClick={() => setIsModalOpen(true)}>
            + Add Catalog Item
          </Button>
        )}
      </div>

      {/* Filters Bar */}
      <Card className="p-4 flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
        <div className="flex flex-wrap gap-3 w-full md:w-auto">
          <Input
            placeholder="Search code / name..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full sm:w-64"
          />

          <select
            value={supplierFilter}
            onChange={(e) => {
              setSupplierFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 border rounded-md text-sm bg-white dark:bg-gray-800 dark:border-gray-700"
          >
            <option value="">All Suppliers</option>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>

          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 border rounded-md text-sm bg-white dark:bg-gray-800 dark:border-gray-700"
          >
            <option value="">All Statuses</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="INACTIVE">INACTIVE</option>
            <option value="ARCHIVED">ARCHIVED</option>
          </select>

          <select
            value={preferredFilter}
            onChange={(e) => {
              setPreferredFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 border rounded-md text-sm bg-white dark:bg-gray-800 dark:border-gray-700"
          >
            <option value="">All Preferences</option>
            <option value="true">Preferred Only</option>
            <option value="false">Non-Preferred Only</option>
          </select>
        </div>
      </Card>

      {/* Content */}
      {items.length === 0 ? (
        <EmptyState
          title="No Supplier Catalog Items"
          description="Start by adding procurement reference data for your active suppliers and products."
          action={
            canManage ? (
              <Button onClick={() => setIsModalOpen(true)}>Add Catalog Item</Button>
            ) : undefined
          }
        />
      ) : (
        <div className="space-y-4">
          {/* Desktop Table View */}
          <div className="hidden md:block overflow-x-auto bg-white dark:bg-gray-800 shadow rounded-lg border border-gray-200 dark:border-gray-700">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-left text-sm">
              <thead className="bg-gray-50 dark:bg-gray-900 text-gray-600 dark:text-gray-300 uppercase font-medium text-xs">
                <tr>
                  <th className="px-4 py-3">Supplier</th>
                  <th className="px-4 py-3">Target Product / Variant</th>
                  <th className="px-4 py-3">Supplier Code / Name</th>
                  <th className="px-4 py-3 text-right">Purchase Price</th>
                  <th className="px-4 py-3">MOQ</th>
                  <th className="px-4 py-3">Lead Time</th>
                  <th className="px-4 py-3">Preferred</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-750 transition">
                    <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                      {item.supplier_name || item.supplier_id}
                    </td>
                    <td className="px-4 py-3">
                      {item.variant_name ? (
                        <div>
                          <span className="font-semibold">{item.variant_name}</span>
                          <span className="text-xs text-gray-500 block">
                            Variant of {item.product_name} ({item.variant_code})
                          </span>
                        </div>
                      ) : (
                        <div>
                          <span className="font-semibold">{item.product_name}</span>
                          <span className="text-xs text-gray-500 block">
                            Code: {item.product_code}
                          </span>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <span>{item.supplier_product_name || '-'}</span>
                        <span className="text-xs text-gray-500 block">
                          {item.supplier_code ? `SKU: ${item.supplier_code}` : ''}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-medium">
                      {item.currency} {parseFloat(item.purchase_price).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      {item.minimum_order_quantity ? `${item.minimum_order_quantity}` : '-'}
                    </td>
                    <td className="px-4 py-3">
                      {item.lead_time_days !== null && item.lead_time_days !== undefined
                        ? `${item.lead_time_days} days`
                        : '-'}
                    </td>
                    <td className="px-4 py-3">
                      {item.is_preferred ? (
                        <Badge variant="success">PREFERRED</Badge>
                      ) : (
                        <span className="text-gray-400 text-xs">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        variant={
                          item.status === 'ACTIVE'
                            ? 'success'
                            : item.status === 'INACTIVE'
                            ? 'warning'
                            : 'neutral'
                        }
                      >
                        {item.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() =>
                          navigate(`/businesses/${businessId}/supplier-catalog/${item.id}`)
                        }
                      >
                        Detail
                      </Button>

                      {canManage && item.status !== 'ARCHIVED' && (
                        <>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleToggleStatus(item)}
                          >
                            {item.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                          </Button>

                          <Button
                            size="sm"
                            variant="danger"
                            onClick={() => setArchiveConfirm(item)}
                          >
                            Archive
                          </Button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile Cards View */}
          <div className="grid grid-cols-1 gap-4 md:hidden">
            {items.map((item) => (
              <Card key={item.id} className="p-4 space-y-3">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-xs font-semibold text-gray-500 uppercase">
                      {item.supplier_name || 'Supplier'}
                    </span>
                    <h3 className="font-bold text-base text-gray-900 dark:text-white">
                      {item.variant_name
                        ? `${item.variant_name} (${item.variant_code})`
                        : `${item.product_name} (${item.product_code})`}
                    </h3>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <Badge
                      variant={
                        item.status === 'ACTIVE'
                          ? 'success'
                          : item.status === 'INACTIVE'
                          ? 'warning'
                          : 'neutral'
                      }
                    >
                      {item.status}
                    </Badge>
                    {item.is_preferred && <Badge variant="success">PREFERRED</Badge>}
                  </div>
                </div>

                <div className="text-sm grid grid-cols-2 gap-2 bg-gray-50 dark:bg-gray-900 p-2 rounded">
                  <div>
                    <span className="text-xs text-gray-500 block">Supplier SKU / Name</span>
                    <span className="font-medium">
                      {item.supplier_code || '-'} / {item.supplier_product_name || '-'}
                    </span>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500 block">Purchase Price</span>
                    <span className="font-mono font-bold text-gray-900 dark:text-white">
                      {item.currency} {parseFloat(item.purchase_price).toLocaleString()}
                    </span>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500 block">MOQ</span>
                    <span>{item.minimum_order_quantity || '-'}</span>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500 block">Lead Time</span>
                    <span>
                      {item.lead_time_days !== null && item.lead_time_days !== undefined
                        ? `${item.lead_time_days} days`
                        : '-'}
                    </span>
                  </div>
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() =>
                      navigate(`/businesses/${businessId}/supplier-catalog/${item.id}`)
                    }
                  >
                    Detail
                  </Button>
                  {canManage && item.status !== 'ARCHIVED' && (
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => setArchiveConfirm(item)}
                    >
                      Archive
                    </Button>
                  )}
                </div>
              </Card>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-between items-center pt-4">
              <span className="text-sm text-gray-500">
                Page {page} of {totalPages} ({total} items)
              </span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modal Add Catalog Item */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-lg w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              Add Supplier Catalog Item
            </h2>

            {formError && (
              <div className="p-3 bg-red-100 text-red-700 rounded text-sm">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4 text-sm">
              <div>
                <label className="block font-medium mb-1">Supplier *</label>
                <select
                  required
                  value={formData.supplier_id}
                  onChange={(e) =>
                    setFormData({ ...formData, supplier_id: e.target.value })
                  }
                  className="w-full p-2 border rounded dark:bg-gray-900"
                >
                  <option value="">Select Supplier</option>
                  {suppliers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-medium mb-1">Target Type *</label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="targetType"
                      value="PRODUCT"
                      checked={targetType === 'PRODUCT'}
                      onChange={() => setTargetType('PRODUCT')}
                    />
                    <span>Product</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="targetType"
                      value="VARIANT"
                      checked={targetType === 'VARIANT'}
                      onChange={() => setTargetType('VARIANT')}
                    />
                    <span>Product Variant</span>
                  </label>
                </div>
              </div>

              {targetType === 'PRODUCT' ? (
                <div>
                  <label className="block font-medium mb-1">Target Product (GOODS only) *</label>
                  <select
                    value={formData.product_id}
                    onChange={(e) =>
                      setFormData({ ...formData, product_id: e.target.value })
                    }
                    className="w-full p-2 border rounded dark:bg-gray-900"
                  >
                    <option value="">Select Product</option>
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.code})
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <div>
                  <label className="block font-medium mb-1">Target Variant *</label>
                  <select
                    value={formData.variant_id}
                    onChange={(e) =>
                      setFormData({ ...formData, variant_id: e.target.value })
                    }
                    className="w-full p-2 border rounded dark:bg-gray-900"
                  >
                    <option value="">Select Variant</option>
                    {variants.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name} ({v.code})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium mb-1">Supplier Product Code</label>
                  <Input
                    placeholder="e.g. SUP-A-001"
                    value={formData.supplier_code}
                    onChange={(e) =>
                      setFormData({ ...formData, supplier_code: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className="block font-medium mb-1">Supplier Product Name</label>
                  <Input
                    placeholder="e.g. T-Shirt 24s"
                    value={formData.supplier_product_name}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        supplier_product_name: e.target.value,
                      })
                    }
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium mb-1">Purchase Price *</label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    required
                    value={formData.purchase_price}
                    onChange={(e) =>
                      setFormData({ ...formData, purchase_price: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className="block font-medium mb-1">Currency *</label>
                  <select
                    value={formData.currency}
                    onChange={(e) =>
                      setFormData({ ...formData, currency: e.target.value })
                    }
                    className="w-full p-2 border rounded dark:bg-gray-900"
                  >
                    <option value="IDR">IDR</option>
                    <option value="USD">USD</option>
                    <option value="SGD">SGD</option>
                    <option value="MYR">MYR</option>
                    <option value="EUR">EUR</option>
                    <option value="JPY">JPY</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium mb-1">Min Order Qty (Optional)</label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0.01"
                    placeholder="e.g. 50"
                    value={formData.minimum_order_quantity}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        minimum_order_quantity: e.target.value,
                      })
                    }
                  />
                </div>
                <div>
                  <label className="block font-medium mb-1">Lead Time Days (Optional)</label>
                  <Input
                    type="number"
                    min="0"
                    placeholder="e.g. 7"
                    value={formData.lead_time_days}
                    onChange={(e) =>
                      setFormData({ ...formData, lead_time_days: e.target.value })
                    }
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="is_preferred"
                  checked={formData.is_preferred}
                  onChange={(e) =>
                    setFormData({ ...formData, is_preferred: e.target.checked })
                  }
                />
                <label htmlFor="is_preferred" className="cursor-pointer font-medium">
                  Set as Preferred Supplier for this item
                </label>
              </div>

              <div>
                <label className="block font-medium mb-1">Notes (Optional)</label>
                <textarea
                  rows={2}
                  className="w-full p-2 border rounded dark:bg-gray-900"
                  value={formData.notes}
                  onChange={(e) =>
                    setFormData({ ...formData, notes: e.target.value })
                  }
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setIsModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? 'Saving...' : 'Save Item'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Archive Modal */}
      {archiveConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">
              Archive Supplier Catalog Item?
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Are you sure you want to archive catalog item for supplier{' '}
              <strong className="text-gray-900 dark:text-white">
                {archiveConfirm.supplier_name || archiveConfirm.supplier_id}
              </strong>
              ? Archived items cannot be modified or reactivated.
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" onClick={() => setArchiveConfirm(null)}>
                Cancel
              </Button>
              <Button variant="danger" onClick={handleArchive}>
                Archive Item
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
