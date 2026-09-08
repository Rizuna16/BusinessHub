import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { PriceList, PriceEntry, PriceEntryCreate } from '@/types/pricing';
import type { BusinessMembership } from '@/types/businessMembership';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';

export const PriceListDetail: React.FC = () => {
  const { businessId, priceListId } = useParams<{ businessId: string; priceListId: string }>();
  const { user } = useAuth();

  const [priceList, setPriceList] = useState<PriceList | null>(null);
  const [entries, setEntries] = useState<PriceEntry[]>([]);
  const [role, setRole] = useState<string | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [archiveConfirm, setArchiveConfirm] = useState<PriceEntry | null>(null);

  const [formData, setFormData] = useState<{
    targetType: 'product' | 'variant';
    targetId: string;
    amount: string;
    effective_from: string;
    effective_to: string;
  }>({
    targetType: 'product',
    targetId: '',
    amount: '',
    effective_from: new Date().toISOString().split('T')[0],
    effective_to: '',
  });

  const loadData = useCallback(async () => {
    if (!businessId || !priceListId || !user) return;
    setIsLoading(true);
    setError(null);
    try {
      const members = await apiClient.listBusinessMembers(businessId);
      const myMembership = members.find((m: BusinessMembership) => m.user_id === user.id);
      if (myMembership) setRole(myMembership.role);

      const [pl, pe] = await Promise.all([
        apiClient.getPriceList(businessId, priceListId),
        apiClient.listPriceEntries(businessId, priceListId),
      ]);

      setPriceList(pl);
      setEntries(pe.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load price list detail.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, priceListId, user]);

  useEffect(() => { loadData(); }, [loadData]);

  const canManage = role === 'OWNER' || role === 'ADMIN';

  const handleOpenCreate = () => {
    setFormData({
      targetType: 'product',
      targetId: '',
      amount: '',
      effective_from: new Date().toISOString().split('T')[0],
      effective_to: '',
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !priceListId) return;
    setFormError(null);

    if (!formData.targetId.trim()) { setFormError('Target ID is required.'); return; }
    if (!formData.amount || isNaN(Number(formData.amount)) || Number(formData.amount) < 0) {
      setFormError('Amount must be a valid non-negative number.');
      return;
    }
    if (!formData.effective_from) { setFormError('Effective from date is required.'); return; }

    setIsSubmitting(true);
    try {
      const payload: PriceEntryCreate = {
        amount: formData.amount,
        effective_from: new Date(formData.effective_from).toISOString(),
        effective_to: formData.effective_to ? new Date(formData.effective_to).toISOString() : undefined,
      };
      if (formData.targetType === 'product') {
        payload.product_id = formData.targetId.trim();
      } else {
        payload.variant_id = formData.targetId.trim();
      }

      await apiClient.createPriceEntry(businessId, priceListId, payload);
      setIsModalOpen(false);
      loadData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to create price entry.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmArchive = async () => {
    if (!businessId || !priceListId || !archiveConfirm) return;
    setIsSubmitting(true);
    try {
      await apiClient.archivePriceEntry(businessId, priceListId, archiveConfirm.id);
      setArchiveConfirm(null);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to archive price entry.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) return <Loading text="Loading pricing detail..." />;
  if (error) return <ErrorState message={error} onRetry={loadData} />;
  if (!priceList) return <ErrorState message="Price list not found." />;

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
            <Link to={`/businesses/${businessId}`} className="hover:underline">Business</Link>
            <span>/</span>
            <Link to={`/businesses/${businessId}/price-lists`} className="hover:underline">Price Lists</Link>
            <span>/</span>
            <span>{priceList.name}</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{priceList.name}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Code: <strong>{priceList.code}</strong> | Currency: <strong>{priceList.currency}</strong>
          </p>
        </div>
        {canManage && (
          <Button onClick={handleOpenCreate} variant="primary">+ Add Price</Button>
        )}
      </div>

      {entries.length === 0 ? (
        <EmptyState
          title="No price entries"
          description="Add product or variant price entries to this price list."
          action={
            canManage ? <Button onClick={handleOpenCreate} variant="primary">Add First Price Entry</Button> : undefined
          }
        />
      ) : (
        <>
          <div className="hidden md:block bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xs overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
              <thead className="bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 uppercase text-xs">
                <tr>
                  <th scope="col" className="px-6 py-3 font-semibold">Target</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Amount</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Effective Period</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Status</th>
                  {canManage && <th scope="col" className="px-6 py-3 font-semibold text-right">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/60">
                {entries.map((pe) => (
                  <tr key={pe.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50">
                    <td className="px-6 py-4">
                      {pe.product_id ? (
                        <span className="font-mono text-xs">Product: {pe.product_id.substring(0, 8)}...</span>
                      ) : (
                        <span className="font-mono text-xs">Variant: {pe.variant_id?.substring(0, 8)}...</span>
                      )}
                    </td>
                    <td className="px-6 py-4 font-semibold text-slate-900 dark:text-slate-100">
                      {priceList.currency} {Number(pe.amount).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500 dark:text-slate-400">
                      {new Date(pe.effective_from).toLocaleDateString()} -{' '}
                      {pe.effective_to ? new Date(pe.effective_to).toLocaleDateString() : 'Open-ended'}
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={pe.status === 'ACTIVE' ? 'success' : 'error'}>{pe.status}</Badge>
                    </td>
                    {canManage && (
                      <td className="px-6 py-4 text-right">
                        <Button size="sm" variant="danger" onClick={() => setArchiveConfirm(pe)}>
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
            {entries.map((pe) => (
              <Card key={pe.id} className="p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                      {priceList.currency} {Number(pe.amount).toLocaleString()}
                    </h2>
                    <span className="font-mono text-xs text-slate-500 dark:text-slate-400">
                      {pe.product_id ? `Product: ${pe.product_id.substring(0, 8)}` : `Variant: ${pe.variant_id?.substring(0, 8)}`}
                    </span>
                  </div>
                  <Badge variant={pe.status === 'ACTIVE' ? 'success' : 'error'}>{pe.status}</Badge>
                </div>
                {canManage && (
                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-700">
                    <Button size="sm" variant="danger" onClick={() => setArchiveConfirm(pe)}>
                      Archive
                    </Button>
                  </div>
                )}
              </Card>
            ))}
          </div>
        </>
      )}

      {/* Add Price Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4">
            <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Add Price Entry</h2>
            {formError && (
              <div className="p-3 text-xs bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 rounded-lg border border-rose-200 dark:border-rose-900">
                {formError}
              </div>
            )}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="target-type" className="text-sm font-medium text-slate-700 dark:text-slate-300">Target Type</label>
                <select
                  id="target-type"
                  className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900 dark:text-slate-100 min-h-[40px]"
                  value={formData.targetType}
                  onChange={(e) => setFormData({ ...formData, targetType: e.target.value as 'product' | 'variant', targetId: '' })}
                >
                  <option value="product">Product</option>
                  <option value="variant">Product Variant</option>
                </select>
              </div>

              <Input
                label={formData.targetType === 'product' ? 'Product ID' : 'Variant ID'}
                placeholder={`Enter target ${formData.targetType} ID`}
                value={formData.targetId}
                onChange={(e) => setFormData({ ...formData, targetId: e.target.value })}
                required
              />

              <Input
                label={`Amount (${priceList.currency})`}
                type="number"
                step="0.01"
                placeholder="e.g. 3500.00"
                value={formData.amount}
                onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                required
              />

              <Input
                label="Effective From"
                type="date"
                value={formData.effective_from}
                onChange={(e) => setFormData({ ...formData, effective_from: e.target.value })}
                required
              />

              <Input
                label="Effective To (Optional)"
                type="date"
                value={formData.effective_to}
                onChange={(e) => setFormData({ ...formData, effective_to: e.target.value })}
              />

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-700">
                <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>Cancel</Button>
                <Button type="submit" variant="primary" isLoading={isSubmitting}>Save Price Entry</Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Archive Modal */}
      {archiveConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Archive Price Entry?</h3>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Are you sure you want to archive this price entry?
            </p>
            <div className="flex items-center justify-end gap-3 pt-2">
              <Button variant="outline" onClick={() => setArchiveConfirm(null)}>Cancel</Button>
              <Button variant="danger" isLoading={isSubmitting} onClick={handleConfirmArchive}>Confirm Archive</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};