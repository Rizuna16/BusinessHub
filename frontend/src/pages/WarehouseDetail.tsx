import React, { useState, useCallback, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { Branch } from '@/types/branch';
import type {
  Warehouse,
  InventoryLocation,
  InventoryLocationType,
  InventoryLocationCreatePayload,
  InventoryLocationUpdatePayload,
} from '@/types/warehouse';
import type { BusinessMembership } from '@/types/businessMembership';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';

export const WarehouseDetail: React.FC = () => {
  const { businessId, warehouseId } = useParams<{ businessId: string; warehouseId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [warehouse, setWarehouse] = useState<Warehouse | null>(null);
  const [branch, setBranch] = useState<Branch | null>(null);
  const [locations, setLocations] = useState<InventoryLocation[]>([]);
  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');
  const [actionError, setActionError] = useState<string>('');

  const [showFormModal, setShowFormModal] = useState<boolean>(false);
  const [editingLocationId, setEditingLocationId] = useState<string | null>(null);
  const [form, setForm] = useState<InventoryLocationCreatePayload>({
    name: '',
    code: '',
    description: '',
    location_type: 'GENERAL',
  });
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string>('');

  const [confirmArchiveModal, setConfirmArchiveModal] = useState<{
    isOpen: boolean;
    location: InventoryLocation | null;
  }>({
    isOpen: false,
    location: null,
  });
  const [isProcessingAction, setIsProcessingAction] = useState<boolean>(false);

  const fetchData = useCallback(async () => {
    if (!businessId || !warehouseId) return;
    try {
      setIsLoading(true);
      setServerError('');
      setActionError('');

      const [whData, locData, membersData] = await Promise.all([
        apiClient.getWarehouse(businessId, warehouseId),
        apiClient.listWareLocations(businessId, warehouseId),
        apiClient.listBusinessMembers(businessId).catch(() => []),
      ]);

      setWarehouse(whData);
      setLocations(locData);

      if (whData.branch_id) {
        const bData = await apiClient.getBranch(businessId, whData.branch_id).catch(() => null);
        setBranch(bData);
      } else {
        setBranch(null);
      }

      if (user) {
        const mine = membersData.find((m: any) => m.user_id === user.id);
        setMyMembership(mine || null);
      }
    } catch (err: any) {
      const msg = err?.message || 'Failed to load warehouse detail.';
      if (msg.toLowerCase().includes('unauthorized') || err?.message?.includes('401')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [businessId, warehouseId, user, navigate]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const canManage = myMembership?.role === 'OWNER' || myMembership?.role === 'ADMIN';

  const validateForm = (): boolean => {
    if (!form.name?.trim()) {
      setFormError('Nama lokasi wajib diisi.');
      return false;
    }
    if (!form.code?.trim()) {
      setFormError('Kode lokasi wajib diisi.');
      return false;
    }
    if (!/^[A-Z0-9_-]+$/.test(form.code.trim().toUpperCase())) {
      setFormError('Kode lokasi hanya boleh huruf kapital, angka, underscore, atau strip.');
      return false;
    }
    return true;
  };

  const resetForm = () => {
    setForm({
      name: '',
      code: '',
      description: '',
      location_type: 'GENERAL',
    });
    setFormError('');
    setEditingLocationId(null);
  };

  const handleOpenAddModal = () => {
    if (warehouse?.status === 'ARCHIVED') {
      setActionError('Tidak dapat membuat lokasi di bawah warehouse yang diarsipkan.');
      return;
    }
    resetForm();
    setShowFormModal(true);
  };

  const handleEditLocation = (loc: InventoryLocation) => {
    if (warehouse?.status === 'ARCHIVED' || loc.status === 'ARCHIVED') {
      setActionError('Tidak dapat mengedit lokasi ini.');
      return;
    }
    if (!canManage) {
      setActionError('Hanya OWNER/ADMIN yang dapat mengedit lokasi.');
      return;
    }
    setEditingLocationId(loc.id);
    setForm({
      name: loc.name,
      code: loc.code,
      description: loc.description ?? '',
      location_type: loc.location_type,
    });
    setFormError('');
    setActionError('');
    setShowFormModal(true);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !warehouseId) return;
    if (!validateForm()) return;
    setIsSubmitting(true);
    setFormError('');
    setActionError('');

    try {
      if (editingLocationId) {
        const payload: InventoryLocationUpdatePayload = {
          name: form.name.trim(),
          description: form.description?.trim() || null,
          location_type: form.location_type,
        };
        await apiClient.updateLocation(businessId, warehouseId, editingLocationId, payload);
        setSuccessMsg('Lokasi berhasil diperbarui.');
      } else {
        const payload: InventoryLocationCreatePayload = {
          name: form.name.trim(),
          code: form.code.trim().toUpperCase(),
          description: form.description?.trim() || undefined,
          location_type: form.location_type,
        };
        await apiClient.createLocation(businessId, warehouseId, payload);
        setSuccessMsg('Lokasi berhasil ditambahkan.');
      }
      setShowFormModal(false);
      resetForm();
      setTimeout(() => setSuccessMsg(''), 4000);
      fetchData();
    } catch (err: any) {
      setFormError(err?.message || 'Gagal menyimpan lokasi.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenArchiveConfirm = (location: InventoryLocation) => {
    if (!canManage) {
      setActionError('Hanya OWNER/ADMIN yang dapat mengarsipkan lokasi.');
      return;
    }
    setConfirmArchiveModal({ isOpen: true, location });
    setActionError('');
  };

  const handleConfirmArchive = async () => {
    const { location } = confirmArchiveModal;
    if (!businessId || !warehouseId || !location) return;
    setIsProcessingAction(true);
    setActionError('');

    try {
      await apiClient.archiveLocation(businessId, warehouseId, location.id);
      setSuccessMsg('Lokasi berhasil diarsipkan.');
      setTimeout(() => setSuccessMsg(''), 4000);
      setConfirmArchiveModal({ isOpen: false, location: null });
      fetchData();
    } catch (err: any) {
      setActionError(err?.message || 'Gagal mengarsipkan lokasi.');
    } finally {
      setIsProcessingAction(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-950">
        <Loading size="lg" text="Memuat detail warehouse..." />
      </div>
    );
  }

  if (serverError || !warehouse) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-950">
        <ErrorState message={serverError || 'Warehouse tidak ditemukan.'} onRetry={fetchData} />
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
                to={`/businesses/${businessId}/warehouses`}
                className="hover:text-slate-700 dark:hover:text-slate-200"
              >
                &larr; Kembali ke Warehouse
              </Link>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-3">
              {warehouse.name}
              <Badge variant={warehouse.status === 'ACTIVE' ? 'success' : warehouse.status === 'SUSPENDED' ? 'warning' : 'error'}>
                {warehouse.status}
              </Badge>
              {warehouse.is_default && <Badge variant="success">Default</Badge>}
            </h1>
            <p className="text-sm font-mono text-slate-500 dark:text-slate-400 mt-0.5">
              Kode: {warehouse.code} {branch ? `• Branch: ${branch.name} (${branch.code})` : '• Gudang Pusat'}
            </p>
          </div>

          {canManage && warehouse.status !== 'ARCHIVED' && (
            <div>
              <Button onClick={handleOpenAddModal} size="sm">
                + Tambah Lokasi
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

        {/* Warehouse Info Card */}
        <Card className="mb-6">
          <div className="grid gap-4 sm:grid-cols-3 text-sm">
            <div>
              <span className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase">Alamat</span>
              <span className="text-slate-900 dark:text-slate-100">{warehouse.address || '-'}</span>
            </div>
            <div>
              <span className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase">Kontak</span>
              <span className="text-slate-900 dark:text-slate-100">{warehouse.phone || warehouse.email || '-'}</span>
            </div>
            <div>
              <span className="block text-xs font-medium text-slate-500 dark:text-slate-400 uppercase">Deskripsi</span>
              <span className="text-slate-900 dark:text-slate-100">{warehouse.description || '-'}</span>
            </div>
          </div>
        </Card>

        {/* Inventory Locations Section */}
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Lokasi Penyimpanan (Inventory Locations)
          </h2>
          <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
            Total Aktif: {locations.length}
          </span>
        </div>

        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
              <thead className="border-b border-slate-200 bg-slate-100/70 text-xs font-semibold uppercase text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                <tr>
                  <th scope="col" className="px-6 py-3.5">Nama Lokasi</th>
                  <th scope="col" className="px-6 py-3.5">Kode</th>
                  <th scope="col" className="px-6 py-3.5">Tipe (Classification)</th>
                  <th scope="col" className="px-6 py-3.5">Default</th>
                  <th scope="col" className="px-6 py-3.5 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {locations.length === 0 ? (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-6 py-8 text-center text-slate-500 dark:text-slate-400"
                    >
                      <EmptyState
                        title="Belum ada lokasi penyimpanan"
                        description="Buat lokasi (misal: RACK-A, RECEIVING, STORAGE) di dalam warehouse ini."
                      />
                    </td>
                  </tr>
                ) : (
                  locations.map((loc) => (
                    <tr
                      key={loc.id}
                      className="hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div className="font-medium text-slate-900 dark:text-slate-100">
                          {loc.name}
                        </div>
                        {loc.description && (
                          <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400 max-w-[200px] truncate">
                            {loc.description}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-slate-500 dark:text-slate-400">
                        {loc.code}
                      </td>
                      <td className="px-6 py-4">
                        <Badge variant="neutral">{loc.location_type}</Badge>
                      </td>
                      <td className="px-6 py-4">
                        {loc.is_default ? (
                          <Badge variant="success">Default</Badge>
                        ) : (
                          <span className="text-xs text-slate-400">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {canManage && warehouse.status !== 'ARCHIVED' ? (
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleEditLocation(loc)}
                              aria-label={`Edit lokasi ${loc.name}`}
                            >
                              Edit
                            </Button>
                            <Button
                              size="sm"
                              variant="danger"
                              onClick={() => handleOpenArchiveConfirm(loc)}
                              aria-label={`Arsipkan lokasi ${loc.name}`}
                            >
                              Arsip
                            </Button>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400 italic">Terkunci</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Modal Add/Edit Location */}
        {showFormModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label={editingLocationId ? 'Edit Lokasi' : 'Tambah Lokasi'}>
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">
                {editingLocationId ? 'Edit Lokasi Penyimpanan' : 'Tambah Lokasi Penyimpanan'}
              </h2>

              {formError && (
                <div className="mb-4 rounded-lg bg-rose-50 dark:bg-rose-950/40 p-3 text-xs text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900" role="alert">
                  {formError}
                </div>
              )}

              <form onSubmit={handleFormSubmit} className="space-y-4">
                <Input
                  id="locName"
                  label="Nama Lokasi"
                  placeholder="Contoh: Rak Besi A1"
                  value={form.name}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, name: e.target.value }))
                  }
                  required
                />

                <Input
                  id="locCode"
                  label="Kode Lokasi"
                  placeholder="Contoh: RACK-A1, RECEIVING"
                  value={form.code}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, code: e.target.value }))
                  }
                  disabled={Boolean(editingLocationId)}
                  required
                />
                {editingLocationId && (
                  <p className="text-xs text-slate-500 -mt-2">Kode lokasi tidak dapat diubah.</p>
                )}

                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Tipe Lokasi (Classification)
                  </label>
                  <select
                    className="w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    value={form.location_type}
                    onChange={(e) =>
                      setForm((prev) => ({ ...prev, location_type: e.target.value as InventoryLocationType }))
                    }
                  >
                    <option value="GENERAL">GENERAL</option>
                    <option value="RECEIVING">RECEIVING</option>
                    <option value="STORAGE">STORAGE</option>
                    <option value="PICKING">PICKING</option>
                    <option value="SHIPPING">SHIPPING</option>
                    <option value="DAMAGED">DAMAGED</option>
                    <option value="QUARANTINE">QUARANTINE</option>
                    <option value="OTHER">OTHER</option>
                  </select>
                </div>

                <Input
                  id="locDescription"
                  label="Deskripsi"
                  placeholder="Deskripsi opsional"
                  value={form.description ?? ''}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, description: e.target.value }))
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
                    {editingLocationId ? 'Simpan Perubahan' : 'Tambah Lokasi'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Confirmation Archive Location Modal */}
        {confirmArchiveModal.isOpen && confirmArchiveModal.location && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="Konfirmasi Arsip Lokasi">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-2">
                Arsipkan Lokasi Penyimpanan?
              </h2>

              <p className="text-sm text-slate-600 dark:text-slate-300 mb-4">
                Lokasi {confirmArchiveModal.location.name} ({confirmArchiveModal.location.code}) akan diarsipkan.
              </p>

              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setConfirmArchiveModal({ isOpen: false, location: null })}
                  disabled={isProcessingAction}
                >
                  Batal
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={handleConfirmArchive}
                  isLoading={isProcessingAction}
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

export default WarehouseDetail;
