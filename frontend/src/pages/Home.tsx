import React from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { ErrorState } from '@/components/ui/ErrorState';
import { useTheme } from '@/hooks/useTheme';

const Home: React.FC = () => {
  const { theme, setTheme } = useTheme();

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 transition-colors duration-200">
      <header className="border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                <span className="text-white font-bold text-sm">BH</span>
              </div>
              <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">BusinessHub</h1>
            </div>
            <div className="flex items-center gap-4">
              <select
                value={theme}
                onChange={(e) => setTheme(e.target.value as 'light' | 'dark' | 'system')}
                className="px-3 py-1.5 text-sm bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                aria-label="Pilih tema"
              >
                <option value="light">Terang</option>
                <option value="dark">Gelap</option>
                <option value="system">Sistem</option>
              </select>
              <Badge variant="info">Foundation Phase</Badge>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-20">
        <section className="text-center mb-16">
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
            BusinessHub Foundation <span className="text-indigo-600 dark:text-indigo-400">Ready</span>
          </h2>
          <p className="mt-4 text-lg sm:text-xl text-slate-600 dark:text-slate-400 max-w-3xl mx-auto">
            Platform SaaS manajemen bisnis multi-tenant untuk Hotel, Retail, dan UMKM.
            Foundation phase selesai - siap untuk pengembangan fitur bisnis.
          </p>
        </section>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
          <Card title="Frontend Stack" description="Modern, type-safe, dan responsive">
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">React 19 + TypeScript</span>
                <Badge variant="success">Active</Badge>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Vite 8</span>
                <Badge variant="success">Active</Badge>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Tailwind CSS 4</span>
                <Badge variant="success">Active</Badge>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">React Router 7</span>
                <Badge variant="success">Active</Badge>
              </div>
            </div>
          </Card>

          <Card title="Backend Stack" description="High-performance API foundation">
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">FastAPI</span>
                <Badge variant="success">Active</Badge>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Python 3.13</span>
                <Badge variant="success">Active</Badge>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Pydantic v2</span>
                <Badge variant="success">Active</Badge>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Modular Monolith</span>
                <Badge variant="success">Ready</Badge>
              </div>
            </div>
          </Card>

          <Card title="Foundation Features" description="Core infrastructure ready">
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Dark Mode Support</span>
                <Badge variant="success">Ready</Badge>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">Responsive Layout</span>
                <Badge variant="success">Ready</Badge>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">UI Primitives</span>
                <Badge variant="success">Ready</Badge>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">API Versioning</span>
                <Badge variant="success">Ready</Badge>
              </div>
            </div>
          </Card>
        </div>

        <section className="mb-16">
          <h3 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-6 text-center">UI Primitives Library</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="min-h-[120px]">
              <div className="w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center mb-3">
                <Button size="sm" variant="primary">Primary</Button>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="primary">Primary</Button>
                <Button size="sm" variant="secondary">Secondary</Button>
                <Button size="sm" variant="outline">Outline</Button>
              </div>
            </Card>
            <Card className="min-h-[120px]">
              <div className="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mb-3">
                <Badge variant="success">Success</Badge>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant="success">Success</Badge>
                <Badge variant="warning">Warning</Badge>
                <Badge variant="error">Error</Badge>
                <Badge variant="info">Info</Badge>
              </div>
            </Card>
            <Card className="min-h-[120px]">
              <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center mb-3">
                <span className="text-sm">📝</span>
              </div>
              <Input label="Email" placeholder="name@example.com" />
            </Card>
            <Card className="min-h-[120px]">
              <div className="w-10 h-10 rounded-lg bg-rose-100 dark:bg-rose-900/30 flex items-center justify-center mb-3">
                <span className="text-sm">⚠️</span>
              </div>
              <ErrorState message="Contoh error state" />
            </Card>
          </div>
        </section>

        <Card className="max-w-3xl mx-auto">
          <div className="flex flex-col items-center text-center">
            <div className="w-12 h-12 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center mb-4">
              <svg className="w-6 h-6 text-indigo-600 dark:text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3m4 7h-4m4 7h-4m-8-7H9m4 0v7M9 3v7m0 7h.01M17 21v-7m0-7h.01M21 21v-7M3 21v-7" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-2">Selanjutnya: Phase 1 - Authentication & Account</h3>
            <p className="text-slate-600 dark:text-slate-400 mb-6 max-w-md">
              Foundation sudah selesai. Siap untuk implementasi Autentikasi, Account, Business, dan Template Usaha.
            </p>
            <div className="flex flex-wrap gap-3 justify-center">
              <Button size="lg" variant="primary">
                Mulai Phase 1
              </Button>
              <Button size="lg" variant="outline">
                Lihat Dokumentasi
              </Button>
            </div>
          </div>
        </Card>
      </main>

      <footer className="border-t border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-slate-500 dark:text-slate-400">
          BusinessHub Foundation — Phase 0 Complete
        </div>
      </footer>
    </div>
  );
};

export default Home;