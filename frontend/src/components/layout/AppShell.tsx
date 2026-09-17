import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { BusinessProvider, useBusiness } from '@/context/BusinessContext';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';

const ShellContent: React.FC = () => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const { isLoading, error, refreshBusiness } = useBusiness();

  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-900">
        <Loading size="lg" text="Memuat konteks bisnis..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-900 p-6">
        <ErrorState message={error} onRetry={refreshBusiness} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col antialiased">
      {/* Sidebar */}
      <Sidebar
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
        collapsed={collapsed}
        setCollapsed={setCollapsed}
      />

      {/* Main Wrapper (shifted based on sidebar width) */}
      <div
        className={`flex flex-col flex-1 transition-all duration-300 ${
          collapsed ? 'lg:pl-20' : 'lg:pl-64'
        }`}
      >
        {/* Topbar */}
        <Topbar onMenuToggle={() => setMobileOpen(!mobileOpen)} />

        {/* Page Content */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export const AppShell: React.FC = () => {
  return (
    <BusinessProvider>
      <ShellContent />
    </BusinessProvider>
  );
};

export default AppShell;
