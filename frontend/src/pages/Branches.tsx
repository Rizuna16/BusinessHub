import React, { useState, useCallback, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { Business } from '@/types/business';
import type { Branch, BranchStatus, BranchCreatePayload, BranchUpdatePayload } from '@/types/branch';
import type { BusinessMembership } from '@/types/businessMembership';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAuth } from '@/context/AuthContext';

export const Branches: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [business, setBusiness] = useState<Business | null>(null);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');
  const [actionError, setActionError] = useState<string>('');

  const [showFormModal, setShowFormModal] = useState<boolean>(false);
  const [editingBranchId, setEditingBranchId] = useState<string | null>(null);
  const [form, setForm] = useState<BranchCreatePayload>({
    name: '',
    code: '',
    description: '',
    address: '',
    phone: '',
    email: '',
    timezone: 'UTC',
    locale: 'en-US',
  });
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string>('');

  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    type: 'suspend' | 'archive' | 'default';
    branch: Branch | null;
  }>({
    isOpen: false,
    type: 'suspend',
    branch: null,
  });
  const [isProcessingAction, setIsProcessingAction] = useState<boolean>(false);

  const fetchData = useCallback(async () => {
    if (!businessId) return;
    try {
      setIsLoading(true);
      setServerError('');
      setActionError('');

      const [bizData, branchesData, membersData] = await Promise.all([
        apiClient.getBusiness(businessId),
        apiClient.listBranches(businessId),
        apiClient.listBusinessMembers(businessId).catch(() => []),
      ]);

      setBusiness(bizData);
      setBranches(branchesData);

      if (user) {
        const mine = membersData.find((m) => m.user_id === user.id);
        setMyMembership(mine || null);
      }
    } catch (err: any) {
      const msg = err?.message || 'Failed to load branch data.';
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
      setFormError('Nama branch wajib diisi.');
      return false;
    }
    if (!form.code?.trim()) {
      setFormError('Kode branch wajib diisi.');
      return false;
    }
    if (!/^[A-Z0-9_-]+$/.test(form.code)) {
      setFormError('Kode branch hanya boleh huruf kapital, angka, underscore, atau strip.');
      return false;
    }
    if (form.code.length > 20) {
      setFormError('Kode branch maksimal 20 karakter.');
      return false;
    }
    if (!form.timezone?.trim()) {
      setFormError('Timezone wajib diisi.');
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
      timezone: 'UTC',
      locale: 'en-US',
    });
    setFormError('');
    setEditingBranchId(null);
  };

  const handleOpenAddModal = () => {
    resetForm();
    setShowFormModal(true);
  };

  const handleEditBranch = (branch: Branch) => {
    if (branch.status === 'ARCHIVED') {
      setActionError('Tidak dapat mengedit branch yang sudah diarsipkan.');
      return;
    }
    if (!canManage) {
      setActionError('Hanya OWNER/ADMIN yang dapat mengedit branch.');
      return;
    }
    setEditingBranchId(branch.id);
    setForm({
      name: branch.name,
      code: branch.code,
      description: branch.description ?? '',
      address: branch.address ?? '',
      phone: branch.phone ?? '',
      email: branch.email ?? '',
      timezone: branch.timezone,
      locale: branch.locale,
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
      if (editingBranchId) {
        const payload: BranchUpdatePayload = {
          name: form.name.trim(),
          code: form.code.trim().toUpperCase(),
          description: form.description?.trim() || undefined,
          address: form.address?.trim() || undefined,
          phone: form.phone?.trim() || undefined,
          email: form.email?.trim() || undefined,
          timezone: form.timezone?.trim() || 'UTC',
          locale: form.locale?.trim() || 'en-US',
        };
        await apiClient.updateBranch(businessId, editingBranchId, payload);
        setSuccessMsg('Branch berhasil diperbarui.');
      } else {
        const payload: BranchCreatePayload = {
          name: form.name.trim(),
          code: form.code.trim().toUpperCase(),
          description: form.description?.trim() || undefined,
          address: form.address?.trim() || undefined,
          phone: form.phone?.trim() || undefined,
          email: form.email?.trim() || undefined,
          timezone: form.timezone?.trim() || 'UTC',
          locale: form.locale?.trim() || 'en-US',
        };
        await apiClient.createBranch(businessId, payload);
        setSuccessMsg('Branch berhasil ditambahkan.');
      }
      setShowFormModal(false);
      resetForm();
      setTimeout(() => setSuccessMsg(''), 4000);
      fetchData();
    } catch (err: any) {
      setFormError(err?.message || 'Gagal menyimpan branch.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenConfirm = (type: 'suspend' | 'archive' | 'default', branch: Branch) => {
    if (!canManage) {
      setActionError('Hanya OWNER/ADMIN yang dapat melakukan aksi ini.');
      return;
    }
    setConfirmModal({ isOpen: true, type, branch });
    setActionError('');
  };

  const handleConfirmAction = async () => {
    const { type, branch } = confirmModal;
    if (!businessId || !branch) return;
    setIsProcessingAction(true);
    setActionError('');

    try {
      if (type === 'suspend') {
        await apiClient.suspendBranch(businessId, branch.id);
        setSuccessMsg('Branch berhasil ditangguhkan.');
      } else if (type === 'archive') {
        await apiClient.archiveBranch(businessId, branch.id);
        setSuccessMsg('Branch berhasil diarsipkan.');
      } else if (type === 'default') {
        await apiClient.setDefaultBranch(businessId, branch.id);
        setSuccessMsg('Branch berhasil dijadikan default.');
      }
      setTimeout(() => setSuccessMsg(''), 4000);
      setConfirmModal({ isOpen: false, type: 'suspend', branch: null });
      fetchData();
    } catch (err: any) {
      setActionError(err?.message || 'Action failed.');
    } finally {
      setIsProcessingAction(false);
    }
  };

  const getStatusBadgeVariant = (status: BranchStatus) => {
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

  const getStatusText = (status: BranchStatus) => {
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
        <Loading size="lg" text="Memuat branch..." />
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
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
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
              Manajemen Branch
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
                + Tambah Branch
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

        {/* Branches Table */}
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
              <thead className="border-b border-slate-200 bg-slate-100/70 text-xs font-semibold uppercase text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                <tr>
                  <th scope="col" className="px-6 py-3.5">Nama</th>
                  <th scope="col" className="px-6 py-3.5">Kode</th>
                  <th scope="col" className="px-6 py-3.5">Status</th>
                  <th scope="col" className="px-6 py-3.5">Default</th>
                  <th scope="col" className="px-6 py-3.5 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {branches.length === 0 ? (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-6 py-8 text-center text-slate-500 dark:text-slate-400"
                    >
                      <EmptyState
                        title="Belum ada branch"
                        description="Branch belum dibuat untuk bisnis ini. Buat branch pertama untuk memulai operasional."
                      />
                    </td>
                  </tr>
                ) : (
                  branches.map((branch) => (
                    <tr
                      key={branch.id}
                      className="hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div className="font-medium text-slate-900 dark:text-slate-100">
                          {branch.name}
                        </div>
                        {branch.address && (
                          <div className="mt-0.5 text-xs text-slate-500 dark:text-slate-400 max-w-[200px] truncate">
                            {branch.address}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-slate-500 dark:text-slate-400">
                        {branch.code}
                      </td>
                      <td className="px-6 py-4">
                        <Badge variant={getStatusBadgeVariant(branch.status)}>
                          {getStatusText(branch.status)}
                        </Badge>
                      </td>
                      <td className="px-6 py-4">
                        {branch.is_default ? (
                          <Badge variant="success">Default</Badge>
                        ) : (
                          <span className="text-xs text-slate-400">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {canManage && branch.status !== 'ARCHIVED' ? (
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleEditBranch(branch)}
                              aria-label={`Edit branch ${branch.name}`}
                            >
                              Edit
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleOpenConfirm('suspend', branch)}
                              aria-label={branch.status === 'SUSPENDED' ? `Aktifkan branch ${branch.name}` : `Tangguhkan branch ${branch.name}`}
                            >
                              {branch.status === 'SUSPENDED' ? 'Aktifkan' : 'Tangguhkan'}
                            </Button>
                            <Button
                              size="sm"
                              variant="danger"
                              onClick={() => handleOpenConfirm('archive', branch)}
                              aria-label={`Arsipkan branch ${branch.name}`}
                            >
                              Arsip
                            </Button>
                            {!branch.is_default && (
                              <Button
                                size="sm"
                                variant="primary"
                                onClick={() => handleOpenConfirm('default', branch)}
                                aria-label={`Jadikan branch ${branch.name} sebagai default`}
                              >
                                Default
                              </Button>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400 italic">
                            {branch.status === 'ARCHIVED' ? 'Diarsipkan' : 'Akses Ditolak'}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Modal Add/Edit Branch */}
        {showFormModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label={editingBranchId ? 'Edit Branch' : 'Tambah Branch'}>
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800 max-h-[90vh] overflow-y-auto">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">
                {editingBranchId ? 'Edit Branch' : 'Tambah Branch Baru'}
              </h2>

              {formError && (
                <div className="mb-4 rounded-lg bg-rose-50 dark:bg-rose-950/40 p-3 text-xs text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900" role="alert">
                  {formError}
                </div>
              )}

              <form onSubmit={handleFormSubmit} className="space-y-4">
                <Input
                  id="branchName"
                  label="Nama Branch"
                  placeholder="Masukkan nama branch"
                  value={form.name}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, name: e.target.value }))
                  }
                  required
                />

                <Input
                  id="branchCode"
                  label="Kode Branch"
                  placeholder="Contoh: BDG, SKB, JKT01"
                  value={form.code}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, code: e.target.value }))
                  }
                  required
                />

                <Input
                  id="branchDescription"
                  label="Deskripsi"
                  placeholder="Deskripsi opsional"
                  value={form.description ?? ''}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, description: e.target.value }))
                  }
                />

                <Input
                  id="branchAddress"
                  label="Alamat"
                  placeholder="Alamat opsional"
                  value={form.address ?? ''}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, address: e.target.value }))
                  }
                />

                <Input
                  id="branchPhone"
                  label="Telepon"
                  placeholder="+628xxxxxxxxxx"
                  value={form.phone ?? ''}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, phone: e.target.value }))
                  }
                />

                <Input
                  id="branchEmail"
                  label="Email"
                  placeholder="email@domain.com"
                  value={form.email ?? ''}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, email: e.target.value }))
                  }
                />

                <Input
                  id="branchTimezone"
                  label="Timezone"
                  placeholder="UTC"
                  value={form.timezone ?? 'UTC'}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, timezone: e.target.value }))
                  }
                  required
                />

                <Input
                  id="branchLocale"
                  label="Locale"
                  placeholder="en-US"
                  value={form.locale ?? 'en-US'}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, locale: e.target.value }))
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
                    {editingBranchId ? 'Simpan Perubahan' : 'Tambah Branch'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Confirmation Modal for Suspend / Archive / Set Default */}
        {confirmModal.isOpen && confirmModal.branch && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="Konfirmasi Aksi">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-2">
                {confirmModal.type === 'suspend'
                  ? confirmModal.branch.status === 'SUSPENDED'
                    ? 'Aktifkan Kembali Branch?'
                    : 'Tangguhkan Branch?'
                  : confirmModal.type === 'archive'
                  ? 'Arsipkan Branch?'
                  : 'Jadikan Branch Default?'}
              </h2>

              <p className="text-sm text-slate-600 dark:text-slate-300 mb-4">
                {confirmModal.type === 'suspend'
                  ? confirmModal.branch.status === 'SUSPENDED'
                    ? `Mengembalikan akses untuk branch ${
                        confirmModal.branch.name || confirmModal.branch.code
                      }.`
                    : `Branch ${
                        confirmModal.branch.name || confirmModal.branch.code
                      } tidak akan dapat diakses selama ditangguhkan.`
                  : confirmModal.type === 'archive'
                  ? `Branch ${
                      confirmModal.branch.name || confirmModal.branch.code
                    } akan diarsipkan. Riwayat tetap tersimpan.`
                  : `Branch ${
                      confirmModal.branch.name || confirmModal.branch.code
                    } akan dijadikan branch default. Branch default sebelumnya akan dibatalkan.`}
              </p>

              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setConfirmModal({ isOpen: false, type: 'suspend', branch: null })}
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
                    ? confirmModal.branch.status === 'SUSPENDED'
                      ? 'Aktifkan'
                      : 'Tangguhkan'
                    : confirmModal.type === 'archive'
                    ? 'Arsipkan'
                    : 'Jadikan Default'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Branches;
