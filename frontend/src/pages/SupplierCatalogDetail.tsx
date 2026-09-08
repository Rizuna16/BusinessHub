import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { SupplierCatalogItem } from '@/types/supplierCatalog';
import type { BusinessMembership } from '@/types/businessMembership';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { useAuth } from '@/context/AuthContext';

export const SupplierCatalogDetail: React.FC = () => {
  const { businessId, catalogId } = useParams<{ businessId: string; catalogId: string }>();
  const { user } = useAuth();

  const [item, setItem] = useState<SupplierCatalogItem | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isEditing, setIsEditing] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showArchiveModal, setShowArchiveModal] = useState(false);

  const [formData, setFormData] = useState({
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
    if (!businessId || !catalogId || !user) return;
    setIsLoading(true);
    setError(null);
    try {
      const members = await apiClient.listBusinessMembers(businessId);
      const myMembership = members.find((m: BusinessMembership) => m.user_id === user.id);
      if (myMembership) setRole(myMembership.role);

      const catalogData = await apiClient.getSupplierCatalogItem(businessId, catalogId);
      setItem(catalogData);

      setFormData({
        supplier_code: catalogData.supplier_code || '',
        supplier_product_name: catalogData.supplier_product_name || '',
        purchase_price: catalogData.purchase_price,
        currency: catalogData.currency,
        minimum_order_quantity: catalogData.minimum_order_quantity || '',
        lead_time_days:
          catalogData.lead_time_days !== null && catalogData.lead_time_days !== undefined
            ? String(catalogData.lead_time_days)
            : '',
        is_preferred: catalogData.is_preferred,
        notes: catalogData.notes || '',
      });
    } catch (err: any) {
      setError(err.message || 'Failed to load catalog item detail.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, catalogId, user]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleUpdateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !catalogId) return;

    const price = parseFloat(formData.purchase_price);
    if (isNaN(price) || price < 0) {
      setFormError('Purchase price must be >= 0.');
      return;
    }

    setFormError(null);
    setIsSubmitting(true);

    try {
      await apiClient.updateSupplierCatalogItem(businessId, catalogId, {
        supplier_code: formData.supplier_code.trim() || null,
        supplier_product_name: formData.supplier_product_name.trim() || null,
        purchase_price: formData.purchase_price,
        currency: formData.currency,
        minimum_order_quantity: formData.minimum_order_quantity ? formData.minimum_order_quantity : null,
        lead_time_days: formData.lead_time_days ? parseInt(formData.lead_time_days, 10) : null,
        is_preferred: formData.is_preferred,
        notes: formData.notes.trim() || null,
      });

      setIsEditing(false);
      loadData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to update catalog item.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleArchive = async () => {
    if (!businessId || !catalogId) return;
    try {
      await apiClient.archiveSupplierCatalogItem(businessId, catalogId);
      setShowArchiveModal(false);
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to archive item.');
    }
  };

  const handleToggleStatus = async () => {
    if (!businessId || !catalogId || !item || !canManage) return;
    try {
      if (item.status === 'ACTIVE') {
        await apiClient.deactivateSupplierCatalogItem(businessId, catalogId);
      } else if (item.status === 'INACTIVE') {
        await apiClient.activateSupplierCatalogItem(businessId, catalogId);
      }
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to change item status.');
    }
  };

  if (isLoading) {
    return <Loading text="Loading Catalog Detail..." />;
  }

  if (error || !item) {
    return <ErrorState message={error || 'Catalog item not found.'} onRetry={loadData} />;
  }

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <nav className="flex text-sm text-gray-500 mb-1">
          <Link to={`/businesses/${businessId}`} className="hover:underline">
            Business Detail
          </Link>
          <span className="mx-2">/</span>
          <Link to={`/businesses/${businessId}/supplier-catalog`} className="hover:underline">
            Supplier Catalog
          </Link>
          <span className="mx-2">/</span>
          <span className="text-gray-900 font-medium">Item Detail</span>
        </nav>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mt-2">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {item.supplier_name || item.supplier_id}
            </h1>
            <p className="text-sm text-gray-500">
              Target:{' '}
              <strong className="text-gray-800 dark:text-gray-200">
                {item.variant_name
                  ? `${item.variant_name} (${item.variant_code})`
                  : `${item.product_name} (${item.product_code})`}
              </strong>
            </p>
          </div>

          <div className="flex items-center gap-2">
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
      </div>

      {/* Main Details Card */}
      <Card className="p-6 space-y-6">
        <div className="flex justify-between items-center border-b pb-4">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">
            Procurement Information
          </h2>
          {canManage && item.status !== 'ARCHIVED' && !isEditing && (
            <div className="space-x-2">
              <Button size="sm" variant="secondary" onClick={() => setIsEditing(true)}>
                Edit
              </Button>
              <Button size="sm" variant="ghost" onClick={handleToggleStatus}>
                {item.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
              </Button>
              <Button size="sm" variant="danger" onClick={() => setShowArchiveModal(true)}>
                Archive
              </Button>
            </div>
          )}
        </div>

        {isEditing ? (
          <form onSubmit={handleUpdateSubmit} className="space-y-4 text-sm">
            {formError && (
              <div className="p-3 bg-red-100 text-red-700 rounded text-sm">
                {formError}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block font-medium mb-1">Supplier SKU / Code</label>
                <Input
                  value={formData.supplier_code}
                  onChange={(e) =>
                    setFormData({ ...formData, supplier_code: e.target.value })
                  }
                />
              </div>

              <div>
                <label className="block font-medium mb-1">Supplier Product Name</label>
                <Input
                  value={formData.supplier_product_name}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      supplier_product_name: e.target.value,
                    })
                  }
                />
              </div>

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

              <div>
                <label className="block font-medium mb-1">Min Order Qty (Optional)</label>
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
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
                id="edit_is_preferred"
                checked={formData.is_preferred}
                onChange={(e) =>
                  setFormData({ ...formData, is_preferred: e.target.checked })
                }
              />
              <label htmlFor="edit_is_preferred" className="cursor-pointer font-medium">
                Set as Preferred Supplier for this item
              </label>
            </div>

            <div>
              <label className="block font-medium mb-1">Notes</label>
              <textarea
                rows={3}
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
                onClick={() => setIsEditing(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Saving...' : 'Save Changes'}
              </Button>
            </div>
          </form>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
            <div className="space-y-3">
              <div>
                <span className="text-xs text-gray-500 uppercase block">Supplier Name</span>
                <span className="font-semibold text-base text-gray-900 dark:text-white">
                  {item.supplier_name || item.supplier_id}
                </span>
              </div>

              <div>
                <span className="text-xs text-gray-500 uppercase block">Target Item</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {item.variant_name
                    ? `${item.variant_name} (SKU: ${item.variant_code})`
                    : `${item.product_name} (SKU: ${item.product_code})`}
                </span>
              </div>

              <div>
                <span className="text-xs text-gray-500 uppercase block">Supplier Code / SKU</span>
                <span className="font-mono">{item.supplier_code || '-'}</span>
              </div>

              <div>
                <span className="text-xs text-gray-500 uppercase block">Supplier Product Name</span>
                <span>{item.supplier_product_name || '-'}</span>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <span className="text-xs text-gray-500 uppercase block">Purchase Price</span>
                <span className="font-mono font-bold text-lg text-gray-900 dark:text-white">
                  {item.currency} {parseFloat(item.purchase_price).toLocaleString()}
                </span>
              </div>

              <div>
                <span className="text-xs text-gray-500 uppercase block">Minimum Order Quantity (MOQ)</span>
                <span>{item.minimum_order_quantity ? `${item.minimum_order_quantity}` : '-'}</span>
              </div>

              <div>
                <span className="text-xs text-gray-500 uppercase block">Lead Time</span>
                <span>
                  {item.lead_time_days !== null && item.lead_time_days !== undefined
                    ? `${item.lead_time_days} Days`
                    : '-'}
                </span>
              </div>

              <div>
                <span className="text-xs text-gray-500 uppercase block">Preferred Status</span>
                <span>{item.is_preferred ? 'Yes (Preferred Supplier)' : 'No'}</span>
              </div>
            </div>

            {item.notes && (
              <div className="md:col-span-2 pt-3 border-t">
                <span className="text-xs text-gray-500 uppercase block">Notes</span>
                <p className="mt-1 text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                  {item.notes}
                </p>
              </div>
            )}

            <div className="md:col-span-2 text-xs text-gray-400 pt-3 border-t flex justify-between">
              <span>Created: {new Date(item.created_at).toLocaleString()}</span>
              <span>Updated: {new Date(item.updated_at).toLocaleString()}</span>
            </div>
          </div>
        )}
      </Card>

      {/* Archive Modal */}
      {showArchiveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">
              Archive Supplier Catalog Item?
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Are you sure you want to archive this catalog item? Archived items cannot be modified or reactivated.
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" onClick={() => setShowArchiveModal(false)}>
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
