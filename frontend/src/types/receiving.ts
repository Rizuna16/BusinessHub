export type ReceivingStatus = 'DRAFT' | 'FINALIZED' | 'CANCELLED';

export interface ReceivingLineResponse {
  id: string;
  receiving_id: string;
  purchase_line_id: string;
  product_id: string;
  variant_id?: string | null;
  quantity: number | string;
  created_at: string;
  updated_at: string;
}

export interface ReceivingResponse {
  id: string;
  business_id: string;
  purchase_id: string;
  inventory_location_id: string;
  receiving_number: string;
  status: ReceivingStatus;
  notes?: string | null;
  created_by_user_id: string;
  finalized_by_user_id?: string | null;
  cancelled_by_user_id?: string | null;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  finalized_at?: string | null;
  cancelled_at?: string | null;
  lines: ReceivingLineResponse[];
}

export interface ReceivingListResponse {
  items: ReceivingResponse[];
  page: number;
  page_size: number;
  total: number;
}

export interface ReceivingCreateInput {
  purchase_id: string;
  inventory_location_id: string;
  notes?: string;
}

export interface ReceivingUpdateInput {
  notes?: string;
}

export interface ReceivingLineCreateInput {
  purchase_line_id: string;
  quantity: number;
}

export interface ReceivingLineUpdateInput {
  quantity: number;
}
