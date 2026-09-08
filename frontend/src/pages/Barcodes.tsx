import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { Barcode, BarcodeCreate } from '@/types/product';
import type { BusinessMembership } from '@/types/businessMembership';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';

export const Barcodes: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const { user } = useAuth();

  const [barcodes, setBarcodes] = useState<Barcode[]>([]);
  const [role, setRole] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [archiveConfirmBarcode, setArchiveConfirmBarcode] = useState<Barcode | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const [formData, setFormData] = useState<{
    code: string;
    barcode_type: string;
    product_id: string;
    variant_id: string;
  }>({
    code: '',
    barcode_type: 'CODE128',
    product_id: '',
    variant_id: '',
  });

  const loadData = useCallback(async () => {
    if (!businessId || !user) return;
    setIsLoading(true);
    setError(null);
    try {
      const members = await apiClient.listBusinessMembers(businessId);
      const myMembership = members.find((m: BusinessMembership) => m.user_id === user.id);
      if (myMembership) setRole(myMembership.role);

      const listRes = await apiClient.listBarcodes(businessId);
      setBarcodes(listRes.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load barcodes.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, user]);

  useEffect(() => { loadData(); }, [loadData]);

  const canManage = role === 'OWNER' || role === 'ADMIN';

  const handleOpenCreate = () => {
    setFormData({ code: '', barcode_type: 'CODE128', product_id: '', variant_id: '' });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    setFormError(null);
    if (!formData.code.trim()) {
      setFormError('Barcode code is required.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: BarcodeCreate = {
        code: formData.code.trim(),
        barcode_type: formData.barcode_type as any,
        product_id: formData.product_id || undefined,
        variant_id: formData.variant_id || undefined,
      };
      await apiClient.createBarcode(businessId, payload);
      setIsModalOpen(false);
      loadData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to save barcode.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmArchive = async () => {
    if (!businessId || !archiveConfirmBarcode) return;
    setIsSubmitting(true);
    try {
      await apiClient.archiveBarcode(businessId, archiveConfirmBarcode.id);
      setArchiveConfirmBarcode(null);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to archive barcode.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) return <Loading text="Loading barcodes..." />;
  if (error) return <ErrorState message={error} onRetry={loadData} />;

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
            <Link to={`/businesses/${businessId}`} className="hover:underline">Business</Link>
            <span>/</span>
            <span>Barcodes</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Barcodes</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Manage barcode identifiers for products and product variants.
          </p>
        </div>
        {canManage && (
          <Button onClick={handleOpenCreate} variant="primary">+ Create Barcode</Button>
        )}
      </div>

      {barcodes.length === 0 ? (
        <EmptyState
          title="No barcodes found"
          description="Create barcodes to identify your products and variants."
          action={
            canManage ? <Button onClick={handleOpenCreate} variant="primary">Create First Barcode</Button> : undefined
          }
        />
      ) : (
        <>
          <div className="hidden md:block bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xs overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
              <thead className="bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 uppercase text-xs">
                <tr>
                  <th scope="col" className="px-6 py-3 font-semibold">Code</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Type</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Target</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Status</th>
                  {canManage && <th scope="col" className="px-6 py-3 font-semibold text-right">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/60">
                {barcodes.map((barcode) => (
                  <tr key={barcode.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50">
                    <td className="px-6 py-4 font-mono text-xs text-slate-700 dark:text-slate-300">{barcode.code}</td>
                    <td className="px-6 py-4">
                      <Badge variant="info">{barcode.barcode_type}</Badge>
                    </td>
                    <td className="px-6 py-4">
                      {barcode.product_id
                        ? `Product: ${barcode.product_id.substring(0, 8)}...`
                        : barcode.variant_id
                          ? `Variant: ${barcode.variant_id.substring(0, 8)}...`
                          : '-'}
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={barcode.status === 'ACTIVE' ? 'success' : 'error'}>
                        {barcode.status}
                      </Badge>
                    </td>
                    {canManage && (
                      <td className="px-6 py-4 text-right space-x-2">
                        <Button size="sm" variant="danger" onClick={() => setArchiveConfirmBarcode(barcode)}>
                          Archive
                        </Button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="md:hidden grid grid-cols-1 gap-4">
            {barcodes.map((barcode) => (
              <Card key={barcode.id} className="p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="font-semibold text-slate-900 dark:text-slate-100">{barcode.code}</h2>
                    <Badge variant="info">{barcode.barcode_type}</Badge>
                  </div>
                  <Badge variant={barcode.status === 'ACTIVE' ? 'success' : 'error'}>
                    {barcode.status}
                  </Badge>
                </div>
                {canManage && (
                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-700">
                    <Button size="sm" variant="danger" onClick={() => setArchiveConfirmBarcode(barcode)}>
                      Archive
                    </Button>
                  </div>
                )}
              </Card>
            ))}
          </div>
        </>
      )}

      {/* Create Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4">
            <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Create Barcode</h2>
            {formError && (
              <div className="p-3 text-xs bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 rounded-lg border border-rose-200 dark:border-rose-900">
                {formError}
              </div>
            )}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="barcode-type" className="text-sm font-medium text-slate-700 dark:text-slate-300">Barcode Type</label>
                <select
                  id="barcode-type"
                  className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900 dark:text-slate-100 min-h-[40px]"
                  value={formData.barcode_type}
                  onChange={(e) => setFormData({ ...formData, barcode_type: e.target.value })}
                >
                  <option value="CODE128">CODE128</option>
                  <option value="EAN13">EAN13 (13 digits)</option>
                  <option value="EAN8">EAN8 (8 digits)</option>
                  <option value="UPC_A">UPC_A (12 digits)</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="barcode-code" className="text-sm font-medium text-slate-700 dark:text-slate-300">Barcode Code</label>
                <input
                  id="barcode-code"
                  type="text"
                  className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900 dark:text-slate-100 font-mono min-h-[40px]"
                  placeholder="e.g. 8991234567890"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                  required
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="product-id" className="text-sm font-medium text-slate-700 dark:text-slate-300">Product ID (optional)</label>
                <input
                  id="product-id"
                  type="text"
                  className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900 dark:text-slate-100 font-mono min-h-[40px]"
                  value={formData.product_id}
                  onChange={(e) => setFormData({ ...formData, product_id: e.target.value, variant_id: e.target.value ? '' : formData.variant_id })}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="variant-id" className="text-sm font-medium text-slate-700 dark:text-slate-300">Variant ID (optional)</label>
                <input
                  id="variant-id"
                  type="text"
                  className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900 dark:text-slate-100 font-mono min-h-[40px]"
                  value={formData.variant_id}
                  onChange={(e) => setFormData({ ...formData, variant_id: e.target.value, product_id: e.target.value ? '' : formData.product_id })}
                />
              </div>
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-700">
                <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>Cancel</Button>
                <Button type="submit" variant="primary" isLoading={isSubmitting}>Create Barcode</Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Archive Confirmation Modal */}
      {archiveConfirmBarcode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Archive Barcode?</h3>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Are you sure you want to archive <strong>{archiveConfirmBarcode.code}</strong> ({archiveConfirmBarcode.barcode_type})?
            </p>
            <div className="flex items-center justify-end gap-3 pt-2">
              <Button variant="outline" onClick={() => setArchiveConfirmBarcode(null)}>Cancel</Button>
              <Button variant="danger" isLoading={isSubmitting} onClick={handleConfirmArchive}>Confirm Archive</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};