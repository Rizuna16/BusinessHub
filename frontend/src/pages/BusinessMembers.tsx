import React, { useState, useCallback, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { Business } from '@/types/business';
import type {
  BusinessMembership,
  BusinessMembershipRole,
  BusinessMembershipStatus,
  AddBusinessMemberInput,
} from '@/types/businessMembership';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { useAuth } from '@/context/AuthContext';

export const BusinessMembers: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [business, setBusiness] = useState<Business | null>(null);
  const [members, setMembers] = useState<BusinessMembership[]>([]);
  const [myMembership, setMyMembership] = useState<BusinessMembership | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [actionError, setActionError] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');

  // Add Member Modal State
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [addUserId, setAddUserId] = useState<string>('');
  const [addRole, setAddRole] = useState<BusinessMembershipRole>('MEMBER');
  const [isAdding, setIsAdding] = useState<boolean>(false);
  const [addError, setAddError] = useState<string>('');

  // Confirmation Modal State
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    type: 'suspend' | 'remove';
    member: BusinessMembership | null;
  }>({
    isOpen: false,
    type: 'suspend',
    member: null,
  });
  const [isProcessingAction, setIsProcessingAction] = useState<boolean>(false);

  // Role Edit State per member
  const [editingMemberId, setEditingMemberId] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState<BusinessMembershipRole>('MEMBER');
  const [isUpdatingRole, setIsUpdatingRole] = useState<boolean>(false);

  const fetchData = useCallback(async () => {
    if (!businessId) return;
    try {
      setIsLoading(true);
      setServerError('');
      setActionError('');

      const [bizData, membersData] = await Promise.all([
        apiClient.getBusiness(businessId),
        apiClient.listBusinessMembers(businessId),
      ]);

      setBusiness(bizData);
      setMembers(membersData);

      if (user) {
        const mine = membersData.find((m) => m.user_id === user.id);
        setMyMembership(mine || null);
      }
    } catch (err: any) {
      const msg = err?.message || 'Failed to load membership data.';
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

  const handleOpenAddModal = () => {
    setAddUserId('');
    setAddRole('MEMBER');
    setAddError('');
    setShowAddModal(true);
  };

  const handleAddMemberSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    if (!addUserId.trim()) {
      setAddError('Target User ID is required.');
      return;
    }
    if (addRole === 'OWNER') {
      setAddError('Cannot assign OWNER role.');
      return;
    }

    setIsAdding(true);
    setAddError('');
    setActionError('');

    try {
      const payload: AddBusinessMemberInput = {
        user_id: addUserId.trim(),
        role: addRole,
      };
      await apiClient.addBusinessMember(businessId, payload);
      setShowAddModal(false);
      setSuccessMsg('Anggota berhasil ditambahkan.');
      setTimeout(() => setSuccessMsg(''), 4000);
      fetchData();
    } catch (err: any) {
      setAddError(err?.message || 'Failed to add member.');
    } finally {
      setIsAdding(false);
    }
  };

  const handleStartEditRole = (member: BusinessMembership) => {
    if (member.role === 'OWNER') return;
    setEditingMemberId(member.id);
    setSelectedRole(member.role);
  };

  const handleSaveRole = async (membershipId: string) => {
    if (!businessId) return;
    setIsUpdatingRole(true);
    setActionError('');

    try {
      await apiClient.updateBusinessMember(businessId, membershipId, {
        role: selectedRole,
      });
      setEditingMemberId(null);
      setSuccessMsg('Peran anggota berhasil diperbarui.');
      setTimeout(() => setSuccessMsg(''), 4000);
      fetchData();
    } catch (err: any) {
      setActionError(err?.message || 'Failed to update member role.');
    } finally {
      setIsUpdatingRole(false);
    }
  };

  const handleOpenConfirm = (type: 'suspend' | 'remove', member: BusinessMembership) => {
    if (member.role === 'OWNER') return;
    setConfirmModal({ isOpen: true, type, member });
  };

  const handleConfirmAction = async () => {
    const { type, member } = confirmModal;
    if (!businessId || !member) return;
    setIsProcessingAction(true);
    setActionError('');

    try {
      if (type === 'suspend') {
        const nextStatus: BusinessMembershipStatus =
          member.status === 'SUSPENDED' ? 'ACTIVE' : 'SUSPENDED';
        await apiClient.updateBusinessMember(businessId, member.id, {
          status: nextStatus,
        });
        setSuccessMsg(
          nextStatus === 'SUSPENDED'
            ? 'Anggota berhasil ditangguhkan (SUSPENDED).'
            : 'Status anggota dikembalikan ke ACTIVE.'
        );
      } else {
        await apiClient.removeBusinessMember(businessId, member.id);
        setSuccessMsg('Anggota berhasil dihapus (REMOVED).');
      }
      setTimeout(() => setSuccessMsg(''), 4000);
      setConfirmModal({ isOpen: false, type: 'suspend', member: null });
      fetchData();
    } catch (err: any) {
      setActionError(err?.message || 'Action failed.');
    } finally {
      setIsProcessingAction(false);
    }
  };

  const getRoleBadgeVariant = (role: BusinessMembershipRole) => {
    switch (role) {
      case 'OWNER':
        return 'info';
      case 'ADMIN':
        return 'warning';
      default:
        return 'neutral';
    }
  };

  const getStatusBadgeVariant = (status: BusinessMembershipStatus) => {
    switch (status) {
      case 'ACTIVE':
        return 'success';
      case 'SUSPENDED':
        return 'warning';
      case 'REMOVED':
        return 'error';
      default:
        return 'neutral';
    }
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-950">
        <Loading size="lg" text="Memuat daftar anggota..." />
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
        {/* Navigation & Header */}
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <Link
                to={`/businesses/${businessId}`}
                className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
              >
                &larr; Detail Bisnis
              </Link>
              <span className="text-slate-300 dark:text-slate-700">/</span>
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Anggota
              </span>
            </div>
            <h1 className="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-100">
              Manajemen Anggota Bisnis
            </h1>
            {business && (
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {business.name} ({business.slug})
              </p>
            )}
          </div>

          {canManage && (
            <div>
              <Button onClick={handleOpenAddModal} size="sm">
                + Tambah Anggota
              </Button>
            </div>
          )}
        </div>

        {/* Notifications */}
        {successMsg && (
          <div className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/30 dark:text-emerald-200">
            <span className="flex items-center gap-2">
              <svg className="h-5 w-5 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 001.414 0z"
                  clipRule="evenodd"
                />
              </svg>
              {successMsg}
            </span>
          </div>
        )}

        {actionError && (
          <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-200">
            <span className="flex items-center gap-2">
              <svg className="h-5 w-5 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
              {actionError}
            </span>
          </div>
        )}

        {/* Member Table / List */}
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600 dark:text-slate-300">
              <thead className="border-b border-slate-200 bg-slate-100/70 text-xs font-semibold uppercase text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                <tr>
                  <th className="px-6 py-3.5">Nama / Email</th>
                  <th className="px-6 py-3.5">User ID</th>
                  <th className="px-6 py-3.5">Peran</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Bergabung</th>
                  {canManage && <th className="px-6 py-3.5 text-right">Aksi</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {members.length === 0 ? (
                  <tr>
                    <td
                      colSpan={canManage ? 6 : 5}
                      className="px-6 py-8 text-center text-slate-500 dark:text-slate-400"
                    >
                      Belum ada anggota.
                    </td>
                  </tr>
                ) : (
                  members.map((member) => {
                    const isSelf = member.user_id === user?.id;
                    const isOwner = member.role === 'OWNER';
                    const isEditingThis = editingMemberId === member.id;

                    return (
                      <tr
                        key={member.id}
                        className="hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition-colors"
                      >
                        <td className="px-6 py-4 font-medium text-slate-900 dark:text-slate-100">
                          <div>
                            {member.display_name || member.email || 'Pengguna'}
                            {isSelf && (
                              <span className="ml-2 text-xs font-normal text-indigo-600 dark:text-indigo-400">
                                (Anda)
                              </span>
                            )}
                          </div>
                          {member.email && (
                            <div className="text-xs text-slate-500 dark:text-slate-400 font-normal">
                              {member.email}
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4 font-mono text-xs text-slate-500 dark:text-slate-400">
                          {member.user_id}
                        </td>
                        <td className="px-6 py-4">
                          {isEditingThis ? (
                            <div className="flex items-center gap-2">
                              <select
                                value={selectedRole}
                                onChange={(e) =>
                                  setSelectedRole(e.target.value as BusinessMembershipRole)
                                }
                                className="rounded border border-slate-300 bg-white px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-900 text-slate-900 dark:text-slate-100"
                              >
                                <option value="ADMIN">ADMIN</option>
                                <option value="MEMBER">MEMBER</option>
                              </select>
                              <Button
                                size="sm"
                                onClick={() => handleSaveRole(member.id)}
                                isLoading={isUpdatingRole}
                              >
                                Simpan
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => setEditingMemberId(null)}
                              >
                                Batal
                              </Button>
                            </div>
                          ) : (
                            <Badge variant={getRoleBadgeVariant(member.role)}>
                              {member.role}
                            </Badge>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <Badge variant={getStatusBadgeVariant(member.status)}>
                            {member.status}
                          </Badge>
                        </td>
                        <td className="px-6 py-4 text-xs text-slate-500 dark:text-slate-400">
                          {new Date(member.created_at).toLocaleDateString()}
                        </td>
                        {canManage && (
                          <td className="px-6 py-4 text-right">
                            {!isOwner && member.status !== 'REMOVED' ? (
                              <div className="flex items-center justify-end gap-2">
                                {!isEditingThis && (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleStartEditRole(member)}
                                  >
                                    Peran
                                  </Button>
                                )}
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleOpenConfirm('suspend', member)}
                                >
                                  {member.status === 'SUSPENDED' ? 'Aktifkan' : 'Tangguhkan'}
                                </Button>
                                <Button
                                  size="sm"
                                  variant="danger"
                                  onClick={() => handleOpenConfirm('remove', member)}
                                >
                                  Hapus
                                </Button>
                              </div>
                            ) : (
                              <span className="text-xs text-slate-400 italic">
                                {isOwner ? 'Owner Protected' : 'Removed'}
                              </span>
                            )}
                          </td>
                        )}
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Modal Add Member */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-4">
              Tambah Anggota Bisnis
            </h2>

            {addError && (
              <div className="mb-4 rounded-lg bg-rose-50 dark:bg-rose-950/40 p-3 text-xs text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900">
                {addError}
              </div>
            )}

            <form onSubmit={handleAddMemberSubmit} className="space-y-4">
              <Input
                id="targetUserId"
                label="Target User ID"
                placeholder="Masukkan UUID pengguna"
                value={addUserId}
                onChange={(e) => setAddUserId(e.target.value)}
                required
              />

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Peran Anggota
                </label>
                <select
                  value={addRole}
                  onChange={(e) => setAddRole(e.target.value as BusinessMembershipRole)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm text-slate-900 shadow-sm transition-colors dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="ADMIN">ADMIN</option>
                  <option value="MEMBER">MEMBER</option>
                </select>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Catatan: Peran OWNER tidak dapat dipilih.
                </p>
              </div>

              <div className="mt-6 flex justify-end gap-3">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowAddModal(false)}
                  disabled={isAdding}
                >
                  Batal
                </Button>
                <Button type="submit" size="sm" isLoading={isAdding}>
                  Tambah Anggota
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Modal for Suspend / Remove */}
      {confirmModal.isOpen && confirmModal.member && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-2">
              {confirmModal.type === 'suspend'
                ? confirmModal.member.status === 'SUSPENDED'
                  ? 'Aktifkan Kembali Member?'
                  : 'Tangguhkan Member?'
                : 'Hapus Member dari Bisnis?'}
            </h2>

            <p className="text-sm text-slate-600 dark:text-slate-300 mb-4">
              {confirmModal.type === 'suspend'
                ? confirmModal.member.status === 'SUSPENDED'
                  ? `Mengembalikan akses untuk anggota ${
                      confirmModal.member.display_name || confirmModal.member.user_id
                    }.`
                  : `Anggota ${
                      confirmModal.member.display_name || confirmModal.member.user_id
                    } tidak akan dapat mengakses bisnis ini selama ditangguhkan.`
                : `Anggota ${
                    confirmModal.member.display_name || confirmModal.member.user_id
                  } akan ditandai REMOVED. Riwayat transaksi dan audit tetap tersimpan.`}
            </p>

            <div className="flex justify-end gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setConfirmModal({ isOpen: false, type: 'suspend', member: null })}
                disabled={isProcessingAction}
              >
                Batal
              </Button>
              <Button
                variant={confirmModal.type === 'remove' ? 'danger' : 'primary'}
                size="sm"
                onClick={handleConfirmAction}
                isLoading={isProcessingAction}
              >
                {confirmModal.type === 'suspend'
                  ? confirmModal.member.status === 'SUSPENDED'
                    ? 'Aktifkan'
                    : 'Tangguhkan'
                  : 'Hapus Member'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BusinessMembers;
