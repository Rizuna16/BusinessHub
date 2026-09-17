import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import type { PlatformBusiness, PlatformBusinessMember } from '../../types/platform';
import { platformApiClient } from '../../services/platformApiClient';

export const PlatformBusinessDetailPage: React.FC = () => {
  const { businessId } = useParams<{ businessId: string }>();
  const navigate = useNavigate();
  
  const [business, setBusiness] = useState<PlatformBusiness | null>(null);
  const [members, setMembers] = useState<PlatformBusinessMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [actionReason, setActionReason] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadData = async () => {
    if (!businessId) return;
    setLoading(true);
    try {
      const [biz, bizMembers] = await Promise.all([
        platformApiClient.getBusinessDetail(businessId),
        platformApiClient.listBusinessMembers(businessId),
      ]);
      setBusiness(biz);
      setMembers(bizMembers);
    } catch (err: any) {
      setError(err.message || 'Failed to load business details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [businessId]);

  const handleAction = async (actionType: 'suspend' | 'activate' | 'archive') => {
    if (!businessId || !actionReason) return;
    
    setActionLoading(true);
    setActionError(null);
    
    try {
      if (actionType === 'suspend') {
        await platformApiClient.suspendBusiness(businessId, { reason: actionReason });
      } else if (actionType === 'activate') {
        await platformApiClient.activateBusiness(businessId, { reason: actionReason });
      } else if (actionType === 'archive') {
        await platformApiClient.archiveBusiness(businessId, { reason: actionReason });
      }
      setActionReason('');
      await loadData();
    } catch (err: any) {
      setActionError(err.message || 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <div className="flex justify-center py-12 text-slate-500">Loading business details...</div>;
  if (error) return <div className="p-4 bg-red-50 text-red-700 rounded-md">{error}</div>;
  if (!business) return null;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <button onClick={() => navigate('/platform/businesses')} className="text-blue-600 hover:text-blue-800 text-sm font-medium">
        ← Back to Businesses
      </button>

      <div className="bg-white shadow rounded-lg p-6 border border-slate-200">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{business.name}</h1>
            <p className="text-slate-500 mt-1">Slug: {business.slug}</p>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
            business.status === 'ACTIVE' ? 'bg-green-100 text-green-800' :
            business.status === 'SUSPENDED' ? 'bg-yellow-100 text-yellow-800' :
            'bg-slate-100 text-slate-800'
          }`}>
            {business.status}
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-6 pt-6 border-t border-slate-200">
          <div>
            <div className="text-sm text-slate-500">Business Type</div>
            <div className="font-medium capitalize">{business.business_type}</div>
          </div>
          <div>
            <div className="text-sm text-slate-500">Owner</div>
            <div className="font-medium">{business.owner_name || business.owner_email}</div>
          </div>
          <div>
            <div className="text-sm text-slate-500">Members</div>
            <div className="font-medium">{business.membership_count}</div>
          </div>
          <div>
            <div className="text-sm text-slate-500">Branches</div>
            <div className="font-medium">{business.branch_count}</div>
          </div>
          <div>
            <div className="text-sm text-slate-500">Timezone</div>
            <div className="font-medium">{business.timezone}</div>
          </div>
          <div>
            <div className="text-sm text-slate-500">Locale</div>
            <div className="font-medium">{business.locale}</div>
          </div>
          <div>
            <div className="text-sm text-slate-500">Created</div>
            <div className="font-medium">{new Date(business.created_at).toLocaleDateString()}</div>
          </div>
          <div>
            <div className="text-sm text-slate-500">Subscription</div>
            <div className="font-medium capitalize">{business.subscription_status || 'N/A'}</div>
          </div>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg p-6 border border-slate-200">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Lifecycle Actions</h2>
        
        {actionError && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-md text-sm">{actionError}</div>
        )}
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Reason *</label>
            <input
              type="text"
              value={actionReason}
              onChange={(e) => setActionReason(e.target.value)}
              placeholder="Provide a reason for the action..."
              className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <div className="flex space-x-4">
            {business.status === 'ACTIVE' && (
              <>
                <button
                  onClick={() => handleAction('suspend')}
                  disabled={actionLoading || !actionReason}
                  className="px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 disabled:opacity-50"
                >
                  {actionLoading ? 'Processing...' : 'Suspend'}
                </button>
                <button
                  onClick={() => handleAction('archive')}
                  disabled={actionLoading || !actionReason}
                  className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                >
                  {actionLoading ? 'Processing...' : 'Archive'}
                </button>
              </>
            )}
            {business.status === 'SUSPENDED' && (
              <>
                <button
                  onClick={() => handleAction('activate')}
                  disabled={actionLoading || !actionReason}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
                >
                  {actionLoading ? 'Processing...' : 'Activate'}
                </button>
                <button
                  onClick={() => handleAction('archive')}
                  disabled={actionLoading || !actionReason}
                  className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                >
                  {actionLoading ? 'Processing...' : 'Archive'}
                </button>
              </>
            )}
            {business.status === 'ARCHIVED' && (
              <span className="text-sm text-slate-500 italic">Archived businesses cannot be restored in v1.</span>
            )}
          </div>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg p-6 border border-slate-200">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Members</h2>
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Email</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Name</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Role</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-slate-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {members.map((m) => (
              <tr key={m.id}>
                <td className="px-4 py-3 text-sm text-slate-900">{m.email}</td>
                <td className="px-4 py-3 text-sm text-slate-900">{m.full_name}</td>
                <td className="px-4 py-3 text-sm text-slate-900 font-medium">{m.role}</td>
                <td className="px-4 py-3 text-sm text-slate-900">{m.status}</td>
              </tr>
            ))}
            {members.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-slate-500">No members found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
