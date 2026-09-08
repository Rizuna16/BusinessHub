export type CustomerType = 'INDIVIDUAL' | 'ORGANIZATION';
export type CustomerStatus = 'ACTIVE' | 'INACTIVE' | 'ARCHIVED';

export interface Customer {
  id: string;
  business_id: string;
  customer_type: CustomerType;
  code: string;
  name: string;
  legal_name?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  city?: string | null;
  province?: string | null;
  postal_code?: string | null;
  country?: string | null;
  notes?: string | null;
  status: CustomerStatus;
  created_at: string;
  updated_at: string;
}

export interface CustomerCreatePayload {
  customer_type: CustomerType;
  name: string;
  legal_name?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  city?: string | null;
  province?: string | null;
  postal_code?: string | null;
  country?: string | null;
  notes?: string | null;
}

export interface CustomerUpdatePayload {
  customer_type?: CustomerType;
  name?: string;
  legal_name?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  city?: string | null;
  province?: string | null;
  postal_code?: string | null;
  country?: string | null;
  notes?: string | null;
}

export interface CustomerListResponse {
  items: Customer[];
  page: number;
  page_size: number;
  total: number;
}
