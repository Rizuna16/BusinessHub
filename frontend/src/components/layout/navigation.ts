import type { BusinessMembershipRole } from '@/types/businessMembership';

export interface NavItem {
  id: string;
  label: string;
  path: (businessId: string) => string;
  iconName: string;
  roles?: BusinessMembershipRole[];
  exact?: boolean;
}

export interface NavGroup {
  id: string;
  title: string;
  items: NavItem[];
}

export const navigationGroups: NavGroup[] = [
  {
    id: 'main',
    title: 'UTAMA',
    items: [
      {
        id: 'dashboard',
        label: 'Dashboard Operasional',
        path: (bId) => `/businesses/${bId}/dashboard/operational`,
        iconName: 'LayoutDashboard',
      },
    ],
  },
  {
    id: 'sales',
    title: 'PENJUALAN',
    items: [
      {
        id: 'checkout',
        label: 'Sales Checkout',
        path: (bId) => `/businesses/${bId}/checkout`,
        iconName: 'MonitorDot',
      },
      {
        id: 'shifts',
        label: 'Shifts',
        path: (bId) => `/businesses/${bId}/shifts`,
        iconName: 'Clock',
      },
      {
        id: 'sales-list',
        label: 'Daftar Penjualan',
        path: (bId) => `/businesses/${bId}/sales`,
        iconName: 'ShoppingCart',
      },
      {
        id: 'sales-returns',
        label: 'Retur Penjualan',
        path: (bId) => `/businesses/${bId}/sales-returns`,
        iconName: 'RotateCcw',
      },
      {
        id: 'receivables',
        label: 'Piutang (AR)',
        path: (bId) => `/businesses/${bId}/receivables`,
        iconName: 'Receipt',
      },
      {
        id: 'delivery-notes',
        label: 'Surat Jalan / Delivery Notes',
        path: (bId) => `/businesses/${bId}/delivery-notes`,
        iconName: 'ClipboardCheck',
      },
      {
        id: 'customers',
        label: 'Pelanggan',
        path: (bId) => `/businesses/${bId}/customers`,
        iconName: 'Users',
      },
    ],
  },
  {
    id: 'purchasing',
    title: 'PEMBELIAN',
    items: [
      {
        id: 'purchases',
        label: 'Daftar Pembelian',
        path: (bId) => `/businesses/${bId}/purchases`,
        iconName: 'ShoppingBag',
      },
      {
        id: 'receivings',
        label: 'Penerimaan Barang',
        path: (bId) => `/businesses/${bId}/receivings`,
        iconName: 'PackageCheck',
      },
      {
        id: 'purchase-returns',
        label: 'Retur Pembelian',
        path: (bId) => `/businesses/${bId}/purchase-returns`,
        iconName: 'Undo2',
      },
      {
        id: 'payables',
        label: 'Hutang (AP)',
        path: (bId) => `/businesses/${bId}/purchases/payables`,
        iconName: 'CreditCard',
      },
      {
        id: 'suppliers',
        label: 'Pemasok',
        path: (bId) => `/businesses/${bId}/suppliers`,
        iconName: 'Truck',
      },
      {
        id: 'supplier-catalog',
        label: 'Katalog Pemasok',
        path: (bId) => `/businesses/${bId}/supplier-catalog`,
        iconName: 'BookOpen',
      },
    ],
  },
  {
    id: 'inventory',
    title: 'INVENTARIS & KATALOG',
    items: [
      {
        id: 'products',
        label: 'Produk Master',
        path: (bId) => `/businesses/${bId}/products`,
        iconName: 'Package',
      },
      {
        id: 'categories',
        label: 'Kategori Produk',
        path: (bId) => `/businesses/${bId}/categories`,
        iconName: 'Tags',
      },
      {
        id: 'units',
        label: 'Satuan (Unit)',
        path: (bId) => `/businesses/${bId}/units`,
        iconName: 'Ruler',
      },
      {
        id: 'barcodes',
        label: 'Barcode Master',
        path: (bId) => `/businesses/${bId}/barcodes`,
        iconName: 'Barcode',
      },
      {
        id: 'price-lists',
        label: 'Daftar Harga',
        path: (bId) => `/businesses/${bId}/price-lists`,
        iconName: 'BadgePercent',
      },
      {
        id: 'warehouses',
        label: 'Gudang',
        path: (bId) => `/businesses/${bId}/warehouses`,
        iconName: 'Warehouse',
      },
      {
        id: 'inventory-stock',
        label: 'Stok Barang',
        path: (bId) => `/businesses/${bId}/inventory`,
        iconName: 'Boxes',
      },
      {
        id: 'stock-opname',
        label: 'Stok Opname',
        path: (bId) => `/businesses/${bId}/inventory/stock-opnames`,
        iconName: 'ClipboardCheck',
      },
      {
        id: 'stock-card',
        label: 'Kartu Stok',
        path: (bId) => `/businesses/${bId}/inventory/stock-cards`,
        iconName: 'FileText',
      },
    ],
  },
  {
    id: 'finance',
    title: 'KEUANGAN & KAS',
    items: [
      {
        id: 'cash-accounts',
        label: 'Akun Kas & Bank',
        path: (bId) => `/businesses/${bId}/cash-accounts`,
        iconName: 'Wallet',
      },
      {
        id: 'expenses',
        label: 'Pengeluaran / Beban',
        path: (bId) => `/businesses/${bId}/expenses`,
        iconName: 'ArrowDownCircle',
      },
      {
        id: 'payments',
        label: 'Histori Pembayaran',
        path: (bId) => `/businesses/${bId}/payments`,
        iconName: 'History',
      },
    ],
  },
  {
    id: 'accounting',
    title: 'AKUNTANSI & PAJAK',
    items: [
      {
        id: 'coa',
        label: 'Bagan Akun (COA)',
        path: (bId) => `/businesses/${bId}/accounting/chart-of-accounts`,
        iconName: 'GitMerge',
        roles: ['OWNER', 'ADMIN'],
      },
      {
        id: 'journals',
        label: 'Jurnal Umum',
        path: (bId) => `/businesses/${bId}/accounting/journals`,
        iconName: 'BookMarked',
        roles: ['OWNER', 'ADMIN'],
      },
      {
        id: 'trial-balance',
        label: 'Neraca Saldo',
        path: (bId) => `/businesses/${bId}/accounting/trial-balance`,
        iconName: 'Scale',
        roles: ['OWNER', 'ADMIN'],
      },
      {
        id: 'periods',
        label: 'Periode Fiskal',
        path: (bId) => `/businesses/${bId}/accounting/periods`,
        iconName: 'CalendarDays',
        roles: ['OWNER', 'ADMIN'],
      },
      {
        id: 'report-pnl',
        label: 'Laba Rugi (P&L)',
        path: (bId) => `/businesses/${bId}/accounting/reports/profit-and-loss`,
        iconName: 'TrendingUp',
        roles: ['OWNER', 'ADMIN'],
      },
      {
        id: 'report-bs',
        label: 'Neraca Keuangan',
        path: (bId) => `/businesses/${bId}/accounting/reports/balance-sheet`,
        iconName: 'Landmark',
        roles: ['OWNER', 'ADMIN'],
      },
      {
        id: 'tax-config',
        label: 'Konfigurasi Pajak',
        path: (bId) => `/businesses/${bId}/tax/configuration`,
        iconName: 'Percent',
        roles: ['OWNER', 'ADMIN'],
      },
      {
        id: 'tax-summary',
        label: 'Ringkasan PPN',
        path: (bId) => `/businesses/${bId}/tax/summary`,
        iconName: 'Calculator',
        roles: ['OWNER', 'ADMIN'],
      },
    ],
  },
  {
    id: 'analytics',
    title: 'ANALITIK & LAPORAN',
    items: [
      {
        id: 'sales-analytics',
        label: 'Analitik Penjualan',
        path: (bId) => `/businesses/${bId}/sales/analytics`,
        iconName: 'BarChart3',
      },
      {
        id: 'purchase-analytics',
        label: 'Analitik Pembelian',
        path: (bId) => `/businesses/${bId}/purchases/analytics`,
        iconName: 'LineChart',
      },
      {
        id: 'expense-analytics',
        label: 'Analitik Pengeluaran',
        path: (bId) => `/businesses/${bId}/expenses/analytics`,
        iconName: 'PieChart',
      },
      {
        id: 'payment-analytics',
        label: 'Analitik Pembayaran',
        path: (bId) => `/businesses/${bId}/payments/analytics`,
        iconName: 'Activity',
      },
      {
        id: 'ar-aging',
        label: 'Umur Piutang (AR Aging)',
        path: (bId) => `/businesses/${bId}/receivables/aging`,
        iconName: 'Clock',
      },
      {
        id: 'ap-aging',
        label: 'Umur Hutang (AP Aging)',
        path: (bId) => `/businesses/${bId}/purchases/payables/aging`,
        iconName: 'Hourglass',
      },
      {
        id: 'product-profitability',
        label: 'Profitabilitas Produk',
        path: (bId) => `/businesses/${bId}/reports/product-profitability`,
        iconName: 'Coins',
      },
    ],
  },
  {
    id: 'administration',
    title: 'ADMINISTRASI & PENGATURAN',
    items: [
      {
        id: 'business-detail',
        label: 'Profil Bisnis',
        path: (bId) => `/businesses/${bId}`,
        iconName: 'Building',
      },
      {
        id: 'branches',
        label: 'Cabang (Branches)',
        path: (bId) => `/businesses/${bId}/branches`,
        iconName: 'GitBranch',
        roles: ['OWNER', 'ADMIN'],
      },
      {
        id: 'members',
        label: 'Anggota & Hak Akses',
        path: (bId) => `/businesses/${bId}/members`,
        iconName: 'UserCheck',
        roles: ['OWNER', 'ADMIN'],
      },
      {
        id: 'configuration',
        label: 'Konfigurasi Sistem',
        path: (bId) => `/businesses/${bId}/configuration`,
        iconName: 'Settings',
        roles: ['OWNER', 'ADMIN'],
      },
    ],
  },
];
