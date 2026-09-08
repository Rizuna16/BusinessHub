export type CategoryStatus = 'ACTIVE' | 'ARCHIVED';

export interface Category {
  id: string;
  business_id: string;
  name: string;
  code: string;
  description?: string | null;
  parent_id?: string | null;
  status: CategoryStatus;
  sort_order: number;
  created_at: string;
  updated_at: string;
  has_children: boolean;
}

export interface CategoryCreatePayload {
  name: string;
  code: string;
  description?: string | null;
  parent_id?: string | null;
  sort_order?: number;
}

export interface CategoryUpdatePayload {
  name?: string;
  code?: string;
  description?: string | null;
  parent_id?: string | null;
  sort_order?: number;
}
