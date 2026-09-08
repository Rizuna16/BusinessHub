export type StockOpnameStatus = 'DRAFT' | 'FINALIZED';

export interface StockOpnameLine {
  id: string;
  product_id: string;
  variant_id: string | null;
  system_quantity: string;
  counted_quantity: string | null;
  variance: string | null;
}

export interface StockOpname {
  id: string;
  business_id: string;
  inventory_location_id: string;
  status: StockOpnameStatus;
  notes: string | null;
  created_by_user_id: string;
  finalized_by_user_id: string | null;
  created_at: string;
  updated_at: string;
  finalized_at: string | null;
  lines: StockOpnameLine[];
}

export interface StockOpnameLineCounts {
  system_quantity: string;
  counted_quantity: string;
  variance: string;
}

export interface StockOpnameCreatePayload {
  inventory_location_id: string;
  notes?: string | null;
}

export interface StockOpnameLineCreatePayload {
  product_id: string;
  variant_id?: string | null;
}

export interface StockOpnameLineUpdatePayload {
  counted_quantity: string;
}