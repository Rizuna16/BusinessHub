import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { Category, CategoryCreatePayload, CategoryUpdatePayload } from '@/types/category';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { useTheme } from '@/hooks/useTheme';

export const Categories: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();
  const { isDark } = useTheme();

  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');

  const [showForm, setShowForm] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string>('');

  const [confirmArchive, setConfirmArchive] = useState<{ open: boolean; category: Category | null }>(
    { open: false, category: null }
  );

  const [form, setForm] = useState<CategoryCreatePayload>({
    name: '',
    code: '',
    description: '',
    parent_id: null,
    sort_order: 0,
  });

  const activeCategories = categories.filter(c => c.status === 'ACTIVE');
  const archivedCategories = categories.filter(c => c.status === 'ARCHIVED');

  const fetchCategories = useCallback(async () => {
    if (!businessId) return;
    try {
      setIsLoading(true);
      setServerError('');
      const data = await apiClient.listCategories(businessId);
      setCategories(data);
    } catch (err: any) {
      const msg = err?.message || 'Gagal memuat kategori.';
      if (msg.toLowerCase().includes('unauthorized')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [businessId, navigate]);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  const resetForm = () => {
    setForm({ name: '', code: '', description: '', parent_id: null, sort_order: 0 });
    setEditingId(null);
    setFormError('');
  };

  const handleEdit = (cat: Category | null) => {
    if (cat) {
      setEditingId(cat.id);
      setForm({
        name: cat.name,
        code: cat.code,
        description: cat.description ?? '',
        parent_id: cat.parent_id ?? null,
        sort_order: cat.sort_order,
      });
    } else {
      resetForm();
    }
    setShowForm(true);
  };

  const handleDelete = (cat: Category) => {
    setConfirmArchive({ open: true, category: cat });
  };

  const confirmDelete = async () => {
    if (!confirmArchive.category || !businessId) return;
    try {
      setIsSubmitting(true);
      await apiClient.archiveCategory(businessId, confirmArchive.category.id);
      setConfirmArchive({ open: false, category: null });
      fetchCategories();
    } catch (err: any) {
      setServerError(err?.message || 'Gagal mengarsipkan.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = async () => {
    setFormError('');

    if (!businessId) return;
    setIsSubmitting(true);
    try {
      const payload: CategoryCreatePayload = {
        name: form.name.trim(),
        code: form.code.trim().toUpperCase(),
        description: form.description?.trim() || null,
        parent_id: form.parent_id,
        sort_order: form.sort_order,
      };

      if (editingId) {
        await apiClient.updateCategory(businessId, editingId, payload as CategoryUpdatePayload);
      } else {
        await apiClient.createCategory(businessId, payload);
      }
      setShowForm(false);
      resetForm();
      fetchCategories();
    } catch (err: any) {
      setFormError(err?.message || 'Gagal menyimpan.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={`min-h-screen transition-colors duration-200 ${isDark ? 'bg-slate-900 text-slate-100' : 'bg-slate-50 text-slate-900'}`}>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className={`text-2xl font-bold ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>
              Kategori
            </h1>
            <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
              Kelola kategori untuk bisnis Anda.
            </p>
          </div>
          <Button variant="primary" size="sm" onClick={() => handleEdit(null)}>
            Tambah Kategori
          </Button>
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="flex h-48 w-full items-center justify-center">
            <Loading size="md" text="Memuat kategori..." />
          </div>
        )}

        {/* Error */}
        {!isLoading && serverError && (
          <ErrorState title="Error" message={serverError} onRetry={fetchCategories} />
        )}

        {/* Empty */}
        {!isLoading && !serverError && activeCategories.length === 0 && (
          <div className="text-center py-12">
            <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 ${
              isDark ? 'bg-slate-800 text-slate-500' : 'bg-slate-100 text-slate-400'
            }`}>
              <span className="text-3xl">📦</span>
            </div>
            <h3 className={`text-lg font-medium mb-2 ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
              Belum ada kategori
            </h3>
            <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
              Tambahkan kategori pertama untuk mulai mengelola master data.
            </p>
          </div>
        )}

        {/* Active Categories */}
        {!isLoading && !serverError && activeCategories.length > 0 && (
          <div className="space-y-4">
            {activeCategories.map((cat) => (
              <Card key={cat.id} className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className={`font-semibold ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>
                        {cat.name}
                      </h3>
                      <Badge variant="info" size="sm">{cat.code}</Badge>
                      {cat.parent_id && (
                        <Badge variant="neutral" size="sm">Has Parent</Badge>
                      )}
                    </div>
                    {cat.description && (
                      <p className={`text-sm mt-1 line-clamp-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                        {cat.description}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 ml-2">
                    <Button variant="outline" size="sm" onClick={() => handleEdit(cat)}>
                      Edit
                    </Button>
                    <Button variant="danger" size="sm" onClick={() => handleDelete(cat)}>
                      Arsipkan
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Archived Categories */}
        {archivedCategories.length > 0 && (
          <div className="mt-8">
            <h2 className={`text-lg font-semibold mb-3 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
              Arsip
            </h2>
            <div className="space-y-2">
              {archivedCategories.map((cat) => (
                <div
                  key={cat.id}
                  className={`p-3 rounded-lg border ${
                    isDark ? 'border-slate-700 bg-slate-800/30' : 'border-slate-200 bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className={`font-medium ${isDark ? 'text-slate-200' : 'text-slate-700'}`}>{cat.name}</span>
                      <Badge variant="warning" size="sm" className="ml-2">Archived</Badge>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Form Modal */}
        {showForm && (
          <div
            className="fixed inset-0 flex items-center justify-center z-50 bg-black/50"
            role="dialog"
            aria-modal="true"
            aria-labelledby="form-title"
          >
            <div className={`rounded-xl shadow-xl max-w-lg w-full mx-4 p-6 ${
              isDark ? 'bg-slate-800 border border-slate-700' : 'bg-white'
            }`}>
              <h2 id="form-title" className={`text-lg font-bold mb-4 ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>
                {editingId ? 'Edit Kategori' : 'Tambah Kategori'}
              </h2>

              {formError && (
                <div className={`mb-4 p-3 rounded text-sm ${
                  isDark ? 'bg-rose-900/30 text-rose-300 border border-rose-800' : 'bg-rose-50 text-rose-800 border border-rose-200'
                }`}>
                  {formError}
                </div>
              )}

              <div className="space-y-4">
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-slate-300' : 'text-slate-700'}`} htmlFor="name">
                    Nama
                  </label>
                  <Input
                    id="name"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className="w-full"
                    aria-label="Nama kategori"
                  />
                </div>

                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-slate-300' : 'text-slate-700'}`} htmlFor="code">
                    Kode
                  </label>
                  <Input
                    id="code"
                    value={form.code}
                    onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                    className="w-full"
                    aria-label="Kode kategori"
                  />
                </div>

                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-slate-300' : 'text-slate-700'}`} htmlFor="description">
                    Deskripsi
                  </label>
                  <textarea
                    id="description"
                    rows={3}
                    className={`w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-y min-h-[72px]`}
                    value={form.description ?? ''}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                    aria-label="Deskripsi kategori"
                  />
                </div>

                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-slate-300' : 'text-slate-700'}`} htmlFor="sort_order">
                    Urutan
                  </label>
                  <Input
                    id="sort_order"
                    type="number"
                    min={0}
                    value={form.sort_order}
                    onChange={(e) => setForm({ ...form, sort_order: parseInt(e.target.value, 10) || 0 })}
                    className="w-full"
                    aria-label="Urutan tampilan"
                  />
                </div>
              </div>

              <div className="mt-6 flex justify-end gap-3">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => { setShowForm(false); resetForm(); }}
                  aria-label="Batal"
                >
                  Batal
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  isLoading={isSubmitting}
                  onClick={handleSubmit}
                  aria-label="Simpan"
                >
                  Simpan
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Archive Confirm */}
        {confirmArchive.open && (
          <div
            className="fixed inset-0 flex items-center justify-center z-50 bg-black/50"
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-title"
          >
            <div className={`rounded-xl shadow-xl max-w-md w-full mx-4 p-6 ${
              isDark ? 'bg-slate-800 border border-slate-700' : 'bg-white'
            }`}>
              <h2 id="confirm-title" className={`text-lg font-bold mb-3 ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>
                Konfirmasi Arsip
              </h2>
              <p className={`text-sm mb-4 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
                Kategori "{confirmArchive.category?.name}" akan diarsipkan. Data tidak akan dihapus.
              </p>
              <div className="flex justify-end gap-3">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setConfirmArchive({ open: false, category: null })}
                  aria-label="Batal"
                >
                  Batal
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  isLoading={isSubmitting}
                  onClick={confirmDelete}
                  aria-label="Arsipkan"
                >
                  Arsipkan
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Categories;
