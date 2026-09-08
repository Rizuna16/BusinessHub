import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type {
  Supplier,
  SupplierCreatePayload,
  SupplierUpdatePayload,
  SupplierType,
} from '@/types/supplier';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { useTheme } from '@/hooks/useTheme';

export const Suppliers: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();
  const { isDark } = useTheme();

  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(10);

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');

  const [showForm, setShowForm] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string>('');

  const [selectedSupplier, setSelectedSupplier] = useState<Supplier | null>(null);
  const [confirmModal, setConfirmModal] = useState<{
    open: boolean;
    action: 'archive' | 'activate' | 'deactivate' | null;
    supplier: Supplier | null;
  }>({ open: false, action: null, supplier: null });

  const [form, setForm] = useState<SupplierCreatePayload>({
    supplier_type: 'INDIVIDUAL',
    name: '',
    legal_name: '',
    phone: '',
    email: '',
    address: '',
    city: '',
    province: '',
    postal_code: '',
    country: '',
    notes: '',
  });

  const fetchSuppliers = useCallback(async () => {
    if (!businessId) return;
    try {
      setIsLoading(true);
      setServerError('');
      const res = await apiClient.listSuppliers(businessId, {
        search: searchQuery || undefined,
        status: statusFilter || undefined,
        supplier_type: typeFilter || undefined,
        page,
        page_size: pageSize,
      });
      setSuppliers(res.items);
      setTotal(res.total);
    } catch (err: any) {
      const msg = err?.message || 'Gagal memuat supplier.';
      if (msg.toLowerCase().includes('unauthorized')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [businessId, searchQuery, statusFilter, typeFilter, page, pageSize, navigate]);

  useEffect(() => {
    fetchSuppliers();
  }, [fetchSuppliers]);

  const resetForm = () => {
    setForm({
      supplier_type: 'INDIVIDUAL',
      name: '',
      legal_name: '',
      phone: '',
      email: '',
      address: '',
      city: '',
      province: '',
      postal_code: '',
      country: '',
      notes: '',
    });
    setEditingId(null);
    setFormError('');
  };

  const handleOpenCreate = () => {
    resetForm();
    setShowForm(true);
  };

  const handleOpenEdit = (s: Supplier | null) => {
    if (s) {
      setEditingId(s.id);
      setForm({
        supplier_type: s.supplier_type,
        name: s.name,
        legal_name: s.legal_name || '',
        phone: s.phone || '',
        email: s.email || '',
        address: s.address || '',
        city: s.city || '',
        province: s.province || '',
        postal_code: s.postal_code || '',
        country: s.country || '',
        notes: s.notes || '',
      });
    } else {
      resetForm();
    }
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      const payload: SupplierCreatePayload = {
        supplier_type: form.supplier_type,
        name: form.name.trim(),
        legal_name: form.legal_name?.trim() || null,
        phone: form.phone?.trim() || null,
        email: form.email?.trim() || null,
        address: form.address?.trim() || null,
        city: form.city?.trim() || null,
        province: form.province?.trim() || null,
        postal_code: form.postal_code?.trim() || null,
        country: form.country?.trim() || null,
        notes: form.notes?.trim() || null,
      };

      if (editingId) {
        await apiClient.updateSupplier(businessId, editingId, payload as SupplierUpdatePayload);
      } else {
        await apiClient.createSupplier(businessId, payload);
      }
      setShowForm(false);
      resetForm();
      fetchSuppliers();
    } catch (err: any) {
      setFormError(err?.message || 'Gagal menyimpan supplier.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleActionConfirm = async () => {
    if (!confirmModal.supplier || !confirmModal.action || !businessId) return;
    try {
      setIsSubmitting(true);
      const supId = confirmModal.supplier.id;
      if (confirmModal.action === 'archive') {
        await apiClient.archiveSupplier(businessId, supId);
      } else if (confirmModal.action === 'activate') {
        await apiClient.activateSupplier(businessId, supId);
      } else if (confirmModal.action === 'deactivate') {
        await apiClient.deactivateSupplier(businessId, supId);
      }
      setConfirmModal({ open: false, action: null, supplier: null });
      fetchSuppliers();
    } catch (err: any) {
      setServerError(err?.message || 'Gagal melakukan aksi.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setPage(1);
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className={`min-h-screen transition-colors duration-200 ${isDark ? 'bg-slate-900 text-slate-100' : 'bg-slate-50 text-slate-900'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate(`/businesses/${businessId}`)}
              >
                ← Kembali ke Bisnis
              </Button>
            </div>
            <h1 className={`text-2xl font-bold ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>
              Supplier Management
            </h1>
            <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
              Kelola master data supplier/vendor untuk bisnis Anda.
            </p>
          </div>
          <Button variant="primary" size="sm" onClick={handleOpenCreate}>
            + Supplier Baru
          </Button>
        </header>

        {/* Filters */}
        <section
          className={`p-4 rounded-xl border mb-6 flex flex-col sm:flex-row gap-4 items-center justify-between ${
            isDark ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'
          }`}
        >
          <div className="w-full sm:w-72">
            <label htmlFor="search" className="sr-only">
              Cari supplier
            </label>
            <Input
              id="search"
              placeholder="Cari kode, nama, telp, email..."
              value={searchQuery}
              onChange={handleSearchChange}
              aria-label="Cari supplier"
            />
          </div>
          <div className="flex flex-wrap gap-3 w-full sm:w-auto items-center">
            <label htmlFor="filter-type" className="sr-only">
              Filter tipe
            </label>
            <select
              id="filter-type"
              className={`px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                isDark ? 'bg-slate-900 border-slate-700 text-slate-200' : 'bg-white border-slate-300 text-slate-800'
              }`}
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value);
                setPage(1);
              }}
              aria-label="Filter tipe supplier"
            >
              <option value="">Semua Tipe</option>
              <option value="INDIVIDUAL">Individual</option>
              <option value="ORGANIZATION">Organization</option>
            </select>

            <label htmlFor="filter-status" className="sr-only">
              Filter status
            </label>
            <select
              id="filter-status"
              className={`px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                isDark ? 'bg-slate-900 border-slate-700 text-slate-200' : 'bg-white border-slate-300 text-slate-800'
              }`}
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              aria-label="Filter status supplier"
            >
              <option value="">Semua Status</option>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
              <option value="ARCHIVED">Archived</option>
            </select>
          </div>
        </section>

        {/* Content States */}
        {isLoading && (
          <div className="flex h-48 w-full items-center justify-center">
            <Loading size="md" text="Memuat supplier..." />
          </div>
        )}

        {!isLoading && serverError && (
          <ErrorState title="Error" message={serverError} onRetry={fetchSuppliers} />
        )}

        {!isLoading && !serverError && suppliers.length === 0 && (
          <div className="text-center py-12 border rounded-xl border-dashed border-slate-700">
            <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 ${
              isDark ? 'bg-slate-800 text-slate-500' : 'bg-slate-100 text-slate-400'
            }`}>
              <span className="text-3xl">🏭</span>
            </div>
            <h3 className={`text-lg font-medium mb-2 ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
              Belum ada supplier
            </h3>
            <p className={`text-sm mb-4 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
              Tambahkan supplier pertama untuk mulai mengelola master data.
            </p>
            <Button variant="primary" size="sm" onClick={handleOpenCreate}>
              + Supplier Baru
            </Button>
          </div>
        )}

        {!isLoading && !serverError && suppliers.length > 0 && (
          <>
            <div className={`border rounded-xl overflow-hidden shadow-sm ${isDark ? 'border-slate-700 bg-slate-800' : 'border-slate-200 bg-white'}`}>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className={`border-b text-xs uppercase tracking-wider ${
                    isDark ? 'bg-slate-800/80 border-slate-700 text-slate-400' : 'bg-slate-50 border-slate-200 text-slate-500'
                  }`}>
                    <tr>
                      <th scope="col" className="py-3 px-4">Kode</th>
                      <th scope="col" className="py-3 px-4">Nama</th>
                      <th scope="col" className="py-3 px-4">Tipe</th>
                      <th scope="col" className="py-3 px-4">Telepon / Email</th>
                      <th scope="col" className="py-3 px-4">Kota</th>
                      <th scope="col" className="py-3 px-4">Status</th>
                      <th scope="col" className="py-3 px-4 text-right">Aksi</th>
                    </tr>
                  </thead>
                  <tbody className={`divide-y ${isDark ? 'divide-slate-700' : 'divide-slate-200'}`}>
                    {suppliers.map((s) => (
                      <tr key={s.id} className={isDark ? 'hover:bg-slate-700/50' : 'hover:bg-slate-50'}>
                        <td className="py-3 px-4 font-mono font-medium">{s.code}</td>
                        <td className="py-3 px-4">
                          <button
                            onClick={() => setSelectedSupplier(s)}
                            className="font-medium text-blue-500 hover:underline text-left"
                          >
                            {s.name}
                          </button>
                          {s.legal_name && (
                            <div className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                              {s.legal_name}
                            </div>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          <Badge variant={s.supplier_type === 'ORGANIZATION' ? 'info' : 'neutral'}>
                            {s.supplier_type}
                          </Badge>
                        </td>
                        <td className="py-3 px-4">
                          <div className={isDark ? 'text-slate-200' : 'text-slate-800'}>
                            {s.phone || '-'}
                          </div>
                          <div className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                            {s.email || '-'}
                          </div>
                        </td>
                        <td className="py-3 px-4">{s.city || '-'}</td>
                        <td className="py-3 px-4">
                          <Badge
                            variant={
                              s.status === 'ACTIVE'
                                ? 'success'
                                : s.status === 'INACTIVE'
                                ? 'warning'
                                : 'error'
                            }
                          >
                            {s.status}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 text-right space-x-2">
                          <button
                            onClick={() => setSelectedSupplier(s)}
                            className="text-xs text-blue-500 hover:underline"
                          >
                            Detail
                          </button>
                          {s.status !== 'ARCHIVED' && (
                            <>
                              <button
                                onClick={() => handleOpenEdit(s)}
                                className="text-xs text-amber-500 hover:underline"
                              >
                                Edit
                              </button>
                              {s.status === 'ACTIVE' ? (
                                <button
                                  onClick={() => setConfirmModal({ open: true, action: 'deactivate', supplier: s })}
                                  className="text-xs text-orange-500 hover:underline"
                                >
                                  Nonaktifkan
                                </button>
                              ) : (
                                <button
                                  onClick={() => setConfirmModal({ open: true, action: 'activate', supplier: s })}
                                  className="text-xs text-emerald-500 hover:underline"
                                >
                                  Aktifkan
                                </button>
                              )}
                              <button
                                onClick={() => setConfirmModal({ open: true, action: 'archive', supplier: s })}
                                className="text-xs text-red-500 hover:underline"
                              >
                                Arsipkan
                              </button>
                            </>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination controls */}
              <nav
                aria-label="Navigasi halaman"
                className={`p-4 border-t flex items-center justify-between ${
                  isDark ? 'border-slate-700 bg-slate-800' : 'border-slate-200 bg-white'
                }`}
              >
                <div className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                  Menampilkan halaman {page} dari {totalPages} ({total} total supplier)
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(p - 1, 1))}
                  >
                    Sebelumnya
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                  >
                    Selanjutnya
                  </Button>
                </div>
              </nav>
            </div>
          </>
        )}

        {/* Create / Edit Modal */}
        {showForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <div className={`w-full max-w-2xl rounded-xl shadow-xl border overflow-y-auto max-h-[90vh] ${
              isDark ? 'bg-slate-800 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-900'
            }`}>
              <div className="p-6">
                <h2 className="text-xl font-bold mb-4">
                  {editingId ? 'Edit Supplier' : 'Tambah Supplier Baru'}
                </h2>

                {formError && (
                  <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm">
                    {formError}
                  </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="supplier_type" className="block text-sm font-medium mb-1">
                        Tipe Supplier
                      </label>
                      <select
                        id="supplier_type"
                        className={`w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                          isDark ? 'bg-slate-900 border-slate-700 text-slate-200' : 'bg-white border-slate-300 text-slate-800'
                        }`}
                        value={form.supplier_type}
                        onChange={(e) => setForm({ ...form, supplier_type: e.target.value as SupplierType })}
                      >
                        <option value="INDIVIDUAL">Individual</option>
                        <option value="ORGANIZATION">Organization</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor="name" className="block text-sm font-medium mb-1">
                        Nama *
                      </label>
                      <Input
                        id="name"
                        required
                        placeholder="Cth: Andi / PT Maju Jaya"
                        value={form.name}
                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="legal_name" className="block text-sm font-medium mb-1">
                        Legal Name
                      </label>
                      <Input
                        id="legal_name"
                        placeholder="Cth: PT Maju Jaya Tbk"
                        value={form.legal_name || ''}
                        onChange={(e) => setForm({ ...form, legal_name: e.target.value })}
                      />
                    </div>
                    <div>
                      <label htmlFor="phone" className="block text-sm font-medium mb-1">
                        Telepon
                      </label>
                      <Input
                        id="phone"
                        placeholder="Cth: 08123456789"
                        value={form.phone || ''}
                        onChange={(e) => setForm({ ...form, phone: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="email" className="block text-sm font-medium mb-1">
                        Email
                      </label>
                      <Input
                        id="email"
                        type="email"
                        placeholder="Cth: email@example.com"
                        value={form.email || ''}
                        onChange={(e) => setForm({ ...form, email: e.target.value })}
                      />
                    </div>
                    <div>
                      <label htmlFor="city" className="block text-sm font-medium mb-1">
                        Kota
                      </label>
                      <Input
                        id="city"
                        placeholder="Cth: Jakarta"
                        value={form.city || ''}
                        onChange={(e) => setForm({ ...form, city: e.target.value })}
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor="address" className="block text-sm font-medium mb-1">
                      Alamat
                    </label>
                    <Input
                      id="address"
                      placeholder="Cth: Jl. Raya No. 1"
                      value={form.address || ''}
                      onChange={(e) => setForm({ ...form, address: e.target.value })}
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div>
                      <label htmlFor="province" className="block text-sm font-medium mb-1">
                        Provinsi
                      </label>
                      <Input
                        id="province"
                        placeholder="Cth: DKI Jakarta"
                        value={form.province || ''}
                        onChange={(e) => setForm({ ...form, province: e.target.value })}
                      />
                    </div>
                    <div>
                      <label htmlFor="postal_code" className="block text-sm font-medium mb-1">
                        Kode Pos
                      </label>
                      <Input
                        id="postal_code"
                        placeholder="Cth: 12345"
                        value={form.postal_code || ''}
                        onChange={(e) => setForm({ ...form, postal_code: e.target.value })}
                      />
                    </div>
                    <div>
                      <label htmlFor="country" className="block text-sm font-medium mb-1">
                        Negara
                      </label>
                      <Input
                        id="country"
                        placeholder="Cth: Indonesia"
                        value={form.country || ''}
                        onChange={(e) => setForm({ ...form, country: e.target.value })}
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor="notes" className="block text-sm font-medium mb-1">
                      Catatan
                    </label>
                    <textarea
                      id="notes"
                      rows={3}
                      className={`w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y ${
                        isDark ? 'bg-slate-900 border-slate-700 text-slate-200' : 'bg-white border-slate-300 text-slate-800'
                      }`}
                      placeholder="Catatan tambahan..."
                      value={form.notes || ''}
                      onChange={(e) => setForm({ ...form, notes: e.target.value })}
                    />
                  </div>

                  <div className="flex justify-end gap-3 pt-4 border-t border-slate-700">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setShowForm(false);
                        resetForm();
                      }}
                    >
                      Batal
                    </Button>
                    <Button type="submit" variant="primary" disabled={isSubmitting}>
                      {isSubmitting ? 'Menyimpan...' : 'Simpan'}
                    </Button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* Detail Modal */}
        {selectedSupplier && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <div className={`w-full max-w-xl rounded-xl shadow-xl border ${
              isDark ? 'bg-slate-800 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-900'
            }`}>
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-bold">Detail Supplier</h2>
                  <Badge variant={selectedSupplier.status === 'ACTIVE' ? 'success' : selectedSupplier.status === 'INACTIVE' ? 'warning' : 'error'}>
                    {selectedSupplier.status}
                  </Badge>
                </div>

                <div className="space-y-3 text-sm">
                  <div className="grid grid-cols-3 gap-2">
                    <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Kode</span>
                    <span className="col-span-2 font-mono font-bold">{selectedSupplier.code}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Tipe</span>
                    <span className="col-span-2">{selectedSupplier.supplier_type}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Nama</span>
                    <span className="col-span-2 font-medium">{selectedSupplier.name}</span>
                  </div>
                  {selectedSupplier.legal_name && (
                    <div className="grid grid-cols-3 gap-2">
                      <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Legal Name</span>
                      <span className="col-span-2">{selectedSupplier.legal_name}</span>
                    </div>
                  )}
                  <div className="grid grid-cols-3 gap-2">
                    <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Telepon</span>
                    <span className="col-span-2">{selectedSupplier.phone || '-'}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Email</span>
                    <span className="col-span-2">{selectedSupplier.email || '-'}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Alamat</span>
                    <span className="col-span-2">
                      {[
                        selectedSupplier.address,
                        selectedSupplier.city,
                        selectedSupplier.province,
                        selectedSupplier.postal_code,
                        selectedSupplier.country,
                      ].filter(Boolean).join(', ') || '-'}
                    </span>
                  </div>
                  {selectedSupplier.notes && (
                    <div className="grid grid-cols-3 gap-2">
                      <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Catatan</span>
                      <span className="col-span-2">{selectedSupplier.notes}</span>
                    </div>
                  )}
                  <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-700">
                    <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Dibuat Pada</span>
                    <span className="col-span-2 text-xs">
                      {new Date(selectedSupplier.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Diperbarui Pada</span>
                    <span className="col-span-2 text-xs">
                      {new Date(selectedSupplier.updated_at).toLocaleString()}
                    </span>
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-6 mt-4 border-t border-slate-700">
                  <Button
                    variant="outline"
                    onClick={() => setSelectedSupplier(null)}
                  >
                    Tutup
                  </Button>
                  {selectedSupplier.status !== 'ARCHIVED' && (
                    <Button
                      variant="primary"
                      onClick={() => {
                        const s = selectedSupplier;
                        setSelectedSupplier(null);
                        handleOpenEdit(s);
                      }}
                    >
                      Edit Supplier
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Confirmation Modal */}
        {confirmModal.open && confirmModal.supplier && confirmModal.action && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <div className={`w-full max-w-md rounded-xl shadow-xl border ${
              isDark ? 'bg-slate-800 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-900'
            }`}>
              <div className="p-6">
                <h3 className="text-lg font-bold mb-2 capitalize">
                  {confirmModal.action === 'archive' && 'Arsipkan Supplier'}
                  {confirmModal.action === 'activate' && 'Aktifkan Supplier'}
                  {confirmModal.action === 'deactivate' && 'Nonaktifkan Supplier'}
                </h3>
                <p className={`text-sm mb-6 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
                  Apakah Anda yakin ingin {confirmModal.action} supplier{' '}
                  <span className="font-semibold">
                    {confirmModal.supplier?.name} ({confirmModal.supplier?.code})
                  </span>
                  ?
                </p>
                <div className="flex justify-end gap-3">
                  <Button
                    variant="outline"
                    onClick={() => setConfirmModal({ open: false, action: null, supplier: null })}
                  >
                    Batal
                  </Button>
                  <Button
                    variant={confirmModal.action === 'archive' ? 'danger' : 'primary'}
                    onClick={handleActionConfirm}
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? 'Memproses...' : 'Ya, Lanjutkan'}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
