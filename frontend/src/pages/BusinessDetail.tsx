import React, { useState, useCallback, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/hooks/useTheme';
import { apiClient } from '@/services/apiClient';
import type { Business, UpdateBusinessInput } from '@/types/business';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';

const BUSINESS_TYPE_LABELS: Record<string, string> = {
  hotel: 'Hotel & Hospitality',
  retail: 'Retail & Toko',
  umkm: 'UMKM & Usaha Mikro',
  restaurant: 'Restoran & F&B',
  service: 'Jasa & Konsultasi',
  production: 'Produksi & Manufaktur',
  garment: 'Garment & Tekstil',
  distributor: 'Distributor & Grosir',
  workshop: 'Bengkel & Otomotif',
  salon: 'Salon & Perawatan',
};

interface SummaryCounts {
  branches: number | null;
  members: number | null;
  products: number | null;
  warehouses: number | null;
}

export const BusinessDetail: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();

  const [business, setBusiness] = useState<Business | null>(null);
  const [counts, setCounts] = useState<SummaryCounts>({
    branches: null,
    members: null,
    products: null,
    warehouses: null,
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isArchiving, setIsArchiving] = useState<boolean>(false);
  const [errors, setErrors] = useState<Record<string, string | undefined>>({});
  const [serverError, setServerError] = useState<string>('');
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  const [form, setForm] = useState<UpdateBusinessInput>({
    name: '',
    description: '',
    timezone: 'UTC',
    locale: 'en-US',
  });

  const fetchBusiness = useCallback(async () => {
    if (!businessId) return;
    try {
      setIsLoading(true);
      setServerError('');
      const data = await apiClient.getBusiness(businessId);
      setBusiness(data);
      setForm({
        name: data.name,
        description: data.description ?? '',
        timezone: data.timezone,
        locale: data.locale,
      });

      // Asynchronously fetch real counts for summary tiles in parallel without blocking main view
      Promise.allSettled([
        apiClient.listBranches(businessId),
        apiClient.listBusinessMembers(businessId),
        apiClient.listProducts(businessId, { page_size: 1 }),
        apiClient.listWarehouses(businessId),
      ]).then(([branchRes, memberRes, prodRes, whRes]) => {
        setCounts({
          branches: branchRes.status === 'fulfilled' ? branchRes.value.length : 0,
          members: memberRes.status === 'fulfilled' ? memberRes.value.length : 0,
          products: prodRes.status === 'fulfilled' ? prodRes.value.total : 0,
          warehouses: whRes.status === 'fulfilled' ? whRes.value.length : 0,
        });
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal memuat data bisnis.';
      if (msg.toLowerCase().includes('unauthorized') || msg.includes('401')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [businessId, navigate]);

  useEffect(() => {
    fetchBusiness();
  }, [fetchBusiness]);

  const handleEdit = () => {
    setIsEditing(true);
    setSaveSuccess(false);
    setErrors({});
    setServerError('');
  };

  const handleCancel = () => {
    setIsEditing(false);
    setErrors({});
    setSaveSuccess(false);
    setServerError('');
    if (business) {
      setForm({
        name: business.name,
        description: business.description ?? '',
        timezone: business.timezone,
        locale: business.locale,
      });
    }
  };

  const handleChange = (field: keyof UpdateBusinessInput) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const value = e.target.value;
    setForm((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string | undefined> = {};
    if (!form.name?.trim()) {
      newErrors.name = 'Nama bisnis wajib diisi.';
    } else if (form.name.trim().length < 2) {
      newErrors.name = 'Nama bisnis minimal 2 karakter.';
    }

    const tz = form.timezone?.trim() ?? '';
    if (tz && tz !== 'UTC' && !tz.includes('/')) {
      newErrors.timezone = 'Format timezone harus valid (cth: Asia/Jakarta atau UTC).';
    }

    const loc = form.locale?.trim() ?? '';
    if (loc && !/^[a-z]{2}-[A-Z]{2}$/.test(loc) && !/^[a-z]{2}$/.test(loc)) {
      newErrors.locale = 'Format locale harus valid (cth: id-ID atau en-US).';
    }

    setErrors(newErrors);
    return !Object.keys(newErrors).some((k) => newErrors[k] !== undefined);
  };

  const handleSave = async () => {
    if (!validate()) return;
    if (!businessId) return;
    setIsSaving(true);
    setServerError('');
    setSaveSuccess(false);

    const payload: UpdateBusinessInput = {
      name: form.name?.trim() || '',
      description: form.description?.trim() || null,
      timezone: form.timezone?.trim() || 'UTC',
      locale: form.locale?.trim() || 'en-US',
    };

    try {
      const updated = await apiClient.updateBusiness(businessId, payload);
      setBusiness(updated);
      setIsEditing(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal menyimpan perubahan.';
      if (msg.toLowerCase().includes('unauthorized') || msg.includes('401')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleArchive = async () => {
    if (!businessId) return;
    const confirmed = window.confirm(
      'Arsipkan bisnis ini?\n\nData bisnis Anda tidak akan dihapus permanen, tetapi tidak akan tampil pada daftar bisnis aktif.'
    );
    if (!confirmed) return;

    setIsArchiving(true);
    setServerError('');

    try {
      await apiClient.archiveBusiness(businessId);
      navigate('/businesses');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Gagal mengarsipkan bisnis.';
      setServerError(msg);
    } finally {
      setIsArchiving(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-[#030712] text-slate-100">
        <Loading size="lg" text="Memuat data bisnis..." />
      </div>
    );
  }

  if (serverError && !business) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-[#030712] px-4">
        <ErrorState message={serverError} onRetry={fetchBusiness} />
      </div>
    );
  }

  if (!business) {
    return null;
  }

  const contextNavItems = [
    { label: 'Ringkasan', to: `/businesses/${business.id}`, active: true },
    { label: 'Kelola Branch', to: `/businesses/${business.id}/branches` },
    { label: 'Kelola Anggota', to: `/businesses/${business.id}/members` },
    { label: 'Konfigurasi', to: `/businesses/${business.id}/configuration` },
    { label: 'Kategori', to: `/businesses/${business.id}/categories` },
    { label: 'Unit', to: `/businesses/${business.id}/units` },
    { label: 'Produk', to: `/businesses/${business.id}/products` },
    { label: 'Barcode', to: `/businesses/${business.id}/barcodes` },
    { label: 'Daftar Harga', to: `/businesses/${business.id}/price-lists` },
    { label: 'Warehouse', to: `/businesses/${business.id}/warehouses` },
    { label: 'Customer', to: `/businesses/${business.id}/customers` },
    { label: 'Supplier', to: `/businesses/${business.id}/suppliers` },
    { label: 'Pembelian', to: `/businesses/${business.id}/purchases` },
    { label: 'Penerimaan', to: `/businesses/${business.id}/receivings` },
    { label: 'Retur Pembelian', to: `/businesses/${business.id}/purchase-returns` },
    { label: 'Supplier Catalog', to: `/businesses/${business.id}/supplier-catalog` },
    { label: 'Penjualan', to: `/businesses/${business.id}/sales` },
    { label: 'Retur Penjualan', to: `/businesses/${business.id}/sales-returns` },
    { label: 'Akuntansi & Jurnal', to: `/businesses/${business.id}/accounting/journals` },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col antialiased selection:bg-blue-600 selection:text-white">
      {/* Top Navbar */}
      <header className="sticky top-0 z-30 border-b border-slate-800/80 bg-[#0B132B]/80 backdrop-blur-xl">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between gap-4">
            {/* Left section: Brand & Mobile toggle */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="lg:hidden rounded-lg p-2 text-slate-400 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label="Toggle Navigation Menu"
              >
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {mobileMenuOpen ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  )}
                </svg>
              </button>

              <Link to="/app" className="flex items-center gap-2.5 font-bold text-lg text-white">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white text-xs shadow-lg shadow-blue-500/20 font-black">
                  BH
                </div>
                <span className="tracking-tight">BusinessHub</span>
              </Link>
            </div>

            {/* Center Search Input */}
            <div className="hidden md:flex flex-1 max-w-md mx-4">
              <div className="relative w-full">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-500 pointer-events-none">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </span>
                <input
                  type="text"
                  placeholder="Cari bisnis, transaksi, atau menu..."
                  className="w-full pl-9 pr-4 py-1.5 text-xs bg-slate-900/60 border border-slate-700/60 rounded-lg text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                  aria-label="Search"
                />
              </div>
            </div>

            {/* Right section: Theme Selector, User Info & Logout */}
            <div className="flex items-center gap-3">
              <select
                value={theme}
                onChange={(e) => setTheme(e.target.value as 'light' | 'dark' | 'system')}
                className="px-2.5 py-1.5 text-xs bg-slate-900 border border-slate-700/80 rounded-lg text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label="Pilih tema tampilan"
              >
                <option value="dark">Dark Theme</option>
                <option value="light">Light Theme</option>
                <option value="system">System</option>
              </select>

              <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400 border-l border-slate-800 pl-3">
                <span className="font-medium text-slate-200 truncate max-w-[130px]">{user?.full_name || user?.email}</span>
                <Badge variant="info" size="sm">Owner</Badge>
              </div>

              <Button variant="outline" size="sm" onClick={handleLogout} className="text-xs">
                Keluar
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container Layout */}
      <div className="mx-auto max-w-7xl w-full flex-1 px-4 sm:px-6 lg:px-8 py-6 flex flex-col lg:flex-row gap-6">
        {/* Mobile Navigation Drawer Overlay */}
        {mobileMenuOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/70 backdrop-blur-xs lg:hidden"
            onClick={() => setMobileMenuOpen(false)}
          />
        )}

        {/* Sidebar Navigation */}
        <aside
          className={`${
            mobileMenuOpen
              ? 'fixed inset-y-0 left-0 z-50 w-64 bg-[#0B132B] p-6 shadow-2xl border-r border-slate-800'
              : 'hidden'
          } lg:block lg:w-60 lg:flex-shrink-0`}
        >
          <div className="space-y-6">
            <div className="flex items-center justify-between lg:hidden pb-4 border-b border-slate-800">
              <span className="font-bold text-white text-sm">Menu Utama</span>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <nav className="space-y-1 text-sm font-medium">
              <Link
                to="/app"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-900/60 transition-colors"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2l2 2m7.56-5.01a8.967 8.967 0 01-1.89-3.03l-2.22-2.22m11.94 1.89l-2.22 2.22M9 10H5a2 2 0 00-2 2v3m4.186-6.814a4.5 4.5 0 11-6.364 6.364M9 20h6a2 2 0 002-2v-3m-6.814-4.186a4.5 4.5 0 11-6.364 6.364M15 9h6m-6 4h6m2-6v6m6-2a2 2 0 01-2 2H9a2 2 0 01-2-2V5a2 2 0 012-2z" />
                </svg>
                Dashboard
              </Link>

              <Link
                to="/businesses"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-blue-400 bg-blue-600/10 border border-blue-500/20 font-semibold"
              >
                <svg className="h-4 w-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5m0 0h4m-4 0V11m0 0H8m4 0h4" />
                </svg>
                Bisnis Saya
              </Link>

              <Link
                to="/account"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-900/60 transition-colors"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                Akun Saya
              </Link>
            </nav>

            {/* Business Context Sidebar Box */}
            <div className="pt-4 border-t border-slate-800/80">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2 px-1">
                Bisnis Aktif
              </span>
              <div className="p-3 rounded-xl bg-slate-900/70 border border-slate-800/80">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 font-bold text-xs">
                    {getInitials(business.name)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold text-white truncate">{business.name}</p>
                    <p className="text-[10px] text-slate-400 truncate">/{business.slug}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 min-w-0 space-y-6">
          {/* Top Context Navigation Bar (Horizontal Scrollable Tabs) */}
          <div className="overflow-x-auto pb-1.5 scrollbar-thin scrollbar-thumb-slate-800">
            <div className="flex items-center gap-1.5 min-w-max border-b border-slate-800/80 pb-2.5">
              {contextNavItems.map((item) => (
                <Link
                  key={item.label}
                  to={item.to}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    item.active
                      ? 'bg-blue-600 text-white shadow-sm shadow-blue-500/25 font-semibold'
                      : 'bg-slate-900/50 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800/60'
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>

          {/* Page Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
                <Link to="/businesses" className="hover:text-blue-400 transition-colors">
                  Bisnis Saya
                </Link>
                <span>/</span>
                <span className="text-slate-200">{business.name}</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
                Profil Bisnis
              </h1>
              <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
                Informasi detail dan manajemen operasional bisnis Anda.
              </p>
            </div>
          </div>

          {/* Save Success Banner */}
          {saveSuccess && (
            <div className="rounded-xl bg-emerald-950/40 border border-emerald-800/50 p-4 text-emerald-300 text-sm flex items-center gap-3">
              <svg className="h-5 w-5 flex-shrink-0 text-emerald-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 001.414 0z" clipRule="evenodd" />
              </svg>
              <span>Perubahan profil bisnis berhasil disimpan.</span>
            </div>
          )}

          {/* Server Error Banner */}
          {serverError && (
            <div className="rounded-xl bg-rose-950/40 border border-rose-800/50 p-4 text-rose-300 text-sm flex items-center gap-3">
              <svg className="h-5 w-5 flex-shrink-0 text-rose-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <span>{serverError}</span>
            </div>
          )}

          {/* 2-Column Responsive Layout for Desktop: Left Hero + Info Grid, Right Quick Actions + Summary */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column (Span 2): Profile Hero Card + Health Card + Recent Activity */}
            <div className="lg:col-span-2 space-y-6">
              {/* Business Profile Hero Card */}
              <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#0D1527] via-[#0F172A] to-[#0A0F1D] border border-slate-800 p-6 shadow-xl">
                {/* Decorative background glow */}
                <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 rounded-full bg-blue-600/10 blur-3xl pointer-events-none" />

                {/* Hero Header */}
                <div className="relative flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
                  <div className="flex items-center gap-4">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white text-xl font-black shadow-lg shadow-blue-500/20 border border-blue-400/20">
                      {getInitials(business.name)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                          {business.name}
                        </h2>
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                          {business.status === 'active' ? 'Aktif' : business.status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1 flex items-center gap-2">
                        <span>Slug: <code className="text-blue-400 font-mono bg-blue-950/40 px-1.5 py-0.5 rounded border border-blue-900/40">/{business.slug}</code></span>
                        <span>•</span>
                        <span>{BUSINESS_TYPE_LABELS[business.business_type] || business.business_type}</span>
                      </p>
                    </div>
                  </div>
                </div>

                {/* Edit Form or Information Grid */}
                {isEditing ? (
                  <div className="mt-6 space-y-4">
                    <h3 className="text-sm font-semibold text-white">Edit Informasi Bisnis</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <Input
                        id="name"
                        label="Nama Bisnis"
                        value={form.name ?? ''}
                        onChange={handleChange('name')}
                        error={errors.name}
                      />
                      <Input
                        id="timezone"
                        label="Timezone"
                        value={form.timezone ?? 'UTC'}
                        onChange={handleChange('timezone')}
                        error={errors.timezone}
                        placeholder="Asia/Jakarta atau UTC"
                      />
                      <Input
                        id="locale"
                        label="Locale"
                        value={form.locale ?? 'en-US'}
                        onChange={handleChange('locale')}
                        error={errors.locale}
                        placeholder="id-ID atau en-US"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">
                        Deskripsi
                      </label>
                      <textarea
                        rows={3}
                        value={form.description ?? ''}
                        onChange={handleChange('description')}
                        className="w-full px-3.5 py-2 text-xs bg-slate-900 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                        placeholder="Tuliskan deskripsi singkat mengenai usaha ini..."
                      />
                    </div>
                    <div className="flex items-center justify-end gap-3 pt-2">
                      <Button variant="outline" size="sm" onClick={handleCancel} disabled={isSaving}>
                        Batal
                      </Button>
                      <Button size="sm" onClick={handleSave} isLoading={isSaving} disabled={isSaving}>
                        Simpan Perubahan
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-y-5 gap-x-6">
                    {/* Information Item 1: Nama Bisnis */}
                    <div className="space-y-1">
                      <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                        <svg className="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5m0 0h4m-4 0V11m0 0H8m4 0h4" />
                        </svg>
                        Nama Bisnis
                      </span>
                      <p className="text-sm font-semibold text-white">{business.name}</p>
                    </div>

                    {/* Information Item 2: Tipe Bisnis */}
                    <div className="space-y-1">
                      <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                        <svg className="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                        </svg>
                        Tipe Bisnis
                      </span>
                      <p className="text-sm font-semibold text-white">
                        {BUSINESS_TYPE_LABELS[business.business_type] || business.business_type}
                      </p>
                    </div>

                    {/* Information Item 3: Status */}
                    <div className="space-y-1">
                      <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                        <svg className="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Status
                      </span>
                      <p className="text-sm font-semibold text-emerald-400 flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-400" />
                        {business.status === 'active' ? 'Aktif' : business.status}
                      </p>
                    </div>

                    {/* Information Item 4: Owner */}
                    <div className="space-y-1">
                      <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                        <svg className="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                        Owner
                      </span>
                      <p className="text-sm font-semibold text-white">
                        {business.owner_user_id.slice(0, 8)}... <span className="text-xs text-blue-400 font-normal">(Anda)</span>
                      </p>
                    </div>

                    {/* Information Item 5: Deskripsi */}
                    <div className="space-y-1 sm:col-span-2">
                      <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                        <svg className="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
                        </svg>
                        Deskripsi
                      </span>
                      <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                        {business.description || <span className="italic text-slate-500">Tidak ada deskripsi</span>}
                      </p>
                    </div>

                    {/* Information Item 6: Timezone */}
                    <div className="space-y-1">
                      <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                        <svg className="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Timezone
                      </span>
                      <p className="text-sm font-semibold text-slate-200">{business.timezone || 'UTC'}</p>
                    </div>

                    {/* Information Item 7: Locale */}
                    <div className="space-y-1">
                      <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                        <svg className="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064" />
                        </svg>
                        Locale
                      </span>
                      <p className="text-sm font-semibold text-slate-200">{business.locale || 'en-US'}</p>
                    </div>

                    {/* Information Item 8: Dibuat Pada */}
                    <div className="space-y-1">
                      <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                        <svg className="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        Dibuat Pada
                      </span>
                      <p className="text-xs sm:text-sm text-slate-300 font-mono">
                        {new Date(business.created_at).toLocaleString()}
                      </p>
                    </div>

                    {/* Information Item 9: Diperbarui Pada */}
                    <div className="space-y-1">
                      <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                        <svg className="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Diperbarui Pada
                      </span>
                      <p className="text-xs sm:text-sm text-slate-300 font-mono">
                        {new Date(business.updated_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Business Health / Readiness Status Card */}
              <div className="rounded-2xl bg-[#0D1527] border border-slate-800 p-5 flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 flex-shrink-0">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">Status Bisnis Aktif & Siap Digunakan</h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Modul operasional cabang, produk, inventori, transaksi, dan akuntansi siap digunakan.
                  </p>
                </div>
              </div>

              {/* Recent Activity Card */}
              <Card title="Aktivitas Terbaru" description="Riwayat aktivitas terkini pada bisnis ini" className="bg-[#0D1527] border-slate-800">
                <div className="space-y-3 pt-2">
                  <div className="flex items-start justify-between gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
                    <div className="flex items-start gap-3">
                      <div className="w-7 h-7 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 text-xs mt-0.5">
                        ✦
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-white">Bisnis Dibuat di Platform</p>
                        <p className="text-[11px] text-slate-400">Diinisialisasi oleh sistem BusinessHub</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-[11px] font-mono text-slate-400 block">
                        {new Date(business.created_at).toLocaleDateString()}
                      </span>
                      <Badge variant="success" size="sm">Sukses</Badge>
                    </div>
                  </div>

                  <div className="flex items-start justify-between gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
                    <div className="flex items-start gap-3">
                      <div className="w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 text-xs mt-0.5">
                        ↺
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-white">Pembaruan Terakhir</p>
                        <p className="text-[11px] text-slate-400">Sinkronisasi status dan konfigurasi profil</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-[11px] font-mono text-slate-400 block">
                        {new Date(business.updated_at).toLocaleDateString()}
                      </span>
                      <Badge variant="info" size="sm">Aktif</Badge>
                    </div>
                  </div>
                </div>
              </Card>
            </div>

            {/* Right Column (Span 1): Quick Actions Card + Business Summary Tiles */}
            <div className="space-y-6">
              {/* Quick Actions Card */}
              <div className="rounded-2xl bg-[#0D1527] border border-slate-800 p-5 shadow-lg space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <span className="text-amber-400">⚡</span> Aksi Cepat
                  </h3>
                </div>

                <div className="space-y-2.5">
                  {!isEditing ? (
                    <Button
                      onClick={handleEdit}
                      className="w-full justify-center bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs shadow-md shadow-blue-500/20 border border-blue-400/20"
                    >
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                      Edit Profil Bisnis
                    </Button>
                  ) : (
                    <Button
                      variant="outline"
                      onClick={handleCancel}
                      className="w-full justify-center text-xs"
                    >
                      Batal Edit
                    </Button>
                  )}

                  <Link to={`/businesses/${business.id}/configuration`} className="block">
                    <Button variant="outline" className="w-full justify-center text-xs bg-slate-900/60 border-slate-700 hover:bg-slate-800 text-slate-200">
                      <svg className="w-4 h-4 mr-2 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      Konfigurasi Bisnis
                    </Button>
                  </Link>

                  <Link to={`/businesses/${business.id}/members`} className="block">
                    <Button variant="outline" className="w-full justify-center text-xs bg-slate-900/60 border-slate-700 hover:bg-slate-800 text-slate-200">
                      <svg className="w-4 h-4 mr-2 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                      </svg>
                      Kelola Anggota
                    </Button>
                  </Link>

                  <div className="pt-2 border-t border-slate-800/80">
                    <Button
                      variant="danger"
                      onClick={handleArchive}
                      isLoading={isArchiving}
                      disabled={isArchiving || isEditing || isSaving}
                      className="w-full justify-center text-xs font-medium"
                    >
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      Arsipkan Bisnis
                    </Button>
                  </div>
                </div>
              </div>

              {/* Business Summary / Key Metrics Card */}
              <div className="rounded-2xl bg-[#0D1527] border border-slate-800 p-5 shadow-lg space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
                  <h3 className="text-sm font-bold text-white">Ringkasan Operasional</h3>
                  <span className="text-[10px] text-slate-400">Data Real-Time</span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  {/* Summary Item: Branch */}
                  <Link
                    to={`/businesses/${business.id}/branches`}
                    className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800/80 hover:border-blue-500/40 hover:bg-slate-800/50 transition-all group"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[11px] font-medium text-slate-400 group-hover:text-blue-400 transition-colors">Branch</span>
                      <span className="text-xs text-slate-500 group-hover:text-blue-400">&rarr;</span>
                    </div>
                    <p className="text-xl font-extrabold text-white font-mono">
                      {counts.branches !== null ? counts.branches : '-'}
                    </p>
                  </Link>

                  {/* Summary Item: Anggota */}
                  <Link
                    to={`/businesses/${business.id}/members`}
                    className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800/80 hover:border-blue-500/40 hover:bg-slate-800/50 transition-all group"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[11px] font-medium text-slate-400 group-hover:text-blue-400 transition-colors">Anggota</span>
                      <span className="text-xs text-slate-500 group-hover:text-blue-400">&rarr;</span>
                    </div>
                    <p className="text-xl font-extrabold text-white font-mono">
                      {counts.members !== null ? counts.members : '-'}
                    </p>
                  </Link>

                  {/* Summary Item: Produk */}
                  <Link
                    to={`/businesses/${business.id}/products`}
                    className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800/80 hover:border-blue-500/40 hover:bg-slate-800/50 transition-all group"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[11px] font-medium text-slate-400 group-hover:text-blue-400 transition-colors">Produk</span>
                      <span className="text-xs text-slate-500 group-hover:text-blue-400">&rarr;</span>
                    </div>
                    <p className="text-xl font-extrabold text-white font-mono">
                      {counts.products !== null ? counts.products : '-'}
                    </p>
                  </Link>

                  {/* Summary Item: Warehouse */}
                  <Link
                    to={`/businesses/${business.id}/warehouses`}
                    className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800/80 hover:border-blue-500/40 hover:bg-slate-800/50 transition-all group"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[11px] font-medium text-slate-400 group-hover:text-blue-400 transition-colors">Warehouse</span>
                      <span className="text-xs text-slate-500 group-hover:text-blue-400">&rarr;</span>
                    </div>
                    <p className="text-xl font-extrabold text-white font-mono">
                      {counts.warehouses !== null ? counts.warehouses : '-'}
                    </p>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* Footer */}
      <footer className="mt-auto border-t border-slate-800/80 bg-[#070D1E] text-[11px] text-slate-400 py-4">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>BusinessHub SaaS Platform &copy; 2026</span>
          <span className="text-slate-400">Enterprise Multi-Tenant Infrastructure Active</span>
        </div>
      </footer>
    </div>
  );
};

export default BusinessDetail;
