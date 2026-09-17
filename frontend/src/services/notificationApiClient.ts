import type { Notification, UnreadCountResponse } from '../types/notification';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

class NotificationApiClient {
  private getToken(): string | null {
    return localStorage.getItem('auth_token');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const errorMessage = data.message || data.detail || (data.errors && data.errors[0]) || 'Notification API error occurred';
      throw new Error(errorMessage);
    }

    return (data.data !== undefined ? data.data : data) as T;
  }

  public async listNotifications(unreadOnly: boolean = false, limit: number = 50): Promise<Notification[]> {
    const params = new URLSearchParams();
    if (unreadOnly) params.set('unread_only', 'true');
    if (limit !== 50) params.set('limit', String(limit));
    const qs = params.toString();
    return this.request<Notification[]>(`/notifications${qs ? `?${qs}` : ''}`);
  }

  public async listPlatformNotifications(unreadOnly: boolean = false, limit: number = 50): Promise<Notification[]> {
    const params = new URLSearchParams();
    if (unreadOnly) params.set('unread_only', 'true');
    if (limit !== 50) params.set('limit', String(limit));
    const qs = params.toString();
    return this.request<Notification[]>(`/notifications/platform${qs ? `?${qs}` : ''}`);
  }

  public async getUnreadCount(): Promise<UnreadCountResponse> {
    return this.request<UnreadCountResponse>('/notifications/unread-count');
  }

  public async getPlatformUnreadCount(): Promise<UnreadCountResponse> {
    return this.request<UnreadCountResponse>('/notifications/platform/unread-count');
  }

  public async markAsRead(notificationId: string): Promise<Notification> {
    return this.request<Notification>(`/notifications/${notificationId}/read`, {
      method: 'POST',
    });
  }

  public async markPlatformAsRead(notificationId: string): Promise<Notification> {
    return this.request<Notification>(`/notifications/platform/${notificationId}/read`, {
      method: 'POST',
    });
  }

  public async markAllRead(): Promise<{ marked_read: number }> {
    return this.request<{ marked_read: number }>('/notifications/read-all', {
      method: 'POST',
    });
  }

  public async markPlatformAllRead(): Promise<{ marked_read: number }> {
    return this.request<{ marked_read: number }>('/notifications/platform/read-all', {
      method: 'POST',
    });
  }
}

export const notificationApiClient = new NotificationApiClient();
