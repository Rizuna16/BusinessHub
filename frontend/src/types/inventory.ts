export type MovementType =
  | 'OPENING_BALANCE'
  | 'ADJUSTMENT_IN'
  | 'ADJUSTMENT_OUT'
  | 'TRANSFER_IN'
  | 'TRANSFER_OUT';

export type MovementStatus = 'POSTED';

export type MovementDirection = 'IN' | 'OUT';

export type ReferenceType = 'OPENING_BALANCE' | 'ADJUSTMENT' | 'TRANSFER';

export interface StockBalance {
  id: string;
  business_id: string;
  inventory_location_id: string;
  product_id: string;
  variant_id: string | null;
  quantity: string;
  created_at: string;
  updated_at: string;
}

export interface StockMovementLine {
  id: string;
  movement_id: string;
  inventory_location_id: string;
  product_id: string;
  variant_id: string | null;
  quantity: string;
  direction: MovementDirection;
  created_at: string;
}

export interface StockMovement {
  id: string;
  business_id: string;
  movement_type: MovementType;
  reference_type: ReferenceType | null;
  reference_id: string | null;
  notes: string | null;
  performed_by_user_id: string;
  status: MovementStatus;
  created_at: string;
  lines: StockMovementLine[];
}

export interface OpeningBalancePayload {
  inventory_location_id: string;
  product_id: string;
  variant_id?: string | null;
  quantity: number | string;
  unit_cost?: number | string;
  notes?: string;
}

export interface AdjustmentPayload {
  inventory_location_id: string;
  product_id: string;
  variant_id?: string | null;
  quantity: number | string;
  notes?: string;
}

export interface TransferPayload {
  source_inventory_location_id: string;
  destination_inventory_location_id: string;
  product_id: string;
  variant_id?: string | null;
  quantity: number | string;
  notes?: string;
}

export interface TotalStockResponse {
  product_id: string;
  product_name: string;
  variant_id: string | null;
  variant_name: string | null;
  total_quantity: string;
}

export interface ValuationSummaryItem {
  product_id: string;
  product_name: string | null;
  variant_id: string | null;
  variant_name: string | null;
  total_quantity: string;
  unit_cost: string;
  total_cost: string;
}

export interface ValuationSummaryResponse {
  items: ValuationSummaryItem[];
  total_inventory_value: string;
}
