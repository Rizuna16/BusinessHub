import type { PlatformRole } from './auth';

export type BusinessStatus = 'ACTIVE' | 'SUSPENDED' | 'ARCHIVED';
export type BusinessType = 'HOTEL' | 'RETAIL' | 'UMKM' | 'RESTAURANT' | 'SERVICE' | 'PRODUCTION' | 'GARMENT' | 'DISTRIBUTOR' | 'WORKSHOP' | 'SALON';

export interface PlatformDashboard {
  total_businesses: number;
  active_businesses: number;
  suspended_businesses: number;
  archived_businesses: number;
  total_accounts: number;
  active_subscriptions: number;
  expired_subscriptions: number;
  mrr_idr: number;
}

export interface PlatformUser {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  platform_role: PlatformRole | null;
  created_at: string;
  updated_at: string;
}

export interface PlatformBusiness {
  id: string;
  owner_user_id: string;
  owner_email: string | null;
  owner_name: string | null;
  name: string;
  slug: string;
  description: string | null;
  business_type: BusinessType;
  status: BusinessStatus;
  timezone: string;
  locale: string;
  membership_count: number;
  branch_count: number;
  created_at: string;
  updated_at: string;
  subscription_status: string | null;
  subscription_plan_name: string | null;
  subscription_current_period_end: string | null;
}

export interface PlatformBusinessMember {
  id: string;
  business_id: string;
  user_id: string;
  role: string;
  status: string;
  email: string | null;
  full_name: string | null;
  created_at: string;
  updated_at: string;
}

export type SubscriptionStatus = 'ACTIVE' | 'PAST_DUE' | 'EXPIRED' | 'CANCELLED' | 'SUSPENDED';
export type BillingInterval = 'MONTHLY' | 'YEARLY';

export interface SubscriptionPlan {
  id: string;
  code: string;
  name: string;
  description: string;
  price: string | number;
  currency: string;
  billing_interval: BillingInterval;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BillingPeriod {
  id: string;
  subscription_id: string;
  business_id: string;
  plan_id: string;
  plan_name_snapshot: string;
  period_start: string;
  period_end: string;
  price_snapshot: string | number;
  currency_snapshot: string;
  billing_interval_snapshot: BillingInterval;
  payment_status: 'PENDING' | 'PROCESSING' | 'PAID' | 'FAILED' | 'EXPIRED' | 'CANCELLED';
  payment_attempt_id: string | null;
  paid_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaymentAttempt {
  id: string;
  billing_period_id: string;
  subscription_id: string;
  business_id: string;
  amount: string | number;
  currency: string;
  provider: string;
  payment_reference: string | null;
  provider_order_id: string;
  provider_transaction_id: string | null;
  status: 'CREATED' | 'PENDING' | 'SUCCESS' | 'FAILED' | 'EXPIRED' | 'CANCELLED';
  failure_code: string | null;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
  paid_at: string | null;
  verification_note: string | null;
  verified_by: string | null;
  verified_at: string | null;
}

export interface PaymentAttemptResponse {
  id: string;
  billing_period_id: string;
  subscription_id: string;
  business_id: string;
  amount: string | number;
  currency: string;
  provider: string;
  provider_order_id: string;
  provider_transaction_id: string | null;
  payment_reference: string | null;
  status: string;
  failure_code: string | null;
  failure_reason: string | null;
  created_at: string;
  paid_at: string | null;
  verification_note: string | null;
  verified_by: string | null;
  verified_at: string | null;
}

export interface VerifyPaymentInput {
  payment_reference: string;
  verification_note: string;
}

export interface PlanCreateInput {
  name: string;
  description: string;
  price: string | number;
  currency: string;
  billing_interval: BillingInterval;
}

export interface PlanUpdateInput {
  name?: string;
  description?: string;
  price?: string | number;
  is_active?: boolean;
}

export interface SubscriptionOverrideInput {
  action: 'EXTEND' | 'SET_STATUS';
  extend_days?: number;
  status?: SubscriptionStatus;
  reason: string;
}

export interface PlatformSubscription {
  id: string;
  business_id: string;
  plan_id: string;
  plan_name: string;
  status: SubscriptionStatus;
  price: string | number;
  currency: string;
  billing_interval: BillingInterval;
  started_at: string;
  current_period_start: string;
  current_period_end: string;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlatformAuditLog {
  id: string;
  actor_account_id: string;
  actor_email: string;
  action: string;
  target_type: string;
  target_id: string;
  target_business_id: string | null;
  reason: string | null;
  before_state: Record<string, any> | null;
  after_state: Record<string, any> | null;
  result: string;
  metadata: Record<string, any> | null;
  created_at: string;
}

export interface BusinessActionInput {
  reason: string;
}

export interface AuditLogFilters {
  actor_id?: string;
  action?: string;
  target_type?: string;
  from_date?: string;
  to_date?: string;
}
