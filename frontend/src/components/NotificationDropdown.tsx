import React, { useState, useEffect, useCallback } from 'react';
import type { Notification } from '../types/notification';
import { notificationApiClient } from '../services/notificationApiClient';


interface NotificationDropdownProps {
  scope: 'tenant' | 'platform';
  onReadUpdate: () => void;
  onClose: () => void;
}

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

export const NotificationDropdown: React.FC<NotificationDropdownProps> = ({ scope, onReadUpdate, onClose }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = scope === 'platform'
        ? await notificationApiClient.listPlatformNotifications(false, 20)
        : await notificationApiClient.listNotifications(false, 20);
      if (Array.isArray(data)) {
        setNotifications(data);
      } else {
        setNotifications([]);
      }
    } catch (err: any) {
      setError(err.message || 'Unable to load notifications.');
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  }, [scope]);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  const handleMarkRead = async (notificationId: string) => {
    try {
      if (scope === 'platform') {
        await notificationApiClient.markPlatformAsRead(notificationId);
      } else {
        await notificationApiClient.markAsRead(notificationId);
      }
      setNotifications(prev =>
        prev.map(n => n.id === notificationId ? { ...n, is_read: true, read_at: new Date().toISOString() } : n)
      );
      onReadUpdate();
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
      onReadUpdate();
    } catch {
      // Best effort
    }
  };

  const safeNotifications = Array.isArray(notifications) ? notifications : [];
  const unreadCount = safeNotifications.filter(n => !n.is_read).length;

  return (
    <div className="absolute right-0 mt-2 w-96 bg-white dark:bg-slate-900 rounded-lg shadow-xl border border-slate-200 dark:border-slate-700 z-50 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          Notifications {unreadCount > 0 && `(${unreadCount})`}
        </h3>
        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllRead}
            className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200"
          >
            Mark all read
          </button>
        )}
      </div>

      <div className="max-h-96 overflow-y-auto">
        {loading && (
          <div className="px-4 py-8 text-center text-sm text-slate-500">Loading notifications...</div>
        )}

        {error && (
          <div className="px-4 py-6 text-center">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            <button
              onClick={loadNotifications}
              className="mt-2 text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400"
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && safeNotifications.length === 0 && (
          <div className="px-4 py-8 text-center text-sm text-slate-500">No notifications</div>
        )}

        {!loading && !error && safeNotifications.map((n) => (
          <div
            key={n.id}
            className={`px-4 py-3 border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer transition-colors ${
              !n.is_read ? 'bg-blue-50/50 dark:bg-blue-950/20' : ''
            }`}
            onClick={() => {
              if (!n.is_read) handleMarkRead(n.id);
            }}
          >
            <div className="flex items-start gap-3">
              <div className={`flex-shrink-0 w-2 h-2 mt-2 rounded-full ${
                n.severity === 'CRITICAL' ? 'bg-red-500' :
                n.severity === 'WARNING' ? 'bg-yellow-500' : 'bg-blue-500'
              }`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <p className={`text-sm font-medium ${!n.is_read ? 'text-slate-900 dark:text-slate-100' : 'text-slate-600 dark:text-slate-400'}`}>
                    {n.title}
                  </p>
                  <span className="text-[10px] text-slate-400 dark:text-slate-500 whitespace-nowrap">
                    {timeAgo(n.created_at)}
                  </span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">
                  {n.message}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="px-4 py-2 border-t border-slate-200 dark:border-slate-700 text-center">
        <button
          onClick={onClose}
          className="text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
        >
          Close
        </button>
      </div>
    </div>
  );
};

export default NotificationDropdown;
