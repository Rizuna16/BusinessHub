import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { Unit, UnitCreatePayload, UnitUpdatePayload, UnitType } from '@/types/unit';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { useTheme } from '@/hooks/useTheme';

export const Units: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();
  const { isDark } = useTheme();

  const [units, setUnits] = useState<Unit[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');

  const [showForm, setShowForm] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string>('');
  const [confirmArchive, setConfirmArchive] = useState<{ open: boolean; unit: Unit | null }>(
    { open: false, unit: null }
  );

  const [form, setForm] = useState<UnitCreatePayload>({
    name: '',
    code: '',
    symbol: '',
    description: '',
    unit_type: 'OTHER',
    precision: 0,
  });

  const activeUnits = units.filter(u => u.status === 'ACTIVE');
  const archivedUnits = units.filter(u => u.status === 'ARCHIVED');

  const fetchUnits = useCallback(async () => {
    if (!businessId) return;
    try {
      setIsLoading(true);
      setServerError('');
      const data = await apiClient.listUnits(businessId);
      setUnits(data);
    } catch (err: any) {
      const msg = err?.message || 'Gagal memuat unit.';
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
    fetchUnits();
  }, [fetchUnits]);

  const resetForm = () => {
    setForm({ name: '', code: '', symbol: '', description: '', unit_type: 'OTHER', precision: 0 });
    setEditingId(null);
    setFormError('');
  };

  const handleEdit = (u: Unit | null) => {
    if (u) {
      setEditingId(u.id);
      setForm({
        name: u.name,
        code: u.code,
        symbol: u.symbol ?? '',
        description: u.description ?? '',
        unit_type: u.unit_type,
        precision: u.precision,
      });
    } else {
      resetForm();
    }
    setShowForm(true);
  };

  const handleDelete = (u: Unit) => {
    setConfirmArchive({ open: true, unit: u });
  };

  const confirmDelete = async () => {
    if (!confirmArchive.unit || !businessId) return;
    try {
      setIsSubmitting(true);
      await apiClient.archiveUnit(businessId, confirmArchive.unit.id);
      setConfirmArchive({ open: false, unit: null });
      fetchUnits();
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
      const payload: UnitCreatePayload = {
        name: form.name.trim(),
        code: form.code.trim().toUpperCase(),
        symbol: form.symbol?.trim() || null,
        description: form.description?.trim() || null,
        unit_type: form.unit_type,
        precision: form.precision,
      };

      if (editingId) {
        await apiClient.updateUnit(businessId, editingId, payload as UnitUpdatePayload);
      } else {
        await apiClient.createUnit(businessId, payload);
      }
      setShowForm(false);
      resetForm();
      fetchUnits();
    } catch (err: any) {
      setFormError(err?.message || 'Gagal menyimpan.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const UNIT_TYPE_LABELS: Record<string, string> = {
    COUNT: 'Count',
    WEIGHT: 'Weight',
    VOLUME: 'Volume',
    LENGTH: 'Length',
    TIME: 'Time',
    OTHER: 'Other',
  };

  return (
    <div className={`min-h-screen transition-colors duration-200 ${isDark ? 'bg-slate-900 text-slate-100' : 'bg-slate-50 text-slate-900'}`}>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className={`text-2xl font-bold ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>
              Unit
            </h1>
            <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
              Kelola satuan ukur untuk bisnis Anda.
            </p>
          </div>
          <Button variant="primary" size="sm" onClick={() => handleEdit(null)}>
            Tambah Unit
          </Button>
        </div>

        {isLoading && (
          <div className="flex h-48 w-full items-center justify-center">
            <Loading size="md" text="Memuat unit..." />
          </div>
        )}

        {!isLoading && serverError && (
          <ErrorState title="Error" message={serverError} onRetry={fetchUnits} />
        )}

        {!isLoading && !serverError && activeUnits.length === 0 && (
          <div className="text-center py-12">
            <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 ${
              isDark ? 'bg-slate-800 text-slate-500' : 'bg-slate-100 text-slate-400'
            }`}>
              <span className="text-3xl">📏</span>
            </div>
            <h3 className={`text-lg font-medium mb-2 ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
              Belum ada unit
            </h3>
            <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
              Tambahkan unit ukur pertama untuk mulai mengelola master data.
            </p>
          </div>
        )}

        {!isLoading && !serverError && activeUnits.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className={isDark ? 'border-slate-700' : 'border-slate-200'}>
                  <th className={`text-left py-2 px-3 border-b ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>Nama</th>
                  <th className={`text-left py-2 px-3 border-b ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>Kode</th>
                  <th className={`text-left py-2 px-3 border-b ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>Simbol</th>
                  <th className={`text-left py-2 px-3 border-b ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>Tipe</th>
                  <th className={`text-center py-2 px-3 border-b ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>Presisi</th>
                  <th className="py-2 px-3 border-b text-right">Aksi</th>
                </tr>
              </thead>
              <tbody>
                {activeUnits.map((u) => (
                  <tr key={u.id} className={isDark ? 'border-slate-700' : 'border-slate-200'}>
                    <td className={`py-2 px-3 ${isDark ? 'text-slate-100' : 'text-slate-900'}`}>{u.name}</td>
                    <td className={`py-2 px-3 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>{u.code}</td>
                    <td className={`py-2 px-3 ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>{u.symbol || '-'}</td>
                    <td className={`py-2 px-3`}>
                      <Badge variant="info">{u.unit_type}</Badge>
                    </td>
                    <td className="py-2 px-3 text-center">{u.precision}</td>
                    <td className="py-2 px-3">
                      <div className="flex justify-end gap-1">
                        <Button variant="outline" size="sm" onClick={() => handleEdit(u)}>Edit</Button>
                        <Button variant="danger" size="sm" onClick={() => handleDelete(u)}>Arsip</Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {archivedUnits.length > 0 && (
          <div className="mt-8">
            <h2 className={`text-lg font-semibold mb-3 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
              Arsip
            </h2>
            <div className="space-y-2">
              {archivedUnits.map((u) => (
                <div
                  key={u.id}
                  className={`p-3 rounded-lg border ${
                    isDark ? 'border-slate-700 bg-slate-800/30' : 'border-slate-200 bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className={`font-medium ${isDark ? 'text-slate-200' : 'text-slate-700'}`}>{u.name}</span>
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
                {editingId ? 'Edit Unit' : 'Tambah Unit'}
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
                    aria-label="Nama unit"
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
                    aria-label="Kode unit"
                  />
                </div>

                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-slate-300' : 'text-slate-700'}`} htmlFor="symbol">
                    Simbol
                  </label>
                  <Input
                    id="symbol"
                    value={form.symbol ?? ''}
                    onChange={(e) => setForm({ ...form, symbol: e.target.value })}
                    className="w-full"
                    aria-label="Simbol unit"
                  />
                </div>

                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-slate-300' : 'text-slate-700'}`} htmlFor="unit_type">
                    Tipe Unit
                  </label>
                  <select
                    id="unit_type"
                    value={form.unit_type}
                    onChange={(e) => setForm({ ...form, unit_type: e.target.value as UnitType })}
                    className={`w-full px-3.5 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 ${isDark ? 'text-slate-100' : 'text-slate-900'}`}
                    aria-label="Tipe unit"
                  >
                    {Object.entries(UNIT_TYPE_LABELS).map(([val, label]) => (
                      <option key={val} value={val}>{label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-slate-300' : 'text-slate-700'}`} htmlFor="precision">
                    Presisi (0-6)
                  </label>
                  <Input
                    id="precision"
                    type="number"
                    min={0}
                    max={6}
                    value={form.precision}
                    onChange={(e) => setForm({ ...form, precision: parseInt(e.target.value, 10) || 0 })}
                    className="w-full"
                    aria-label="Presisi desimal"
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
                    aria-label="Deskripsi unit"
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
                Unit "{confirmArchive.unit?.name}" akan diarsipkan.
              </p>
              <div className="flex justify-end gap-3">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setConfirmArchive({ open: false, unit: null })}
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

export default Units;
