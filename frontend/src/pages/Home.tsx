import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { useTheme } from '@/hooks/useTheme';

const Home: React.FC = () => {
  const { theme, setTheme } = useTheme();

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 transition-colors duration-200 text-slate-900 dark:text-slate-100">
      {/* Navigation */}
      <header className="border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-8">
              <Link to="/" className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                  <span className="text-white font-bold text-sm">BH</span>
                </div>
                <span className="text-xl font-bold tracking-tight">BusinessHub</span>
              </Link>
              <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600 dark:text-slate-300">
                <a href="#fitur" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">Fitur</a>
                <a href="#jenis-usaha" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">Jenis Usaha</a>
                <a href="#keamanan" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">Keamanan</a>
                <Link to="/login" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">Dokumentasi</Link>
              </nav>
            </div>
            <div className="flex items-center gap-4">
              <select
                value={theme}
                onChange={(e) => setTheme(e.target.value as 'light' | 'dark' | 'system')}
                className="px-3 py-1.5 text-sm bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                aria-label="Pilih tema"
              >
                <option value="light">Terang</option>
                <option value="dark">Gelap</option>
                <option value="system">Sistem</option>
              </select>
              <Link to="/login">
                <Button variant="outline" size="sm">Masuk</Button>
              </Link>
              <Link to="/register">
                <Button variant="primary" size="sm">Mulai Gratis</Button>
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 lg:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-800/80 text-indigo-700 dark:text-indigo-300 text-xs font-semibold mb-6">
            <span>✨ Platform Manajemen Bisnis Terpadu</span>
          </div>
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-bold tracking-tight text-slate-900 dark:text-white max-w-4xl mx-auto leading-tight">
            Kelola Seluruh Operasional Bisnis Anda dalam <span className="text-indigo-600 dark:text-indigo-400">Satu Platform</span>
          </h1>
          <p className="mt-6 text-lg sm:text-xl text-slate-600 dark:text-slate-300 max-w-2xl mx-auto leading-relaxed">
            BusinessHub membantu bisnis mengelola penjualan, inventory, purchasing, customer, keuangan, accounting, dan multi-branch dalam satu platform terpadu.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <Link to="/register">
              <Button size="lg" variant="primary">
                Mulai Coba Gratis
              </Button>
            </Link>
            <Link to="/login">
              <Button size="lg" variant="outline">
                Masuk ke Akun
              </Button>
            </Link>
          </div>

          {/* Product Preview Card / Mockup */}
          <div className="mt-16 max-w-5xl mx-auto rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 shadow-2xl p-6 lg:p-8 text-left">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800 mb-6">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-rose-500"></div>
                <div className="w-3 h-3 rounded-full bg-amber-500"></div>
                <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
                <span className="text-xs font-mono text-slate-400 ml-2">businesshub.app/dashboard</span>
              </div>
              <Badge variant="success">Live Operations</Badge>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
                <div className="text-xs text-slate-500 dark:text-slate-400">Total Penjualan Hari Ini</div>
                <div className="text-xl font-bold mt-1 text-slate-900 dark:text-slate-100">Rp 14.850.000</div>
                <div className="text-xs text-emerald-600 dark:text-emerald-400 mt-1 font-medium">↑ 12% dari kemarin</div>
              </div>
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
                <div className="text-xs text-slate-500 dark:text-slate-400">Transaksi Sales</div>
                <div className="text-xl font-bold mt-1 text-slate-900 dark:text-slate-100">48 Transaksi</div>
                <div className="text-xs text-indigo-600 dark:text-indigo-400 mt-1 font-medium">Checkout aktif</div>
              </div>
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
                <div className="text-xs text-slate-500 dark:text-slate-400">Inventory Status</div>
                <div className="text-xl font-bold mt-1 text-slate-900 dark:text-slate-100">1.240 SKU</div>
                <div className="text-xs text-amber-600 dark:text-amber-400 mt-1 font-medium">3 stock opname pending</div>
              </div>
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
                <div className="text-xs text-slate-500 dark:text-slate-400">Cabang Aktif</div>
                <div className="text-xl font-bold mt-1 text-slate-900 dark:text-slate-100">4 Cabang</div>
                <div className="text-xs text-emerald-600 dark:text-emerald-400 mt-1 font-medium">Multi-branch sinkron</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Business Types Section */}
      <section id="jenis-usaha" className="py-20 bg-slate-100/60 dark:bg-slate-950/40 border-y border-slate-200 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 dark:text-white">
              Dirancang untuk Berbagai Jenis Usaha
            </h2>
            <p className="mt-4 text-slate-600 dark:text-slate-400 text-lg">
              Arsitektur multi-tenant BusinessHub mendukung fleksibilitas operasional lintas industri.
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {[
              { name: 'Hotel', icon: '🏨', desc: 'Manajemen kamar & layanan' },
              { name: 'Retail', icon: '🛒', desc: 'Kasir & barcode produk' },
              { name: 'UMKM', icon: '📦', desc: 'Pencatatan usaha harian' },
              { name: 'Restoran', icon: '🍽️', desc: 'Meja & pesanan kuliner' },
              { name: 'Service', icon: '🔧', desc: 'Layanan & perbaikan' },
              { name: 'Production', icon: '🏭', desc: 'Proses produksi barang' },
              { name: 'Garment', icon: '👕', desc: 'Varian ukuran & warna' },
              { name: 'Distributor', icon: '🚚', desc: 'Gudang & logistik' },
              { name: 'Workshop', icon: '⚙️', desc: 'Bengkel & sparepart' },
              { name: 'Salon', icon: '💇', desc: 'Layanan & appointment' },
            ].map((type) => (
              <Card key={type.name} className="text-center p-6 hover:shadow-lg transition-all duration-200">
                <div className="text-3xl mb-3">{type.icon}</div>
                <h3 className="font-semibold text-slate-900 dark:text-slate-100">{type.name}</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{type.desc}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Core Capabilities Section */}
      <section id="fitur" className="py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 dark:text-white">
              Kapabilitas Utama Bisnis Anda
            </h2>
            <p className="mt-4 text-slate-600 dark:text-slate-400 text-lg">
              Solusi end-to-end dari manajemen inventory hingga laporan keuangan akuntansi.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <Card title="Sales & Checkout" description="Penjualan & Transaksi" className="h-full">
              <ul className="space-y-2.5 text-sm text-slate-600 dark:text-slate-400 mt-4">
                <li className="flex items-center gap-2">✓ Sales Checkout & Kasir Shift</li>
                <li className="flex items-center gap-2">✓ Sales Orders & Quotations</li>
                <li className="flex items-center gap-2">✓ Customer & Credit Management</li>
                <li className="flex items-center gap-2">✓ Sales Returns & Payment Tracking</li>
              </ul>
            </Card>

            <Card title="Inventory & Warehouse" description="Stok & Gudang" className="h-full">
              <ul className="space-y-2.5 text-sm text-slate-600 dark:text-slate-400 mt-4">
                <li className="flex items-center gap-2">✓ Multi-warehouse Management</li>
                <li className="flex items-center gap-2">✓ Product Variants & Barcode Scanning</li>
                <li className="flex items-center gap-2">✓ Batch, Lot & Expiry Tracking</li>
                <li className="flex items-center gap-2">✓ Stock Opname & Stock Cards</li>
              </ul>
            </Card>

            <Card title="Purchasing & Procurement" description="Pembelian & Supplier" className="h-full">
              <ul className="space-y-2.5 text-sm text-slate-600 dark:text-slate-400 mt-4">
                <li className="flex items-center gap-2">✓ Purchase Orders & Receiving</li>
                <li className="flex items-center gap-2">✓ Supplier Directory & Catalog</li>
                <li className="flex items-center gap-2">✓ Purchase Returns</li>
                <li className="flex items-center gap-2">✓ Accounts Payable (AP) & Aging</li>
              </ul>
            </Card>

            <Card title="Finance & Accounting" description="Keuangan & Akuntansi" className="h-full">
              <ul className="space-y-2.5 text-sm text-slate-600 dark:text-slate-400 mt-4">
                <li className="flex items-center gap-2">✓ Double-entry Chart of Accounts</li>
                <li className="flex items-center gap-2">✓ General Journals & Fiscal Periods</li>
                <li className="flex items-center gap-2">✓ Profit & Loss, Balance Sheet</li>
                <li className="flex items-center gap-2">✓ Tax Management & AR/AP Aging</li>
              </ul>
            </Card>
          </div>
        </div>
      </section>

      {/* Operational Value Section */}
      <section className="py-20 bg-indigo-50/50 dark:bg-indigo-950/20 border-y border-indigo-100 dark:border-indigo-900/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 dark:text-white">
                Satu Pusat Kendali untuk Seluruh Aktivitas Operasional
              </h2>
              <p className="mt-4 text-slate-600 dark:text-slate-300 text-lg leading-relaxed">
                Tinggalkan pencatatan manual yang terpisah. BusinessHub menyatukan kasir, gudang, pembelian, dan pembukuan dalam satu layar terintegrasi.
              </p>
              <div className="mt-8 space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center text-xs font-bold mt-0.5">1</div>
                  <div>
                    <h3 className="font-semibold text-slate-900 dark:text-slate-100">Visibilitas Real-Time</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-400">Pantau pergerakan stok dan omzet penjualan secara langsung.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center text-xs font-bold mt-0.5">2</div>
                  <div>
                    <h3 className="font-semibold text-slate-900 dark:text-slate-100">Kontrol Keuangan Akurat</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-400">Pembukuan otomatis dengan standar double-entry accounting.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center text-xs font-bold mt-0.5">3</div>
                  <div>
                    <h3 className="font-semibold text-slate-900 dark:text-slate-100">Multi-Branch Terpusat</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-400">Kelola banyak cabang dalam satu akun perusahaan dengan isolasi data aman.</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Card className="p-6">
                <div className="text-2xl mb-2">📊</div>
                <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-1">Laporan Laba Rugi</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">Hitung profitabilitas produk dan perusahaan secara instan.</p>
              </Card>
              <Card className="p-6">
                <div className="text-2xl mb-2">🏷️</div>
                <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-1">Barcode & Varian</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">Manajemen varian produk lengkap dengan barcode.</p>
              </Card>
              <Card className="p-6">
                <div className="text-2xl mb-2">📜</div>
                <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-1">AR / AP Aging</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">Laporan umur piutang dan hutang secara terperinci.</p>
              </Card>
              <Card className="p-6">
                <div className="text-2xl mb-2">🚚</div>
                <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-1">Delivery Notes</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">Kelola surat jalan dan pengiriman barang ke customer.</p>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Security & Multi-Branch Section */}
      <section id="keamanan" className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 dark:text-white">
              Multi-Branch & Keamanan Terjamin
            </h2>
            <p className="mt-4 text-slate-600 dark:text-slate-400 text-lg">
              Arsitektur multi-tenant dengan isolasi data ketat dan manajemen akses berbasis peran.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <Card title="Business Isolation" description="Pemisahan data tenant">
              <p className="text-sm text-slate-600 dark:text-slate-400 mt-2">
                Data dan operasi bisnis dibatasi secara ketat berdasarkan business context untuk menjaga privasi perusahaan Anda.
              </p>
            </Card>
            <Card title="Role-Based Access (RBAC)" description="Hak akses terstruktur">
              <p className="text-sm text-slate-600 dark:text-slate-400 mt-2">
                Akses pengguna ke fitur dan cabang diatur melalui membership role yang tervalidasi secara real-time.
              </p>
            </Card>
            <Card title="Auditability" description="Jejak aktivitas sistem">
              <p className="text-sm text-slate-600 dark:text-slate-400 mt-2">
                Platform menyediakan pencatatan log aktivitas untuk transparansi operasional dan pengawasan platform.
              </p>
            </Card>
          </div>
        </div>
      </section>

      {/* Final CTA Section */}
      <section className="py-20 bg-indigo-600 text-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-5xl font-bold tracking-tight">
            Siap Mengoptimalkan Operasional Bisnis Anda?
          </h2>
          <p className="mt-4 text-indigo-100 text-lg max-w-2xl mx-auto">
            Bergabunglah dengan BusinessHub dan rasakan kemudahan mengelola seluruh aspek bisnis dalam satu platform.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link to="/register">
              <Button size="lg" variant="secondary" className="bg-white text-indigo-600 hover:bg-slate-100">
                Mulai Coba Gratis
              </Button>
            </Link>
            <Link to="/login">
              <Button size="lg" variant="outline" className="border-white text-white hover:bg-indigo-700">
                Masuk ke Akun
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                  <span className="text-white font-bold text-xs">BH</span>
                </div>
                <span className="font-bold text-slate-900 dark:text-slate-100">BusinessHub</span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Platform manajemen bisnis multi-tenant terpadu untuk efisiensi operasional maksimal.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100 mb-3">Product</h3>
              <ul className="space-y-2 text-xs text-slate-600 dark:text-slate-400">
                <li><a href="#fitur" className="hover:text-indigo-600">Fitur Utama</a></li>
                <li><a href="#jenis-usaha" className="hover:text-indigo-600">Jenis Usaha</a></li>
                <li><a href="#keamanan" className="hover:text-indigo-600">Keamanan</a></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100 mb-3">Resources</h3>
              <ul className="space-y-2 text-xs text-slate-600 dark:text-slate-400">
                <li><Link to="/login" className="hover:text-indigo-600">Dokumentasi</Link></li>
                <li><Link to="/login" className="hover:text-indigo-600">Bantuan</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100 mb-3">Akses</h3>
              <ul className="space-y-2 text-xs text-slate-600 dark:text-slate-400">
                <li><Link to="/login" className="hover:text-indigo-600">Masuk</Link></li>
                <li><Link to="/register" className="hover:text-indigo-600">Pendaftaran</Link></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-slate-200 dark:border-slate-800 pt-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <div>© {new Date().getFullYear()} BusinessHub. All rights reserved.</div>
            <div className="mt-4 sm:mt-0 flex gap-4">
              <span>Multi-Tenant SaaS Architecture</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Home;