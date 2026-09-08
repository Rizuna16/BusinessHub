import React, { useState, useCallback, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { Business } from '@/types/business';
import type { Branch } from '@/types/branch';
import type { Warehouse, WarehouseStatus, WarehouseCreatePayload, WarehouseUpdatePayload } from '@/types/warehouse';
import type { BusinessMembership } from '@/types/businessMembership';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';

export const Warehouses: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [business, setBusiness] = useState<Business | null>(null);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');
  const [actionError, setActionError] = useState<string>('');

  const [showFormModal, setShowFormModal] = useState<boolean>(false);
  const [editingWarehouseId, setEditingWarehouseId] = useState<string | null>(null);
  const [form, setForm] = useState<WarehouseCreatePayload>({
    name: '',
    code: '',
    description: '',
    address: '',
    phone: '',
    email: '',
    branch_id: '',
  });
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string>('');

  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    type: 'suspend' | 'activate' | 'archive';
    warehouse: Warehouse | null;
  }>({
    isOpen: false,
    type: 'suspend',
    warehouse: null,
  });
  const [isProcessingAction, setIsProcessingAction] = useState<boolean>(false);

  const fetchData = useCallback(async () => {
    if (!businessId) return;
    try {
      setIsLoading(true);
      setServerError('');
      setActionError('');

      const [bizData, whData, branchData, membersData] = await Promise.all([
        apiClient.getBusiness(businessId),
        apiClient.listWarehouses(businessId),
        apiClient.listBranches(businessId).catch(() => []),
        apiClient.listBusinessMembers(businessId).catch(() => []),
      ]);

      setBusiness(bizData);
      setWarehouses(whData);
      setBranches(branchData);

      if (user) {
        const mine = membersData.find((m) => m.user_id === user.id);
        setMyMembership(mine || null);
      }
    } catch (err: any) {
      const msg = err?.message || 'Failed to load warehouse data.';
      if (msg.toLowerCase().includes('unauthorized') || err?.message?.includes('401')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [businessId, user, navigate]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const canManage = myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN';

  const validateForm = (): boolean => {
    if (!form.name?.trim()) {
      setFormError('Nama warehouse wajib diisi.');
      return false;
    }
    if (!form.code?.trim()) {
      setFormError('Kode warehouse wajib diisi.');
      return false;
    }
    if (!/^[A-Z0-9_-]+$/.test(form.code.trim().toUpperCase())) {
      setFormError('Kode warehouse hanya boleh huruf kapital, angka, underscore, atau strip.');
      return false;
    }
    return true;
  };

  const resetForm = () => {
    setForm({
      name: '',
      code: '',
      description: '',
      address: '',
      phone: '',
      email: '',
      branch_id: '',
    });
    setFormError('');
    setEditingWarehouseId(null);
  };

  const handleOpenAddModal = () => {
    resetForm();
    setShowFormModal(true);
  };

  const handleEditWarehouse = (wh: Warehouse) => {
    if (wh.status === 'ARCHIVED') {
      setActionError('Tidak dapat mengedit warehouse yang sudah diarsipkan.');
      return;
    }
    if (!canManage) {
      setActionError('Hanya OWNER/ADMIN yang dapat mengedit warehouse.');
      return;
    }
    setEditingWarehouseId(wh.id);
    setForm({
      name: wh.name,
      code: wh.code,
      description: wh.description ?? '',
      address: wh.address ?? '',
      phone: wh.phone ?? '',
      email: wh.email ?? '',
      branch_id: wh.branch_id ?? '',
    });
    setFormError('');
    setActionError('');
    setShowFormModal(true);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    if (!validateForm()) return;
    setIsSubmitting(true);
    setFormError('');
    setActionError('');

    try {
      if (editingWarehouseId) {
        const payload: WarehouseUpdatePayload = {
          name: form.name.trim(),
          description: form.description?.trim() || null,
          address: form.address?.trim() || null,
          phone: form.phone?.trim() || null,
          email: form.email?.trim() || null,
          branch_id: form.branch_id ? form.branch_id : null,
        };
        await apiClient.updateWarehouse(businessId, editingWarehouseId, payload);
        setSuccessMsg('Warehouse berhasil diperbarui.');
      } else {
        const payload: WarehouseCreatePayload = {
          name: form.name.trim(),
          code: form.code.trim().toUpperCase(),
          description: form.description?.trim() || undefined,
          address: form.address?.trim() || undefined,
          phone: form.phone?.trim() || undefined,
          email: form.email?.trim() || undefined,
          branch_id: form.branch_id ? form.branch_id : undefined,
        };
        await apiClient.createWarehouse(businessId, payload);
        setSuccessMsg('Warehouse berhasil ditambahkan.');
      }
      setShowFormModal(false);
      resetForm();
      setTimeout(() => setSuccessMsg(''), 4000);
      fetchData();
    } catch (err: any) {
      setFormError(err?.message || 'Gagal menyimpan warehouse.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenConfirm = (type: 'suspend' | 'activate' | 'archive', warehouse: Warehouse) => {
    if (!canManage) {
      setActionError('Hanya OWNER/ADMIN yang dapat melakukan aksi ini.');
      return;
    }
    setConfirmModal({ isOpen: true, type, warehouse });
    setActionError('');
  };

  const handleConfirmAction = async () => {
    const { type, warehouse } = confirmModal;
    if (!businessId || !warehouse) return;
    setIsProcessingAction(true);
    setActionError('');

    try {
      if (type === 'suspend') {
        await apiClient.suspendWarehouse(businessId, warehouse.id);
        setSuccessMsg('Warehouse berhasil ditangguhkan.');
      } else if (type === 'activate') {
        await apiClient.activateWarehouse(businessId, warehouse.id);
        setSuccessMsg('Warehouse berhasil diaktifkan.');
      } else if (type === 'archive') {
        await apiClient.archiveWarehouse(businessId, warehouse.id);
        setSuccessMsg('Warehouse berhasil diarsipkan.');
      }
      setTimeout(() => setSuccessMsg(''), 4000);
      setConfirmModal({ isOpen: false, type: 'suspend', warehouse: null });
      fetchData();
    } catch (err: any) {
      setActionError(err?.message || 'Aksi gagal.');
    } finally {
      setIsProcessingAction(false);
    }
  };

  const getStatusBadgeVariant = (status: WarehouseStatus) => {
    switch (status) {
      case 'ACTIVE':
        return 'success';
      case 'SUSPENDED':
        return 'warning';
      case 'ARCHIVED':
        return 'error';
      default:
        return 'neutral';
    }
  };

  const getStatusText = (status: WarehouseStatus) => {
    switch (status) {
      case 'ACTIVE':
        return 'Aktif';
      case 'SUSPENDED':
        return 'Ditangguhkan';
      case 'ARCHIVED':
        return 'Diarsipkan';
      default:
        return status;
    }
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-950">
        <Loading size="lg" text="Memuat warehouse..." />
      </div>
    );
  }

  if (serverError && !business) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-950">
        <ErrorState message={serverError} onRetry={fetchData} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 mb-1">
              <Link
                to={`/businesses/${businessId}`}
                className="hover:text-slate-700 dark:hover:text-slate-200"
              >
                &larr; {business?.name || 'Bisnis'}
              </Link>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              Warehouse & Lokasi Penyimpanan
            </h1>
            {business && (
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {business.name}
              </p>
            )}
          </div>

          {canManage && (
            <div>
              <Button onClick={handleOpenAddModal} size="sm">
                + Tambah Warehouse
              </Button>
            </div>
          )}
        </div>

        {/* Notifications */}
        {successMsg && (
          <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/30 dark:text-emerald-200" role="status">
            <span className="flex items-center gap-2">
              <svg className="h-4 w-4 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 001.414 0z" clipRule="evenodd" />
              </svg>
              {successMsg}
            </span>
          </div>
        )}

        {actionError && (
          <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-200" role="alert">
            <span className="flex items-center gap-2">
              <svg className="h-4 w-4 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              {actionError}
            </span>
          </div>
        )}

        {/* Warehouses Table */}
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
              <thead className="border-b border-slate-200 bg-slate-100/70 text-xs font-semibold uppercase text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                <tr>
                  <th scope="col" className="px-6 py-3.5">Warehouse</th>
                  <th scope="col" className="px-6 py-3.5">Kode</th>
                  <th scope="col" className="px-6 py-3.5">Branch</th>
                  <th scope="col" className="px-6 py-3.5">Status</th>
                  <th scope="col" className="px-6 py-3.5">Default</th>
                  <th scope="col" className="px-6 py-3.5 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {warehouses.length === 0 ? (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-6 py-8 text-center text-slate-500 dark:text-slate-400"
                    >
                      <EmptyState
                        title="Belum ada warehouse"
                        description="Warehouse belum dibuat untuk bisnis ini. Buat warehouse pertama untuk mulai mengelola lokasi penyimpanan."
                      />
                    </td>
                  </tr>
                ) : (
                  warehouses.map((wh) => {
                    const linkedBranch = branches.find((b) => b.id === wh.branch_id);
                    return (
                      <tr
                        key={wh.id}
                        className="hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition-colors"
                      >
                        <td className="px-6 py-4">
                          <Link
                            to={`/businesses/${businessId}/warehouses/${wh.id}`}
                            className="font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
                          >
                            {wh.name}
                          </Link>
                          {wh.description && (
                            <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400 max-w-[220px] truncate">
                              {wh.description}
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4 font-mono text-xs text-slate-500 dark:text-slate-400">
                          {wh.code}
                        </td>
                        <td className="px-6 py-4 text-xs text-slate-500 dark:text-slate-400">
                          {linkedBranch ? linkedBranch.name : <span className="italic text-slate-400">Pusat (Tanpa Branch)</span>}
                        </td>
                        <td className="px-6 py-4">
                          <Badge variant={getStatusBadgeVariant(wh.status)}>
                            {getStatusText(wh.status)}
                          </Badge>
                        </td>
                        <td className="px-6 py-4">
                          {wh.is_default ? (
                            <Badge variant="success">Default</Badge>
                          ) : (
                            <span className="text-xs text-slate-400">-</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Link to={`/businesses/${businessId}/warehouses/${wh.id}`}>
                              <Button size="sm" variant="outline">
                                Detail
                              </Button>
                            </Link>
                            {canManage && wh.status !== 'ARCHIVED' && (
                              <>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleEditWarehouse(wh)}
                                  aria-label={`Edit warehouse ${wh.name}`}
                                >
                                  Edit
                                </Button>
                                {wh.status === 'SUSPENDED' ? (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleOpenConfirm('activate', wh)}
                                    aria-label={`Aktifkan warehouse ${wh.name}`}
                                  >
                                    Aktifkan
                                  </Button>
                                ) : (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleOpenConfirm('suspend', wh)}
                                    aria-label={`Tangguhkan warehouse ${wh.name}`}
                                  >
                                    Tangguhkan
                                  </Button>
                                )}
                                <Button
                                  size="sm"
                                  variant="danger"
                                  onClick={() => handleOpenConfirm('archive', wh)}
                                  aria-label={`Arsipkan warehouse ${wh.name}`}
                                >
                                  Arsip
                                </Button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Modal Add/Edit Warehouse */}
        {showFormModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label={editingWarehouseId ? 'Edit Warehouse' : 'Tambah Warehouse'}>
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800 max-h-[90vh] overflow-y-auto">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">
                {editingWarehouseId ? 'Edit Warehouse' : 'Tambah Warehouse Baru'}
              </h2>

              {formError && (
                <div className="mb-4 rounded-lg bg-rose-50 dark:bg-rose-950/40 p-3 text-xs text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900" role="alert">
                  {formError}
                </div>
              )}

              <form onSubmit={handleFormSubmit} className="space-y-4">
                <Input
                  id="whName"
                  label="Nama Warehouse"
                  placeholder="Contoh: Gudang Utama Jakarta"
                  value={form.name}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, name: e.target.value }))
                  }
                  required
                />

                <Input
                  id="whCode"
                  label="Kode Warehouse"
                  placeholder="Contoh: WH-MAIN, WH-JKT"
                  value={form.code}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, code: e.target.value }))
                  }
                  disabled={Boolean(editingWarehouseId)}
                  required
                />
                {editingWarehouseId && (
                  <p className="text-xs text-slate-500 -mt-2">Kode warehouse tidak dapat diubah.</p>
                )}

                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Branch Terikat (Opsional)
                  </label>
                  <select
                    className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    value={form.branch_id ?? ''}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, branch_id: e.target.value }))
                    }
                  >
                    <option value="">-- Tanpa Branch (Pusat / Independen) --</option>
                    {branches
                      .filter((b) => b.status === 'ACTIVE')
                      .map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.name} ({b.code})
                        </option>
                      ))}
                  </select>
                </div>

                <Input
                  id="whDescription"
                  label="Deskripsi"
                  placeholder="Deskripsi opsional"
                  value={form.description ?? ''}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, description: e.target.value }))
                  }
                />

                <Input
                  id="whAddress"
                  label="Alamat"
                  placeholder="Alamat warehouse"
                  value={form.address ?? ''}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, address: e.target.value }))
                  }
                />

                <Input
                  id="whPhone"
                  label="Telepon"
                  placeholder="+628xxxxxxxxxx"
                  value={form.phone ?? ''}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, phone: e.target.value }))
                  }
                />

                <Input
                  id="whEmail"
                  label="Email"
                  placeholder="warehouse@domain.com"
                  value={form.email ?? ''}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, email: e.target.value }))
                  }
                />

                <div className="mt-6 flex justify-end gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setShowFormModal(false);
                      resetForm();
                    }}
                    disabled={isSubmitting}
                  >
                    Batal
                  </Button>
                  <Button type="submit" size="sm" isLoading={isSubmitting}>
                    {editingWarehouseId ? 'Simpan Perubahan' : 'Tambah Warehouse'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Confirmation Modal */}
        {confirmModal.isOpen && confirmModal.warehouse && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="Konfirmasi Aksi">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-2">
                {confirmModal.type === 'suspend'
                  ? 'Tangguhkan Warehouse?'
                  : confirmModal.type === 'activate'
                  ? 'Aktifkan Warehouse?'
                  : 'Arsipkan Warehouse?'}
              </h2>

              <p className="text-sm text-slate-600 dark:text-slate-300 mb-4">
                {confirmModal.type === 'suspend'
                  ? `Warehouse ${confirmModal.warehouse.name} akan ditangguhkan.`
                  : confirmModal.type === 'activate'
                  ? `Warehouse ${confirmModal.warehouse.name} akan diaktifkan kembali.`
                  : `Warehouse ${confirmModal.warehouse.name} akan diarsipkan. Lokasi di dalamnya tetap tersimpan.`}
              </p>

              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setConfirmModal({ isOpen: false, type: 'suspend', warehouse: null })}
                  disabled={isProcessingAction}
                >
                  Batal
                </Button>
                <Button
                  variant={confirmModal.type === 'archive' ? 'danger' : 'primary'}
                  size="sm"
                  onClick={handleConfirmAction}
                  isLoading={isProcessingAction}
                >
                  {confirmModal.type === 'suspend'
                    ? 'Tangguhkan'
                    : confirmModal.type === 'activate'
                    ? 'Aktifkan'
                    : 'Arsipkan'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Warehouses;
