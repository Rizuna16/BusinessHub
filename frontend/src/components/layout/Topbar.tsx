import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/hooks/useTheme';
import { useBusiness } from '@/context/BusinessContext';
import { Menu, LogOut, ChevronRight, User } from 'lucide-react';
import { NotificationBell } from '@/components/NotificationBell';

interface TopbarProps {
  onMenuToggle: () => void;
}

// Route to breadcrumb label mapping
const breadcrumbLabels: Record<string, string> = {
  dashboard: 'Dashboard',
  operational: 'Operasional',
  sales: 'Penjualan',
  'sales-returns': 'Retur Penjualan',
  receivables: 'Piutang',
  customers: 'Pelanggan',
  purchases: 'Pembelian',
  receivings: 'Penerimaan',
  'purchase-returns': 'Retur Pembelian',
  payables: 'Hutang',
  suppliers: 'Pemasok',
  'supplier-catalog': 'Katalog Pemasok',
  products: 'Produk',
  categories: 'Kategori',
  units: 'Satuan',
  barcodes: 'Barcode',
  'price-lists': 'Daftar Harga',
  warehouses: 'Gudang',
  inventory: 'Inventaris',
  'stock-opnames': 'Stok Opname',
  'stock-cards': 'Kartu Stok',
  'cash-accounts': 'Kas & Bank',
  expenses: 'Pengeluaran',
  payments: 'Pembayaran',
  accounting: 'Akuntansi',
  'chart-of-accounts': 'Bagan Akun',
  journals: 'Jurnal',
  'trial-balance': 'Neraca Saldo',
  periods: 'Periode Fiskal',
  reports: 'Laporan',
  'profit-and-loss': 'Laba Rugi',
  'balance-sheet': 'Neraca',
  tax: 'Pajak',
  configuration: 'Konfigurasi',
  summary: 'Ringkasan',
  aging: 'Aging',
  'product-profitability': 'Profitabilitas Produk',
  analytics: 'Analitik',
  branches: 'Cabang',
  members: 'Anggota',
};

function buildBreadcrumbs(pathname: string) {
  const segments = pathname.split('/').filter(Boolean);
  const crumbs: { label: string; path: string }[] = [];

  let currentPath = '';
  for (const seg of segments) {
    currentPath += `/${seg}`;
    const label = breadcrumbLabels[seg] || seg;
    crumbs.push({ label, path: currentPath });
  }
  return crumbs;
}

export const Topbar: React.FC<TopbarProps> = ({ onMenuToggle }) => {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const { business } = useBusiness();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    window.location.href = '/login';
  };

  const breadcrumbs = buildBreadcrumbs(location.pathname);

  return (
    <header className="sticky top-0 z-30 flex items-center h-16 px-4 sm:px-6 lg:px-8 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 gap-4">
      {/* Mobile menu toggle */}
      <button
        type="button"
        onClick={onMenuToggle}
        className="lg:hidden rounded-lg p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        aria-label="Open Sidebar Menu"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Business Name & Breadcrumb (Desktop) */}
      <div className="hidden md:flex flex-1 items-center text-sm text-slate-500 dark:text-slate-400 gap-1 overflow-hidden">
        <Link
          to="/app"
          className="font-semibold text-slate-800 dark:text-slate-200 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors flex-shrink-0"
        >
          BusinessHub
        </Link>

        {breadcrumbs.map((crumb, index) => (
          <React.Fragment key={crumb.path}>
            <ChevronRight className="h-3.5 w-3.5 flex-shrink-0 text-slate-400" />
            <Link
              to={crumb.path}
              className={`hover:text-slate-900 dark:hover:text-slate-100 transition-colors truncate max-w-[150px] ${
                index === breadcrumbs.length - 1
                  ? 'font-medium text-slate-800 dark:text-slate-200 truncate'
                  : ''
              }`}
            >
              {crumb.label}
            </Link>
          </React.Fragment>
        ))}
      </div>

      {/* Mobile business name */}
      <div className="flex md:hidden flex-1 overflow-hidden">
        {business && (
          <span className="text-sm font-semibold text-slate-800 dark:text-slate-200 truncate">
            {business.name}
          </span>
        )}
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
        {/* Notification Bell */}
        <NotificationBell scope="tenant" />

        {/* Theme Toggle */}
        <select
          value={theme}
          onChange={(e) => setTheme(e.target.value as 'light' | 'dark' | 'system')}
          className="px-2 py-1.5 text-xs bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 appearance-none cursor-pointer"
          aria-label="Select Theme"
        >
          <option value="light">Terang</option>
          <option value="dark">Gelap</option>
          <option value="system">Sistem</option>
        </select>

        {/* User Profile Area */}
        <div className="flex items-center gap-2 pl-2 sm:pl-3 sm:border-l border-slate-200 dark:border-slate-800">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center text-white font-bold text-xs shadow-sm flex-shrink-0">
            {user?.full_name ? user.full_name.charAt(0).toUpperCase() : <User className="h-4 w-4" />}
          </div>
          <div className="hidden lg:block truncate max-w-[120px]">
            <p className="text-xs font-medium text-slate-900 dark:text-slate-100 truncate leading-tight">
              {user?.full_name || 'User'}
            </p>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate leading-tight">
              {user?.email}
            </p>
          </div>
        </div>

        {/* Logout */}
        <button
          type="button"
          onClick={handleLogout}
          className="rounded-lg p-2 text-slate-500 hover:text-rose-500 dark:text-slate-400 dark:hover:text-rose-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          aria-label="Sign Out"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
};
