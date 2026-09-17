import React, { useEffect, useState } from 'react';
import type { PlatformAuditLog } from '../../types/platform';
import { platformApiClient } from '../../services/platformApiClient';

export const PlatformAuditLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<PlatformAuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');
  const [targetTypeFilter, setTargetTypeFilter] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await platformApiClient.listAuditLogs({
        action: actionFilter || undefined,
        target_type: targetTypeFilter || undefined,
      });
      setLogs(data);
    } catch (err: any) {
      console.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [actionFilter, targetTypeFilter]);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Audit Logs</h1>

      <div className="flex space-x-4">
        <input
          type="text"
          placeholder="Filter by action (e.g. BUSINESS_SUSPENDED)..."
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="flex-1 px-4 py-2 border border-slate-300 rounded-md"
        />
        <input
          type="text"
          placeholder="Filter by target type (e.g. BUSINESS)..."
          value={targetTypeFilter}
          onChange={(e) => setTargetTypeFilter(e.target.value)}
          className="flex-1 px-4 py-2 border border-slate-300 rounded-md"
        />
      </div>

      {loading ? (
        <div className="flex justify-center py-12 text-slate-500">Loading audit logs...</div>
      ) : (
        <div className="bg-white shadow rounded-lg overflow-hidden border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Timestamp</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Actor</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Action</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Target</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50">
                  <td className="px-4 py-4 whitespace-nowrap text-xs text-slate-500">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-slate-900">{log.actor_email}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm font-semibold text-slate-800">{log.action}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-slate-600">
                    {log.target_type} ({log.target_id.substring(0, 8)}...)
                  </td>
                  <td className="px-4 py-4 text-sm text-slate-600 max-w-xs truncate">{log.reason || '—'}</td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-500">No audit logs found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
