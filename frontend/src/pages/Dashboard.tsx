import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../hooks/useTheme';
import { apiClient } from '../services/apiClient';
import type { Business } from '../types/business';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Loading } from '../components/ui/Loading';
import { ErrorState } from '../components/ui/ErrorState';

export const Dashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();

  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [isLoadingBusinesses, setIsLoadingBusinesses] = useState<boolean>(true);
  const [businessError, setBusinessError] = useState<string>('');
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  const fetchBusinesses = useCallback(async () => {
    try {
      setIsLoadingBusinesses(true);
      setBusinessError('');
      const data = await apiClient.listBusinesses();
      setBusinesses(data);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Gagal memuat data bisnis.';
      if (errorMsg.toLowerCase().includes('unauthorized') || errorMsg.includes('401')) {
        navigate('/login');
      } else {
        setBusinessError(errorMsg);
      }
    } finally {
      setIsLoadingBusinesses(false);
    }
  }, [navigate]);

  useEffect(() => {
    fetchBusinesses();
  }, [fetchBusinesses]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col antialiased">
      {/* Top Navbar */}
      <header className="sticky top-0 z-30 border-b border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between gap-4">
            {/* Left section: Brand & Mobile toggle */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="lg:hidden rounded-lg p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
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

              <Link to="/app" className="flex items-center gap-2 font-bold text-lg text-slate-900 dark:text-slate-100">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xs">
                  BH
                </div>
                <span>BusinessHub</span>
              </Link>
            </div>

            {/* Right section: Theme Selector, User Info & Logout */}
            <div className="flex items-center gap-3">
              <select
                value={theme}
                onChange={(e) => setTheme(e.target.value as 'light' | 'dark' | 'system')}
                className="px-2.5 py-1.5 text-xs sm:text-sm bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                aria-label="Pilih tema tampilan"
              >
                <option value="light">Terang</option>
                <option value="dark">Gelap</option>
                <option value="system">Sistem</option>
              </select>

              <div className="hidden sm:flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 border-l border-slate-200 dark:border-slate-800 pl-3">
                <span className="font-medium truncate max-w-[150px]">{user?.full_name || user?.email}</span>
              </div>

              <Button variant="outline" size="sm" onClick={handleLogout}>
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
            className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-xs lg:hidden"
            onClick={() => setMobileMenuOpen(false)}
          />
        )}

        {/* Sidebar Navigation */}
        <aside
          className={`${
            mobileMenuOpen
              ? 'fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-slate-900 p-6 shadow-xl'
              : 'hidden'
          } lg:block lg:w-64 lg:flex-shrink-0`}
        >
          <div className="space-y-6">
            <div className="flex items-center justify-between lg:hidden pb-4 border-b border-slate-200 dark:border-slate-800">
              <span className="font-bold text-slate-900 dark:text-slate-100">Menu Navigation</span>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              >
                ✕
              </button>
            </div>

            <nav className="space-y-1">
              <Link
                to="/app"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-900/50"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2l2 2m7.56-5.01a8.967 8.967 0 01-1.89-3.03l-2.22-2.22m11.94 1.89l-2.22 2.22M9 10H5a2 2 0 00-2 2v3m4.186-6.814a4.5 4.5 0 11-6.364 6.364M9 20h6a2 2 0 002-2v-3m-6.814-4.186a4.5 4.5 0 11-6.364 6.364M15 9h6m-6 4h6m2-6v6m6-2a2 2 0 01-2 2H9a2 2 0 01-2-2V5a2 2 0 012-2z" />
                </svg>
                Dashboard
              </Link>

              <Link
                to="/businesses"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5m0 0h4m-4 0V11m0 0H8m4 0h4" />
                </svg>
                Bisnis Saya
              </Link>

              <Link
                to="/account"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                Akun Saya
              </Link>
            </nav>

            <div className="pt-4 border-t border-slate-200 dark:border-slate-800">
              <div className="px-3 py-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Session Info</span>
                <div className="mt-2 space-y-1 text-xs text-slate-600 dark:text-slate-400">
                  <div className="truncate"><span className="font-medium text-slate-700 dark:text-slate-300">User:</span> {user?.full_name}</div>
                  <div className="truncate"><span className="font-medium text-slate-700 dark:text-slate-300">Email:</span> {user?.email}</div>
                  <div><span className="font-medium text-slate-700 dark:text-slate-300">Status:</span> <Badge variant="success" size="sm">Active</Badge></div>
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 min-w-0 space-y-6">
          {/* Page Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                Dashboard UTAMA
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                Ikhtisar akun dan operasional bisnis Anda
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Button onClick={() => navigate('/businesses/new')} size="sm">
                + Tambah Bisnis
              </Button>
            </div>
          </div>

          {/* Loading or Error States for Businesses */}
          {isLoadingBusinesses ? (
            <Card>
              <div className="py-12 flex justify-center">
                <Loading text="Memuat data bisnis..." />
              </div>
            </Card>
          ) : businessError ? (
            <ErrorState message={businessError} onRetry={fetchBusinesses} />
          ) : (
            <>
              {/* Summary / KPI Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <Card title="Total Bisnis">
                  <div className="flex items-baseline justify-between mt-2">
                    <span className="text-3xl font-extrabold text-indigo-600 dark:text-indigo-400">
                      {businesses.length}
                    </span>
                    <Badge variant="info">Aktif</Badge>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
                    Bisnis yang terdaftar di akun Anda
                  </p>
                  <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-700/60">
                    <Link
                      to="/businesses"
                      className="text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:underline inline-flex items-center gap-1"
                    >
                      Kelola Bisnis &rarr;
                    </Link>
                  </div>
                </Card>

                <Card title="Status Sesi">
                  <div className="flex items-baseline justify-between mt-2">
                    <span className="text-3xl font-extrabold text-emerald-600 dark:text-emerald-400">
                      Aktif
                    </span>
                    <Badge variant="success">Authenticated</Badge>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
                    Terhubung ke backend FastAPI
                  </p>
                  <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-700/60">
                    <Link
                      to="/account"
                      className="text-xs font-medium text-emerald-600 dark:text-emerald-400 hover:underline inline-flex items-center gap-1"
                    >
                      Profil Akun &rarr;
                    </Link>
                  </div>
                </Card>

                <Card title="Aksesibilitas">
                  <div className="flex items-baseline justify-between mt-2">
                    <span className="text-3xl font-extrabold text-purple-600 dark:text-purple-400">
                      Multi-Tenant
                    </span>
                    <Badge variant="neutral">SaaS Ready</Badge>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
                    Dukungan isolasi tenant & role membership
                  </p>
                  <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-700/60">
                    <span className="text-xs text-slate-400 dark:text-slate-500">
                      System Operational
                    </span>
                  </div>
                </Card>
              </div>

              {/* Businesses List Section */}
              <Card title="Daftar Bisnis Terdaftar" description="Pilih bisnis untuk mengelola modul operasional">
                {businesses.length === 0 ? (
                  <div className="py-6 text-center">
                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                      Anda belum memiliki bisnis yang terdaftar.
                    </p>
                    <Button size="sm" onClick={() => navigate('/businesses/new')}>
                      Buat Bisnis Pertama
                    </Button>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-100 dark:divide-slate-700/60">
                    {businesses.map((b) => (
                      <div key={b.id} className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="font-semibold text-slate-900 dark:text-slate-100">{b.name}</h4>
                            <Badge variant={b.status === 'active' ? 'success' : 'neutral'} size="sm">
                              {b.status}
                            </Badge>
                          </div>
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                            Tipe: <span className="capitalize">{b.business_type}</span> | Slug: /{b.slug}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Link
                            to={`/businesses/${b.id}`}
                            className="inline-flex items-center justify-center font-medium rounded-lg border border-slate-300 hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs px-3 py-1.5 min-h-[32px]"
                          >
                            Buka Detail
                          </Link>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              {/* Profile Card */}
              <Card title="Informasi Akun Terautentikasi">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                  <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                    <span className="text-xs text-slate-500 dark:text-slate-400 block">Nama Lengkap</span>
                    <span className="font-semibold text-slate-900 dark:text-slate-100">{user?.full_name || '-'}</span>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                    <span className="text-xs text-slate-500 dark:text-slate-400 block">Email</span>
                    <span className="font-semibold text-slate-900 dark:text-slate-100">{user?.email || '-'}</span>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                    <span className="text-xs text-slate-500 dark:text-slate-400 block">ID Pengguna</span>
                    <span className="font-mono text-xs text-slate-700 dark:text-slate-300 break-all">{user?.id || '-'}</span>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                    <span className="text-xs text-slate-500 dark:text-slate-400 block">Tanggal Bergabung</span>
                    <span className="font-semibold text-slate-900 dark:text-slate-100">
                      {user?.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}
                    </span>
                  </div>
                </div>
              </Card>
            </>
          )}
        </main>
      </div>

      {/* Footer */}
      <footer className="mt-auto border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs text-slate-500 dark:text-slate-400 py-4">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>BusinessHub SaaS Platform &copy; 2026</span>
          <span>Foundation Baseline Active</span>
        </div>
      </footer>
    </div>
  );
};

export default Dashboard;