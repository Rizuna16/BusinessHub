export type SalesReturnStatus = 'DRAFT' | 'FINALIZED' | 'CANCELLED';

export interface SalesReturnLineResponse {
  id: string;
  sales_return_id: string;
  sales_line_id: string;
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

export interface SalesReturnResponse {
  id: string;
  business_id: string;
  sales_id: string;
  inventory_location_id: string;
  return_number: string;
  return_date: string;
  status: SalesReturnStatus;
  notes?: string | null;
  subtotal: number | string;
  discount_total: number | string;
  tax_total: number | string;
  grand_total: number | string;
  created_by_user_id: string;
  finalized_by_user_id?: string | null;
  cancelled_by_user_id?: string | null;
  created_at: string;
  updated_at: string;
  finalized_at?: string | null;
  cancelled_at?: string | null;
  lines: SalesReturnLineResponse[];
}

export interface SalesReturnListResponse {
  items: SalesReturnResponse[];
  page: number;
  page_size: number;
  total: number;
}

export interface SalesReturnCreateInput {
  sales_id: string;
  inventory_location_id?: string;
  notes?: string;
}

export interface SalesReturnUpdateInput {
  notes?: string;
}

export interface SalesReturnLineCreateInput {
  sales_line_id: string;
  quantity: number;
}

export interface SalesReturnLineUpdateInput {
  quantity: number;
}
