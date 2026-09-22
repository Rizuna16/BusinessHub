import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { Product, ProductCreate, ProductUpdate, ProductType, ProductImage } from '@/types/product';
import type { Category } from '@/types/category';
import type { Unit } from '@/types/unit';
import type { BusinessMembership } from '@/types/businessMembership';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';

export const Products: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const { user } = useAuth();

  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [role, setRole] = useState<string | null>(null);
  const [productImages, setProductImages] = useState<Record<string, ProductImage>>({});

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Filter states
  const [search, setSearch] = useState('');
  const [selectedType, setSelectedType] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');

  // Modal / Form states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [archiveConfirmProduct, setArchiveConfirmProduct] = useState<Product | null>(null);

  // Form inputs
  const [formData, setFormData] = useState<{
    name: string;
    code: string;
    description: string;
    category_id: string;
    unit_id: string;
    product_type: ProductType;
  }>({
    name: '',
    code: '',
    description: '',
    category_id: '',
    unit_id: '',
    product_type: 'GOODS',
  });

  const loadData = useCallback(async () => {
    if (!businessId || !user) return;
    setIsLoading(true);
    setError(null);
    try {
      // Load user membership to determine role
      const members = await apiClient.listBusinessMembers(businessId);
      const myMembership = members.find((m: BusinessMembership) => m.user_id === user.id);
      if (myMembership) {
        setRole(myMembership.role);
      }

      // Load products, categories, units
      const [prodRes, cats, uns] = await Promise.all([
        apiClient.listProducts(businessId, {
          search: search || undefined,
          product_type: selectedType || undefined,
          category_id: selectedCategory || undefined,
        }),
        apiClient.listCategories(businessId, null, false),
        apiClient.listUnits(businessId, null, false),
      ]);

      setProducts(prodRes.items);
      setCategories(cats.filter((c) => c.status === 'ACTIVE'));
      setUnits(uns.filter((u) => u.status === 'ACTIVE'));

      // Fetch primary images for products
      const imagesMap: Record<string, ProductImage> = {};
      await Promise.all(
        prodRes.items.map(async (p) => {
          try {
            const imgRes = await apiClient.listProductImages(businessId, p.id);
            const primary = imgRes.items.find((i) => i.is_primary) || imgRes.items[0];
            if (primary) imagesMap[p.id] = primary;
          } catch {
            // ignore - image fetch is optional
          }
        })
      );
      setProductImages(imagesMap);
    } catch (err: any) {
      setError(err.message || 'Failed to load products.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, user, search, selectedType, selectedCategory]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const canManage = role === 'OWNER' || role === 'ADMIN';

  const handleOpenCreate = () => {
    setEditingProduct(null);
    setFormData({
      name: '',
      code: '',
      description: '',
      category_id: '',
      unit_id: units.length > 0 ? units[0].id : '',
      product_type: 'GOODS',
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (product: Product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      code: product.code,
      description: product.description || '',
      category_id: product.category_id || '',
      unit_id: product.unit_id,
      product_type: product.product_type,
    });
    setFormError(null);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    setFormError(null);

    if (!formData.name.trim()) {
      setFormError('Product name is required.');
      return;
    }
    if (!formData.code.trim()) {
      setFormError('Product code is required.');
      return;
    }
    if (!formData.unit_id) {
      setFormError('Unit is required.');
      return;
    }

    setIsSubmitting(true);
    try {
      if (editingProduct) {
        const payload: ProductUpdate = {
          name: formData.name.trim(),
          code: formData.code.trim(),
          description: formData.description.trim() || null,
          category_id: formData.category_id || null,
          unit_id: formData.unit_id,
          product_type: formData.product_type,
        };
        await apiClient.updateProduct(businessId, editingProduct.id, payload);
      } else {
        const payload: ProductCreate = {
          name: formData.name.trim(),
          code: formData.code.trim(),
          description: formData.description.trim() || null,
          category_id: formData.category_id || null,
          unit_id: formData.unit_id,
          product_type: formData.product_type,
        };
        await apiClient.createProduct(businessId, payload);
      }
      setIsModalOpen(false);
      loadData();
    } catch (err: any) {
      setFormError(err.message || 'Failed to save product.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmArchive = async () => {
    if (!businessId || !archiveConfirmProduct) return;
    setIsSubmitting(true);
    try {
      await apiClient.archiveProduct(businessId, archiveConfirmProduct.id);
      setArchiveConfirmProduct(null);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to archive product.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getCategoryName = (catId: string | null) => {
    if (!catId) return '-';
    const c = categories.find((cat) => cat.id === catId);
    return c ? c.name : '-';
  };

  const getUnitName = (uId: string) => {
    const u = units.find((unit) => unit.id === uId);
    return u ? `${u.name} (${u.code})` : uId;
  };

  const handleUploadProductImage = async (productId: string, file: File) => {
    if (!businessId) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const img = await apiClient.uploadProductImage(businessId, productId, formData);
      setProductImages((prev) => ({ ...prev, [productId]: img }));
    } catch (err: any) {
      alert(err.message || 'Failed to upload image.');
    }
  };

  if (isLoading) {
    return <Loading text="Loading products..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadData} />;
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
            <span>Products</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Product Master</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Manage product definitions, types, categories, and operational units.
          </p>
        </div>

        {canManage && (
          <Button onClick={handleOpenCreate} variant="primary">
            + Create Product
          </Button>
        )}
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Input
            label="Search"
            placeholder="Search by name or code..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          <div className="flex flex-col gap-1.5">
            <label htmlFor="filter-type" className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Product Type
            </label>
            <select
              id="filter-type"
              aria-label="Product Type"
              className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900 dark:text-slate-100 min-h-[40px]"
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
            >
              <option value="">All Types</option>
              <option value="GOODS">GOODS (Physical)</option>
              <option value="SERVICE">SERVICE (Non-physical)</option>
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="filter-category" className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Category
            </label>
            <select
              id="filter-category"
              aria-label="Category"
              className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900 dark:text-slate-100 min-h-[40px]"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
            >
              <option value="">All Categories</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {/* List / Table */}
      {products.length === 0 ? (
        <EmptyState
          title="No products found"
          description={
            search || selectedType || selectedCategory
              ? 'No products match your selected filters.'
              : 'Start by adding master products for this business.'
          }
          action={
            canManage ? (
              <Button onClick={handleOpenCreate} variant="primary">
                Create First Product
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
                  <th scope="col" className="px-6 py-3 font-semibold">Product</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Code</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Category</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Unit</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Type</th>
                  <th scope="col" className="px-6 py-3 font-semibold">Status</th>
                  {canManage && <th scope="col" className="px-6 py-3 font-semibold text-right">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700/60">
                {products.map((product) => (
                  <tr key={product.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className={`w-8 h-8 rounded flex items-center justify-center ${productImages[product.id] ? 'bg-emerald-100 dark:bg-emerald-900/30' : 'bg-slate-100 dark:bg-slate-700'}`}>
                          {productImages[product.id] ? (
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
                                if (file) handleUploadProductImage(product.id, file);
                                e.target.value = '';
                              }}
                            />
                          </label>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">{product.name}</div>
                      {product.description && (
                        <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 max-w-xs truncate">
                          {product.description}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-slate-700 dark:text-slate-300">{product.code}</td>
                    <td className="px-6 py-4">{getCategoryName(product.category_id)}</td>
                    <td className="px-6 py-4">{getUnitName(product.unit_id)}</td>
                    <td className="px-6 py-4">
                      <Badge variant={product.product_type === 'GOODS' ? 'info' : 'neutral'}>
                        {product.product_type}
                      </Badge>
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={product.status === 'ACTIVE' ? 'success' : 'error'}>
                        {product.status}
                      </Badge>
                    </td>
                    {canManage && (
                      <td className="px-6 py-4 text-right space-x-2">
                        {product.product_type === 'GOODS' && (
                          <Link to={`/businesses/${businessId}/products/${product.id}/variants`}>
                            <Button size="sm" variant="outline">
                              Variants
                            </Button>
                          </Link>
                        )}
                        <Button size="sm" variant="ghost" onClick={() => handleOpenEdit(product)}>
                          Edit
                        </Button>
                        <Button size="sm" variant="danger" onClick={() => setArchiveConfirmProduct(product)}>
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
            {products.map((product) => (
              <Card key={product.id} className="p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="font-semibold text-slate-900 dark:text-slate-100">{product.name}</h2>
                    <span className="font-mono text-xs text-slate-500 dark:text-slate-400">{product.code}</span>
                  </div>
                  <Badge variant={product.status === 'ACTIVE' ? 'success' : 'error'}>
                    {product.status}
                  </Badge>
                </div>

                {product.description && (
                  <p className="text-xs text-slate-600 dark:text-slate-400">{product.description}</p>
                )}

                <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 dark:text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-700">
                  <div>
                    <span className="font-medium text-slate-500">Category:</span> {getCategoryName(product.category_id)}
                  </div>
                  <div>
                    <span className="font-medium text-slate-500">Unit:</span> {getUnitName(product.unit_id)}
                  </div>
                  <div>
                    <span className="font-medium text-slate-500">Type:</span> {product.product_type}
                  </div>
                </div>

                {canManage && (
                  <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-700">
                    <Button size="sm" variant="outline" onClick={() => handleOpenEdit(product)}>
                      Edit
                    </Button>
                    <Button size="sm" variant="danger" onClick={() => setArchiveConfirmProduct(product)}>
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
              {editingProduct ? 'Edit Product' : 'Create Product'}
            </h2>

            {formError && (
              <div className="p-3 text-xs bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 rounded-lg border border-rose-200 dark:border-rose-900">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="Product Name"
                placeholder="e.g. Indomie Goreng"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />

              <Input
                label="Product Code"
                placeholder="e.g. PRD-001"
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                required
              />

              <div className="flex flex-col gap-1.5">
                <label htmlFor="product-type" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Product Type
                </label>
                <select
                  id="product-type"
                  aria-label="Product Type"
                  className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900 dark:text-slate-100 min-h-[40px]"
                  value={formData.product_type}
                  onChange={(e) => setFormData({ ...formData, product_type: e.target.value as ProductType })}
                >
                  <option value="GOODS">GOODS (Physical barang)</option>
                  <option value="SERVICE">SERVICE (Jasa / offering)</option>
                </select>
              </div>

              <div className="flex flex-col gap-1.5">
                <label htmlFor="unit-select" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Unit (Base Operational Unit)
                </label>
                <select
                  id="unit-select"
                  aria-label="Unit (Base Operational Unit)"
                  className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900 dark:text-slate-100 min-h-[40px]"
                  value={formData.unit_id}
                  onChange={(e) => setFormData({ ...formData, unit_id: e.target.value })}
                  required
                >
                  <option value="" disabled>
                    Select Unit
                  </option>
                  {units.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name} ({u.code})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-1.5">
                <label htmlFor="category-select" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Category (Optional)
                </label>
                <select
                  id="category-select"
                  aria-label="Category (Optional)"
                  className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900 dark:text-slate-100 min-h-[40px]"
                  value={formData.category_id}
                  onChange={(e) => setFormData({ ...formData, category_id: e.target.value })}
                >
                  <option value="">No Category (Uncategorized)</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-1.5">
                <label htmlFor="description" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Description (Optional)
                </label>
                <textarea
                  id="description"
                  rows={3}
                  className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900 dark:text-slate-100"
                  placeholder="Optional product description..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-700">
                <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" isLoading={isSubmitting}>
                  {editingProduct ? 'Save Changes' : 'Create Product'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Archive Modal */}
      {archiveConfirmProduct && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
              Archive Product?
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Are you sure you want to archive <strong>{archiveConfirmProduct.name}</strong> ({archiveConfirmProduct.code})? It will be soft-archived and removed from active list.
            </p>
            <div className="flex items-center justify-end gap-3 pt-2">
              <Button variant="outline" onClick={() => setArchiveConfirmProduct(null)}>
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
