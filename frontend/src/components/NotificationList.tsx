import React, { useState, useEffect, useCallback } from 'react';
import type { Notification } from '../types/notification';
import { notificationApiClient } from '../services/notificationApiClient';

interface NotificationListProps {
  scope: 'tenant' | 'platform';
}

const severityColors: Record<string, string> = {
  INFO: 'bg-blue-100 text-blue-800',
  WARNING: 'bg-yellow-100 text-yellow-800',
  CRITICAL: 'bg-red-100 text-red-800',
};

function timeAgo(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export const NotificationList: React.FC<NotificationListProps> = ({ scope }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = scope === 'platform'
        ? await notificationApiClient.listPlatformNotifications(false, 100)
        : await notificationApiClient.listNotifications(false, 100);
      if (Array.isArray(data)) {
        setNotifications(data);
      } else {
        setNotifications([]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load notifications.');
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  }, [scope]);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  const handleMarkRead = async (id: string) => {
    try {
      if (scope === 'platform') {
        await notificationApiClient.markPlatformAsRead(id);
      } else {
        await notificationApiClient.markAsRead(id);
      }
      setNotifications(prev =>
        prev.map(n => n.id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n)
      );
    } catch {
      // Best effort
    }
  };

  const handleMarkAllRead = async () => {
    try {
      if (scope === 'platform') {
        await notificationApiClient.markPlatformAllRead();
      } else {
        await notificationApiClient.markAllRead();
      }
      setNotifications(prev =>
        prev.map(n => ({ ...n, is_read: true, read_at: n.read_at || new Date().toISOString() }))
      );
    } catch {
      // Best effort
    }
  };

  const safeNotifications = Array.isArray(notifications) ? notifications : [];
  const unreadCount = safeNotifications.filter(n => !n.is_read).length;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          Notifications {unreadCount > 0 && <span className="text-sm font-normal text-slate-500">({unreadCount} unread)</span>}
        </h1>
        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllRead}
            className="px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-800 border border-blue-200 rounded-md hover:bg-blue-50 dark:text-blue-400 dark:border-blue-800 dark:hover:bg-blue-950"
          >
            Mark all as read
          </button>
        )}
      </div>

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-400 rounded-md border border-red-200 dark:border-red-800">
          {error}
          <button onClick={loadNotifications} className="ml-2 underline text-sm">Retry</button>
        </div>
      )}

      {loading && (
        <div className="flex justify-center py-12 text-slate-500">Loading notifications...</div>
      )}

      {!loading && safeNotifications.length === 0 && !error && (
        <div className="text-center py-12 text-slate-500">No notifications</div>
      )}

      {!loading && safeNotifications.map((n) => (
        <div
          key={n.id}
          className={`bg-white dark:bg-slate-900 border rounded-lg p-4 cursor-pointer hover:shadow-sm transition-shadow ${
            !n.is_read
              ? 'border-blue-200 dark:border-blue-800 bg-blue-50/30 dark:bg-blue-950/10'
              : 'border-slate-200 dark:border-slate-700'
          }`}
          onClick={() => {
            if (!n.is_read) handleMarkRead(n.id);
          }}
        >
          <div className="flex items-start gap-3">
            <div className={`flex-shrink-0 w-3 h-3 mt-1 rounded-full ${
              n.severity === 'CRITICAL' ? 'bg-red-500' :
              n.severity === 'WARNING' ? 'bg-yellow-500' : 'bg-blue-500'
            }`} />
            <div className="flex-1">
              <div className="flex items-center justify-between gap-2">
                <h3 className={`text-sm font-semibold ${
                  !n.is_read ? 'text-slate-900 dark:text-slate-100' : 'text-slate-600 dark:text-slate-400'
                }`}>
                  {n.title}
                </h3>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${severityColors[n.severity] || 'bg-gray-100 text-gray-800'}`}>
                    {n.severity}
                  </span>
                  <span className="text-xs text-slate-400 dark:text-slate-500 whitespace-nowrap">
                    {timeAgo(n.created_at)}
                  </span>
                </div>
              </div>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{n.message}</p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">{n.type.replace(/_/g, ' ')}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default NotificationList;
