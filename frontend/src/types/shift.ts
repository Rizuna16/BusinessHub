export type ShiftStatus = 'OPEN' | 'CLOSED';

export interface CashierShift {
  id: string;
  business_id: string;
  branch_id: string;
  cashier_user_id: string;
  cash_account_id: string;
  opening_balance: number | string;
  actual_cash_count: number | string | null;
  discrepancy: number | string | null;
  status: ShiftStatus;
  opened_at: string;
  closed_at: string | null;
  closed_by_user_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  expected_cash?: number | string;
  cash_account_name?: string | null;
  branch_name?: string | null;
  cashier_name?: string | null;
}

export interface CashierShiftCreateInput {
  branch_id: string;
  cash_account_id: string;
  opening_balance?: number | string;
  notes?: string | null;
}

export interface CashierShiftCloseInput {
  actual_cash_count: number | string;
  notes?: string | null;
}

export interface CashierShiftForceCloseInput {
  notes: string;
}

export interface CashierShiftListResponse {
  items: CashierShift[];
  page: number;
  page_size: number;
  total: number;
}
