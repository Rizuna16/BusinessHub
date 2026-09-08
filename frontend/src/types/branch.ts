export type BranchStatus = 'ACTIVE' | 'SUSPENDED' | 'ARCHIVED';

export interface Branch {
  id: string;
  business_id: string;
  name: string;
  code: string;
  description: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  timezone: string;
  locale: string;
  status: BranchStatus;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface BranchCreatePayload {
  name: string;
  code: string;
  description?: string;
  address?: string;
  phone?: string;
  email?: string;
  timezone?: string;
  locale?: string;
}

export interface BranchUpdatePayload {
  name?: string;
  code?: string;
  description?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  timezone?: string;
  locale?: string;
}
