import React, { useEffect, useState } from 'react';
import type { PlatformDashboard } from '../../types/platform';
import { platformApiClient } from '../../services/platformApiClient';

export const PlatformDashboardPage: React.FC = () => {
  const [dashboard, setDashboard] = useState<PlatformDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        const data = await platformApiClient.getDashboard();
        setDashboard(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load dashboard');
      } finally {
        setLoading(false);
      }
    };
    loadDashboard();
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-slate-500">Loading dashboard...</div>;
  }

  if (error) {
    return <div className="p-4 bg-red-50 text-red-700 rounded-md">{error}</div>;
  }

  if (!dashboard) return null;

  const cards = [
    { label: 'Total Businesses', value: dashboard.total_businesses, color: 'text-blue-600' },
    { label: 'Active Businesses', value: dashboard.active_businesses, color: 'text-green-600' },
    { label: 'Suspended Businesses', value: dashboard.suspended_businesses, color: 'text-yellow-600' },
    { label: 'Archived Businesses', value: dashboard.archived_businesses, color: 'text-slate-600' },
    { label: 'Total Accounts', value: dashboard.total_accounts, color: 'text-purple-600' },
    { label: 'Active Subscriptions', value: dashboard.active_subscriptions, color: 'text-indigo-600' },
    { label: 'Expired Subscriptions', value: dashboard.expired_subscriptions, color: 'text-red-600' },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Platform Dashboard</h1>
      
      <div className="bg-white rounded-lg shadow p-6 border border-slate-200">
        <div className="text-sm font-medium text-slate-500">Monthly Recurring Revenue (IDR)</div>
        <div className="mt-1 text-3xl font-bold text-slate-900">
          Rp {dashboard.mrr_idr.toLocaleString('id-ID')}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((card) => (
          <div key={card.label} className="bg-white rounded-lg shadow p-6 border border-slate-200">
            <div className="text-sm font-medium text-slate-500">{card.label}</div>
            <div className={`mt-1 text-2xl font-bold ${card.color}`}>
              {card.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
