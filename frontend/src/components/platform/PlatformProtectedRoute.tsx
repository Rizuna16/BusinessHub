import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

interface PlatformProtectedRouteProps {
  children: React.ReactNode;
}

export const PlatformProtectedRoute: React.FC<PlatformProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-slate-50">
        <div className="text-slate-500">Verifying platform session...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (!user || user.platform_role !== 'SUPER_ADMIN') {
    return <Navigate to="/app" replace />;
  }

  return <>{children}</>;
};
