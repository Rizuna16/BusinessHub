import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { Product, ProductVariant, ProductVariantCreate, ProductVariantUpdate, ProductImage } from '@/types/product';
import type { BusinessMembership } from '@/types/businessMembership';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';

export const ProductVariants: React.FC = () => {
  const { businessId, productId } = useParams<{ businessId: string; productId: string }>();
  const { user } = useAuth();

  const [product, setProduct] = useState<Product | null>(null);
  const [variants, setVariants] = useState<ProductVariant[]>([]);
  const [role, setRole] = useState<string | null>(null);
  const [variantImages, setVariantImages] = useState<Record<string, ProductImage>>({});

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Modal / Form states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingVariant, setEditingVariant] = useState<ProductVariant | null>(null);
  const [archiveConfirmVariant, setArchiveConfirmVariant] = useState<ProductVariant | null>(null);

  // Form inputs
  const [formData, setFormData] = useState<{
    name: string;
    code: string;
    attributes: Record<string, unknown>;
  }>({
    name: '',
    code: '',
    attributes: {},
  });

  const loadData = useCallback(async () => {
    if (!businessId || !productId || !user) return;
    setIsLoading(true);
    setError(null);
    try {
      const members = await apiClient.listBusinessMembers(businessId);
      const myMembership = members.find((m: BusinessMembership) => m.user_id === user.id);
      if (myMembership) {
        setRole(myMembership.role);
      }

      const [prod, vars] = await Promise.all([
        apiClient.getProduct(businessId, productId),
        apiClient.listProductVariants(businessId, productId),
      ]);

      setProduct(prod);
      setVariants(vars.items);

      // Fetch primary images for variants
      const imagesMap: Record<string, ProductImage> = {};
      await Promise.all(
        vars.items.map(async (v) => {
          try {
            const imgRes = await apiClient.listProductImages(businessId, productId, v.id);
            const primary = imgRes.items.find((i) => i.is_primary) || imgRes.items[0];
            if (primary) imagesMap[v.id] = primary;
          } catch {
            // ignore - image fetch is optional
          }
        })
      );
      setVariantImages(imagesMap);
    } catch (err: any) {
      setError(err.message || 'Failed to load variants.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, productId, user]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const canManage = role === 'OWNER' || role === 'ADMIN';

  const handleOpenCreate = () => {
    setEditingVariant(null);
    setFormData({
      name: '',
      code: '',
      attributes: {},
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (variant: ProductVariant) => {
    setEditingVariant(variant);
    setFormData({
      name: variant.name,
      code: variant.code,
      attributes: variant.attributes || {},
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !productId) return;
    setFormError(null);

    if (!formData.name.trim()) {
      setFormError('Variant name is required.');
      return;
    }
    if (!formData.code.trim()) {
      setFormError('Variant code is required.');
      return;
    }

    setIsSubmitting(true);
    try {
      if (editingVariant) {
        const payload: ProductVariantUpdate = {
          name: formData.name.trim(),
          code: formData.code.trim(),
          attributes: Object.keys(formData.attributes).length > 0 ? formData.attributes : undefined,
        };
        await apiClient.updateProductVariant(businessId, productId, editingVariant.id, payload);
      } else {
        const payload: ProductVariantCreate = {
          name: formData.name.trim(),
          code: formData.code.trim(),
          attributes: Object.keys(formData.attributes).length > 0 ? formData.attributes : undefined,
        };
        await apiClient.createProductVariant(businessId, productId, payload);
      }
      setIsModalOpen(false);
      loadData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to save variant.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmArchive = async () => {
    if (!businessId || !productId || !archiveConfirmVariant) return;
    setIsSubmitting(true);
    try {
      await apiClient.archiveProductVariant(businessId, productId, archiveConfirmVariant.id);
      setArchiveConfirmVariant(null);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to archive variant.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUploadVariantImage = async (variantId: string, file: File) => {
    if (!businessId || !productId) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const img = await apiClient.uploadProductImage(businessId, productId, formData, variantId);
      setVariantImages((prev) => ({ ...prev, [variantId]: img }));
    } catch (err: any) {
      alert(err.message || 'Failed to upload image.');
    }
  };

  if (isLoading) {
    return <Loading text="Loading variants..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

  if (!product) {
    return <ErrorState message="Product not found." />;
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
            <Link to={`/businesses/${businessId}`} className="hover:underline">
              Business
            </Link>
            <span>/</span>
            <Link to={`/businesses/${businessId}/products`} className="hover:underline">
              Products
            </Link>
            <span>/</span>
            <span>{product.name}</span>
            <span>/</span>
            <span>Variants</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Product Variants</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Manage concrete variations for product <strong>{product.name}</strong> ({product.code}).
          </p>
        </div>

        {canManage && product.product_type === 'GOODS' && (
          <Button onClick={handleOpenCreate} variant="primary">
            + Create Variant
          </Button>
        )}
      </div>

      {product.product_type === 'SERVICE' && (
        <Card className="border-amber-200 bg-amber-50 dark:bg-amber-950/20">
          <div className="flex items-center gap-3 p-4">
            <svg className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <p className="text-sm text-amber-800 dark:text-amber-200">
              Variants are only available for <strong>GOODS</strong> products. This product is a <strong>SERVICE</strong>.
            </p>
          </div>
        </Card>
      )}

      {/* List / Table */}
      {variants.length === 0 && product.product_type === 'GOODS' ? (
        <EmptyState
          title="No variants found"
          description="Create variants to represent different configurations of this product (e.g., colors, sizes)."
          action={
            canManage ? (
              <Button onClick={handleOpenCreate} variant="primary">
                Create First Variant
              </Button>
            ) : undefined
          }
        />
      ) : (
        <>
          {/* Desktop Table View */}
          <div className="hidden md:block bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xs overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
              <thead className="bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 uppercase text-xs">
                <tr>
                  <th scope="col" className="px-6 py-3 font-semibold">Image</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Variant</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Code</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Attributes</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Status</th>
                  {canManage && <th scope="col" className="px-6 py-3 font-semibold text-right">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/60">
                {variants.map((variant) => (
                  <tr key={variant.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className={`w-8 h-8 rounded flex items-center justify-center ${variantImages[variant.id] ? 'bg-emerald-100 dark:bg-emerald-900/30' : 'bg-slate-100 dark:bg-slate-700'}`}>
                          {variantImages[variant.id] ? (
                            <span className="text-emerald-600 dark:text-emerald-400 text-sm">IMG</span>
                          ) : (
                            <span className="text-xs text-slate-400">--</span>
                          )}
                        </div>
                        {canManage && (
                          <label className="cursor-pointer text-xs text-indigo-600 hover:text-indigo-800 dark:text-indigo-400">
                            Upload
                            <input
                              type="file"
                              accept="image/jpeg,image/png,image/webp"
                              className="hidden"
                              onChange={(e) => {
                                const file = e.target.files?.[0];
                                if (file) handleUploadVariantImage(variant.id, file);
                                e.target.value = '';
                              }}
                            />
                          </label>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 font-semibold text-slate-900 dark:text-slate-100">{variant.name}</td>
                    <td className="px-6 py-4 font-mono text-xs text-slate-700 dark:text-slate-300">{variant.code}</td>
                    <td className="px-6 py-4">
                      {variant.attributes && Object.keys(variant.attributes).length > 0 ? (
                        <div className="text-xs text-slate-600 dark:text-slate-400 font-mono">
                          {JSON.stringify(variant.attributes)}
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400 dark:text-slate-500 italic">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={variant.status === 'ACTIVE' ? 'success' : 'error'}>
                        {variant.status}
                      </Badge>
                    </td>
                    {canManage && (
                      <td className="px-6 py-4 text-right space-x-2">
                        <Button size="sm" variant="ghost" onClick={() => handleOpenEdit(variant)}>
                          Edit
                        </Button>
                        <Button size="sm" variant="danger" onClick={() => setArchiveConfirmVariant(variant)}>
                          Archive
                        </Button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile Card List View */}
          <div className="md:hidden grid grid-cols-1 gap-4">
            {variants.map((variant) => (
              <Card key={variant.id} className="p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="font-semibold text-slate-900 dark:text-slate-100">{variant.name}</h2>
                    <span className="font-mono text-xs text-slate-500 dark:text-slate-400">{variant.code}</span>
                  </div>
                  <Badge variant={variant.status === 'ACTIVE' ? 'success' : 'error'}>
                    {variant.status}
                  </Badge>
                </div>

                {variant.attributes && Object.keys(variant.attributes).length > 0 && (
                  <div className="text-xs text-slate-600 dark:text-slate-400 font-mono">
                    {JSON.stringify(variant.attributes)}
                  </div>
                )}

                {canManage && (
                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-700">
                    <Button size="sm" variant="outline" onClick={() => handleOpenEdit(variant)}>
                      Edit
                    </Button>
                    <Button size="sm" variant="danger" onClick={() => setArchiveConfirmVariant(variant)}>
                      Archive
                    </Button>
                  </div>
                )}
              </Card>
            ))}
          </div>
        </>
      )}

      {/* Create / Edit Dialog Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4">
            <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
              {editingVariant ? 'Edit Variant' : 'Create Variant'}
            </h2>

            {formError && (
              <div className="p-3 text-xs bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 rounded-lg border border-rose-200 dark:border-rose-900">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="Variant Name"
                placeholder="e.g. Black / Small"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />

              <Input
                label="Variant Code"
                placeholder="e.g. TSHIRT-BLK-S"
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                required
              />

              <div className="flex flex-col gap-1.5">
                <label htmlFor="attributes" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Attributes (JSON)
                </label>
                <textarea
                  id="attributes"
                  rows={4}
                  className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900 dark:text-slate-100 font-mono text-xs"
                  placeholder='{"color": "Black", "size": "S"}'
                  value={JSON.stringify(formData.attributes, null, 2)}
                  onChange={(e) => {
                    try {
                      const parsed = JSON.parse(e.target.value || '{}');
                      if (typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)) {
                        setFormData({ ...formData, attributes: parsed });
                      }
                    } catch {
                      // Ignore invalid JSON while typing
                    }
                  }}
                />
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  Optional. Key-value pairs describing variant properties.
                </span>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-700">
                <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" isLoading={isSubmitting}>
                  {editingVariant ? 'Save Changes' : 'Create Variant'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Archive Modal */}
      {archiveConfirmVariant && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
              Archive Variant?
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Are you sure you want to archive <strong>{archiveConfirmVariant.name}</strong> ({archiveConfirmVariant.code})?
            </p>
            <div className="flex items-center justify-end gap-3 pt-2">
              <Button variant="outline" onClick={() => setArchiveConfirmVariant(null)}>
                Cancel
              </Button>
              <Button variant="danger" isLoading={isSubmitting} onClick={handleConfirmArchive}>
                Confirm Archive
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};