import React, { useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import type { Business, BusinessStatus } from '@/types/business';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { Badge } from '@/components/ui/Badge';

export const Businesses: React.FC = () => {
  const navigate = useNavigate();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [serverError, setServerError] = useState<string>('');

  const fetchBusinesses = useCallback(async () => {
    try {
      setIsLoading(true);
      setServerError('');
      const data = await apiClient.listBusinesses();
      setBusinesses(data);
    } catch (err: any) {
      const msg = err?.message || 'Failed to load businesses.';
      if (msg.toLowerCase().includes('unauthorized') || err?.message?.includes('401')) {
        navigate('/login');
      } else {
        setServerError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [navigate]);

  React.useEffect(() => {
    fetchBusinesses();
  }, [fetchBusinesses]);

  const getStatusVariant = (status: BusinessStatus): 'success' | 'warning' | 'neutral' => {
    switch (status) {
      case 'active': return 'success';
      case 'suspended': return 'warning';
      case 'archived': return 'neutral';
      default: return 'neutral';
    }
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
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-900">
        <Loading size="lg" text="Loading businesses..." />
      </div>
    );
  }

  if (serverError) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 dark:bg-slate-900">
        <ErrorState message={serverError} onRetry={fetchBusinesses} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              Bisnis Saya
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Kelola semua bisnis yang Anda miliki.
            </p>
          </div>
          <Button
            onClick={() => navigate('/businesses/new')}
            className="w-full sm:w-auto"
          >
            <span className="flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
              </svg>
              Tambah Bisnis
            </span>
          </Button>
        </header>

        {businesses.length === 0 ? (
          <EmptyState
            title="Belum ada bisnis"
            description="Anda belum memiliki bisnis. Buat bisnis pertama Anda untuk mulai mengelola operasional."
            action={
              <Button onClick={() => navigate('/businesses/new')}>
                Tambah Bisnis Pertama
              </Button>
            }
          />
        ) : (
          <div className="space-y-4">
            {businesses.map((business) => (
              <Card
                key={business.id}
                className="hover:border-indigo-300 dark:hover:border-indigo-800 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div
                    className={`flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 font-bold`}
                  >
                    {getInitials(business.name)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                        {business.name}
                      </h3>
                      <Badge variant={getStatusVariant(business.status)} className="capitalize">
                        {business.status}
                      </Badge>
                    </div>
                    <p className="text-sm text-slate-600 dark:text-slate-300 mt-1 break-all">
                      /{business.slug}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
                      <span className="bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                        {business.business_type}
                      </span>
                      <span>{business.timezone}</span>
                      <span>{business.locale}</span>
                    </div>
                    {business.description && (
                      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300 line-clamp-2">
                        {business.description}
                      </p>
                    )}
                  </div>
                </div>
                <div className="mt-4 flex justify-end gap-2">
                  <Link
                    to={`/businesses/${business.id}`}
                    className="inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 border border-slate-300 hover:bg-slate-100 text-slate-700 focus:ring-slate-400 dark:border-slate-600 dark:hover:bg-slate-800 dark:text-slate-200 text-sm px-3 py-1.5 min-h-[32px]"
                  >
                    Lihat Detail
                  </Link>
                </div>
              </Card>
            ))}
          </div>
        )}

        <div className="mt-8 text-center">
          <Link
            to="/account"
            className="inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 border border-slate-300 hover:bg-slate-100 text-slate-700 focus:ring-slate-400 dark:border-slate-600 dark:hover:bg-slate-800 dark:text-slate-200 text-sm px-4 py-2 min-h-[40px]"
          >
            Akun Saya
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Businesses;
