import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type {
  Customer,
  CustomerCreatePayload,
  CustomerUpdatePayload,
  CustomerType,
} from '@/types/customer';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { useTheme } from '@/hooks/useTheme';

export const Customers: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();
  const { isDark } = useTheme();

  const [customers, setCustomers] = useState<Customer[]>([]);
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

  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [confirmModal, setConfirmModal] = useState<{
    open: boolean;
    action: 'archive' | 'activate' | 'deactivate' | null;
    customer: Customer | null;
  }>({ open: false, action: null, customer: null });

  const [form, setForm] = useState<CustomerCreatePayload>({
    customer_type: 'INDIVIDUAL',
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

  const fetchCustomers = useCallback(async () => {
    if (!businessId) return;
    try {
      setIsLoading(true);
      setServerError('');
      const res = await apiClient.listCustomers(businessId, {
        search: searchQuery || undefined,
        status: statusFilter || undefined,
        customer_type: typeFilter || undefined,
        page,
        page_size: pageSize,
      });
      setCustomers(res.items);
      setTotal(res.total);
    } catch (err: any) {
      const msg = err?.message || 'Gagal memuat customer.';
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
    fetchCustomers();
  }, [fetchCustomers]);

  const resetForm = () => {
    setForm({
      customer_type: 'INDIVIDUAL',
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

  const handleOpenEdit = (c: Customer) => {
    setEditingId(c.id);
    setForm({
      customer_type: c.customer_type,
      name: c.name,
      legal_name: c.legal_name || '',
      phone: c.phone || '',
      email: c.email || '',
      address: c.address || '',
      city: c.city || '',
      province: c.province || '',
      postal_code: c.postal_code || '',
      country: c.country || '',
      notes: c.notes || '',
    });
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    setFormError('');
    setIsSubmitting(true);
    try {
      const payload: CustomerCreatePayload = {
        customer_type: form.customer_type,
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
        await apiClient.updateCustomer(businessId, editingId, payload as CustomerUpdatePayload);
      } else {
        await apiClient.createCustomer(businessId, payload);
      }
      setShowForm(false);
      resetForm();
      fetchCustomers();
    } catch (err: any) {
      setFormError(err?.message || 'Gagal menyimpan customer.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleActionConfirm = async () => {
    if (!confirmModal.customer || !confirmModal.action || !businessId) return;
    try {
      setIsSubmitting(true);
      const custId = confirmModal.customer.id;
      if (confirmModal.action === 'archive') {
        await apiClient.archiveCustomer(businessId, custId);
      } else if (confirmModal.action === 'activate') {
        await apiClient.activateCustomer(businessId, custId);
      } else if (confirmModal.action === 'deactivate') {
        await apiClient.deactivateCustomer(businessId, custId);
      }
      setConfirmModal({ open: false, action: null, customer: null });
      fetchCustomers();
    } catch (err: any) {
      setServerError(err?.message || 'Gagal melakukan aksi.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className={`min-h-screen transition-colors duration-200 ${isDark ? 'bg-slate-900 text-slate-100' : 'bg-slate-50 text-slate-900'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
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
              Customer Management
            </h1>
            <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
              Kelola master data customer individual dan organisasi untuk bisnis Anda.
            </p>
          </div>
          <Button variant="primary" size="sm" onClick={handleOpenCreate}>
            + Customer Baru
          </Button>
        </div>

        {/* Search & Filters */}
        <div className={`p-4 rounded-xl border mb-6 flex flex-col sm:flex-row gap-4 items-center justify-between ${
          isDark ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'
        }`}>
          <div className="w-full sm:w-72">
            <Input
              placeholder="Cari kode, nama, telp, email..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <div className="flex flex-wrap gap-3 w-full sm:w-auto items-center">
            <select
              aria-label="Filter Tipe Customer"
              className={`px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                isDark ? 'bg-slate-900 border-slate-700 text-slate-200' : 'bg-white border-slate-300 text-slate-800'
              }`}
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="">Semua Tipe</option>
              <option value="INDIVIDUAL">Individual</option>
              <option value="ORGANIZATION">Organization</option>
            </select>

            <select
              aria-label="Filter Status Customer"
              className={`px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                isDark ? 'bg-slate-900 border-slate-700 text-slate-200' : 'bg-white border-slate-300 text-slate-800'
              }`}
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="">Semua Status</option>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
              <option value="ARCHIVED">Archived</option>
            </select>
          </div>
        </div>

        {/* Content States */}
        {isLoading && (
          <div className="flex h-48 w-full items-center justify-center">
            <Loading size="md" text="Memuat customer..." />
          </div>
        )}

        {!isLoading && serverError && (
          <ErrorState title="Error" message={serverError} onRetry={fetchCustomers} />
        )}

        {!isLoading && !serverError && customers.length === 0 && (
          <div className="text-center py-16 border rounded-xl border-dashed border-slate-700">
            <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 ${
              isDark ? 'bg-slate-800 text-slate-500' : 'bg-slate-100 text-slate-400'
            }`}>
              <span className="text-3xl">👥</span>
            </div>
            <h3 className={`text-lg font-medium mb-2 ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
              Tidak ada customer ditemukan
            </h3>
            <p className={`text-sm mb-4 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
              Mulai dengan menambahkan customer baru ke dalam sistem.
            </p>
            <Button variant="primary" size="sm" onClick={handleOpenCreate}>
              + Customer Baru
            </Button>
          </div>
        )}

        {!isLoading && !serverError && customers.length > 0 && (
          <>
            {/* Desktop Table & Mobile Card view */}
            <div className={`border rounded-xl overflow-hidden shadow-sm ${isDark ? 'border-slate-700 bg-slate-800' : 'border-slate-200 bg-white'}`}>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className={`border-b text-xs uppercase tracking-wider ${
                    isDark ? 'bg-slate-800/80 border-slate-700 text-slate-400' : 'bg-slate-50 border-slate-200 text-slate-500'
                  }`}>
                    <tr>
                      <th className="py-3 px-4">Kode</th>
                      <th className="py-3 px-4">Nama</th>
                      <th className="py-3 px-4">Tipe</th>
                      <th className="py-3 px-4">Telepon / Email</th>
                      <th className="py-3 px-4">Kota</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4 text-right">Aksi</th>
                    </tr>
                  </thead>
                  <tbody className={`divide-y ${isDark ? 'divide-slate-700' : 'divide-slate-200'}`}>
                    {customers.map((c) => (
                      <tr key={c.id} className={`transition-colors ${isDark ? 'hover:bg-slate-700/50' : 'hover:bg-slate-50'}`}>
                        <td className="py-3 px-4 font-mono font-medium">{c.code}</td>
                        <td className="py-3 px-4">
                          <button
                            onClick={() => setSelectedCustomer(c)}
                            className="font-medium text-blue-500 hover:underline text-left"
                          >
                            {c.name}
                          </button>
                          {c.legal_name && (
                            <div className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                              {c.legal_name}
                            </div>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          <Badge variant={c.customer_type === 'ORGANIZATION' ? 'info' : 'neutral'}>
                            {c.customer_type}
                          </Badge>
                        </td>
                        <td className="py-3 px-4">
                          <div className={isDark ? 'text-slate-200' : 'text-slate-800'}>
                            {c.phone || '-'}
                          </div>
                          <div className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                            {c.email || '-'}
                          </div>
                        </td>
                        <td className="py-3 px-4">{c.city || '-'}</td>
                        <td className="py-3 px-4">
                          <Badge
                            variant={
                              c.status === 'ACTIVE'
                                ? 'success'
                                : c.status === 'INACTIVE'
                                ? 'warning'
                                : 'error'
                            }
                          >
                            {c.status}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 text-right space-x-2">
                          <button
                            onClick={() => setSelectedCustomer(c)}
                            className="text-xs text-blue-500 hover:underline"
                          >
                            Detail
                          </button>
                          {c.status !== 'ARCHIVED' && (
                            <>
                              <button
                                onClick={() => handleOpenEdit(c)}
                                className="text-xs text-amber-500 hover:underline"
                              >
                                Edit
                              </button>
                              {c.status === 'ACTIVE' ? (
                                <button
                                  onClick={() => setConfirmModal({ open: true, action: 'deactivate', customer: c })}
                                  className="text-xs text-orange-500 hover:underline"
                                >
                                  Nonaktifkan
                                </button>
                              ) : (
                                <button
                                  onClick={() => setConfirmModal({ open: true, action: 'activate', customer: c })}
                                  className="text-xs text-emerald-500 hover:underline"
                                >
                                  Aktifkan
                                </button>
                              )}
                              <button
                                onClick={() => setConfirmModal({ open: true, action: 'archive', customer: c })}
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
              <div className={`p-4 border-t flex items-center justify-between ${
                isDark ? 'border-slate-700 bg-slate-800' : 'border-slate-200 bg-white'
              }`}>
                <div className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                  Menampilkan halaman {page} dari {totalPages} ({total} total customer)
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
              </div>
            </div>
          </>
        )}

        {/* Create / Edit Modal */}
        {showForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <div className={`w-full max-w-2xl rounded-xl shadow-xl p-6 border overflow-y-auto max-h-[90vh] ${
              isDark ? 'bg-slate-800 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-900'
            }`}>
              <h2 className="text-xl font-bold mb-4">
                {editingId ? 'Edit Customer' : 'Tambah Customer Baru'}
              </h2>

              {formError && (
                <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm">
                  {formError}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Tipe Customer</label>
                    <select
                      className={`w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                        isDark ? 'bg-slate-900 border-slate-700 text-slate-200' : 'bg-white border-slate-300 text-slate-800'
                      }`}
                      value={form.customer_type}
                      onChange={(e) => setForm({ ...form, customer_type: e.target.value as CustomerType })}
                    >
                      <option value="INDIVIDUAL">Individual</option>
                      <option value="ORGANIZATION">Organization</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Nama *</label>
                    <Input
                      required
                      placeholder="Cth: Budi Santoso / PT Maju"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Legal Name</label>
                    <Input
                      placeholder="Cth: PT Maju Jaya Tbk"
                      value={form.legal_name || ''}
                      onChange={(e) => setForm({ ...form, legal_name: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Telepon</label>
                    <Input
                      placeholder="Cth: 08123456789"
                      value={form.phone || ''}
                      onChange={(e) => setForm({ ...form, phone: e.target.value })}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Email</label>
                    <Input
                      type="email"
                      placeholder="Cth: email@example.com"
                      value={form.email || ''}
                      onChange={(e) => setForm({ ...form, email: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Kota</label>
                    <Input
                      placeholder="Cth: Jakarta"
                      value={form.city || ''}
                      onChange={(e) => setForm({ ...form, city: e.target.value })}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Alamat</label>
                  <Input
                    placeholder="Cth: Jl. Sudirman No. 123"
                    value={form.address || ''}
                    onChange={(e) => setForm({ ...form, address: e.target.value })}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Provinsi</label>
                    <Input
                      placeholder="Cth: DKI Jakarta"
                      value={form.province || ''}
                      onChange={(e) => setForm({ ...form, province: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Kode Pos</label>
                    <Input
                      placeholder="Cth: 12190"
                      value={form.postal_code || ''}
                      onChange={(e) => setForm({ ...form, postal_code: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Negara</label>
                    <Input
                      placeholder="Cth: Indonesia"
                      value={form.country || ''}
                      onChange={(e) => setForm({ ...form, country: e.target.value })}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Catatan</label>
                  <textarea
                    rows={3}
                    className={`w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 focus:ring-blue-500 ${
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
        )}

        {/* Detail Modal */}
        {selectedCustomer && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <div className={`w-full max-w-xl rounded-xl shadow-xl p-6 border ${
              isDark ? 'bg-slate-800 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-900'
            }`}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold">Detail Customer</h2>
                <Badge variant={selectedCustomer.status === 'ACTIVE' ? 'success' : 'warning'}>
                  {selectedCustomer.status}
                </Badge>
              </div>

              <div className="space-y-3 text-sm">
                <div className="grid grid-cols-3 gap-2">
                  <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Kode</span>
                  <span className="col-span-2 font-mono font-bold">{selectedCustomer.code}</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Tipe</span>
                  <span className="col-span-2">{selectedCustomer.customer_type}</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Nama</span>
                  <span className="col-span-2 font-medium">{selectedCustomer.name}</span>
                </div>
                {selectedCustomer.legal_name && (
                  <div className="grid grid-cols-3 gap-2">
                    <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Legal Name</span>
                    <span className="col-span-2">{selectedCustomer.legal_name}</span>
                  </div>
                )}
                <div className="grid grid-cols-3 gap-2">
                  <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Telepon</span>
                  <span className="col-span-2">{selectedCustomer.phone || '-'}</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Email</span>
                  <span className="col-span-2">{selectedCustomer.email || '-'}</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Alamat</span>
                  <span className="col-span-2">
                    {[selectedCustomer.address, selectedCustomer.city, selectedCustomer.province, selectedCustomer.postal_code, selectedCustomer.country]
                      .filter(Boolean)
                      .join(', ') || '-'}
                  </span>
                </div>
                {selectedCustomer.notes && (
                  <div className="grid grid-cols-3 gap-2">
                    <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Catatan</span>
                    <span className="col-span-2">{selectedCustomer.notes}</span>
                  </div>
                )}
                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-700">
                  <span className={`font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Dibuat Pada</span>
                  <span className="col-span-2 text-xs">{new Date(selectedCustomer.created_at).toLocaleString()}</span>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-6 mt-4 border-t border-slate-700">
                <Button variant="outline" onClick={() => setSelectedCustomer(null)}>
                  Tutup
                </Button>
                {selectedCustomer.status !== 'ARCHIVED' && (
                  <Button
                    variant="primary"
                    onClick={() => {
                      const c = selectedCustomer;
                      setSelectedCustomer(null);
                      handleOpenEdit(c);
                    }}
                  >
                    Edit Customer
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Confirmation Modal */}
        {confirmModal.open && confirmModal.customer && confirmModal.action && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <div className={`w-full max-w-md rounded-xl shadow-xl p-6 border ${
              isDark ? 'bg-slate-800 border-slate-700 text-slate-100' : 'bg-white border-slate-200 text-slate-900'
            }`}>
              <h3 className="text-lg font-bold mb-2 capitalize">
                {confirmModal.action === 'archive' && 'Arsipkan Customer'}
                {confirmModal.action === 'activate' && 'Aktifkan Customer'}
                {confirmModal.action === 'deactivate' && 'Nonaktifkan Customer'}
              </h3>
              <p className={`text-sm mb-6 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
                Apakah Anda yakin ingin {confirmModal.action} customer{' '}
                <span className="font-semibold">{confirmModal.customer.name}</span> ({confirmModal.customer.code})?
              </p>
              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  onClick={() => setConfirmModal({ open: false, action: null, customer: null })}
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
        )}
      </div>
    </div>
  );
};
