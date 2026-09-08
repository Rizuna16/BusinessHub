import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { JournalEntry } from '@/types/accounting';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

const STATUS_COLORS: Record<string, string> = {
  POSTED: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
  VOIDED: 'bg-gray-100 text-gray-500 border border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700 line-through',
  DRAFT: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800',
};

export const AccountingJournals: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();

  const [journals, setJournals] = useState<JournalEntry[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  const fetchData = useCallback(async () => {
    if (!businessId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const data = await apiClient.listJournals(businessId, {
        status: statusFilter || undefined,
        page_size: 100,
      });
      setJournals(data.items || []);
    } catch (err: any) {
      setServerError(err.message || 'Gagal memuat jurnal.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, statusFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '0' : num.toLocaleString('id-ID');
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Accounting Journals</h1>
        <Link to={`/businesses/${businessId}/accounting/trial-balance`}>
          <Button variant="secondary">Lihat Trial Balance</Button>
        </Link>
      </div>

      <Card>
        <div className="p-4 flex flex-col md:flex-row gap-4 justify-between items-center border-b">
          <div className="flex gap-2 w-full md:w-auto">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 border rounded-md text-sm"
            >
              <option value="">Semua Status</option>
              <option value="POSTED">POSTED</option>
              <option value="VOIDED">VOIDED</option>
              <option value="DRAFT">DRAFT</option>
            </select>
          </div>
        </div>

        {isLoading ? (
          <Loading />
        ) : serverError ? (
          <ErrorState message={serverError} onRetry={fetchData} />
        ) : journals.length === 0 ? (
          <EmptyState title="Tidak ada jurnal" description="Belum ada data jurnal akuntansi." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase font-medium">
                <tr>
                  <th className="p-3">Nomor Jurnal</th>
                  <th className="p-3">Tanggal</th>
                  <th className="p-3">Deskripsi</th>
                  <th className="p-3">Referensi</th>
                  <th className="p-3 text-right">Total Debit</th>
                  <th className="p-3 text-right">Total Kredit</th>
                  <th className="p-3 text-center">Status</th>
                  <th className="p-3 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {journals.map((j) => (
                  <tr key={j.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                    <td className="p-3 font-mono font-medium">{j.journal_number}</td>
                    <td className="p-3">{new Date(j.journal_date).toLocaleDateString('id-ID')}</td>
                    <td className="p-3">{j.description}</td>
                    <td className="p-3 font-mono text-xs">{j.reference_type || '-'}</td>
                    <td className="p-3 text-right font-medium">Rp {formatCurrency(j.total_debit)}</td>
                    <td className="p-3 text-right font-medium">Rp {formatCurrency(j.total_credit)}</td>
                    <td className="p-3 text-center">
                      <span className={`px-2 py-1 text-xs rounded-full font-semibold ${STATUS_COLORS[j.status] || ''}`}>
                        {j.status}
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      <Link to={`/businesses/${businessId}/accounting/journals/${j.id}`}>
                        <Button size="sm" variant="secondary">Detail</Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};
