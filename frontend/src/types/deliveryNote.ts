export type DeliveryNoteStatus = 'DRAFT' | 'READY' | 'DELIVERED' | 'CANCELLED';

export interface DeliveryNoteLine {
  id: string;
  delivery_note_id: string;
  sales_order_line_id: string;
  product_id: string;
  variant_id: string | null;
  product_name_snapshot: string;
  variant_snapshot: string | null;
  ordered_quantity_snapshot: string;
  fulfilled_quantity_snapshot: string;
  delivery_quantity: string;
  unit: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface DeliveryNote {
  id: string;
  business_id: string;
  branch_id: string;
  delivery_number: string;
  sales_order_id: string;
  customer_id: string | null;
  delivery_date: string;
  status: string;
  shipping_address: string | null;
  recipient_name: string | null;
  recipient_phone: string | null;
  notes: string | null;
  created_by_user_id: string;
  ready_by_user_id: string | null;
  ready_at: string | null;
  delivered_by_user_id: string | null;
  delivered_at: string | null;
  cancelled_by_user_id: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
  lines: DeliveryNoteLine[];
}

export interface DeliveryNoteListResponse {
  items: DeliveryNote[];
  page: number;
  page_size: number;
  total: number;
}

export interface DeliveryNoteCreatePayload {
  sales_order_id: string;
  branch_id: string;
  customer_id?: string | null;
  delivery_date: string;
  shipping_address?: string | null;
  recipient_name?: string | null;
  recipient_phone?: string | null;
  notes?: string | null;
  lines: DeliveryNoteLineCreatePayload[];
}

export interface DeliveryNoteLineCreatePayload {
  sales_order_line_id: string;
  delivery_quantity: string;
  notes?: string | null;
}

export interface DeliveryNoteUpdatePayload {
  delivery_date?: string | null;
  shipping_address?: string | null;
  recipient_name?: string | null;
  recipient_phone?: string | null;
  notes?: string | null;
}
