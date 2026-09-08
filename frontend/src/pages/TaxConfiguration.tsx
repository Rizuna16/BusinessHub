import React, { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

interface TaxConfig {
  tax_enabled: boolean;
  pricing_mode: string;
  default_tax_treatment: string;
}

export const TaxConfiguration: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();

  const [config, setConfig] = useState<TaxConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchConfig = useCallback(async () => {
    if (!businessId) return;
    setIsLoading(true);
    setError('');
    try {
      const response = await fetch(`/api/v1/businesses/${businessId}/accounting/tax-config`, {
        credentials: 'include',
      });
      if (!response.ok) throw new Error('Gagal memuat pengaturan pajak');
      const data = await response.json();
      setConfig(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal memuat pengaturan pajak.';
      if (msg.includes('401')) {
        navigate('/login');
      } else {
        setError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [businessId, navigate]);

  useEffect(() => { fetchConfig(); }, [fetchConfig]);

  const handleSave = async () => {
    if (!businessId || !config) return;
    setIsSaving(true);
    setError('');
    setSuccess('');
    try {
      const response = await fetch(`/api/v1/businesses/${businessId}/accounting/tax-config`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          tax_enabled: config.tax_enabled,
          pricing_mode: config.pricing_mode,
          default_tax_treatment: config.default_tax_treatment,
        }),
      });
      if (!response.ok) throw new Error('Gagal menyimpan pengaturan.');
      setSuccess('Pengaturan pajak berhasil disimpan.');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal menyimpan pengaturan.';
      setError(msg);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <div className="flex items-center justify-center py-20">
          <div className="text-slate-500">Memuat...</div>
        </div>
      </div>
    );
  }

  if (error && !config) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600 text-sm">{error}</p>
          <button onClick={fetchConfig} className="mt-2 text-sm text-red-600 underline">Coba Lagi</button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">
            <span onClick={() => navigate(-1)} className="hover:underline cursor-pointer">Kembali</span> / Pengaturan Pajak
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Pengaturan PPN</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Konfigurasi pajak pertambahan nilai untuk bisnis ini.
          </p>
        </div>
      </div>

      {/* Success/Error messages */}
      {success && (
        <div className="bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 rounded-lg p-4 text-sm text-emerald-700 dark:text-emerald-300">
          {success}
        </div>
      )}
      {error && (
        <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-lg p-4 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {config && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-6 space-y-6 shadow-sm">
          {/* PPN Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">PPN Aktif</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Aktifkan/menonaktifkan penghitungan PPN otomatis</p>
            </div>
            <button
              type="button"
              onClick={() => setConfig(prev => prev ? { ...prev, tax_enabled: !prev.tax_enabled } : prev)}
              className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${config.tax_enabled ? 'bg-blue-600' : 'bg-slate-300 dark:bg-slate-600'}`}
              aria-label={config.tax_enabled ? 'Nonaktifkan PPN' : 'Aktifkan PPN'}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition duration-200 ease-in-out ${config.tax_enabled ? 'translate-x-5' : 'translate-x-0'}`}
              />
            </button>
          </div>

          <div className="border-t border-slate-100 dark:border-slate-800 pt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Pricing Mode */}
              <div>
                <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Mode Harga</label>
                <select
                  value={config.pricing_mode}
                  onChange={(e) => setConfig(prev => prev ? { ...prev, pricing_mode: e.target.value } : prev)}
                  className="mt-1 block w-full px-3 py-2 text-sm bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="TAX_EXCLUSIVE">Harga Eksklusif Pajak (Eksklusif)</option>
                  <option value="TAX_INCLUSIVE">Harga Termasuk Pajak (Inklusif)</option>
                </select>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                  {config.pricing_mode === 'TAX_EXCLUSIVE'
                    ? 'Harga satuan belum termasuk PPN. PPN dihitung dan ditambahkan.'
                    : 'Harga satuan sudah termasuk PPN. PPN diekstraksi dari harga jual.'}
                </p>
              </div>

              {/* Default Tax Treatment */}
              <div>
                <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Treatment Pajak Default</label>
                <select
                  value={config.default_tax_treatment}
                  onChange={(e) => setConfig(prev => prev ? { ...prev, default_tax_treatment: e.target.value } : prev)}
                  className="mt-1 block w-full px-3 py-2 text-sm bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="STANDARD_NON_LUXURY">Standar Non-Mewah (PPN 12%)</option>
                  <option value="NON_TAXABLE">Tidak Kena Pajak</option>
                </select>
                <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                  Treatment pajak default untuk transaksi baru.
                </p>
              </div>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end pt-4 border-t border-slate-100 dark:border-slate-800">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50"
            >
              {isSaving ? 'Menyimpan...' : 'Simpan Pengaturan'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
