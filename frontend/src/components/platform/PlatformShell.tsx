import React from 'react';
import { PlatformSidebar } from './PlatformSidebar';
import { PlatformTopbar } from './PlatformTopbar';

interface PlatformShellProps {
  children: React.ReactNode;
}

export const PlatformShell: React.FC<PlatformShellProps> = ({ children }) => {
  return (
    <div className="flex h-screen bg-slate-50">
      <PlatformSidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <PlatformTopbar />
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
};
