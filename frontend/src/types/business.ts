export type BusinessType =
  | 'hotel'
  | 'retail'
  | 'umkm'
  | 'restaurant'
  | 'service'
  | 'production'
  | 'garment'
  | 'distributor'
  | 'workshop'
  | 'salon';

export type BusinessStatus = 'active' | 'suspended' | 'archived';

export interface Business {
  id: string;
  owner_user_id: string;
  name: string;
  slug: string;
  description: string | null;
  business_type: BusinessType;
  status: BusinessStatus;
  timezone: string;
  locale: string;
  created_at: string;
  updated_at: string;
}

export interface CreateBusinessInput {
  name: string;
  description?: string;
  business_type: BusinessType;
  timezone: string;
  locale: string;
}

export interface UpdateBusinessInput {
  name?: string;
  description?: string | null;
  timezone?: string;
  locale?: string;
}

export interface BusinessApiResponse {
  success?: boolean;
  message?: string;
  errors?: string[];
  data?: Business | Business[];
}