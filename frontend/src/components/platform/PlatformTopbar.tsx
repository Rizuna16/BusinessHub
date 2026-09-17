import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { NotificationBell } from '../NotificationBell';

export const PlatformTopbar: React.FC = () => {
  const { user } = useAuth();

  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 shadow-sm">
      <div className="flex items-center space-x-3">
        <span className="px-2.5 py-1 bg-purple-100 text-purple-800 text-xs font-semibold rounded-full">
          Platform Admin
        </span>
      </div>
      <div className="flex items-center space-x-4">
        <NotificationBell scope="platform" />
        <div className="text-sm font-medium text-slate-700">
          {user?.email}
        </div>
      </div>
    </header>
  );
};
