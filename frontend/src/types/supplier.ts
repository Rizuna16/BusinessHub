export type SupplierType = 'INDIVIDUAL' | 'ORGANIZATION';
export type SupplierStatus = 'ACTIVE' | 'INACTIVE' | 'ARCHIVED';

export interface Supplier {
  id: string;
  business_id: string;
  supplier_type: SupplierType;
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
  status: SupplierStatus;
  created_at: string;
  updated_at: string;
}

export interface SupplierCreatePayload {
  supplier_type: SupplierType;
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

export interface SupplierUpdatePayload {
  supplier_type?: SupplierType;
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

export interface SupplierListResponse {
  items: Supplier[];
  page: number;
  page_size: number;
  total: number;
}
