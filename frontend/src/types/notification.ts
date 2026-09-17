export type NotificationScope = 'TENANT' | 'PLATFORM';
export type NotificationSeverity = 'INFO' | 'WARNING' | 'CRITICAL';
export type NotificationType =
  | 'SUBSCRIPTION_RENEWAL_REMINDER'
  | 'PAYMENT_VERIFICATION_REQUIRED'
  | 'PAYMENT_VERIFIED'
  | 'STOCK_LOW';

export interface Notification {
  id: string;
  recipient_id: string;
  business_id: string | null;
  scope: NotificationScope;
  type: NotificationType;
  severity: NotificationSeverity;
  title: string;
  message: string;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
  metadata: Record<string, any> | null;
}

export interface UnreadCountResponse {
  count: number;
}
