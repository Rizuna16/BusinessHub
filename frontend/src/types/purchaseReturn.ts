export type PurchaseReturnStatus = 'DRAFT' | 'FINALIZED' | 'CANCELLED';

export interface PurchaseReturnLineResponse {
  id: string;
  return_id: string;
  purchase_line_id: string;
  product_id: string;
  variant_id?: string | null;
  quantity: number | string;
  unit_price: number | string;
  discount_amount: number | string;
  tax_amount: number | string;
  line_subtotal: number | string;
  line_total: number | string;
  created_at: string;
  updated_at: string;
}

export interface PurchaseReturnResponse {
  id: string;
  business_id: string;
  purchase_id: string;
  inventory_location_id: string;
  return_number: string;
  status: PurchaseReturnStatus;
  notes?: string | null;
  subtotal: number | string;
  discount_total: number | string;
  tax_total: number | string;
  grand_total: number | string;
  created_by_user_id: string;
  finalized_by_user_id?: string | null;
  cancelled_by_user_id?: string | null;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  finalized_at?: string | null;
  cancelled_at?: string | null;
  lines: PurchaseReturnLineResponse[];
}

export interface PurchaseReturnListResponse {
  items: PurchaseReturnResponse[];
  page: number;
  page_size: number;
  total: number;
}

export interface PurchaseReturnCreateInput {
  purchase_id: string;
  inventory_location_id: string;
  notes?: string;
}

export interface PurchaseReturnUpdateInput {
  notes?: string;
}

export interface PurchaseReturnLineCreateInput {
  purchase_line_id: string;
  quantity: number;
  unit_price?: number;
  discount_amount?: number;
  tax_amount?: number;
}

export interface PurchaseReturnLineUpdateInput {
  quantity?: number;
  unit_price?: number;
  discount_amount?: number;
  tax_amount?: number;
}
