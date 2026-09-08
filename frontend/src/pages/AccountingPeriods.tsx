import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { AccountingPeriod } from '@/types/accounting';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

export const AccountingPeriods: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();

  const [periods, setPeriods] = useState<AccountingPeriod[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [closingId, setClosingId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [form, setForm] = useState({
    period_name: '',
    start_date: '',
    end_date: '',
  });
  const [formError, setFormError] = useState<string>('');

  const fetchPeriods = useCallback(async () => {
    if (!businessId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const data = await apiClient.listPeriods(businessId);
      setPeriods(data.items || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal memuat periode akuntansi.';
      setServerError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [businessId]);

  useEffect(() => {
    fetchPeriods();
  }, [fetchPeriods]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId) return;
    setFormError('');

    if (!form.period_name.trim() || !form.start_date || !form.end_date) {
      setFormError('Semua field wajib diisi.');
      return;
    }

    if (form.start_date > form.end_date) {
      setFormError('Tanggal awal tidak boleh melebihi tanggal akhir.');
      return;
    }

    setIsCreating(true);
    try {
      await apiClient.createPeriod(businessId, {
        period_name: form.period_name.trim(),
        start_date: form.start_date,
        end_date: form.end_date,
      });
      setForm({ period_name: '', start_date: '', end_date: '' });
      setShowCreateModal(false);
      fetchPeriods();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal membuat periode.';
      setFormError(msg);
    } finally {
      setIsCreating(false);
    }
  };

  const handleClosePeriod = async (period: AccountingPeriod) => {
    if (!businessId) return;
    const confirmed = window.confirm(
      `Tutup periode akuntansi "${period.period_name}" (${period.start_date} s/d ${period.end_date})?\n\nSetelah ditutup, jurnal baru tidak dapat diposting pada rentang tanggal ini. Tindakan ini tidak dapat dibatalkan.`
    );
    if (!confirmed) return;

    setClosingId(period.id);
    try {
      await apiClient.closePeriod(businessId, period.id);
      fetchPeriods();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal menutup periode.';
      alert(msg);
    } finally {
      setClosingId(null);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
            <Link to={`/businesses/${businessId}`} className="hover:text-blue-500">
              Bisnis
            </Link>
            <span>/</span>
            <span>Akuntansi</span>
            <span>/</span>
            <span className="text-slate-900 dark:text-slate-100 font-medium">Periode Fiskal</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Periode Akuntansi
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Kelola periode pembukuan fiskal dan batasan tanggal posting jurnal.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link to={`/businesses/${businessId}/accounting/journals`}>
            <Button variant="outline" size="sm">
              Lihat Jurnal
            </Button>
          </Link>
          <Button size="sm" onClick={() => { setShowCreateModal(true); setFormError(''); }}>
            + Buat Periode
          </Button>
        </div>
      </div>

      {/* Error state */}
      {serverError && (
        <ErrorState message={serverError} onRetry={fetchPeriods} />
      )}

      {/* Loading state */}
      {isLoading ? (
        <Card>
          <div className="py-12 flex justify-center">
            <Loading text="Memuat periode akuntansi..." />
          </div>
        </Card>
      ) : periods.length === 0 ? (
        <EmptyState
          title="Belum ada periode akuntansi"
          description="Buat periode akuntansi untuk mengontrol rentang tanggal posting pembukuan."
          action={
            <Button onClick={() => { setShowCreateModal(true); setFormError(''); }}>
              Buat Periode Pertama
            </Button>
          }
        />
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                <tr>
                  <th className="px-4 py-3">Nama Periode</th>
                  <th className="px-4 py-3">Tanggal Awal</th>
                  <th className="px-4 py-3">Tanggal Akhir</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Ditutup Pada</th>
                  <th className="px-4 py-3 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {periods.map((period) => (
                  <tr key={period.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                    <td className="px-4 py-3.5 font-semibold text-slate-900 dark:text-slate-100">
                      {period.period_name}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300 font-mono text-xs">
                      {period.start_date}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300 font-mono text-xs">
                      {period.end_date}
                    </td>
                    <td className="px-4 py-3.5">
                      <Badge
                        variant={period.status === 'OPEN' ? 'success' : 'neutral'}
                        size="sm"
                      >
                        {period.status === 'OPEN' ? 'OPEN' : 'CLOSED'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-500 dark:text-slate-400">
                      {period.closed_at
                        ? new Date(period.closed_at).toLocaleString('id-ID')
                        : '-'}
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      {period.status === 'OPEN' ? (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleClosePeriod(period)}
                          isLoading={closingId === period.id}
                          disabled={closingId === period.id}
                          className="text-xs text-rose-600 border-rose-300 hover:bg-rose-50 dark:border-rose-800 dark:text-rose-400 dark:hover:bg-rose-950/40"
                        >
                          Tutup Periode
                        </Button>
                      ) : (
                        <span className="text-xs text-slate-400 italic">Terkunci</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                Buat Periode Akuntansi
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="p-3 text-xs bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-600 dark:text-rose-400 rounded-lg">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4">
              <Input
                label="Nama Periode"
                placeholder="cth: 2026-01"
                value={form.period_name}
                onChange={(e) => setForm((prev) => ({ ...prev, period_name: e.target.value }))}
                required
              />

              <div className="grid grid-cols-2 gap-3">
                <Input
                  type="date"
                  label="Tanggal Awal"
                  value={form.start_date}
                  onChange={(e) => setForm((prev) => ({ ...prev, start_date: e.target.value }))}
                  required
                />
                <Input
                  type="date"
                  label="Tanggal Akhir"
                  value={form.end_date}
                  onChange={(e) => setForm((prev) => ({ ...prev, end_date: e.target.value }))}
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowCreateModal(false)}
                  disabled={isCreating}
                >
                  Batal
                </Button>
                <Button type="submit" size="sm" isLoading={isCreating} disabled={isCreating}>
                  Simpan Periode
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AccountingPeriods;
