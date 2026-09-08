import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { PriceList } from '@/types/pricing';
import type { BusinessMembership } from '@/types/businessMembership';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';

export const PriceLists: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [priceLists, setPriceLists] = useState<PriceList[]>([]);
  const [role, setRole] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [archiveConfirm, setArchiveConfirm] = useState<PriceList | null>(null);

  const [formData, setFormData] = useState<{
    name: string;
    code: string;
    description: string;
    currency: string;
  }>({
    name: '',
    code: '',
    description: '',
    currency: 'IDR',
  });

  const loadData = useCallback(async () => {
    if (!businessId || !user) return;
    setIsLoading(true);
    setError(null);
    try {
      const members = await apiClient.listBusinessMembers(businessId);
      const myMembership = members.find((m: BusinessMembership) => m.user_id === user.id);
      if (myMembership) setRole(myMembership.role);

      const res = await apiClient.listPriceLists(businessId);
      setPriceLists(res.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load price lists.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, user]);

  useEffect(() => { loadData(); }, [loadData]);

  const canManage = role === 'OWNER' || role === 'ADMIN';

  const handleOpenCreate = () => {
    setFormData({ name: '', code: '', description: '', currency: 'IDR' });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    setFormError(null);
    if (!formData.name.trim()) { setFormError('Name is required.'); return; }
    if (!formData.code.trim()) { setFormError('Code is required.'); return; }

    setIsSubmitting(true);
    try {
      await apiClient.createPriceList(businessId, formData);
      setIsModalOpen(false);
      loadData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to create price list.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmArchive = async () => {
    if (!businessId || !archiveConfirm) return;
    setIsSubmitting(true);
    try {
      await apiClient.archivePriceList(businessId, archiveConfirm.id);
      setArchiveConfirm(null);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to archive price list.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) return <Loading text="Loading price lists..." />;
  if (error) return <ErrorState message={error} onRetry={loadData} />;

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
            <Link to={`/businesses/${businessId}`} className="hover:underline">Business</Link>
            <span>/</span>
            <span>Price Lists</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Price Lists</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Manage pricing containers for this business.
          </p>
        </div>
        {canManage && (
          <Button onClick={handleOpenCreate} variant="primary">+ Create Price List</Button>
        )}
      </div>

      {priceLists.length === 0 ? (
        <EmptyState
          title="No price lists found"
          description="Create a price list to manage product and variant pricing."
          action={
            canManage ? <Button onClick={handleOpenCreate} variant="primary">Create First Price List</Button> : undefined
          }
        />
      ) : (
        <>
          <div className="hidden md:block bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xs overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
              <thead className="bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 uppercase text-xs">
                <tr>
                  <th scope="col" className="px-6 py-3 font-semibold">Name</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Code</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Currency</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Default</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Status</th>
                  {canManage && <th scope="col" className="px-6 py-3 font-semibold text-right">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/60">
                {priceLists.map((pl) => (
                  <tr key={pl.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50">
                    <td className="px-6 py-4 font-semibold text-slate-900 dark:text-slate-100">
                      <button
                        type="button"
                        className="cursor-pointer hover:underline text-left"
                        onClick={() => navigate(`/businesses/${businessId}/price-lists/${pl.id}`)}
                      >
                        {pl.name}
                      </button>
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-slate-700 dark:text-slate-300">{pl.code}</td>
                    <td className="px-6 py-4">{pl.currency}</td>
                    <td className="px-6 py-4">
                      {pl.is_default && (
                        <Badge variant="success">Default</Badge>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={pl.status === 'ACTIVE' ? 'success' : 'error'}>{pl.status}</Badge>
                    </td>
                    {canManage && (
                      <td className="px-6 py-4 text-right space-x-2">
                        <Button size="sm" variant="outline" onClick={() => navigate(`/businesses/${businessId}/price-lists/${pl.id}`)}>
                          Manage Prices
                        </Button>
                        <Button size="sm" variant="danger" onClick={() => setArchiveConfirm(pl)}>
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
            {priceLists.map((pl) => (
              <Card key={pl.id} className="p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <button
                      type="button"
                      className="cursor-pointer hover:underline text-left"
                      onClick={() => navigate(`/businesses/${businessId}/price-lists/${pl.id}`)}
                    >
                      <h2 className="font-semibold text-slate-900 dark:text-slate-100">{pl.name}</h2>
                    </button>
                    <span className="font-mono text-xs text-slate-500 dark:text-slate-400">{pl.code}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {pl.is_default && <Badge variant="success">Default</Badge>}
                    <Badge variant={pl.status === 'ACTIVE' ? 'success' : 'error'}>{pl.status}</Badge>
                  </div>
                </div>
                <div className="text-sm text-slate-600 dark:text-slate-300 pt-2 border-t border-slate-100 dark:border-slate-700">
                  Currency: {pl.currency}
                </div>
                {canManage && (
                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-700">
                    <Button size="sm" variant="outline" onClick={() => navigate(`/businesses/${businessId}/price-lists/${pl.id}`)}>
                      Manage Prices
                    </Button>
                    <Button size="sm" variant="danger" onClick={() => setArchiveConfirm(pl)}>
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
            <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Create Price List</h2>
            {formError && (
              <div className="p-3 text-xs bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 rounded-lg border border-rose-200 dark:border-rose-900">
                {formError}
              </div>
            )}
            <form onSubmit={handleSubmit} className="space-y-4">
              <Input label="Name" placeholder="e.g. Retail List" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required />
              <Input label="Code" placeholder="e.g. RETAIL" value={formData.code} onChange={(e) => setFormData({ ...formData, code: e.target.value })} required />
              <Input label="Description (Optional)" placeholder="Optional description" value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} />
              <div className="flex flex-col gap-1.5">
                <label htmlFor="currency" className="text-sm font-medium text-slate-700 dark:text-slate-300">Currency</label>
                <select
                  id="currency"
                  className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900 dark:text-slate-100 min-h-[40px]"
                  value={formData.currency}
                  onChange={(e) => setFormData({ ...formData, currency: e.target.value.toUpperCase() })}
                >
                  <option value="IDR">IDR</option>
                  <option value="USD">USD</option>
                  <option value="SGD">SGD</option>
                  <option value="MYR">MYR</option>
                  <option value="EUR">EUR</option>
                  <option value="JPY">JPY</option>
                </select>
              </div>
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-700">
                <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>Cancel</Button>
                <Button type="submit" variant="primary" isLoading={isSubmitting}>Create</Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Archive Confirmation Modal */}
      {archiveConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Archive Price List?</h3>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Are you sure you want to archive <strong>{archiveConfirm.name}</strong> ({archiveConfirm.code})?
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