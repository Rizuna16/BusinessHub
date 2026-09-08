import React, { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { JournalEntry } from '@/types/accounting';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';

const STATUS_COLORS: Record<string, string> = {
  POSTED: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
  VOIDED: 'bg-gray-100 text-gray-500 border border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700 line-through',
  DRAFT: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800',
};

export const AccountingJournalDetail: React.FC = () => {
  const { businessId, journalId } = useParams<{ businessId: string; journalId: string }>();

  const [journal, setJournal] = useState<JournalEntry | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isVoiding, setIsVoiding] = useState<boolean>(false);
  const [serverError, setServerError] = useState<string>('');

  const fetchDetail = useCallback(async () => {
    if (!businessId || !journalId) return;
    setIsLoading(true);
    setServerError('');
    try {
      const data = await apiClient.getJournal(businessId, journalId);
      setJournal(data);
    } catch (err: any) {
      setServerError(err.message || 'Gagal memuat detail jurnal.');
    } finally {
      setIsLoading(false);
    }
  }, [businessId, journalId]);

  useEffect(() => { fetchDetail(); }, [fetchDetail]);

  const handleVoid = async () => {
    if (!businessId || !journalId || !confirm('Anda yakin ingin membatalkan jurnal ini?')) return;
    setIsVoiding(true);
    try {
      const updated = await apiClient.voidJournal(businessId, journalId);
      setJournal(updated);
    } catch (err: any) {
      alert('Gagal membatalkan jurnal: ' + (err.message || 'Unknown error'));
    } finally {
      setIsVoiding(false);
    }
  };

  const formatCurrency = (val: number | string) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return isNaN(num) ? '0' : num.toLocaleString('id-ID');
  };

  if (isLoading) return <div className="p-6"><Loading /></div>;
  if (serverError || !journal) return <div className="p-6"><ErrorState message={serverError || 'Journal not found'} onRetry={fetchDetail} /></div>;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-3">
            Jurnal: {journal.journal_number}
            <span className={`px-2.5 py-0.5 text-xs rounded-full font-semibold ${STATUS_COLORS[journal.status] || ''}`}>
              {journal.status}
            </span>
          </h1>
          <p className="text-sm text-gray-500">
            Tanggal Jurnal: {new Date(journal.journal_date).toLocaleDateString('id-ID')}
          </p>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="danger" 
            onClick={handleVoid} 
            disabled={isVoiding || journal.status === 'VOIDED'}
          >
            {isVoiding ? 'Membatalkan...' : 'Batalkan Jurnal'}
          </Button>
          <Link to={`/businesses/${businessId}/accounting/journals`}>
            <Button variant="secondary">Kembali</Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <h3 className="font-semibold text-sm mb-3">Detail Jurnal</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-gray-500">Deskripsi:</span><span className="font-medium">{journal.description}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Referensi:</span><span className="font-mono font-medium">{journal.reference_type} {journal.reference_id || ''}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Dibuat Oleh:</span><span className="font-mono text-xs">{journal.created_by_user_id}</span></div>
          </div>
        </Card>
        <Card>
          <h3 className="font-semibold text-sm mb-3">Rincian Keuangan</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-gray-500">Total Debit:</span><span className="font-bold">Rp {formatCurrency(journal.total_debit)}</span></div>
            <div className="flex justify-between"><span className="text-gray-500">Total Kredit:</span><span className="font-bold">Rp {formatCurrency(journal.total_credit)}</span></div>
            <div className="flex justify-between border-t pt-2"><span className="text-gray-500">Selisih:</span><span className={`font-bold ${parseFloat(String(journal.total_debit)) === parseFloat(String(journal.total_credit)) ? 'text-emerald-600' : 'text-rose-600'}`}>
              Rp {formatCurrency(parseFloat(String(journal.total_debit)) - parseFloat(String(journal.total_credit)))}
            </span></div>
          </div>
        </Card>
      </div>

      <Card>
        <h3 className="font-semibold text-sm mb-3">Detail Baris Jurnal</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase font-medium">
              <tr>
                <th className="p-3">Akun</th>
                <th className="p-3">Deskripsi</th>
                <th className="p-3 text-right">Debit</th>
                <th className="p-3 text-right">Kredit</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {journal.lines.map((line) => (
                <tr key={line.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <td className="p-3 font-mono font-medium">{line.account_code} - {line.account_name}</td>
                  <td className="p-3">{line.description || '-'}</td>
                  <td className="p-3 text-right font-medium text-emerald-600">
                    {parseFloat(String(line.debit)) > 0 ? `Rp ${formatCurrency(line.debit)}` : '-'}
                  </td>
                  <td className="p-3 text-right font-medium text-rose-600">
                    {parseFloat(String(line.credit)) > 0 ? `Rp ${formatCurrency(line.credit)}` : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
